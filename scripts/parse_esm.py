#!/usr/bin/env python3
"""
Parse all 6 Fallout 3 GOTY .esm files (both ENG cp1252 and RUS cp1251)
from /tmp/f3_extract/esm and save structured raw gameplay data to
/tmp/f3_extract/parsed_raw.json.
"""

from __future__ import annotations

import json
import os
import re
import struct
import sys
import time
import zlib
from collections import defaultdict
from pathlib import Path
from typing import Any

ESM_DIR = Path("/tmp/f3_extract/esm")
OUT_PATH = Path("/tmp/f3_extract/parsed_raw.json")

ESMS = [
    ("Fallout3.esm", "base", "Базовая игра"),
    ("Anchorage.esm", "anchorage", "Operation: Anchorage"),
    ("ThePitt.esm", "pitt", "The Pitt"),
    ("BrokenSteel.esm", "brokensteel", "Broken Steel"),
    ("PointLookout.esm", "pointlookout", "Point Lookout"),
    ("Zeta.esm", "zeta", "Mothership Zeta"),
]

GLOBAL_IDX_BY_NAME = {name.lower(): idx for idx, (name, _, _) in enumerate(ESMS)}
DLC_BY_GLOBAL_IDX = {idx: dlc for idx, (_, dlc, _) in enumerate(ESMS)}

REC_HDR = struct.Struct("<4sIIIIHH")
SUB_HDR = struct.Struct("<4sH")

# Record types we need to inspect deeply
TARGET_TYPES = {
    b"TES4",
    b"FACT",
    b"RACE",
    b"NPC_",
    b"CREA",
    b"WRLD",
    b"CELL",
    b"REFR",
    b"ACHR",
    b"ACRE",
    b"QUST",
    b"SCPT",
    b"DIAL",
    b"INFO",
    b"WEAP",
    b"ARMO",
    b"ALCH",
    b"AMMO",
    b"BOOK",
    b"KEYM",
    b"NOTE",
    b"MISC",
    b"TERM",
    b"ACTI",
    b"CONT",
    b"DOOR",
    b"PERK",
}

ITEM_TYPES = {b"WEAP", b"ARMO", b"ALCH", b"AMMO", b"BOOK", b"KEYM", b"NOTE", b"MISC"}
OBJECT_TYPES = {b"TERM", b"ACTI", b"CONT", b"DOOR", b"PERK"}

# Fallout 3 CTDA function indices used for dialogue/quest links
CTDA_GET_IS_ID = 72
CTDA_GET_IN_FACTION = 71
CTDA_GET_IS_REFERENCE = 136
CTDA_GET_STAGE = 58
CTDA_GET_STAGE_DONE = 59
CTDA_GET_QUEST_RUNNING = 56


def decode_zstr(data: bytes, encoding: str) -> str:
    if not data:
        return ""
    nul = data.find(b"\x00")
    if nul != -1:
        data = data[:nul]
    return data.decode(encoding, errors="replace").strip()


def iter_subrecords(payload: bytes):
    i = 0
    n = len(payload)
    next_size = None
    while i + 6 <= n:
        stype = payload[i : i + 4]
        ssize = struct.unpack_from("<H", payload, i + 4)[0]
        i += 6
        if stype == b"XXXX":
            if i + 4 <= n:
                next_size = struct.unpack_from("<I", payload, i)[0]
            i += ssize
            continue
        if next_size is not None:
            ssize = next_size
            next_size = None
        end = min(i + ssize, n)
        yield stype, payload[i:end]
        i = end


def make_remapper(masters: list[str], my_idx: int):
    master_map = [GLOBAL_IDX_BY_NAME.get(m.lower(), my_idx) for m in masters]
    n_masters = len(master_map)

    def remap(fid: int) -> int:
        if fid == 0:
            return 0
        mod_idx = (fid >> 24) & 0xFF
        g_idx = master_map[mod_idx] if mod_idx < n_masters else my_idx
        return (g_idx << 24) | (fid & 0x00FFFFFF)

    return remap


def iter_records(buf: memoryview, start: int, end: int, wrld_fid: int = 0, cell_fid: int = 0, dial_fid: int = 0, remap=None):
    pos = start
    while pos + 24 <= end:
        magic, size, flags, fid, vc, fver, unk = REC_HDR.unpack_from(buf, pos)
        if magic == b"GRUP":
            # In GRUP header: size includes 24-byte header; label is bytes 8..12; group_type is bytes 12..16
            g_size = size
            label_bytes = buf[pos + 8 : pos + 12].tobytes()
            g_type = fid  # offset 12 is group_type
            sub_wrld = wrld_fid
            sub_cell = cell_fid
            sub_dial = dial_fid
            if g_type == 0:
                # Top group: label is 4-char record type. Skip groups we don't care about!
                top_tag = label_bytes
                if top_tag not in TARGET_TYPES:
                    pos += g_size
                    continue
            elif g_type == 1:
                raw_fid = struct.unpack("<I", label_bytes)[0]
                sub_wrld = remap(raw_fid) if remap else raw_fid
            elif g_type in (6, 8, 9, 10):
                raw_fid = struct.unpack("<I", label_bytes)[0]
                sub_cell = remap(raw_fid) if remap else raw_fid
            elif g_type == 7:
                raw_fid = struct.unpack("<I", label_bytes)[0]
                sub_dial = remap(raw_fid) if remap else raw_fid

            grp_end = min(pos + g_size, end)
            if grp_end > pos + 24:
                yield from iter_records(buf, pos + 24, grp_end, sub_wrld, sub_cell, sub_dial, remap)
            pos = grp_end
        else:
            rec_end = min(pos + 24 + size, end)
            if magic in TARGET_TYPES and not (flags & 0x00000020):  # skip Deleted
                payload_mv = buf[pos + 24 : rec_end]
                if flags & 0x00040000:  # zlib compressed
                    if len(payload_mv) >= 4:
                        try:
                            payload = zlib.decompress(payload_mv[4:].tobytes())
                        except zlib.error:
                            payload = b""
                    else:
                        payload = b""
                else:
                    payload = payload_mv.tobytes()
                yield magic, flags, fid, wrld_fid, cell_fid, dial_fid, payload
            pos = rec_end


def read_tes4_masters(buf: memoryview) -> tuple[list[str], int]:
    magic, size, flags, fid, vc, fver, unk = REC_HDR.unpack_from(buf, 0)
    assert magic == b"TES4", f"Expected TES4, got {magic!r}"
    payload = buf[24 : 24 + size].tobytes()
    masters = []
    for stype, sdata in iter_subrecords(payload):
        if stype == b"MAST":
            masters.append(decode_zstr(sdata, "latin1"))
    return masters, 24 + size


def extract_eng_names() -> dict[int, dict[str, str]]:
    """Fast pass over ENG/Data/*.esm to capture English FULL names and NOTE/TERM texts."""
    eng_dir = ESM_DIR / "ENG" / "Data"
    names: dict[int, dict[str, str]] = {}
    for idx, (fname, _, _) in enumerate(ESMS):
        fpath = eng_dir / fname
        if not fpath.exists():
            print(f"[WARN] Missing ENG file: {fpath}", file=sys.stderr)
            continue
        raw = fpath.read_bytes()
        mv = memoryview(raw)
        masters, body_start = read_tes4_masters(mv)
        remap = make_remapper(masters, idx)
        for rtype, flags, raw_fid, wrld_fid, cell_fid, dial_fid, payload in iter_records(mv, body_start, len(raw), remap=remap):
            if rtype in (b"REFR", b"ACHR", b"ACRE", b"INFO", b"SCPT", b"DIAL"):
                # Only need FULL on XMRK REFRs
                if rtype == b"REFR" and b"XMRK" not in payload:
                    continue
                if rtype != b"REFR":
                    continue
            fid = remap(raw_fid)
            edid = ""
            full = ""
            for stype, sdata in iter_subrecords(payload):
                if stype == b"EDID":
                    edid = decode_zstr(sdata, "cp1252")
                elif stype == b"FULL":
                    full = decode_zstr(sdata, "cp1252")
                    if edid:
                        break
            if full or edid:
                entry = names.setdefault(fid, {})
                if full:
                    entry["name_en"] = full
                if edid:
                    entry["edid"] = edid
    return names


def parse_rus_esms(eng_names: dict[int, dict[str, str]]) -> dict[str, Any]:
    rus_dir = ESM_DIR / "RUS" / "Data"

    factions: dict[int, dict[str, Any]] = {}
    races: dict[int, dict[str, Any]] = {}
    npcs: dict[int, dict[str, Any]] = {}
    creatures: dict[int, dict[str, Any]] = {}
    worlds: dict[int, dict[str, Any]] = {}
    cells: dict[int, dict[str, Any]] = {}
    markers: dict[int, dict[str, Any]] = {}
    items: dict[int, dict[str, Any]] = {}
    objects: dict[int, dict[str, Any]] = {}
    quests: dict[int, dict[str, Any]] = {}
    scripts: dict[int, dict[str, Any]] = {}
    dialogues: dict[int, dict[str, Any]] = {}
    refs: dict[int, dict[str, Any]] = {}  # placed REFR/ACHR/ACRE

    # Accumulators
    npc_placements: list[dict[str, Any]] = []
    item_placements: list[dict[str, Any]] = []
    obj_placements: list[dict[str, Any]] = []
    door_links: list[dict[str, Any]] = []
    object_locks: list[dict[str, Any]] = []
    quest_dialogue_links: list[dict[str, Any]] = []

    for idx, (fname, dlc_id, dlc_label) in enumerate(ESMS):
        fpath = rus_dir / fname
        if not fpath.exists():
            raise FileNotFoundError(f"Missing RUS ESM: {fpath}")
        t0 = time.time()
        raw = fpath.read_bytes()
        mv = memoryview(raw)
        masters, body_start = read_tes4_masters(mv)
        remap = make_remapper(masters, idx)
        rec_count = 0

        for rtype, flags, raw_fid, wrld_fid, cell_fid, dial_fid, payload in iter_records(mv, body_start, len(raw), remap=remap):
            rec_count += 1
            fid = remap(raw_fid)
            origin_dlc = DLC_BY_GLOBAL_IDX.get((fid >> 24) & 0xFF, dlc_id)
            eng_info = eng_names.get(fid, {})

            if rtype == b"FACT":
                rec = factions.setdefault(fid, {"fid": fid, "dlc": origin_dlc, "edid": "", "name": "", "name_en": eng_info.get("name_en", "")})
                for st, sd in iter_subrecords(payload):
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")

            elif rtype == b"RACE":
                rec = races.setdefault(fid, {"fid": fid, "dlc": origin_dlc, "edid": "", "name": "", "name_en": eng_info.get("name_en", "")})
                for st, sd in iter_subrecords(payload):
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")

            elif rtype in (b"NPC_", b"CREA"):
                target_dict = npcs if rtype == b"NPC_" else creatures
                rec = target_dict.setdefault(
                    fid,
                    {
                        "fid": fid,
                        "kind": "npc" if rtype == b"NPC_" else "creature",
                        "dlc": origin_dlc,
                        "edid": "",
                        "name": "",
                        "name_en": eng_info.get("name_en", ""),
                        "female": False,
                        "essential": False,
                        "unique": False,
                        "is_template_only": False,
                        "level": 1,
                        "race_fid": 0,
                        "script_fid": 0,
                        "factions": [],
                        "inventory": [],
                        "template_fid": 0,
                    },
                )
                factions_list = []
                inv_list = []
                for st, sd in iter_subrecords(payload):
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"ACBS" and len(sd) >= 12:
                        acbs_flags, fatigue, barter_gold, level = struct.unpack_from("<IHHh", sd, 0)
                        rec["female"] = bool(acbs_flags & 0x01)
                        rec["essential"] = bool(acbs_flags & 0x02)
                        rec["unique"] = bool(acbs_flags & 0x20)
                        rec["level"] = level
                    elif st == b"RNAM" and len(sd) >= 4:
                        rec["race_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"SCRI" and len(sd) >= 4:
                        rec["script_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"TPLT" and len(sd) >= 4:
                        rec["template_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"SNAM" and len(sd) >= 5:
                        ffid, rank = struct.unpack_from("<Ib", sd, 0)
                        factions_list.append({"fid": remap(ffid), "rank": rank})
                    elif st == b"CNTO" and len(sd) >= 8:
                        ifid, cnt = struct.unpack_from("<Ii", sd, 0)
                        inv_list.append({"fid": remap(ifid), "count": cnt})
                if factions_list:
                    rec["factions"] = factions_list
                if inv_list:
                    rec["inventory"] = inv_list

            elif rtype == b"WRLD":
                rec = worlds.setdefault(
                    fid,
                    {
                        "fid": fid,
                        "dlc": origin_dlc,
                        "edid": "",
                        "name": "",
                        "name_en": eng_info.get("name_en", ""),
                        "parent_wrld": 0,
                    },
                )
                for st, sd in iter_subrecords(payload):
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"WNAM" and len(sd) >= 4:
                        rec["parent_wrld"] = remap(struct.unpack_from("<I", sd, 0)[0])

            elif rtype == b"CELL":
                rec = cells.setdefault(
                    fid,
                    {
                        "fid": fid,
                        "dlc": origin_dlc,
                        "wrld_fid": wrld_fid,
                        "edid": "",
                        "name": "",
                        "name_en": eng_info.get("name_en", ""),
                        "is_interior": False,
                        "grid_x": None,
                        "grid_y": None,
                    },
                )
                for st, sd in iter_subrecords(payload):
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"DATA" and len(sd) >= 1:
                        rec["is_interior"] = bool(sd[0] & 0x01)
                    elif st == b"XCLC" and len(sd) >= 8:
                        gx, gy = struct.unpack_from("<ii", sd, 0)
                        rec["grid_x"] = gx
                        rec["grid_y"] = gy
                if wrld_fid == 0:
                    rec["is_interior"] = True

            elif rtype in (b"REFR", b"ACHR", b"ACRE"):
                base_fid = 0
                edid = ""
                pos_xyz = None
                is_marker = False
                marker_name = ""
                marker_type = 0
                xtel_dest = 0
                lock_level = None
                key_fid = 0
                for st, sd in iter_subrecords(payload):
                    if st == b"EDID":
                        edid = decode_zstr(sd, "cp1251")
                    elif st == b"NAME" and len(sd) >= 4:
                        base_fid = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"DATA" and len(sd) >= 12:
                        x, y, z = struct.unpack_from("<fff", sd, 0)
                        pos_xyz = [round(x, 1), round(y, 1), round(z, 1)]
                    elif st == b"XMRK":
                        is_marker = True
                    elif st == b"FULL":
                        marker_name = decode_zstr(sd, "cp1251")
                    elif st == b"TNAM" and len(sd) >= 1:
                        marker_type = sd[0]
                    elif st == b"XTEL" and len(sd) >= 4:
                        xtel_dest = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"XLOC" and len(sd) >= 8:
                        lock_level = sd[0]
                        key_fid = remap(struct.unpack_from("<I", sd, 4)[0])

                refs[fid] = {
                    "fid": fid,
                    "rtype": rtype.decode("ascii"),
                    "base_fid": base_fid,
                    "wrld_fid": wrld_fid,
                    "cell_fid": cell_fid,
                    "edid": edid,
                    "pos": pos_xyz,
                }

                if is_marker and marker_name:
                    markers[fid] = {
                        "fid": fid,
                        "dlc": origin_dlc,
                        "wrld_fid": wrld_fid,
                        "cell_fid": cell_fid,
                        "edid": edid,
                        "name": marker_name,
                        "name_en": eng_info.get("name_en", ""),
                        "marker_type": marker_type,
                        "pos": pos_xyz,
                    }
                if rtype in (b"ACHR", b"ACRE") and base_fid:
                    npc_placements.append(
                        {
                            "ref_fid": fid,
                            "base_fid": base_fid,
                            "wrld_fid": wrld_fid,
                            "cell_fid": cell_fid,
                            "pos": pos_xyz,
                        }
                    )
                if rtype == b"REFR" and base_fid:
                    if xtel_dest:
                        door_links.append(
                            {
                                "ref_fid": fid,
                                "dest_ref_fid": xtel_dest,
                                "base_fid": base_fid,
                                "wrld_fid": wrld_fid,
                                "cell_fid": cell_fid,
                                "pos": pos_xyz,
                            }
                        )
                    if key_fid or lock_level is not None:
                        object_locks.append(
                            {
                                "ref_fid": fid,
                                "base_fid": base_fid,
                                "key_fid": key_fid,
                                "lock_level": lock_level,
                                "cell_fid": cell_fid,
                                "wrld_fid": wrld_fid,
                            }
                        )
                    item_placements.append(
                        {
                            "ref_fid": fid,
                            "base_fid": base_fid,
                            "wrld_fid": wrld_fid,
                            "cell_fid": cell_fid,
                            "pos": pos_xyz,
                        }
                    )

            elif rtype in ITEM_TYPES:
                subtype_map = {
                    b"WEAP": "weapon",
                    b"ARMO": "armor",
                    b"ALCH": "aid",
                    b"AMMO": "ammo",
                    b"BOOK": "book",
                    b"KEYM": "key",
                    b"NOTE": "note",
                    b"MISC": "misc",
                }
                rec = items.setdefault(
                    fid,
                    {
                        "fid": fid,
                        "subtype": subtype_map[rtype],
                        "dlc": origin_dlc,
                        "edid": "",
                        "name": "",
                        "name_en": eng_info.get("name_en", ""),
                        "value": 0,
                        "weight": 0.0,
                        "damage": 0,
                        "dr": 0,
                        "playable": True,
                        "text": "",
                        "script_fid": 0,
                        "note_type": 0,
                    },
                )
                note_type = rec["note_type"]
                tname_raw = b""
                for st, sd in iter_subrecords(payload):
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"DESC":
                        txt = decode_zstr(sd, "cp1251")
                        if txt:
                            rec["text"] = txt
                    elif st == b"SCRI" and len(sd) >= 4:
                        rec["script_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"DATA":
                        if rtype == b"WEAP" and len(sd) >= 14:
                            val, health, weight, dmg = struct.unpack_from("<IIfH", sd, 0)
                            rec["value"] = val
                            rec["weight"] = round(weight, 2)
                            rec["damage"] = dmg
                        elif rtype == b"ARMO" and len(sd) >= 12:
                            val, cond, weight = struct.unpack_from("<IIf", sd, 0)
                            rec["value"] = val
                            rec["weight"] = round(weight, 2)
                        elif rtype in (b"ALCH", b"BOOK", b"KEYM", b"MISC") and len(sd) >= 4:
                            if rtype == b"ALCH" and len(sd) >= 4:
                                rec["weight"] = round(struct.unpack_from("<f", sd, 0)[0], 2)
                            elif rtype == b"BOOK" and len(sd) >= 10:
                                val, weight = struct.unpack_from("<If", sd, 2)
                                rec["value"] = val
                                rec["weight"] = round(weight, 2)
                            elif rtype in (b"KEYM", b"MISC") and len(sd) >= 8:
                                val, weight = struct.unpack_from("<If", sd, 0)
                                rec["value"] = val
                                rec["weight"] = round(weight, 2)
                        elif rtype == b"NOTE" and len(sd) >= 1:
                            note_type = sd[0]
                            rec["note_type"] = note_type
                        elif rtype == b"AMMO" and len(sd) >= 12:
                            # Speed(f), Flags(B), 3pad, Value(I)
                            rec["value"] = struct.unpack_from("<I", sd, 8)[0]
                    elif st == b"BMDT" and len(sd) >= 5:
                        if sd[4] & 0x40:
                            rec["playable"] = False
                    elif st == b"DNAM":
                        if rtype == b"ARMO" and len(sd) >= 2:
                            rec["dr"] = round(struct.unpack_from("<H", sd, 0)[0] / 100.0, 1)
                        elif rtype == b"WEAP" and len(sd) >= 16:
                            # Weapon DNAM flags1 at offset 12 or 1: bit 1 (0x02) Not Playable at offset 12
                            wflags = sd[12]
                            if wflags & 0x80:  # Non-playable in FO3 WEAP DNAM flags2
                                rec["playable"] = False
                    elif st == b"ENAM" and rtype == b"ALCH" and len(sd) >= 4:
                        rec["value"] = struct.unpack_from("<I", sd, 0)[0]
                    elif st == b"TNAM":
                        tname_raw = sd
                if rtype == b"NOTE" and tname_raw:
                    # note_type 1 = text note, 0 = sound, 2 = image, 3 = voice
                    if note_type == 1 or len(tname_raw) != 4:
                        rec["text"] = decode_zstr(tname_raw, "cp1251")

            elif rtype in OBJECT_TYPES:
                subtype_map = {
                    b"TERM": "terminal",
                    b"ACTI": "activator",
                    b"CONT": "container",
                    b"DOOR": "door",
                    b"PERK": "perk",
                }
                rec = objects.setdefault(
                    fid,
                    {
                        "fid": fid,
                        "subtype": subtype_map[rtype],
                        "dlc": origin_dlc,
                        "edid": "",
                        "name": "",
                        "name_en": eng_info.get("name_en", ""),
                        "desc": "",
                        "script_fid": 0,
                        "scro_fids": [],
                        "contents": [],
                        "menu_items": [],
                        "lock_diff": None,
                        "password_fid": 0,
                        "playable": True,
                        "min_level": 0,
                    },
                )
                cur_itxt = ""
                menu_items = []
                contents = []
                scro_fids = list(rec["scro_fids"])
                for st, sd in iter_subrecords(payload):
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"DESC":
                        rec["desc"] = decode_zstr(sd, "cp1251")
                    elif st == b"SCRI" and len(sd) >= 4:
                        rec["script_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"SCRO" and len(sd) >= 4:
                        scro_fids.append(remap(struct.unpack_from("<I", sd, 0)[0]))
                    elif st == b"CNTO" and len(sd) >= 8:
                        ifid, cnt = struct.unpack_from("<Ii", sd, 0)
                        contents.append({"fid": remap(ifid), "count": cnt})
                    elif st == b"DNAM" and rtype == b"TERM" and len(sd) >= 1:
                        rec["lock_diff"] = sd[0]
                    elif st == b"TNAM" and rtype == b"TERM" and len(sd) >= 4:
                        rec["password_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"ITXT" and rtype == b"TERM":
                        cur_itxt = decode_zstr(sd, "cp1251")
                    elif st == b"RNAM" and rtype == b"TERM":
                        rtxt = decode_zstr(sd, "cp1251")
                        if cur_itxt or rtxt:
                            menu_items.append({"title": cur_itxt, "text": rtxt})
                            cur_itxt = ""
                    elif st == b"DATA" and rtype == b"PERK" and len(sd) >= 5:
                        # trait(B), minLevel(B), ranks(B), playable(B), hidden(B)
                        rec["min_level"] = sd[1]
                        rec["playable"] = bool(sd[3]) and not bool(sd[4])
                if contents:
                    rec["contents"] = contents
                if menu_items:
                    rec["menu_items"] = menu_items
                if scro_fids:
                    rec["scro_fids"] = list(dict.fromkeys(scro_fids))

            elif rtype == b"QUST":
                rec = quests.setdefault(
                    fid,
                    {
                        "fid": fid,
                        "dlc": origin_dlc,
                        "edid": "",
                        "name": "",
                        "name_en": eng_info.get("name_en", ""),
                        "flags": 0,
                        "priority": 0,
                        "script_fid": 0,
                        "stages": {},  # stage_idx -> {flags, logs, scros, sctxs}
                        "objectives": {},  # obj_idx -> {text, targets}
                    },
                )
                cur_stage = None
                cur_obj = None
                for st, sd in iter_subrecords(payload):
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"DATA" and len(sd) >= 2:
                        rec["flags"] = sd[0]
                        rec["priority"] = sd[1]
                    elif st == b"SCRI" and len(sd) >= 4:
                        rec["script_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"INDX" and len(sd) >= 2:
                        cur_stage = struct.unpack_from("<H", sd, 0)[0]
                        cur_obj = None
                        rec["stages"].setdefault(str(cur_stage), {"stage": cur_stage, "flags": 0, "logs": [], "scros": [], "sctxs": []})
                    elif st == b"QSDT" and cur_stage is not None and len(sd) >= 1:
                        rec["stages"][str(cur_stage)]["flags"] |= sd[0]
                    elif st == b"CNAM" and cur_stage is not None:
                        log = decode_zstr(sd, "cp1251")
                        if log and log not in rec["stages"][str(cur_stage)]["logs"]:
                            rec["stages"][str(cur_stage)]["logs"].append(log)
                    elif st == b"SCTX" and cur_stage is not None:
                        sctx = decode_zstr(sd, "cp1251")
                        if sctx:
                            rec["stages"][str(cur_stage)]["sctxs"].append(sctx)
                    elif st == b"SCRO" and cur_stage is not None and len(sd) >= 4:
                        sfid = remap(struct.unpack_from("<I", sd, 0)[0])
                        if sfid and sfid not in rec["stages"][str(cur_stage)]["scros"]:
                            rec["stages"][str(cur_stage)]["scros"].append(sfid)
                    elif st == b"QOBJ" and len(sd) >= 4:
                        cur_obj = struct.unpack_from("<i", sd, 0)[0]
                        cur_stage = None
                        rec["objectives"].setdefault(str(cur_obj), {"index": cur_obj, "text": "", "targets": []})
                    elif st == b"NNAM" and cur_obj is not None:
                        txt = decode_zstr(sd, "cp1251")
                        if txt:
                            rec["objectives"][str(cur_obj)]["text"] = txt
                    elif st == b"QSTA" and cur_obj is not None and len(sd) >= 4:
                        tfid = remap(struct.unpack_from("<I", sd, 0)[0])
                        if tfid and tfid not in rec["objectives"][str(cur_obj)]["targets"]:
                            rec["objectives"][str(cur_obj)]["targets"].append(tfid)

            elif rtype == b"SCPT":
                rec = scripts.setdefault(
                    fid,
                    {
                        "fid": fid,
                        "edid": "",
                        "sctx": "",
                        "scros": [],
                    },
                )
                scros = []
                for st, sd in iter_subrecords(payload):
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"SCTX":
                        rec["sctx"] = decode_zstr(sd, "cp1251")
                    elif st == b"SCRO" and len(sd) >= 4:
                        scros.append(remap(struct.unpack_from("<I", sd, 0)[0]))
                if scros:
                    rec["scros"] = list(dict.fromkeys(scros))

            elif rtype == b"DIAL":
                rec = dialogues.setdefault(fid, {"fid": fid, "edid": "", "qstis": []})
                for st, sd in iter_subrecords(payload):
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"QSTI" and len(sd) >= 4:
                        qfid = remap(struct.unpack_from("<I", sd, 0)[0])
                        if qfid not in rec["qstis"]:
                            rec["qstis"].append(qfid)

            elif rtype == b"INFO":
                qsti = 0
                speaker_npcs = []
                scros = []
                sctx = ""
                for st, sd in iter_subrecords(payload):
                    if st == b"QSTI" and len(sd) >= 4:
                        qsti = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"CTDA" and len(sd) >= 20:
                        func_idx = struct.unpack_from("<H", sd, 8)[0]
                        p1 = struct.unpack_from("<I", sd, 12)[0]
                        if func_idx == CTDA_GET_IS_ID and p1:
                            speaker_npcs.append(remap(p1))
                    elif st == b"SCRO" and len(sd) >= 4:
                        scros.append(remap(struct.unpack_from("<I", sd, 0)[0]))
                    elif st == b"SCTX":
                        sctx = decode_zstr(sd, "cp1251")
                if not qsti and dial_fid in dialogues and dialogues[dial_fid]["qstis"]:
                    qsti = dialogues[dial_fid]["qstis"][0]
                if qsti and (speaker_npcs or scros):
                    quest_dialogue_links.append(
                        {
                            "quest_fid": qsti,
                            "speakers": speaker_npcs,
                            "scros": scros,
                            "has_additem": "additem" in sctx.lower() if sctx else False,
                        }
                    )

        print(f"[PARSE] {fname}: {rec_count} target records in {time.time() - t0:.2f}s")

    # Resolve references in item_placements: only keep items/objects that actually exist in items/objects dicts
    filtered_item_placements = [p for p in item_placements if p["base_fid"] in items]
    filtered_obj_placements = [p for p in item_placements if p["base_fid"] in objects]

    return {
        "factions": {str(k): v for k, v in factions.items()},
        "races": {str(k): v for k, v in races.items()},
        "npcs": {str(k): v for k, v in npcs.items()},
        "creatures": {str(k): v for k, v in creatures.items()},
        "worlds": {str(k): v for k, v in worlds.items()},
        "cells": {str(k): v for k, v in cells.items()},
        "markers": {str(k): v for k, v in markers.items()},
        "items": {str(k): v for k, v in items.items()},
        "objects": {str(k): v for k, v in objects.items()},
        "quests": {str(k): v for k, v in quests.items()},
        "scripts": {str(k): v for k, v in scripts.items()},
        "refs": {str(k): v for k, v in refs.items()},
        "npc_placements": npc_placements,
        "item_placements": filtered_item_placements,
        "obj_placements": filtered_obj_placements,
        "door_links": door_links,
        "object_locks": object_locks,
        "quest_dialogue_links": quest_dialogue_links,
    }


def main():
    t0 = time.time()
    print("[1/3] Extracting English names from ENG/Data/*.esm ...")
    eng_names = extract_eng_names()
    print(f"      Captured {len(eng_names)} ENG entries in {time.time() - t0:.2f}s")

    print("[2/3] Parsing Russian GOTY ESMs from RUS/Data/*.esm ...")
    parsed = parse_rus_esms(eng_names)

    print("[3/3] Writing", OUT_PATH)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False)

    print("=== PARSE SUMMARY ===")
    for key in ["factions", "races", "npcs", "creatures", "worlds", "cells", "markers", "items", "objects", "quests", "scripts"]:
        print(f"  {key:14s}: {len(parsed[key])}")
    for key in ["npc_placements", "item_placements", "obj_placements", "door_links", "object_locks", "quest_dialogue_links"]:
        print(f"  {key:20s}: {len(parsed[key])}")

    # Sample Russian names
    sample_quests = [v["name"] for v in parsed["quests"].values() if v["name"]][:10]
    sample_markers = [v["name"] for v in parsed["markers"].values() if v["name"]][:10]
    print("  Sample quests :", sample_quests)
    print("  Sample markers:", sample_markers)


if __name__ == "__main__":
    main()
