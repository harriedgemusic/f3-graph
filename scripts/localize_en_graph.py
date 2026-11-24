#!/usr/bin/env python3
"""
Polish all remaining raw EDIDs, DC* sector codes, character presets, random
encounter dev notes, and quest labels in `node["labelEn"]` inside
public/data/graph.json without modifying Russian labels, coords, tiers, or edges.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = ROOT / "public" / "data" / "graph.json"

HAS_CYRILLIC = re.compile(r"[А-Яа-яЁё]")
RACE_PRESET_RE = re.compile(r"^race(AfricanAmerican|Asian|Caucasian|Hispanic)([FM])(\d{2})$")

RACE_PRESET_EN = {
    "AfricanAmerican": "African American",
    "Asian": "Asian",
    "Caucasian": "Caucasian",
    "Hispanic": "Hispanic",
}

DC_SECTOR_LABELS_EN: dict[str, str] = {
    "loc_00094287": "DC Ruins Sector DC01a (Chevy Chase — Rock Creek)",
    "loc_00094286": "DC Ruins Sector DC01b (Chevy Chase — East)",
    "loc_00094290": "DC Ruins Sector DC03a (Dupont — Northeast)",
    "loc_00094291": "DC Ruins Sector DC03b (Dupont — West)",
    "loc_00094292": "DC Ruins Sector DC03c (Dupont Circle)",
    "loc_0009428b": "DC Ruins Sector DC05a (Takoma Park)",
    "loc_0009428c": "DC Ruins Sector DC05b (Takoma Industrial)",
    "loc_0009428d": "DC Ruins Sector DC06a (Vernon Square — North)",
    "loc_0009428e": "DC Ruins Sector DC06b (Vernon Square — East)",
    "loc_0001eb92": "DC Ruins Sector DC06c (Vernon Square Station)",
    "loc_00094295": "DC Ruins Sector DC08a (Vernon Square — Hospital)",
    "loc_00027963": "DC Ruins Sector DC08b (Our Lady of Hope Hospital)",
    "loc_00027966": "DC Ruins Sector DC08c (The Statesman Hotel)",
    "loc_00094296": "DC Ruins Sector DC09a (Pennsylvania Ave — Northwest)",
    "loc_00094297": "DC Ruins Sector DC09b (The Mall — Northwest)",
    "loc_0009429c": "DC Ruins Sector DC09c (Pennsylvania Ave — East)",
    "loc_00094299": "DC Ruins Sector DC09e (Pennsylvania Ave — South)",
    "loc_0009429a": "DC Ruins Sector DC09f (Pennsylvania Ave — Metro Central)",
    "loc_0009429b": "DC Ruins Sector DC09g (Pennsylvania Ave — North)",
    "loc_0009429d": "DC Ruins Sector DC10a (L'Enfant Plaza)",
    "loc_0009429e": "DC Ruins Sector DC10b (Jefferson Memorial)",
    "loc_00094288": "DC Ruins Sector DC11a (Georgetown — North)",
    "loc_00094293": "DC Ruins Sector DC11b (Georgetown — South)",
    "loc_00094294": "DC Ruins Sector DC11c (Georgetown — East)",
    "loc_000942a3": "DC Ruins Sector DC12a (The Mall — Metro Central)",
    "loc_000942a4": "DC Ruins Sector DC12b (The Mall — Capitol)",
    "loc_000942a5": "DC Ruins Sector DC12c (Seward Square — Capitol)",
    "loc_000942a2": "DC Ruins Sector DC14d (L'Enfant Plaza — Anacostia)",
    "loc_00095d37": "DC Ruins Sector DC15a (Grayditch — Anchorage Memorial)",
    "loc_00095d40": "DC Ruins Sector DC15a (Citadel Outer Perimeter)",
    "loc_00095d43": "DC Ruins Sector DC15b (Arlington Cemetery)",
    "loc_00095d3b": "DC Ruins Sector DC16a (Falls Church — Marigold Station)",
    "loc_00095d3c": "DC Ruins Sector DC17a (Mason District — Hubris Comics)",
    "loc_00027a49": "DC Ruins Sector DC18b (Falls Church — East)",
    "loc_00095d44": "DC Ruins Sector DC19a (Arlington — Mama Dolce's)",
    "loc_00095d41": "DC Ruins Sector DC20b (Alexandria Arms)",
    "loc_00095d42": "DC Ruins Sector DC20c (Arlington Library Outskirts)",
    "loc_00095d3e": "DC Ruins Sector DC21a (Red Racer Factory — Bailey's Crossroads)",
    "loc_00095d3f": "DC Ruins Sector DC21b (Bailey's Crossroads — South)",
    "loc_00095d48": "DC Ruins Sector DC23a (Nuka-Cola Plant)",
    "loc_00095d47": "DC Ruins Sector DC23b (Flooded Metro — Arlington)",
    "loc_00095d45": "DC Ruins Sector DC25a (South Arlington)",
}

RANDOM_ENCOUNTER_LABELS_EN: dict[str, str] = {
    "evt_re_ffeuniquea_1": "Thirsty Wastelander Begging for Water",
    "evt_re_ffeuniquea_2": "Deathclaw Pursuing Settlers",
    "evt_re_ffeuniquea_3": "Settlers Standoff Over Water Supply",
    "evt_re_ffeuniquea_4": "Deathclaw Hunting Ground & Remains",
    "evt_re_ffeuniquea_5": "Brotherhood Patrol vs. Raiders Ambush",
    "evt_re_ffeuniquea_6": "Uncle Leo — Friendly Super Mutant",
    "evt_re_ffeuniquea_7": "Wounded Deathclaw & Fallen Hunters",
    "evt_re_ffeuniquea_8": "Alien Probe Crash (Firelance)",
    "evt_re_ffeuniquea_9": "Enclave Courier with Intel",
    "evt_re_ffeuniquea_10": "Escaped Slave with Explosive Collar",
    "evt_re_ffeuniquea_11": "Sam Warrick — Trapped Hunter",
    "evt_re_ffeuniquea_12": "Hunter with Tamed Yao Guai",
    "evt_re_ffeuniquea_13": "Mel & His Explosive Brahmin Scam",
    "evt_re_ffeuniquea_14": "Ben Haze — Escaped Scientist",
    "evt_re_ffeuniquea_15": "Mine-Obsessed Psychopath (Dirty Joe)",
    "evt_re_ffeuniquea_16": "Lone Preacher of the Holy Flame",
    "evt_re_ffeuniquea_17": "Crashed Enclave Vertibird",
    "evt_re_ffeuniqueb_51": "Cannibals Selling Strange Meat",
    "evt_re_ffeuniqueb_52": "Cannibals Hunting Wastelander",
    "evt_re_ffeuniqueb_53": "Sniper Using Decoy Bait",
    "evt_re_ffeuniqueb_54": "Human Bomb & Raider Ambush",
    "evt_re_ffeuniqueb_55": "Shady Wasteland Charlatan Merchant",
    "evt_re_fferepeata_1": "Giant Ants vs. Radscorpion",
    "evt_re_fferepeata_2": "Giant Ants Around Toxic Barrel",
    "evt_re_fferepeatb_51": "Brotherhood Outcasts Patrol",
    "evt_re_fferepeatb_52": "Outcasts Skirmish with Raiders",
    "evt_re_fferepeatb_53": "Outcast Scout Fleeing Deathclaws",
}

EXPLICIT_LABELS_EN: dict[str, str] = {
    # 14 Special Quests
    "qst_0009426d": "Companion Recruitment: Butch DeLoria",
    "qst_000371d2": "Companion Recruitment: Charon",
    "qst_000943ec": "Companion Recruitment: Clover",
    "qst_000943ed": "Companion Recruitment: Dogmeat",
    "qst_000943ee": "Companion Recruitment: Fawkes",
    "qst_0002fa33": "Companion Recruitment: Jericho",
    "qst_000943eb": "Companion Recruitment: Sergeant RL-3",
    "qst_00062736": "Companion Recruitment: Star Paladin Cross",
    "qst_000173d8": "Megaton Freeform Quests",
    "qst_000173d1": "DC Ruins Exploration",
    "qst_000173d9": "The Citadel Freeform Quests",
    "qst_0006136d": "Power Armor Training",
    "qst_010034da": "Operation: Anchorage Simulation Intel",
    "qst_05005c70": "Mothership Zeta: Steerage Rats",
    # Locations & Creatures with raw tokens
    "loc_0007c25b": "Nifty Thrifty",
    "loc_0400c2b4": "Submarine SSN-37-1A",
    "chr_000854d7": "Nukalurk",
    # Dev / Test / Voice NPCs
    "chr_0100c166": "Voice Actor: Gary",
    "chr_0100c164": "Voice Actor #2 (Anchorage)",
    "chr_0100c163": "Voice Actor #1 (Anchorage)",
    "chr_02001961": "Pitt Test Character",
    "chr_02002a55": "Pitt Test Character #2",
    "chr_02002a57": "Pitt Test Character #3",
    "chr_020028fc": "Pitt Test Character (Asian, M)",
    "chr_020028fb": "Pitt Test Character (Hispanic, M)",
    "chr_020028fa": "Pitt Test Character (African American, M)",
    "chr_020028f9": "Pitt Test Character (Caucasian, M)",
    "chr_020028f8": "Pitt Test Character (Caucasian, F)",
    "chr_02002be1": "Street Trog (Pitt Test)",
    "chr_0300b958": "Audio Narrator (Broken Steel)",
    "chr_04010a4b": "Dialogue Voice Placeholder",
    "chr_04003f2c": "Dialogue Voice Placeholder",
    "chr_0500a672": "Zeta Test Character (Child)",
    "chr_050079a0": "Zeta Test Character",
}


def parse_race_preset_en(raw_label: str) -> str | None:
    m = RACE_PRESET_RE.match(raw_label)
    if not m:
        return None
    race_key, gender_key, num = m.groups()
    return f"Appearance Preset: {RACE_PRESET_EN[race_key]} ({gender_key} #{num})"


def main() -> None:
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    updated = 0

    for node in graph["nodes"]:
        nid = node["id"]
        old_en = node.get("labelEn", "")
        new_en = old_en

        if nid in DC_SECTOR_LABELS_EN:
            new_en = DC_SECTOR_LABELS_EN[nid]
        elif nid in RANDOM_ENCOUNTER_LABELS_EN:
            new_en = RANDOM_ENCOUNTER_LABELS_EN[nid]
        elif nid in EXPLICIT_LABELS_EN:
            new_en = EXPLICIT_LABELS_EN[nid]
        else:
            preset = parse_race_preset_en(old_en)
            if preset:
                new_en = preset

        if new_en != old_en:
            node["labelEn"] = new_en
            updated += 1

    # Strict validation
    cyr_nodes = [
        (n["id"], n["labelEn"])
        for n in graph["nodes"]
        if HAS_CYRILLIC.search(n.get("labelEn", ""))
    ]
    if cyr_nodes:
        raise RuntimeError(f"Cyrillic found in labelEn: {cyr_nodes[:10]}")

    raw_left = [
        (n["id"], n["labelEn"])
        for n in graph["nodes"]
        if RACE_PRESET_RE.match(n.get("labelEn", ""))
        or n.get("labelEn", "").startswith("FFEUnique")
        or n.get("labelEn", "") in ("FreeformPowerArmor", "DLC02FF")
    ]
    if raw_left:
        raise RuntimeError(f"Unpolished raw labelEn remained: {raw_left[:10]}")

    GRAPH_PATH.write_text(
        json.dumps(graph, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Updated labelEn on {updated} nodes (total {len(graph['nodes'])}); 0 Cyrillic, 0 raw tokens.")


if __name__ == "__main__":
    main()
