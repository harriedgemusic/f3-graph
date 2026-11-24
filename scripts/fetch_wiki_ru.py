#!/usr/bin/env python3
"""Harvest Russian Fallout 3 encyclopedia lore from fallout.fandom.com/ru/api.php
and match conservatively to public/data/graph.json nodes.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

import requests

API_URL = "https://fallout.fandom.com/ru/api.php"
WIKI_BASE_URL = "https://fallout.fandom.com/ru/wiki/"
USER_AGENT = "Fallout3GraphEncyclopedia/1.0"
BATCH_SIZE = 40
REQUEST_DELAY = 0.18
MAX_RETRIES = 4

GRAPH_PATH = Path("/Users/harriedgemusic/Documents/repos/f3-graph/public/data/graph.json")
OUT_DIR = Path("/tmp/f3_encyclopedia")
CACHE_PATH = OUT_DIR / "wiki_cache.json"
OUT_PATH = OUT_DIR / "wiki_ru.json"

ROOT_CATEGORIES = [
    "Категория:Персонажи Fallout 3",
    "Категория:Оружие Fallout 3",
    "Категория:Локации Fallout 3",
    "Категория:Существа Fallout 3",
    "Категория:Броня и одежда Fallout 3",
    "Категория:Предметы Fallout 3",
    "Категория:Квесты Fallout 3",
    "Категория:Способности Fallout 3",
    "Категория:Игровые объекты Fallout 3",
    "Категория:Случайные встречи Fallout 3",
]

DLC_CATEGORY_TARGETS = {
    "operation: anchorage",
    "the pitt",
    "broken steel",
    "point lookout",
    "mothership zeta",
}

SKIP_SUBCAT_SUBSTRS = (
    "изображения",
    "звуки",
    "видео",
    "диалоговые файлы",
    "актёры озвучивания",
    "актеры озвучивания",
    "разработчики",
    "игровые файлы",
    "достижения и трофеи",
    "баги",
    "проблемные статьи",
    "карты локаций",
    "патчи",
    "публикации",
    "песни",
    "тестовые",
    "упоминаем",
    "шаблоны",
    "участники",
    "обсуждени",
)

SKIP_SECTION_HEADINGS = {
    "галерея",
    "за кулисами",
    "появление",
    "появления",
    "см. также",
    "баги",
    "известные баги",
    "ошибки",
    "примечания",
    "источники",
    "ссылки",
    "внешние ссылки",
    "видео",
    "звуки",
    "аудио",
    "base id",
    "editor id",
}

MAINTENANCE_CAT_PREFIXES = (
    "статьи к доработке",
    "неэнциклопедичные статьи",
    "статьи с незавершёнными",
    "статьи с незавершенными",
    "статьи с ошибками перевода",
    "статьи с пасхальными яйцами",
    "проблемные статьи",
    "страницы",
    "неоднозначности",
    "корневые статьи",
    "обзорные статьи",
)

PARENTHETICAL_QUALIFIERS = {
    "fallout 3",
    "fallout",
    "broken steel",
    "point lookout",
    "operation: anchorage",
    "the pitt",
    "mothership zeta",
    "квест",
    "персонаж",
    "существо",
    "локация",
    "оружие",
    "броня",
    "одежда",
    "головной убор",
    "способность",
    "предмет",
    "книга",
    "заметка",
    "ключ",
    "голодиск",
    "терминал",
    "химикат",
    "боеприпас",
    "револьвер",
    "нож",
    "приёмник",
    "приемник",
    "контейнер",
    "пистолет",
    "винтовка",
    "ружьё",
    "ружье",
}

DISQUALIFYING_PARENS = {
    "организация",
    "радиостанция",
    "достижение",
    "компания",
    "серия игр",
    "содружество",
    "фракция",
    "журнал",
}

LANG_NAMES_RU = {
    "en": "англ.",
    "fr": "фр.",
    "de": "нем.",
    "es": "исп.",
    "la": "лат.",
    "zh": "кит.",
    "ja": "яп.",
    "it": "итал.",
    "pl": "польск.",
    "uk": "укр.",
}

INLINE_TEXT_TEMPLATES = {
    "lang",
    "lang-en",
    "подсказка",
    "tooltip",
    "nobr",
    "nowrap",
    "small",
    "big",
    "color",
    "цвет",
    "в тексте",
    "перевод",
    "нп3",
    "нп5",
    "iw",
    "цитата",
    "quote",
    "заметка",
    "письмо",
    "дневник",
    "·",
    "•",
    "ndash",
    "mdash",
    "--",
    "---",
    "=",
    "!",
}

FO3_GAME_CODES = {"fo3", "oa", "tp", "bs", "pl", "mz", "fallout 3"}

INTERWIKI_RE = re.compile(r"^[a-z]{2,3}(?:-[a-z0-9]{2,5})?:", re.IGNORECASE)


class WikiClient:
    """Polite batched MediaWiki API client with caching and retry handling."""

    def __init__(self, cache_path: Path = CACHE_PATH) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.cache_path = cache_path
        self.last_request_ts = 0.0
        self.cache: dict[str, Any] = {
            "discovered_dlcs": [],
            "category_walk_done": False,
            "category_pages": {},
            "pages": {},
            "redirects": {},
            "normalized": {},
        }
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.cache.update(loaded)
            except Exception as exc:
                print(f"[warn] failed to load cache: {exc}", file=sys.stderr)

    def save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False)
        tmp.replace(self.cache_path)

    def _pace(self) -> None:
        elapsed = time.monotonic() - self.last_request_ts
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)

    def request(self, params: dict[str, Any], method: str = "GET") -> dict[str, Any]:
        """Execute a polite MediaWiki API call with retry and backoff."""
        for attempt in range(MAX_RETRIES + 1):
            self._pace()
            try:
                if method == "POST":
                    resp = self.session.post(API_URL, data=params, timeout=30)
                else:
                    resp = self.session.get(API_URL, params=params, timeout=30)
                self.last_request_ts = time.monotonic()
                if resp.status_code == 429 or resp.status_code >= 500:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after and retry_after.isdigit() else (1.5 * (2**attempt))
                    if attempt < MAX_RETRIES:
                        time.sleep(wait)
                        continue
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as exc:
                self.last_request_ts = time.monotonic()
                if attempt >= MAX_RETRIES:
                    raise RuntimeError(f"API request failed after {MAX_RETRIES + 1} attempts: {exc}") from exc
                time.sleep(1.5 * (2**attempt))
        return {}

    def get_category_members(self, cat_title: str, cmtype: str = "page|subcat") -> list[dict[str, Any]]:
        """Enumerate members of a single category handling cmcontinue."""
        members: list[dict[str, Any]] = []
        params: dict[str, Any] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": cat_title,
            "cmtype": cmtype,
            "cmnamespace": "0|14",
            "cmlimit": "max",
            "format": "json",
        }
        while True:
            data = self.request(params, method="GET")
            members.extend(data.get("query", {}).get("categorymembers", []))
            cont = data.get("continue", {}).get("cmcontinue")
            if not cont:
                break
            params["cmcontinue"] = cont
        return members

    def discover_dlc_categories(self) -> list[str]:
        """Discover the 5 Fallout 3 DLC categories under Категория:Fallout 3."""
        if self.cache.get("discovered_dlcs"):
            return list(self.cache["discovered_dlcs"])

        found: set[str] = set()
        top_subcats = self.get_category_members("Категория:Fallout 3", cmtype="subcat")
        for m in top_subcats:
            title = m.get("title", "")
            short = title.replace("Категория:", "").strip().lower()
            if short in DLC_CATEGORY_TARGETS:
                found.add(title)
            elif "дополнени" in short:
                for m2 in self.get_category_members(title, cmtype="subcat"):
                    t2 = m2.get("title", "")
                    if t2.replace("Категория:", "").strip().lower() in DLC_CATEGORY_TARGETS:
                        found.add(t2)

        dlcs = sorted(found)
        self.cache["discovered_dlcs"] = dlcs
        self.save_cache()
        return dlcs

    def walk_categories(self, max_depth: int = 2) -> dict[str, list[str]]:
        """BFS walk of Fallout 3 categories up to max_depth (depth 3 for weapon/armor subcats)."""
        if self.cache.get("category_walk_done") and self.cache.get("category_pages"):
            if not self.cache.get("dlc_depth3_done"):
                self._supplement_dlc_weapon_armor_subcats()
            return self.cache["category_pages"]

        dlcs = self.discover_dlc_categories()
        roots = list(dict.fromkeys(ROOT_CATEGORIES + dlcs))
        visited_cats: set[str] = set(roots)
        cat_pages: dict[str, set[str]] = defaultdict(set)

        queue: deque[tuple[str, int]] = deque((r, 0) for r in roots)
        processed = 0

        print(f"[cats] starting BFS from {len(roots)} roots (DLCs: {dlcs})", flush=True)
        while queue:
            cat, depth = queue.popleft()
            cat_low = cat.lower()
            allow_deep = depth < max_depth or (
                depth == max_depth
                and any(k in cat_low for k in ("оружие", "броня", "одежда", "уникальн"))
            )
            cmtype = "page|subcat" if allow_deep else "page"
            try:
                members = self.get_category_members(cat, cmtype=cmtype)
            except Exception as exc:
                print(f"[warn] category failed {cat}: {exc}", file=sys.stderr)
                continue
            processed += 1
            for m in members:
                ns = m.get("ns")
                title = m.get("title", "")
                if not title:
                    continue
                if ns == 0:
                    cat_pages[title].add(cat)
                elif ns == 14 and allow_deep:
                    low = title.lower()
                    if any(s in low for s in SKIP_SUBCAT_SUBSTRS):
                        continue
                    if title not in visited_cats:
                        visited_cats.add(title)
                        queue.append((title, depth + 1))

            if processed % 30 == 0:
                print(
                    f"[cats] visited={processed}, queue={len(queue)}, unique_pages={len(cat_pages)}",
                    flush=True,
                )

        serialized = {k: sorted(v) for k, v in cat_pages.items()}
        self.cache["category_pages"] = serialized
        self.cache["category_walk_done"] = True
        self.cache["dlc_depth3_done"] = True
        self.save_cache()
        print(f"[cats] done: {processed} categories walked, {len(serialized)} unique pages", flush=True)
        return serialized

    def _supplement_dlc_weapon_armor_subcats(self) -> None:
        """Fetch depth-3 DLC weapon/armor subcategories when upgrading existing cache."""
        seeds = [
            "Категория:Уникальное оружие The Pitt",
            "Категория:Уникальное оружие Point Lookout",
            "Категория:Уникальное оружие Broken Steel",
            "Категория:Оружие Broken Steel",
            "Категория:Оружие Point Lookout",
            "Категория:Оружие The Pitt",
            "Категория:Оружие Mothership Zeta",
            "Категория:Оружие Operation: Anchorage",
            "Категория:Броня и одежда The Pitt",
            "Категория:Броня и одежда Point Lookout",
            "Категория:Броня и одежда Broken Steel",
        ]
        cat_pages: dict[str, list[str]] = self.cache.get("category_pages", {})
        visited: set[str] = set(seeds)
        q: deque[tuple[str, int]] = deque((s, 0) for s in seeds)
        added = 0
        while q:
            cat, d = q.popleft()
            try:
                members = self.get_category_members(cat, cmtype="page|subcat" if d < 2 else "page")
            except Exception:
                continue
            for m in members:
                ns, t = m.get("ns"), m.get("title", "")
                if not t:
                    continue
                if ns == 0:
                    if t not in cat_pages:
                        cat_pages[t] = [cat]
                        added += 1
                    elif cat not in cat_pages[t]:
                        cat_pages[t].append(cat)
                elif ns == 14 and d < 2 and not any(s in t.lower() for s in SKIP_SUBCAT_SUBSTRS):
                    if t not in visited:
                        visited.add(t)
                        q.append((t, d + 1))
        self.cache["category_pages"] = cat_pages
        self.cache["dlc_depth3_done"] = True
        self.save_cache()
        print(f"[cats] supplemented DLC depth-3 weapon/armor subcats (+{added} pages)", flush=True)

    def resolve_title(self, title: str) -> str:
        """Resolve MediaWiki normalization and redirect chain in cache."""
        cur = title
        seen = set()
        while cur not in seen:
            seen.add(cur)
            if cur in self.cache["normalized"]:
                cur = self.cache["normalized"][cur]
                continue
            if cur in self.cache["redirects"]:
                cur = self.cache["redirects"][cur]
                continue
            break
        return cur

    def fetch_pages_batch(self, titles: list[str], mark_missing: bool = True) -> None:
        """Fetch full wikitext and categories in batches of BATCH_SIZE (40)."""
        todo: list[str] = []
        seen_todo: set[str] = set()
        for t in titles:
            if not t or "|" in t:
                continue
            resolved = self.resolve_title(t)
            if resolved in self.cache["pages"] or t in self.cache["pages"]:
                continue
            if t not in seen_todo:
                seen_todo.add(t)
                todo.append(t)

        if not todo:
            return

        total_batches = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"[fetch] fetching {len(todo)} titles in {total_batches} batches...", flush=True)

        for idx in range(0, len(todo), BATCH_SIZE):
            batch = todo[idx : idx + BATCH_SIZE]
            batch_num = idx // BATCH_SIZE + 1
            try:
                data = self.request(
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
            except Exception as exc:
                print(f"[warn] batch {batch_num}/{total_batches} failed: {exc}", file=sys.stderr)
                continue

            query = data.get("query", {})
            for item in query.get("normalized", []):
                self.cache["normalized"][item["from"]] = item["to"]
            for item in query.get("redirects", []):
                self.cache["redirects"][item["from"]] = item["to"]

            for page in query.get("pages", {}).values():
                ptitle = page.get("title", "")
                if not ptitle or page.get("ns", 0) != 0:
                    continue
                if "missing" in page:
                    if mark_missing:
                        self.cache["pages"][ptitle] = {"title": ptitle, "missing": True}
                    continue
                cats = [c["title"] for c in page.get("categories", []) if "title" in c]
                revs = page.get("revisions", [])
                wikitext = ""
                if revs:
                    slots = revs[0].get("slots", {})
                    wikitext = slots.get("main", {}).get("*", "")
                self.cache["pages"][ptitle] = {
                    "title": ptitle,
                    "missing": False,
                    "categories": cats,
                    "wikitext": wikitext,
                }

            # Mark any unresolved queried title that didn't map to an existing page
            if mark_missing:
                for t in batch:
                    rt = self.resolve_title(t)
                    if rt not in self.cache["pages"]:
                        self.cache["pages"][rt] = {"title": rt, "missing": True}

            if batch_num % 10 == 0 or batch_num == total_batches:
                print(f"[fetch] batch {batch_num}/{total_batches} saved ({len(self.cache['pages'])} cached)", flush=True)
                self.save_cache()


# ---------------------------------------------------------------------------
# Balanced Wikitext Parsing & Cleaning
# ---------------------------------------------------------------------------


def iter_top_level_templates(text: str) -> list[str]:
    """Return raw inner contents of top-level {{...}} templates."""
    templates: list[str] = []
    i = 0
    n = len(text)
    while i < n - 1:
        if text[i : i + 2] == "{{":
            # Skip triple-brace parameter syntax {{{...}}} if present
            depth = 1
            start = i + 2
            i += 2
            while i < n and depth > 0:
                if text[i : i + 2] == "{{":
                    depth += 1
                    i += 2
                elif text[i : i + 2] == "}}":
                    depth -= 1
                    if depth == 0:
                        templates.append(text[start:i])
                        i += 2
                        break
                    i += 2
                else:
                    i += 1
        else:
            i += 1
    return templates


def split_template_args(inner: str) -> list[str]:
    """Split template body on top-level '|' ignoring nested {{...}} and [[...]]."""
    parts: list[str] = []
    buf: list[str] = []
    brace_depth = 0
    bracket_depth = 0
    i = 0
    n = len(inner)
    while i < n:
        ch2 = inner[i : i + 2]
        if ch2 == "{{":
            brace_depth += 1
            buf.append(ch2)
            i += 2
        elif ch2 == "}}":
            brace_depth = max(0, brace_depth - 1)
            buf.append(ch2)
            i += 2
        elif ch2 == "[[":
            bracket_depth += 1
            buf.append(ch2)
            i += 2
        elif ch2 == "]]":
            bracket_depth = max(0, bracket_depth - 1)
            buf.append(ch2)
            i += 2
        elif inner[i] == "|" and brace_depth == 0 and bracket_depth == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(inner[i])
            i += 1
    parts.append("".join(buf))
    return parts


def parse_template_parts(inner: str) -> tuple[str, list[str], dict[str, str]]:
    """Parse template name, positional args, and named args."""
    parts = split_template_args(inner)
    name = parts[0].strip() if parts else ""
    pos: list[str] = []
    named: dict[str, str] = {}
    for part in parts[1:]:
        # Only treat '=' as key=value if '=' isn't inside nested templates/links
        eq_idx = -1
        bd = 0
        kd = 0
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
            k = part[:eq_idx].strip().lower()
            v = part[eq_idx + 1 :].strip()
            named[k] = v
        else:
            pos.append(part.strip())
    return name, pos, named


def strip_wiki_tables(text: str) -> str:
    """Strip balanced {| ... |} wiki tables."""
    out: list[str] = []
    i = 0
    n = len(text)
    depth = 0
    while i < n:
        ch2 = text[i : i + 2]
        if ch2 == "{|":
            depth += 1
            i += 2
        elif ch2 == "|}" and depth > 0:
            depth -= 1
            i += 2
        else:
            if depth == 0:
                out.append(text[i])
            i += 1
    return "".join(out)


def render_inline_template(raw_inner: str) -> str:
    """Render safe inline templates to readable text, or strip infoboxes/meta."""
    name, pos, named = parse_template_parts(raw_inner)
    tname = re.sub(r"\s+", " ", name.lower().replace("_", " ")).strip()
    if not tname:
        return ""

    if tname in ("lang", "lang-en"):
        if tname == "lang-en":
            txt = named.get("1") or (pos[0] if pos else "")
            txt = expand_templates(txt).strip()
            return f"англ. {txt}" if txt else ""
        lang_code = (pos[0] if len(pos) >= 2 else "en").lower()
        txt = pos[1] if len(pos) >= 2 else (pos[0] if pos else named.get("text", ""))
        txt = expand_templates(txt).strip()
        if not txt:
            return ""
        prefix = LANG_NAMES_RU.get(lang_code, "")
        return f"{prefix} {txt}".strip() if prefix else txt

    if tname in ("подсказка", "tooltip"):
        txt = pos[0] if pos else named.get("1", "")
        return expand_templates(txt).strip()

    if tname in ("nobr", "nowrap", "small", "big", "в тексте", "перевод", "опечатка"):
        txt = pos[0] if pos else named.get("1", "")
        return expand_templates(txt).strip()

    if tname in ("color", "цвет"):
        txt = pos[1] if len(pos) >= 2 else (pos[0] if pos else "")
        return expand_templates(txt).strip()

    if tname in ("нп3", "нп5", "iw"):
        disp = pos[1] if len(pos) >= 2 and pos[1] else (pos[0] if pos else "")
        return expand_templates(disp).strip()

    if tname in ("цитата", "quote"):
        qtext = named.get("текст") or named.get("text") or named.get("1") or (pos[0] if pos else "")
        author = named.get("автор") or named.get("author") or named.get("2") or (pos[1] if len(pos) >= 2 else "")
        qtext = expand_templates(qtext).strip()
        author = expand_templates(author).strip()
        if not qtext:
            return ""
        if author:
            return f"«{qtext}» — {author}\n\n"
        return f"«{qtext}»\n\n"

    if tname in ("заметка", "письмо", "дневник"):
        # Skip if it looks like an infobox rather than a readable note box
        if "название" in named or "base_id" in named or "editor_id" in named:
            return ""
        txt = named.get("текст") or named.get("text") or named.get("1") or (pos[0] if pos else "")
        txt = expand_templates(txt).strip()
        return f"{txt}\n" if txt else ""

    if tname in ("·", "•"):
        return " • "
    if tname in ("mdash", "---"):
        return " — "
    if tname in ("ndash", "--"):
        return " – "
    if tname == "=":
        return "="
    if tname == "!":
        return "|"

    # All other templates (infoboxes, navboxes, icons, IDs, banners) are stripped
    return ""


def expand_templates(text: str) -> str:
    """Walk text and strip/expand balanced {{...}} templates."""
    if "{{" not in text:
        return text
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i : i + 2] == "{{":
            # Check for {{{param|default}}} just in case
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
                        inner = text[start:j]
                        out.append(render_inline_template(inner))
                        i = j + 2
                        closed = True
                        break
                    j += 2
                else:
                    j += 1
            if not closed:
                # Unclosed template brace; drop remainder of broken tag start
                i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def clean_wikilinks(text: str) -> str:
    """Resolve [[Target|Display]] -> Display, [[Target]] -> Target,
    and strip files/categories/interwiki links using balanced bracket tracking.
    """
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
                        inner = text[start:j]
                        out.append(_resolve_wikilink(inner))
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
    if low.startswith(("файл:", "file:", "изображение:", "image:", "медиа:", "media:", "категория:", "category:")):
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


def clean_tabber_blocks(text: str) -> str:
    """Clean <tabber>...</tabber> blocks so empty infobox/ID tabs disappear cleanly."""
    if "<tabber" not in text.lower():
        return text

    def _repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        tabs = re.split(r"\|-\|", inner)
        kept: list[str] = []
        for tab in tabs:
            if "=" in tab:
                _, body = tab.split("=", 1)
            else:
                body = tab
            body_no_tmpl = strip_wiki_tables(expand_templates(body))
            body_no_html = re.sub(r"</?[a-zA-Z][^>]*>", "", body_no_tmpl).strip()
            if body_no_html:
                kept.append(body.strip())
        return "\n\n".join(kept)

    return re.sub(r"<tabber\b[^>]*>(.*?)</tabber>", _repl, text, flags=re.DOTALL | re.IGNORECASE)


def clean_wikitext_block(raw: str) -> str:
    """Clean a block of wikitext (lead or section body) into readable Russian prose."""
    text = raw
    # 1. Strip comments, <ref>, <gallery>
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<ref\b[^>]*>.*?</ref>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<ref\b[^>]*/\s*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<gallery\b[^>]*>.*?</gallery>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # 2. Clean <tabber> blocks (dropping empty infobox/BaseID tabs)
    text = clean_tabber_blocks(text)
    # 3. Convert <br> to newlines before stripping HTML tags
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    # 4. Expand/strip balanced templates, then strip balanced tables
    text = expand_templates(text)
    text = strip_wiki_tables(text)
    # Second pass in case a template revealed/wrapped another
    if "{{" in text:
        text = expand_templates(text)
    # 5. Resolve wikilinks and strip images/categories/interwikis
    text = clean_wikilinks(text)
    # 6. External links [https://... label] -> label, bare [https://...] -> ""
    text = re.sub(r"\[https?://[^\s\]]+\s+([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[https?://[^\s\]]+\]", "", text)
    # 7. Strip remaining HTML tags, stray tabber dividers & magic words
    text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)
    text = re.sub(r"(?m)^\s*\|-\|\s*[^=\n]*=\s*$", "", text)
    text = re.sub(r"__(?:TOC|NOTOC|FORCETOC|NOEDITSECTION|HIDDENCAT|NEWSECTIONLINK)__", "", text)
    # 7. Unescape HTML entities and normalize invisible chars
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\u200b\u200e\u200f\ufeff]", "", text)
    # 8. Strip MediaWiki bold/italic apostrophe runs (preserving single apostrophes)
    text = re.sub(r"'{2,5}", "", text)
    # 9. Final safety sweep against any stray unbalanced markup tokens
    text = text.replace("{{", "").replace("}}", "").replace("[[", "").replace("]]", "")
    text = text.replace("{|", "").replace("|}", "")
    text = re.sub(r"<ref\b[^>]*>", "", text, flags=re.IGNORECASE)
    # 10. Clean empty parentheses left behind by stripped inline icons/templates
    text = re.sub(r"\(\s*[,;:\-–—]*\s*\)", "", text)
    text = re.sub(r"\[\s*\]", "", text)

    # 11. Format lines cleanly
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]{2,}", " ", line).strip()
        if not line:
            cleaned_lines.append("")
            continue
        # Convert wiki bullets/indents cleanly
        if re.match(r"^\*+\s*$", line) or re.match(r"^[:;#]+\s*$", line):
            continue
        line = re.sub(r"^\*+\s*", "• ", line)
        line = re.sub(r"^#+\s*", "- ", line)
        line = re.sub(r"^[:;]+\s*", "", line)
        # Drop lines that ended up as lone punctuation
        if re.match(r"^[,.;:•\-–—]+$", line):
            continue
        line = re.sub(r"\s+([,.;:!?])", r"\1", line)
        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return result


def extract_lead_and_sections(wikitext: str) -> tuple[str, list[dict[str, str]]]:
    """Split wikitext by headings into clean lead and filtered relevant sections."""
    # Remove HTML comments first so commented headings aren't treated as sections
    clean_raw = re.sub(r"<!--.*?-->", "", wikitext, flags=re.DOTALL)
    heading_re = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$", re.MULTILINE)

    matches = list(heading_re.finditer(clean_raw))
    if not matches:
        return clean_wikitext_block(clean_raw), []

    lead_raw = clean_raw[: matches[0].start()]
    lead = clean_wikitext_block(lead_raw)

    sections: list[dict[str, str]] = []
    skip_until_level: int | None = None
    cur_l2_heading: str | None = None
    cur_l2_chunks: list[str] = []

    def flush_current() -> None:
        nonlocal cur_l2_heading, cur_l2_chunks
        if cur_l2_heading is not None:
            body = "\n\n".join(c for c in cur_l2_chunks if c).strip()
            if body:
                sections.append({"heading": cur_l2_heading, "text": body})
        cur_l2_heading = None
        cur_l2_chunks = []

    for idx, m in enumerate(matches):
        level = len(m.group(1))
        raw_title = m.group(2)
        sec_title = clean_wikitext_block(raw_title).strip()
        sec_title_norm = sec_title.lower().replace("ё", "е")

        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(clean_raw)
        chunk_raw = clean_raw[start:end]

        if skip_until_level is not None:
            if level > skip_until_level:
                continue
            skip_until_level = None

        if any(
            sec_title_norm == sk or sec_title_norm.startswith(sk + " ")
            for sk in SKIP_SECTION_HEADINGS
        ):
            if level == 2:
                flush_current()
            skip_until_level = level
            continue

        chunk_clean = clean_wikitext_block(chunk_raw)
        if level == 2:
            flush_current()
            cur_l2_heading = sec_title
            if chunk_clean:
                cur_l2_chunks.append(chunk_clean)
        else:
            if cur_l2_heading is None:
                cur_l2_heading = sec_title
                if chunk_clean:
                    cur_l2_chunks.append(chunk_clean)
            elif chunk_clean:
                if sec_title:
                    cur_l2_chunks.append(f"{sec_title}:\n{chunk_clean}")
                else:
                    cur_l2_chunks.append(chunk_clean)

    flush_current()
    return lead, sections


# ---------------------------------------------------------------------------
# Metadata Extraction, Normalization & Conservative Entity Matching
# ---------------------------------------------------------------------------


def extract_wiki_metadata(title: str, categories: list[str], wikitext: str) -> dict[str, Any]:
    """Extract infobox type, Fallout 3 relevance, base/editor IDs, and semantic types."""
    templates = iter_top_level_templates(wikitext)
    infobox_names: list[str] = []
    wiki_types: set[str] = set()
    fo3_relevant = False
    is_disambig = False
    is_cut_article = False
    hex_ids: set[str] = set()
    editor_ids: set[str] = set()
    infobox_titles: list[str] = []

    cat_lows = [c.lower() for c in categories]
    for cl in cat_lows:
        if any(k in cl for k in ("неоднозначност", "корневые статьи", "обзорные статьи")):
            is_disambig = True
        if "вырезан" in cl:
            is_cut_article = True
        if any(
            k in cl
            for k in (
                "fallout 3",
                "broken steel",
                "operation: anchorage",
                "point lookout",
                "the pitt",
                "mothership zeta",
                "столичн",
                "мегатонн",
                "ривет-сити",
                "цитадел",
                "убежище 101",
                "тенпенни-тауэр",
                "парадиз-фоллз",
                "олд-олни",
                "рэйвен-рок",
                "оазис",
                "арефу",
                "андейл",
                "гердершейд",
                "грейдич",
                "республики дэйва",
                "храм единения",
                "мемориал",
                "исторический музей",
                "кэпитал пост",
                "станция уоррингтон",
                "форт ",
                "завод «",
                "школа спрингвейла",
                "штаб-квартира регуляторов",
                "обитатели ",
                "безымянные персонажи",
                "компания «коготь»",
            )
        ):
            fo3_relevant = True

        # Category -> semantic types
        if "квесты" in cl:
            wiki_types.add("quest")
        if "способности" in cl:
            wiki_types.update(("object", "perk"))
        if any(k in cl for k in ("персонажи", "напарники", "обитатели", "люди", "гули", "супермутанты", "учёные", "ученые", "торговцы", "медики", "попрошайки воды")):
            wiki_types.update(("character", "npc"))
        if any(k in cl for k in ("существа", "когти смерти", "роботы", "компьютеры и роботы")):
            wiki_types.update(("character", "creature", "npc"))
        if any(k in cl for k in ("локации", "маркеры карты", "районы", "здания", "города", "магазины", "метро", "кратеры", "убежища")):
            wiki_types.add("location")
        if "оружие" in cl:
            wiki_types.update(("item", "weapon"))
        if any(k in cl for k in ("броня", "одежда", "головные уборы")):
            wiki_types.update(("item", "armor"))
        if "боеприпасы" in cl:
            wiki_types.update(("item", "ammo"))
        if "медпрепараты и еда" in cl:
            wiki_types.update(("item", "aid"))
        if "книги" in cl:
            wiki_types.update(("item", "book"))
        if "ключи" in cl:
            wiki_types.update(("item", "key"))
        if any(k in cl for k in ("заметки", "голодиски")):
            wiki_types.update(("item", "note"))
        if any(k in cl for k in ("разные предметы", "компоненты самодельного оружия", "квестовые предметы", "схемы")):
            wiki_types.update(("item", "misc"))
        if "терминалы" in cl:
            wiki_types.update(("object", "terminal"))
        if any(k in cl for k in ("активаторы", "ловушки", "контейнеры", "улучшения дома")):
            wiki_types.update(("object", "activator", "container"))
        if "игровые объекты" in cl:
            wiki_types.add("object")
        if "случайные встречи" in cl:
            wiki_types.add("event")

    for tmpl in templates:
        tname, pos, named = parse_template_parts(tmpl)
        tn = re.sub(r"\s+", " ", tname.lower().replace("_", " ")).strip()
        if not tn:
            continue
        if tn in ("неоднозначность", "корневая статья", "обзор введение", "обзоры"):
            is_disambig = True
        if tn in ("вырезанный контент-статья", "вырезанный контент"):
            is_cut_article = True
        if tn == "игры":
            for arg in pos:
                if arg.strip().lower() in FO3_GAME_CODES:
                    fo3_relevant = True
        for gkey in ("игра", "игра1", "игра2", "игра3"):
            if gkey in named and any(c in named[gkey].lower() for c in FO3_GAME_CODES):
                fo3_relevant = True

        # Infobox template names
        if tn in ("квест", "описание квеста"):
            wiki_types.add("quest")
            infobox_names.append(tn)
        elif tn in ("персонаж", "персонаж fo3"):
            wiki_types.update(("character", "npc"))
            infobox_names.append(tn)
        elif tn in ("робот", "робот fo3"):
            wiki_types.update(("character", "npc", "creature"))
            infobox_names.append(tn)
        elif tn in ("существо", "существо fo3"):
            wiki_types.update(("character", "creature"))
            infobox_names.append(tn)
        elif tn in ("локация", "локация fo3"):
            wiki_types.add("location")
            infobox_names.append(tn)
        elif tn in ("оружие", "оружие fo3"):
            wiki_types.update(("item", "weapon"))
            infobox_names.append(tn)
        elif tn in ("броня", "броня fo3", "одежда"):
            wiki_types.update(("item", "armor"))
            infobox_names.append(tn)
        elif tn in ("боеприпас", "боеприпасы"):
            wiki_types.update(("item", "ammo"))
            infobox_names.append(tn)
        elif tn in ("способность", "перк"):
            wiki_types.update(("object", "perk"))
            infobox_names.append(tn)
        elif tn in ("заметка", "голодиск") and ("название" in named or "base_id" in named or "editor_id" in named):
            wiki_types.update(("item", "note"))
            infobox_names.append(tn)
        elif tn == "терминал" and ("название" in named or "локация" in named or "base_id" in named):
            wiki_types.update(("object", "terminal"))
            infobox_names.append(tn)
        elif tn in ("объект", "игровой объект", "контейнер", "активатор"):
            wiki_types.update(("object", "activator", "container"))
            infobox_names.append(tn)
        elif tn in ("предмет", "разный предмет", "книга", "медпрепарат", "химпрепарат", "еда", "напиток", "ключ"):
            infobox_names.append(tn)
            wiki_types.add("item")
            tip = (named.get("тип", "") + " " + named.get("тип в ред.", "")).lower()
            if "ключ" in tip or "key" in tip or tn == "ключ":
                wiki_types.add("key")
            elif any(w in tip for w in ("заметка", "голодиск", "note")) or tn in ("заметка", "голодиск"):
                wiki_types.add("note")
            elif any(w in tip for w in ("книга", "журнал", "схема", "book")) or tn == "книга":
                wiki_types.add("book")
            elif any(w in tip for w in ("хим", "лекар", "мед", "еда", "напиток", "препарат", "ingestible", "aid")) or tn in ("медпрепарат", "химпрепарат", "еда", "напиток"):
                wiki_types.add("aid")
            else:
                wiki_types.add("misc")
        elif tn in ("организация", "радиостанция", "достижение"):
            wiki_types.add(tn)

        # Extract base_id / form_id / editor_id / title from infoboxes
        for k in ("название", "имя"):
            if k in named and named[k]:
                tclean = clean_wikitext_block(named[k])
                if tclean:
                    infobox_titles.append(tclean)

        for k in ("base_id", "base_id1", "form_id", "ref_id", "id"):
            if k in named and named[k]:
                for m in re.finditer(r"\{\{(?:DLC )?ID\|([0-9a-fA-F]+)\}\}", named[k], re.IGNORECASE):
                    hx = m.group(1).lstrip("0").lower()
                    if hx:
                        hex_ids.add(hx)
                for m in re.finditer(r"\b([0-9a-fA-F]{4,8})\b", named[k]):
                    hx = m.group(1).lstrip("0").lower()
                    if hx:
                        hex_ids.add(hx)

        for k in ("editor_id", "cell name"):
            if k in named and named[k]:
                ed = re.sub(r"'{2,5}|<[^>]+>", " ", named[k])
                for tok in re.findall(r"[A-Za-z0-9_]{3,}", ed):
                    editor_ids.add(tok.lower())

    # Title parenthetical qualifier refinement
    m_par = re.search(r"\s*\(([^()]+)\)\s*$", title)
    if m_par:
        p_low = m_par.group(1).strip().lower()
        if p_low in DISQUALIFYING_PARENS:
            wiki_types.add("non_graph_entity")
        elif p_low == "квест":
            wiki_types = {"quest"}
        elif p_low == "способность":
            wiki_types = {"object", "perk"}
        elif p_low == "локация":
            wiki_types = {"location"}
        elif p_low == "персонаж":
            wiki_types = {"character", "npc"}
        elif p_low == "существо":
            wiki_types = {"character", "creature"}
        elif p_low == "оружие":
            wiki_types = {"item", "weapon"}
        elif p_low in ("броня", "одежда", "головной убор"):
            wiki_types = {"item", "armor"}
        elif p_low == "книга":
            wiki_types = {"item", "book", "misc"}
        elif p_low in ("заметка", "голодиск"):
            wiki_types = {"item", "note"}
        elif p_low == "ключ":
            wiki_types = {"item", "key"}
        elif p_low == "терминал":
            wiki_types = {"object", "terminal"}
        elif p_low == "предмет":
            wiki_types.add("item")

    return {
        "wiki_types": wiki_types,
        "infobox_names": infobox_names,
        "fo3_relevant": fo3_relevant,
        "is_disambig": is_disambig,
        "is_cut_article": is_cut_article,
        "hex_ids": hex_ids,
        "editor_ids": editor_ids,
        "infobox_titles": infobox_titles,
    }


def norm_label(s: str, expand_abbrev: bool = False) -> str:
    """Normalize Russian/English label: lowercase, ё->е, …->..., strip quotes, unify dashes."""
    s = s.replace("\xa0", " ").replace("…", "...")
    s = re.sub(r"[\u200b\u200e\u200f\ufeff]", "", s)
    s = s.lower().replace("ё", "е")
    # Strip quotes
    s = re.sub(r'["\'«»„“”’‘`]', "", s)
    # Unify dashes
    s = re.sub(r"[—–−]", "-", s)
    if expand_abbrev:
        s = re.sub(r"\bд-ра\b", "доктора", s)
        s = re.sub(r"\bд-р\b", "доктор", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def strip_wiki_disambig_paren(title: str) -> str:
    """Strip known Fallout wiki disambiguation parentheses from a title."""
    m = re.search(r"\s*\(([^()]+)\)\s*$", title)
    if not m:
        return title
    inner = m.group(1).strip().lower()
    if inner in PARENTHETICAL_QUALIFIERS or any(q in inner for q in ("fallout 3", "квест", "локация", "оружие", "способность")):
        return title[: m.start()].strip()
    return title


def is_type_compatible(
    node: dict[str, Any], meta: dict[str, Any], exact_id_match: bool = False
) -> tuple[bool, int]:
    """Conservatively check if a graph node matches a wiki page's semantic type.
    Returns (compatible, compatibility_score).
    """
    if meta["is_disambig"] or not meta["fo3_relevant"]:
        return False, -1
    wtypes = meta["wiki_types"]
    if "non_graph_entity" in wtypes or not wtypes:
        return False, -1

    ntype = node["type"]
    subtype = node.get("subtype", "")

    if ntype == "quest":
        if "quest" not in wtypes:
            return False, -1
        return True, 20

    if ntype == "location":
        if "location" not in wtypes:
            return False, -1
        return True, 20

    if ntype == "event":
        if "event" not in wtypes:
            return False, -1
        return True, 20

    if ntype == "character":
        if not wtypes.intersection({"character", "npc", "creature"}):
            return False, -1
        score = 15
        if subtype == "npc" and "npc" in wtypes:
            score += 5
        elif subtype == "creature" and "creature" in wtypes:
            score += 5
        return True, score

    if ntype == "object":
        if subtype == "perk":
            if "perk" not in wtypes:
                return False, -1
            return True, 25
        if subtype == "terminal":
            if "terminal" not in wtypes:
                return False, -1
            return True, 20
        # activator, container, door
        if not wtypes.intersection({"object", "activator", "container"}):
            return False, -1
        if "perk" in wtypes:
            return False, -1
        return True, 15

    if ntype == "item":
        if "item" not in wtypes:
            return False, -1
        if subtype == "weapon":
            if "weapon" in wtypes:
                return True, 25
            return False, -1
        if subtype == "armor":
            if "armor" in wtypes:
                return True, 25
            if exact_id_match and "misc" in wtypes:
                return True, 20
            return False, -1
        if subtype == "ammo":
            if "ammo" in wtypes:
                return True, 25
            return False, -1
        if subtype == "aid":
            if "aid" in wtypes:
                return True, 25
            if "misc" in wtypes and not wtypes.intersection({"weapon", "armor", "ammo", "key", "note"}):
                return True, 10
            return False, -1
        if subtype == "book":
            if "book" in wtypes:
                return True, 25
            if "misc" in wtypes and not wtypes.intersection({"weapon", "armor", "ammo", "key", "note", "aid"}):
                return True, 12
            return False, -1
        if subtype == "key":
            if "key" in wtypes:
                return True, 25
            if "misc" in wtypes and not wtypes.intersection({"weapon", "armor", "ammo", "note", "aid", "book"}):
                return True, 10
            return False, -1
        if subtype == "note":
            if "note" in wtypes or "terminal" in wtypes:
                return True, 25
            if "misc" in wtypes and not wtypes.intersection({"weapon", "armor", "ammo", "key", "aid", "book"}):
                return True, 8
            return False, -1
        if subtype == "misc":
            # Misc can match misc or book (e.g. Survival Guide misc item)
            if wtypes.intersection({"weapon", "armor", "ammo", "key", "note"}):
                return False, -1
            if "misc" in wtypes:
                return True, 20
            if "book" in wtypes:
                return True, 15
            return True, 10

    return False, -1


DLC_LABEL_SUFFIXES = {
    "anchorage": "Operation: Anchorage",
    "pitt": "The Pitt",
    "brokensteel": "Broken Steel",
    "pointlookout": "Point Lookout",
    "zeta": "Mothership Zeta",
}


def generate_direct_lookup_titles(nodes: list[dict[str, Any]], unmatched_only_labels: set[str]) -> list[str]:
    """Generate prioritized candidate MediaWiki titles for unmatched nodes."""
    priority_order = {
        ("quest", "*"): 0,
        ("event", "*"): 1,
        ("object", "perk"): 2,
        ("location", "world"): 3,
        ("location", "marker"): 4,
        ("item", "weapon"): 5,
        ("item", "armor"): 6,
        ("item", "book"): 7,
        ("item", "aid"): 8,
        ("item", "ammo"): 9,
        ("character", "npc"): 10,
        ("character", "creature"): 11,
        ("location", "interior"): 12,
        ("item", "note"): 13,
        ("item", "key"): 14,
        ("item", "misc"): 15,
        ("object", "terminal"): 16,
    }

    label_counts = Counter(n["label"] for n in nodes)

    def node_prio(n: dict[str, Any]) -> int:
        t = n["type"]
        st = n.get("subtype", "")
        if (t, st) in priority_order:
            return priority_order[(t, st)]
        if (t, "*") in priority_order:
            return priority_order[(t, "*")]
        return 99

    prioritized = sorted(
        [n for n in nodes if n["label"] in unmatched_only_labels],
        key=node_prio,
    )

    candidates: list[str] = []
    seen_candidates: set[str] = set()
    seen_node_keys: set[tuple[str, str, str]] = set()

    def add_cand(t: str) -> None:
        t = t.strip()
        if t and "|" not in t and t not in seen_candidates:
            seen_candidates.add(t)
            candidates.append(t)

    for n in prioritized:
        ntype = n["type"]
        subtype = n.get("subtype", "")
        dlc = n.get("dlc", "base")
        label = n["label"].strip()
        if not label:
            continue
        # Skip pure generic repeated NPCs/objects/doors and English internal edids
        if ntype == "object" and subtype in ("door", "container", "activator"):
            continue
        if ntype == "character" and label_counts[label] > 2:
            continue
        if re.match(r"^(?:DC\d+[a-z]?|Freeform|Hiring .+ Quest|DLC\d+)", label):
            continue
        # Skip raw ASCII-only internal labels for quests
        if ntype == "quest" and re.match(r"^[A-Za-z0-9_ :\-]+$", label):
            continue

        key = (ntype, dlc, label)
        if key in seen_node_keys:
            continue
        seen_node_keys.add(key)

        variants = [label]
        # Replace straight quotes "..." with «...» AND also add quote-stripped variant
        if '"' in label:
            variants.append(re.sub(r'"([^"]+)"', r"«\1»", label))
            variants.append(re.sub(r'["«»]', "", label).strip())
        # Replace " - " with " — "
        if " - " in label:
            variants.extend([v.replace(" - ", " — ") for v in list(variants)])
        # Replace ... with …
        if "..." in label:
            variants.extend([v.replace("...", "…") for v in list(variants)])
        # Handle ALL CAPS quests
        if label.isupper() and len(label) > 3:
            for v in list(variants):
                variants.append(v.capitalize())
                variants.append(v.title())
        # Expand д-р -> доктор
        if re.search(r"\bд-р\b", label, re.IGNORECASE):
            for v in list(variants):
                variants.append(re.sub(r"\bд-р\b", "Доктор", v, flags=re.IGNORECASE))

        for v in dict.fromkeys(variants):
            add_cand(v)
            add_cand(f"{v} (Fallout 3)")
            if dlc in DLC_LABEL_SUFFIXES:
                add_cand(f"{v} ({DLC_LABEL_SUFFIXES[dlc]})")
            if ntype == "quest":
                add_cand(f"{v} (квест)")
            elif ntype == "location":
                add_cand(f"{v} (локация)")
            elif ntype == "object" and subtype == "perk":
                add_cand(f"{v} (способность)")
            elif ntype == "item" and subtype == "book":
                add_cand(f"{v} (книга)")
            elif ntype == "item" and subtype == "weapon":
                add_cand(f"{v} (оружие)")
            elif ntype == "item" and subtype == "armor":
                add_cand(f"{v} (броня)")

    return candidates


def extract_fo3_links_from_disambig(
    pages_cache: dict[str, dict[str, Any]], unmatched_labels: set[str]
) -> list[str]:
    """Extract Fallout 3 / DLC target links from cached disambiguation/root pages."""
    norm_unmatched = {norm_label(lbl) for lbl in unmatched_labels}
    targets: list[str] = []
    seen: set[str] = set()
    fo3_line_markers = ("fallout 3", "operation: anchorage", "the pitt", "broken steel", "point lookout", "mothership zeta", "fo3", "oa", "tp", "bs", "pl", "mz")
    for title, pdata in pages_cache.items():
        if pdata.get("missing") or not pdata.get("wikitext"):
            continue
        if norm_label(title) not in norm_unmatched:
            continue
        wt = pdata["wikitext"]
        if not any(tag in wt.lower() for tag in ("{{неоднозначность", "{{корневая статья")):
            continue
        for line in wt.splitlines():
            low = line.lower()
            if any(m in low for m in fo3_line_markers):
                for m in re.finditer(r"\[\[([^|\]]+)", line):
                    tgt = m.group(1).split("#", 1)[0].strip()
                    if tgt and ":" not in tgt and tgt not in seen:
                        seen.add(tgt)
                        targets.append(tgt)
    return targets


def format_clean_categories(raw_cats: list[str]) -> list[str]:
    """Return clean non-maintenance Russian category names without 'Категория:' prefix."""
    cleaned: list[str] = []
    for c in raw_cats:
        name = c[10:] if c.startswith("Категория:") else c
        low = name.lower()
        if any(low.startswith(pref) for pref in MAINTENANCE_CAT_PREFIXES):
            continue
        cleaned.append(name)
    return cleaned


def build_page_index(
    pages_cache: dict[str, dict[str, Any]],
    redirects: dict[str, str],
    normalized: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    """Extract metadata for valid pages and index them by normalized keys."""
    meta_by_title: dict[str, dict[str, Any]] = {}
    index: dict[str, list[str]] = defaultdict(list)

    def add_idx(key: str, title: str) -> None:
        if key and title not in index[key]:
            index[key].append(title)

    for title, pdata in pages_cache.items():
        if pdata.get("missing") or not pdata.get("wikitext"):
            continue
        cats = pdata.get("categories", [])
        wikitext = pdata.get("wikitext", "")
        meta = extract_wiki_metadata(title, cats, wikitext)
        if meta["is_disambig"] or not meta["fo3_relevant"]:
            continue
        meta_by_title[title] = meta

        # Index by canonical title and stripped disambig title
        add_idx(norm_label(title), title)
        add_idx(norm_label(title, expand_abbrev=True), title)

        stripped = strip_wiki_disambig_paren(title)
        if stripped != title:
            add_idx(norm_label(stripped), title)
            add_idx(norm_label(stripped, expand_abbrev=True), title)

        for it in meta["infobox_titles"]:
            add_idx(norm_label(it), title)
            add_idx(norm_label(it, expand_abbrev=True), title)

    # Also index redirect source titles to their resolved canonical page
    def resolve(t: str) -> str:
        cur = t
        seen = set()
        while cur not in seen:
            seen.add(cur)
            if cur in normalized:
                cur = normalized[cur]
            elif cur in redirects:
                cur = redirects[cur]
            else:
                break
        return cur

    for src in list(redirects.keys()) + list(normalized.keys()):
        dst = resolve(src)
        if dst in meta_by_title:
            add_idx(norm_label(src), dst)
            add_idx(norm_label(src, expand_abbrev=True), dst)
            stripped_src = strip_wiki_disambig_paren(src)
            if stripped_src != src:
                add_idx(norm_label(stripped_src), dst)

    return meta_by_title, index


def match_nodes(
    nodes: list[dict[str, Any]],
    meta_by_title: dict[str, dict[str, Any]],
    index: dict[str, list[str]],
) -> dict[str, str]:
    """Conservatively match graph.json nodes to wiki page titles."""
    matched: dict[str, str] = {}

    for node in nodes:
        label = node.get("label", "").strip()
        if not label:
            continue
        k1 = norm_label(label)
        k2 = norm_label(label, expand_abbrev=True)
        cand_titles: list[str] = []
        for k in (k1, k2):
            for t in index.get(k, []):
                if t not in cand_titles:
                    cand_titles.append(t)

        if not cand_titles:
            continue

        fid = node.get("fid", "")
        edid = node.get("edid", "").lower()
        node_hex_full = ""
        node_hex_dlc = ""
        if fid.startswith("0x"):
            try:
                val = int(fid, 16)
                node_hex_full = hex(val)[2:].lower()
                if (val >> 24) != 0:
                    node_hex_dlc = hex(val & 0xFFFFFF)[2:].lower()
            except ValueError:
                pass

        best_title: str | None = None
        best_score = -1

        for title in cand_titles:
            meta = meta_by_title.get(title)
            if not meta:
                continue
            exact_id_match = bool(
                (node_hex_full and node_hex_full in meta["hex_ids"])
                or (node_hex_dlc and node_hex_dlc in meta["hex_ids"])
                or (edid and edid in meta["editor_ids"])
            )
            ok, type_score = is_type_compatible(node, meta, exact_id_match=exact_id_match)
            if not ok:
                continue

            score = type_score
            # Exact title match bonus over parenthesized title
            if norm_label(title) == k1:
                score += 10
            elif norm_label(strip_wiki_disambig_paren(title)) == k1:
                score += 5

            # BaseID / FormID / EditorID verification bonus
            if exact_id_match:
                score += 100

            # Prefer non-cut articles by default
            if not meta["is_cut_article"]:
                score += 2

            if score > best_score:
                best_score = score
                best_title = title

        if best_title is not None:
            matched[node["id"]] = best_title

    return matched


def verify_no_raw_tokens(records: dict[str, Any]) -> list[str]:
    """Verify zero raw wikitext tokens remain in output fields."""
    bad_tokens = ("{{", "}}", "[[", "]]", "<ref", "{|", "|}")
    errors: list[str] = []
    for nid, rec in records.items():
        texts = [rec.get("lead", "")]
        for sec in rec.get("sections", []):
            texts.append(sec.get("heading", ""))
            texts.append(sec.get("text", ""))
        for txt in texts:
            for tok in bad_tokens:
                if tok in txt:
                    errors.append(f"{nid} ({rec.get('wikiTitle')}): found {tok!r}")
    return errors


def test_cleaner_samples() -> None:
    """Quick smoke test fetching and cleaning 6 diverse Fallout 3 pages."""
    client = WikiClient()
    samples = [
        "Забери его!",
        "Хоккейная маска Леду",
        "Мегатонна",
        "Смерть на взлёте",
        "Штурмовая винтовка (Fallout 3)",
        "Записи в терминалах «Кэпитал Пост»",
    ]
    client.fetch_pages_batch(samples)
    for t in samples:
        rt = client.resolve_title(t)
        p = client.cache["pages"].get(rt, {})
        wt = p.get("wikitext", "")
        lead, secs = extract_lead_and_sections(wt)
        print("=" * 60)
        print("TITLE:", rt)
        print("LEAD:\n", lead[:500])
        print("SECTIONS:", [s["heading"] for s in secs])
        if secs:
            print("FIRST SEC PREVIEW:\n", secs[0]["text"][:300])


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest Russian Fallout 3 wiki lore.")
    parser.add_argument("--test-clean", action="store_true", help="Test cleaner on sample pages and exit.")
    parser.add_argument("--skip-fetch", action="store_true", help="Rebuild wiki_ru.json from existing cache only.")
    args = parser.parse_args()

    if args.test_clean:
        test_cleaner_samples()
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    nodes: list[dict[str, Any]] = graph["nodes"]
    print(f"[init] loaded {len(nodes)} nodes from {GRAPH_PATH}", flush=True)

    client = WikiClient(CACHE_PATH)

    if not args.skip_fetch:
        # Phase 1: Walk categories up to depth 2
        cat_pages = client.walk_categories(max_depth=2)
        client.fetch_pages_batch(sorted(cat_pages.keys()), mark_missing=True)
        client.save_cache()

        # Phase 2: Preliminary match to find unmatched prioritized labels
        meta_by_title, index = build_page_index(
            client.cache["pages"],
            client.cache["redirects"],
            client.cache["normalized"],
        )
        prelim_matched = match_nodes(nodes, meta_by_title, index)
        unmatched_labels = {
            n["label"] for n in nodes if n["id"] not in prelim_matched and n.get("label")
        }
        print(
            f"[phase1] prelim matched {len(prelim_matched)}/{len(nodes)} nodes; "
            f"{len(unmatched_labels)} distinct unmatched labels",
            flush=True,
        )

        # Phase 3: Direct title batch lookups for unmatched prioritized labels
        cand_titles = generate_direct_lookup_titles(nodes, unmatched_labels)
        print(f"[phase2] generated {len(cand_titles)} direct lookup titles", flush=True)
        client.fetch_pages_batch(cand_titles, mark_missing=True)
        disambig_targets = extract_fo3_links_from_disambig(client.cache["pages"], unmatched_labels)
        if disambig_targets:
            print(f"[phase3] following {len(disambig_targets)} disambiguation links", flush=True)
            client.fetch_pages_batch(disambig_targets, mark_missing=True)
        client.save_cache()

    # Final index & conservative matching
    meta_by_title, index = build_page_index(
        client.cache["pages"],
        client.cache["redirects"],
        client.cache["normalized"],
    )
    matched_titles = match_nodes(nodes, meta_by_title, index)

    # Clean wikitext once per matched wikiTitle
    cleaned_cache: dict[str, dict[str, Any]] = {}
    for wtitle in set(matched_titles.values()):
        pdata = client.cache["pages"][wtitle]
        lead, sections = extract_lead_and_sections(pdata.get("wikitext", ""))
        if not lead and not sections:
            continue
        wiki_url = WIKI_BASE_URL + urllib.parse.quote(wtitle.replace(" ", "_"), safe="/:()")
        cleaned_cache[wtitle] = {
            "wikiTitle": wtitle,
            "wikiUrl": wiki_url,
            "categories": format_clean_categories(pdata.get("categories", [])),
            "lead": lead,
            "sections": sections,
        }

    # Build final output keyed by nodeId
    output: dict[str, Any] = {}
    matched_by_type: Counter[str] = Counter()
    total_by_type: Counter[str] = Counter(n["type"] for n in nodes)

    for node in nodes:
        nid = node["id"]
        wtitle = matched_titles.get(nid)
        if not wtitle or wtitle not in cleaned_cache:
            continue
        output[nid] = cleaned_cache[wtitle]
        matched_by_type[node["type"]] += 1

    # Verify zero raw wikitext tokens
    errors = verify_no_raw_tokens(output)
    if errors:
        print(f"[ERROR] raw wikitext tokens detected ({len(errors)}):", file=sys.stderr)
        for e in errors[:20]:
            print(" ", e, file=sys.stderr)
        sys.exit(1)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[done] wrote {len(output)}/{len(nodes)} matched nodes to {OUT_PATH}", flush=True)
    for ntype in sorted(total_by_type.keys()):
        print(f"  {ntype}: {matched_by_type[ntype]}/{total_by_type[ntype]}", flush=True)


if __name__ == "__main__":
    main()
