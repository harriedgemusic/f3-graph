#!/usr/bin/env python3
"""Merge and strictly validate all 4 Fallout 3 encyclopedia JSON parts into public/data/details.json."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = REPO_ROOT / "public" / "data" / "graph.json"
OUT_DETAILS_PATH = REPO_ROOT / "public" / "data" / "details.json"
PARTS_DIR = Path("/tmp/f3_encyclopedia/parts")

PART_FILES = [
    "characters.json",
    "items.json",
    "locations.json",
    "objects_quests_events.json",
]

FORBIDDEN_TOKENS = [
    "{{",
    "}}",
    "[[",
    "]]",
    "<ref",
    "<div",
    "\ufffd",
    "Предмет категории «",
    "Интерактивный объект-активатор (",
    "Игровой мир / крупная внешняя область (",
    "Обитатель Пустоши (",
    "Запертый/открываемый контейнер (",
    "Переходная дверь (",
    "Терминал: Интерактивный",
]


def main():
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    nodes = graph["nodes"]
    expected_ids = {n["id"] for n in nodes}

    merged = {}
    for fname in PART_FILES:
        part_path = PARTS_DIR / fname
        assert part_path.exists(), f"Missing part file: {part_path}"
        data = json.loads(part_path.read_text(encoding="utf-8"))
        print(f"Loaded {fname}: {len(data)} entries")
        merged.update(data)

    assert set(merged.keys()) == expected_ids, (
        f"ID mismatch: missing={len(expected_ids - set(merged))}, extra={len(set(merged) - expected_ids)}"
    )

    total_sections = 0
    with_wiki = 0
    with_quotes = 0
    with_unlocks = 0
    with_effects = 0
    total_chars = 0

    for nid, entry in merged.items():
        role = (entry.get("role") or "").strip()
        summary = (entry.get("summary") or "").strip()
        sections = entry.get("sections") or []

        assert role, f"Empty role for {nid}"
        assert len(summary) >= 90, f"Short summary ({len(summary)}) for {nid}: {summary}"
        valid_secs = [
            s for s in sections
            if isinstance(s, dict) and (s.get("title") or "").strip() and len((s.get("text") or "").strip()) >= 40
        ]
        assert len(valid_secs) >= 2, f"Fewer than 2 valid sections for {nid}"

        blob = json.dumps(entry, ensure_ascii=False)
        for tok in FORBIDDEN_TOKENS:
            assert tok not in blob, f"Forbidden token {tok!r} found in {nid}"

        total_sections += len(valid_secs)
        total_chars += len(summary) + sum(len(s.get("text", "")) for s in valid_secs)
        if entry.get("wikiUrl"):
            with_wiki += 1
        if entry.get("quotes"):
            with_quotes += 1
        if entry.get("unlocks"):
            with_unlocks += 1
        if entry.get("effects"):
            with_effects += 1

    OUT_DETAILS_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    size_mb = OUT_DETAILS_PATH.stat().st_size / (1024 * 1024)
    print(
        f"Successfully wrote {OUT_DETAILS_PATH} ({size_mb:.2f} MB):\n"
        f"  Nodes: {len(merged)} / {len(expected_ids)}\n"
        f"  Total sections: {total_sections} (avg {total_sections / len(merged):.2f}/node)\n"
        f"  Avg prose length: {total_chars // len(merged)} chars/node\n"
        f"  Wiki-linked entries: {with_wiki}\n"
        f"  Characters with dialogue quotes: {with_quotes}\n"
        f"  Entries with unlocks: {with_unlocks}\n"
        f"  Entries with effects/bonuses: {with_effects}"
    )


if __name__ == "__main__":
    main()
