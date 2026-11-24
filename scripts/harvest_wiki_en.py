#!/usr/bin/env python3
"""
Harvest English Fallout Wiki articles for all matched entities in public/data/graph.json
and public/data/details.json using:
  1. RU -> EN langlinks on fallout.fandom.com/ru/api.php
  2. Direct title lookups on fallout.fandom.com/api.php for remaining notable entities
  3. Clean English wikitext parsing (lead, sections, quotes, transcripts)

Outputs:
  - /tmp/f3_encyclopedia_en/wiki_en_cache.json
  - /tmp/f3_encyclopedia_en/wiki_en_by_node.json
"""

from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = REPO_ROOT / "public" / "data" / "graph.json"
DETAILS_PATH = REPO_ROOT / "public" / "data" / "details.json"

OUT_DIR = Path("/tmp/f3_encyclopedia_en")
CACHE_PATH = OUT_DIR / "wiki_en_cache.json"
OUT_BY_NODE_PATH = OUT_DIR / "wiki_en_by_node.json"

RU_API = "https://fallout.fandom.com/ru/api.php"
EN_API = "https://fallout.fandom.com/api.php"
EN_WIKI_BASE = "https://fallout.fandom.com/wiki/"
USER_AGENT = "Fallout3GraphEncyclopediaEN/1.0"

REQUEST_DELAY = 0.12
MAX_RETRIES = 4
BATCH_SIZE = 45

SKIP_HEADINGS_EN = {
    "gallery",
    "behind the scenes",
    "appearances",
    "bugs",
    "sounds",
    "references",
    "notes",
    "see also",
    "external links",
    "videos",
    "audio",
    "base id",
    "editor id",
    "related perks",
    "fallout: new vegas",
    "fallout new vegas",
    "fallout 4",
    "fallout 76",
    "fallout shelter",
    "fallout tactics",
    "fallout 2",
    "fallout",
}

OTHER_GAME_SECTION_PREFIXES = (
    "fallout: new vegas",
    "fallout new vegas",
    "fallout 4",
    "fallout 76",
    "fallout shelter",
    "fallout tactics",
    "fallout 2",
    "fallout 1",
    "van buren",
)

FO3_GAME_CODES = {"fo3", "oa", "tp", "bs", "pl", "mz", "fallout 3"}
INTERWIKI_RE = re.compile(r"^[a-z]{2,3}(?:-[a-z0-9]{2,5})?:", re.IGNORECASE)
HAS_CYRILLIC = re.compile(r"[А-Яа-яЁё]")


class WikiSession:
    def __init__(self, cache_path: Path = CACHE_PATH) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.cache_path = cache_path
        self.last_ts = 0.0
        self.cache: dict[str, Any] = {
            "ru_to_en": {},       # ru_title -> en_title or ""
            "en_normalized": {},  # from -> to
            "en_redirects": {},   # from -> to
            "en_pages": {},       # title -> {title, missing, categories, wikitext}
        }
        if cache_path.exists():
            try:
                loaded = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    for k in self.cache:
                        if k in loaded and isinstance(loaded[k], dict):
                            self.cache[k].update(loaded[k])
            except Exception as exc:
                print(f"[warn] failed to load cache: {exc}", file=sys.stderr)

    def save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.cache_path)

    def _pace(self) -> None:
        dt = time.monotonic() - self.last_ts
        if dt < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - dt)

    def req(self, url: str, params: dict[str, Any], method: str = "GET") -> dict[str, Any]:
        for attempt in range(MAX_RETRIES + 1):
            self._pace()
            try:
                if method == "POST":
                    resp = self.session.post(url, data=params, timeout=30)
                else:
                    resp = self.session.get(url, params=params, timeout=30)
                self.last_ts = time.monotonic()
                if resp.status_code == 429 or resp.status_code >= 500:
                    wait = 1.5 * (2**attempt)
                    if attempt < MAX_RETRIES:
                        time.sleep(wait)
                        continue
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as exc:
                self.last_ts = time.monotonic()
                if attempt >= MAX_RETRIES:
                    print(f"[warn] API failed after retries: {exc}", file=sys.stderr)
                    return {}
                time.sleep(1.5 * (2**attempt))
        return {}

    def fetch_ru_langlinks(self, ru_titles: list[str]) -> None:
        todo = [t for t in dict.fromkeys(ru_titles) if t and "|" not in t and t not in self.cache["ru_to_en"]]
        if not todo:
            return
        total_b = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"[langlinks] querying {len(todo)} RU wiki titles in {total_b} batches...", flush=True)
        for i in range(0, len(todo), BATCH_SIZE):
            batch = todo[i : i + BATCH_SIZE]
            bnum = i // BATCH_SIZE + 1
            data = self.req(
                RU_API,
                {
                    "action": "query",
                    "prop": "langlinks",
                    "lllang": "en",
                    "lllimit": "max",
                    "redirects": 1,
                    "titles": "|".join(batch),
                    "format": "json",
                },
                method="POST",
            )
            q = data.get("query", {})
            norm_map = {x["from"]: x["to"] for x in q.get("normalized", [])}
            redir_map = {x["from"]: x["to"] for x in q.get("redirects", [])}

            title_to_en: dict[str, str] = {}
            for page in q.get("pages", {}).values():
                pt = page.get("title", "")
                lls = page.get("langlinks", [])
                en_t = ""
                for ll in lls:
                    if ll.get("lang") == "en" and ll.get("*"):
                        en_t = ll["*"]
                        break
                if pt:
                    title_to_en[pt] = en_t

            for orig in batch:
                cur = norm_map.get(orig, orig)
                seen = set()
                while cur in redir_map and cur not in seen:
                    seen.add(cur)
                    cur = redir_map[cur]
                self.cache["ru_to_en"][orig] = title_to_en.get(cur, "")

            if bnum % 10 == 0 or bnum == total_b:
                print(f"[langlinks] {bnum}/{total_b} saved", flush=True)
                self.save()

    def resolve_en_title(self, t: str) -> str:
        cur = t
        seen = set()
        while cur not in seen:
            seen.add(cur)
            if cur in self.cache["en_normalized"]:
                cur = self.cache["en_normalized"][cur]
                continue
            if cur in self.cache["en_redirects"]:
                cur = self.cache["en_redirects"][cur]
                continue
            break
        return cur

    def fetch_en_pages(self, titles: list[str]) -> None:
        todo: list[str] = []
        seen_t: set[str] = set()
        for t in titles:
            if not t or "|" in t:
                continue
            rt = self.resolve_en_title(t)
            if rt in self.cache["en_pages"] or t in self.cache["en_pages"]:
                continue
            if t not in seen_t:
                seen_t.add(t)
                todo.append(t)
        if not todo:
            return

        total_b = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"[en-wiki] fetching {len(todo)} EN pages in {total_b} batches...", flush=True)
        for i in range(0, len(todo), BATCH_SIZE):
            batch = todo[i : i + BATCH_SIZE]
            bnum = i // BATCH_SIZE + 1
            data = self.req(
                EN_API,
                {
                    "action": "query",
                    "prop": "revisions|categories",
                    "titles": "|".join(batch),
                    "rvprop": "content",
                    "rvslots": "main",
                    "cllimit": "max",
                    "redirects": 1,
                    "format": "json",
                },
                method="POST",
            )
            q = data.get("query", {})
            for x in q.get("normalized", []):
                self.cache["en_normalized"][x["from"]] = x["to"]
            for x in q.get("redirects", []):
                self.cache["en_redirects"][x["from"]] = x["to"]

            for page in q.get("pages", {}).values():
                pt = page.get("title", "")
                if not pt or page.get("ns", 0) != 0:
                    continue
                if "missing" in page:
                    self.cache["en_pages"][pt] = {"title": pt, "missing": True}
                    continue
                cats = [c["title"] for c in page.get("categories", []) if "title" in c]
                revs = page.get("revisions", [])
                wt = ""
                if revs:
                    wt = revs[0].get("slots", {}).get("main", {}).get("*", "")
                self.cache["en_pages"][pt] = {
                    "title": pt,
                    "missing": False,
                    "categories": cats,
                    "wikitext": wt,
                }
            for orig in batch:
                rt = self.resolve_en_title(orig)
                if rt not in self.cache["en_pages"]:
                    self.cache["en_pages"][rt] = {"title": rt, "missing": True}

            if bnum % 10 == 0 or bnum == total_b:
                print(f"[en-wiki] {bnum}/{total_b} saved ({len(self.cache['en_pages'])} cached)", flush=True)
                self.save()


# ---------------------------------------------------------------------------
# English Wikitext Cleaning & Parsing
# ---------------------------------------------------------------------------

def split_template_args(inner: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    bd = kd = 0
    i = 0
    n = len(inner)
    while i < n:
        c2 = inner[i : i + 2]
        if c2 == "{{":
            bd += 1
            buf.append(c2)
            i += 2
        elif c2 == "}}":
            bd = max(0, bd - 1)
            buf.append(c2)
            i += 2
        elif c2 == "[[":
            kd += 1
            buf.append(c2)
            i += 2
        elif c2 == "]]":
            kd = max(0, kd - 1)
            buf.append(c2)
            i += 2
        elif inner[i] == "|" and bd == 0 and kd == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(inner[i])
            i += 1
    parts.append("".join(buf))
    return parts


def parse_template_parts(inner: str) -> tuple[str, list[str], dict[str, str]]:
    parts = split_template_args(inner)
    name = parts[0].strip() if parts else ""
    pos: list[str] = []
    named: dict[str, str] = {}
    for part in parts[1:]:
        eq_idx = -1
        bd = kd = 0
        for j, ch in enumerate(part):
            if part[j : j + 2] == "{{":
                bd += 1
            elif part[j : j + 2] == "}}":
                bd = max(0, bd - 1)
            elif part[j : j + 2] == "[[":
                kd += 1
            elif part[j : j + 2] == "]]":
                kd = max(0, kd - 1)
            elif ch == "=" and bd == 0 and kd == 0:
                eq_idx = j
                break
        if eq_idx != -1:
            named[part[:eq_idx].strip().lower()] = part[eq_idx + 1 :].strip()
        else:
            pos.append(part.strip())
    return name, pos, named


def strip_wiki_tables(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    depth = 0
    while i < n:
        c2 = text[i : i + 2]
        if c2 == "{|":
            depth += 1
            i += 2
        elif c2 == "|}" and depth > 0:
            depth -= 1
            i += 2
        else:
            if depth == 0:
                out.append(text[i])
            i += 1
    return "".join(out)


def render_inline_template_en(raw_inner: str) -> str:
    name, pos, named = parse_template_parts(raw_inner)
    tn = re.sub(r"\s+", " ", name.lower().replace("_", " ")).strip()
    if not tn:
        return ""
    if tn in ("tooltip", "nobr", "nowrap", "small", "big", "sic", "verify", "lang"):
        txt = pos[-1] if pos else named.get("1", "")
        return expand_templates_en(txt).strip()
    if tn in ("color",):
        txt = pos[1] if len(pos) >= 2 else (pos[0] if pos else "")
        return expand_templates_en(txt).strip()
    if tn in ("quote", "cquote"):
        qt = named.get("text") or named.get("quote") or named.get("1") or (pos[0] if pos else "")
        au = named.get("author") or named.get("2") or (pos[1] if len(pos) >= 2 else "")
        qt = expand_templates_en(qt).strip()
        au = expand_templates_en(au).strip()
        if not qt:
            return ""
        return f'"{qt}" — {au}\n\n' if au else f'"{qt}"\n\n'
    if tn in ("transcript", "holotape", "note"):
        if "name" in named or "base_id" in named or "editor_id" in named:
            return ""
        txt = named.get("text") or named.get("1") or (pos[0] if pos else "")
        txt = expand_templates_en(txt).strip()
        return f"{txt}\n" if txt else ""
    if tn in ("icon", "fo3icon", "special"):
        return expand_templates_en(pos[0]).strip() if pos else ""
    if tn in ("·", "•"):
        return " • "
    if tn in ("mdash", "---"):
        return " — "
    if tn in ("ndash", "--"):
        return " – "
    if tn == "=":
        return "="
    if tn == "!":
        return "|"
    return ""


def expand_templates_en(text: str) -> str:
    if "{{" not in text:
        return text
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i : i + 2] == "{{":
            if text[i : i + 3] == "{{{":
                end = text.find("}}}", i + 3)
                if end != -1:
                    i = end + 3
                    continue
            depth = 1
            start = i + 2
            j = i + 2
            closed = False
            while j < n and depth > 0:
                if text[j : j + 2] == "{{":
                    depth += 1
                    j += 2
                elif text[j : j + 2] == "}}":
                    depth -= 1
                    if depth == 0:
                        out.append(render_inline_template_en(text[start:j]))
                        i = j + 2
                        closed = True
                        break
                    j += 2
                else:
                    j += 1
            if not closed:
                i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _resolve_wikilink(inner: str) -> str:
    s = inner.strip()
    if not s:
        return ""
    low = s.lstrip(":").lower()
    if low.startswith(("file:", "image:", "media:", "category:")):
        return ""
    if INTERWIKI_RE.match(low):
        return ""
    if "|" in s:
        target, display = s.split("|", 1)
        display = clean_wikilinks(display).strip()
        if display:
            return display
        s = target.strip()
    if "#" in s:
        base, frag = s.split("#", 1)
        s = base.strip() or frag.strip()
    return s.lstrip(":")


def clean_wikilinks(text: str) -> str:
    if "[[" not in text:
        return text
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i : i + 2] == "[[":
            depth = 1
            start = i + 2
            j = i + 2
            closed = False
            while j < n and depth > 0:
                if text[j : j + 2] == "[[":
                    depth += 1
                    j += 2
                elif text[j : j + 2] == "]]":
                    depth -= 1
                    if depth == 0:
                        out.append(_resolve_wikilink(text[start:j]))
                        i = j + 2
                        closed = True
                        break
                    j += 2
                else:
                    j += 1
            if not closed:
                i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def clean_tabber_blocks(text: str) -> str:
    if "<tabber" not in text.lower():
        return text
    def _repl(m: re.Match[str]) -> str:
        tabs = re.split(r"\|-\|", m.group(1))
        kept = []
        for tab in tabs:
            body = tab.split("=", 1)[1] if "=" in tab else tab
            t2 = re.sub(r"</?[a-zA-Z][^>]*>", "", strip_wiki_tables(expand_templates_en(body))).strip()
            if t2:
                kept.append(body.strip())
        return "\n\n".join(kept)
    return re.sub(r"<tabber\b[^>]*>(.*?)</tabber>", _repl, text, flags=re.DOTALL | re.IGNORECASE)


def clean_wikitext_en(raw: str) -> str:
    text = raw
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<ref\b[^>]*>.*?</ref>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<ref\b[^>]*/\s*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<gallery\b[^>]*>.*?</gallery>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = clean_tabber_blocks(text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = expand_templates_en(text)
    text = strip_wiki_tables(text)
    if "{{" in text:
        text = expand_templates_en(text)
    text = clean_wikilinks(text)
    text = re.sub(r"\[https?://[^\s\]]+\s+([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[https?://[^\s\]]+\]", "", text)
    text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)
    text = re.sub(r"(?m)^\s*\|-\|\s*[^=\n]*=\s*$", "", text)
    text = re.sub(r"__(?:TOC|NOTOC|FORCETOC|NOEDITSECTION|HIDDENCAT|NEWSECTIONLINK)__", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[\u200b\u200e\u200f\ufeff]", "", text)
    text = re.sub(r"'{2,5}", "", text)
    text = text.replace("{{", "").replace("}}", "").replace("[[", "").replace("]]", "")
    text = text.replace("{|", "").replace("|}", "")
    text = re.sub(r"<ref\b[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\(\s*[,;:\-–—]*\s*\)", "", text)
    text = re.sub(r"\[\s*\]", "", text)

    lines: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]{2,}", " ", line).strip()
        if not line:
            lines.append("")
            continue
        if re.match(r"^\*+\s*$", line) or re.match(r"^[:;#]+\s*$", line):
            continue
        line = re.sub(r"^\*+\s*", "• ", line)
        line = re.sub(r"^#+\s*", "- ", line)
        line = re.sub(r"^[:;]+\s*", "", line)
        if re.match(r"^[,.;:•\-–—]+$", line):
            continue
        line = re.sub(r"\s+([,.;:!?])", r"\1", line)
        lines.append(line)
    res = "\n".join(lines)
    res = re.sub(r"\n{3,}", "\n\n", res).strip()
    return res


def extract_quotes_and_sections(wikitext: str) -> tuple[str, list[dict[str, str]], list[str]]:
    clean_raw = re.sub(r"<!--.*?-->", "", wikitext, flags=re.DOTALL)
    heading_re = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$", re.MULTILINE)
    matches = list(heading_re.finditer(clean_raw))

    quotes: list[str] = []
    # Extract top-level {{Quote|...}}
    for m in re.finditer(r"\{\{(?:quote|cquote)\|([^}]+)\}\}", clean_raw, re.IGNORECASE):
        qt_clean = clean_wikitext_en("{{" + m.group(0)[2:-2] + "}}").strip()
        if 15 <= len(qt_clean) <= 280 and qt_clean not in quotes:
            quotes.append(qt_clean)
            if len(quotes) >= 5:
                break

    if not matches:
        return clean_wikitext_en(clean_raw), [], quotes

    lead = clean_wikitext_en(clean_raw[: matches[0].start()])
    sections: list[dict[str, str]] = []
    skip_until_level: int | None = None
    cur_h: str | None = None
    cur_chunks: list[str] = []

    def flush() -> None:
        nonlocal cur_h, cur_chunks
        if cur_h is not None:
            body = "\n\n".join(c for c in cur_chunks if c).strip()
            if body:
                sections.append({"heading": cur_h, "text": body})
        cur_h = None
        cur_chunks = []

    for idx, m in enumerate(matches):
        level = len(m.group(1))
        stitle = clean_wikitext_en(m.group(2)).strip()
        snorm = stitle.lower()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(clean_raw)
        chunk_raw = clean_raw[start:end]

        if skip_until_level is not None:
            if level > skip_until_level:
                continue
            skip_until_level = None

        if any(snorm == sk or snorm.startswith(sk + " ") or snorm.startswith(sk + ":") for sk in SKIP_HEADINGS_EN):
            if level == 2:
                flush()
            skip_until_level = level
            continue

        if any(snorm.startswith(p) for p in OTHER_GAME_SECTION_PREFIXES):
            if level == 2:
                flush()
            skip_until_level = level
            continue

        chunk_clean = clean_wikitext_en(chunk_raw)
        if snorm in ("quotes", "notable quotes") and chunk_clean and not quotes:
            for qline in chunk_clean.splitlines():
                ql = qline.lstrip("•- ").strip()
                if 15 <= len(ql) <= 280 and ql not in quotes:
                    quotes.append(ql)
                    if len(quotes) >= 5:
                        break
            if level == 2:
                flush()
            skip_until_level = level
            continue

        if level == 2:
            flush()
            cur_h = stitle
            if chunk_clean:
                cur_chunks.append(chunk_clean)
        else:
            if cur_h is None:
                cur_h = stitle
                if chunk_clean:
                    cur_chunks.append(chunk_clean)
            elif chunk_clean:
                cur_chunks.append(f"{stitle}:\n{chunk_clean}" if stitle else chunk_clean)

    flush()
    return lead, sections, quotes


def is_fo3_page(page: dict[str, Any]) -> bool:
    if not page or page.get("missing"):
        return False
    cats = " ".join(page.get("categories", [])).lower()
    wt = page.get("wikitext", "")[:3500].lower()
    if any(k in cats for k in ("disambiguation", "fallout: new vegas", "fallout 4", "fallout 76")) and "fallout 3" not in cats:
        return False
    if any(k in cats for k in ("fallout 3", "broken steel", "point lookout", "the pitt", "mothership zeta", "operation: anchorage", "capital wasteland", "megaton", "rivet city", "citadel", "vault 101", "tenpenny tower", "paradise falls")):
        return True
    if "{{games|fo3" in wt or "game=fo3" in wt or "games = fo3" in wt or "|fo3" in wt:
        return True
    return False


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    details = json.loads(DETAILS_PATH.read_text(encoding="utf-8"))

    ws = WikiSession()

    # 1. Extract RU wiki titles from details.json wikiUrl
    ru_title_by_nid: dict[str, str] = {}
    for nid, det in details.items():
        wurl = det.get("wikiUrl", "")
        if "/ru/wiki/" in wurl:
            raw_t = wurl.split("/ru/wiki/", 1)[1].split("#", 1)[0]
            ru_title = urllib.parse.unquote(raw_t).replace("_", " ").strip()
            if ru_title:
                ru_title_by_nid[nid] = ru_title

    print(f"Found {len(ru_title_by_nid)} nodes with RU wikiUrl ({len(set(ru_title_by_nid.values()))} unique RU titles).")
    ws.fetch_ru_langlinks(list(ru_title_by_nid.values()))

    # Map nodes that resolved via RU -> EN langlink
    node_en_title: dict[str, str] = {}
    missing_nodes: list[dict[str, Any]] = []
    for n in graph["nodes"]:
        nid = n["id"]
        ru_t = ru_title_by_nid.get(nid)
        en_t = ws.cache["ru_to_en"].get(ru_t, "") if ru_t else ""
        if en_t:
            node_en_title[nid] = en_t
        else:
            missing_nodes.append(n)

    print(f"Resolved via RU->EN langlinks: {len(node_en_title)} nodes; missing: {len(missing_nodes)}.")

    # 2. For missing non-generic nodes (excluding DC sectors, presets, random encounters, test NPCs),
    # try direct English title + "(Fallout 3)" on fallout.fandom.com/api.php
    fallback_candidates: dict[str, list[str]] = {}
    all_en_queries: list[str] = list(node_en_title.values())
    for n in missing_nodes:
        nid = n["id"]
        lbl = n.get("labelEn", "").strip()
        if not lbl or len(lbl) < 3:
            continue
        if n["type"] == "event":
            continue
        if lbl.startswith(("DC Ruins Sector", "Appearance Preset:", "Pitt Test", "Zeta Test", "Voice Actor")):
            continue
        cands = [lbl, f"{lbl} (Fallout 3)"]
        fallback_candidates[nid] = cands
        all_en_queries.extend(cands)

    ws.fetch_en_pages(all_en_queries)
    ws.save()

    # 3. Build clean parsed wiki entries per node
    out_by_node: dict[str, dict[str, Any]] = {}
    for n in graph["nodes"]:
        nid = n["id"]
        chosen_title = node_en_title.get(nid)
        page = None
        if chosen_title:
            rt = ws.resolve_en_title(chosen_title)
            cand_page = ws.cache["en_pages"].get(rt)
            if cand_page and not cand_page.get("missing"):
                page = cand_page
        else:
            for cand in fallback_candidates.get(nid, []):
                rt = ws.resolve_en_title(cand)
                cand_page = ws.cache["en_pages"].get(rt)
                if cand_page and is_fo3_page(cand_page):
                    page = cand_page
                    break

        if not page or not page.get("wikitext"):
            continue

        lead, sections, quotes = extract_quotes_and_sections(page["wikitext"])
        # Ensure zero Cyrillic
        if HAS_CYRILLIC.search(lead):
            lead = HAS_CYRILLIC.sub("", lead).strip()
        clean_secs = []
        for s in sections:
            h = s["heading"]
            t = s["text"]
            if HAS_CYRILLIC.search(h) or HAS_CYRILLIC.search(t):
                continue
            if len(t) >= 25:
                clean_secs.append({"heading": h, "text": t})
        clean_quotes = [q for q in quotes if not HAS_CYRILLIC.search(q)]

        if not lead and not clean_secs:
            continue

        url_slug = urllib.parse.quote(page["title"].replace(" ", "_"), safe="():,'!-")
        out_by_node[nid] = {
            "title": page["title"],
            "url": f"{EN_WIKI_BASE}{url_slug}",
            "lead": lead,
            "sections": clean_secs,
            "quotes": clean_quotes,
        }

    OUT_BY_NODE_PATH.write_text(json.dumps(out_by_node, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(out_by_node)} parsed English Wiki entries to {OUT_BY_NODE_PATH}")


if __name__ == "__main__":
    main()
