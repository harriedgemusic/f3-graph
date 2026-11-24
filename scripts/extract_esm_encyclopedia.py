#!/usr/bin/env python3
"""
Extract deep structured Russian encyclopedia metadata from all 6 Fallout 3 GOTY
RUS .esm files into /tmp/f3_encyclopedia/esm_rich.json keyed by node["id"] from
public/data/graph.json.
"""

from __future__ import annotations

import json
import re
import struct
import sys
import time
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from parse_esm import (  # noqa: E402
    DLC_BY_GLOBAL_IDX,
    ESMS,
    REC_HDR,
    decode_zstr,
    iter_subrecords,
    make_remapper,
    read_tes4_masters,
)

ESM_DIR = Path("/tmp/f3_encyclopedia/esm_raw")
GRAPH_PATH = REPO_ROOT / "public" / "data" / "graph.json"
DETAILS_PATH = REPO_ROOT / "public" / "data" / "details.json"
OUT_PATH = Path("/tmp/f3_encyclopedia/esm_rich.json")

TARGET_TYPES = {
    b"TES4",
    b"AVIF",
    b"MGEF",
    b"ENCH",
    b"SPEL",
    b"FACT",
    b"RACE",
    b"PACK",
    b"NPC_",
    b"CREA",
    b"WRLD",
    b"CELL",
    b"REFR",
    b"ACHR",
    b"ACRE",
    b"QUST",
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

CTDA_GET_IS_ID = 72
CTDA_GET_AV = 14
CTDA_HAS_PERK = 449
CTDA_GET_PERM_AV = 495

WEAPON_CLASS_RU = {
    0: "Рукопашное оружие",
    1: "Одноручное холодное оружие",
    2: "Двуручное холодное оружие",
    3: "Пистолет",
    4: "Энергетический пистолет",
    5: "Винтовка",
    6: "Автомат / Карабин",
    7: "Энергетическая винтовка",
    8: "Тяжёлое оружие",
    9: "Огнемёт / Ракетомёт",
    10: "Граната",
    11: "Мина",
    12: "Мина (спец.)",
    13: "Метательное оружие",
}

ACTOR_VALUES_RU = {
    0: "Агрессивность",
    1: "Уверенность",
    2: "Энергичность",
    3: "Ответственность",
    4: "Настроение",
    5: "Сила",
    6: "Восприятие",
    7: "Выносливость",
    8: "Харизма",
    9: "Интеллект",
    10: "Ловкость",
    11: "Удача",
    12: "Очки действия",
    13: "Макс. вес",
    14: "Шанс крит. удара",
    15: "Скорость лечения",
    16: "Здоровье",
    17: "Урон в ближнем бою",
    18: "Сопротивление урону",
    19: "Сопротивление ядам",
    20: "Сопротивление радиации",
    21: "Скорость передвижения",
    32: "Бартер",
    33: "Тяжёлое оружие",
    34: "Энергетическое оружие",
    35: "Взрывчатка",
    36: "Взлом",
    37: "Медицина",
    38: "Холодное оружие",
    39: "Ремонт",
    40: "Наука",
    41: "Лёгкое оружие",
    42: "Скрытность",
    43: "Красноречие",
    45: "Без оружия",
    54: "Радиация",
}

BOOK_SKILL_RU = {
    0: "Бартер",
    1: "Тяжёлое оружие",
    2: "Энергетическое оружие",
    3: "Взрывчатка",
    4: "Взлом",
    5: "Медицина",
    6: "Холодное оружие",
    7: "Ремонт",
    8: "Наука",
    9: "Лёгкое оружие",
    10: "Скрытность",
    11: "Красноречие",
    13: "Без оружия",
}

AGGRESSION_RU = {
    0: "Мирный",
    1: "Агрессивный",
    2: "Очень агрессивный",
    3: "Берсерк",
}

CONFIDENCE_RU = {
    0: "Трусливый",
    1: "Осторожный",
    2: "Средний",
    3: "Смелый",
    4: "Безрассудный",
}

MOOD_RU = {
    0: "Нейтральное",
    1: "Испуганное",
    2: "Раздражённое",
    3: "Радостное",
    4: "Печальное",
    5: "Удивлённое",
    6: "Озадаченное",
    7: "Отвращение",
}

PACKAGE_TYPE_RU = {
    0: "поиск",
    1: "сопровождение",
    2: "эскорт",
    3: "приём пищи",
    4: "сон",
    5: "патруль",
    6: "перемещение",
    7: "сопровождение",
    8: "работа с объектом",
    9: "засада",
    10: "бегство",
    11: "применение эффекта",
    12: "быт / свободное поведение",
    13: "патруль",
    14: "охрана",
    15: "диалог / встреча",
    16: "бой",
}

AIDT_SERVICES_RU = [
    (0x00000001, "Оружие"),
    (0x00000002, "Броня"),
    (0x00000004, "Алкоголь"),
    (0x00000008, "Книги и схемы"),
    (0x00000010, "Еда"),
    (0x00000020, "Химия и медикаменты"),
    (0x00000040, "Припасы / торговля"),
    (0x00000080, "Снаряжение"),
    (0x00000400, "Хлам и разное"),
    (0x00002000, "Одежда и товары"),
    (0x00010000, "Обучение"),
    (0x00020000, "Ремонт"),
]

MARKER_TYPES_RU = {
    0: "Нет маркера",
    1: "Город",
    2: "Поселение",
    3: "Лагерь",
    4: "Природный объект",
    5: "Убежище",
    6: "Памятник",
    7: "Пещера",
    8: "Завод / Фабрика",
    9: "Метро",
    10: "Офисное здание",
    11: "Городские руины",
    12: "Заброшенный город",
    13: "Канализация / Коллектор",
    14: "Военная база",
}

TERM_LOCK_RU = {
    0: "Очень лёгкий (0)",
    1: "Лёгкий (25)",
    2: "Средний (50)",
    3: "Сложный (75)",
    4: "Очень сложный (100)",
    5: "Требуется ключ",
}

NOTE_TYPE_RU = {
    0: "Аудиозапись",
    1: "Текстовая заметка",
    2: "Изображение",
    3: "Голосовая голозапись",
}

IGNORED_LOC_RE = re.compile(
    r"(?:^test|^zz|^aa[a-z]|dummy|holding|warehouse|chargen|preview)",
    re.I,
)

TAG_RE = re.compile(r"[<>&{}\[\]]")
BOOK_HTML_RE = re.compile(r"<(?:div|br|p|font|img|/div|/p|/font)\b[^>]*>", re.I)
SPACE_RE = re.compile(r"\s+")
CYR_RE = re.compile(r"[А-Яа-яЁё]")
END_PUNCT_RE = re.compile(r"[.!?…»\"]$")


def clean_text(s: str) -> str:
    return SPACE_RE.sub(" ", (s or "")).strip()


def xloc_lock_label(level: int | None) -> str:
    if level is None:
        return ""
    if level == 255:
        return "Требуется ключ"
    if level == 0:
        return "Очень лёгкий (0)"
    if level <= 25:
        return "Лёгкий (25)"
    if level <= 50:
        return "Средний (50)"
    if level <= 75:
        return "Сложный (75)"
    if level <= 100:
        return "Очень сложный (100)"
    return f"Уровень {level}"


def iter_records_all(
    buf: memoryview,
    start: int,
    end: int,
    wrld_fid: int = 0,
    cell_fid: int = 0,
    dial_fid: int = 0,
    remap=None,
):
    """Iterate target ESM records while preserving GRUP WRLD/CELL/DIAL hierarchy."""
    pos = start
    while pos + 24 <= end:
        magic, size, flags, fid, _, _, _ = REC_HDR.unpack_from(buf, pos)
        if magic == b"GRUP":
            g_size = size
            label_bytes = buf[pos + 8 : pos + 12].tobytes()
            g_type = fid
            sub_wrld = wrld_fid
            sub_cell = cell_fid
            sub_dial = dial_fid
            if g_type == 0:
                if label_bytes not in TARGET_TYPES:
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
                yield from iter_records_all(
                    buf, pos + 24, grp_end, sub_wrld, sub_cell, sub_dial, remap
                )
            pos = grp_end
        else:
            rec_end = min(pos + 24 + size, end)
            if magic in TARGET_TYPES:
                is_deleted = bool(flags & 0x00000020)
                if is_deleted:
                    yield magic, flags, fid, wrld_fid, cell_fid, dial_fid, None
                else:
                    payload_mv = buf[pos + 24 : rec_end]
                    if flags & 0x00040000:
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


def decode_services(svc_flags: int) -> list[str]:
    if not svc_flags:
        return []
    out = [label for bit, label in AIDT_SERVICES_RU if svc_flags & bit]
    return out


def compute_npc_level_and_hp(
    acbs_flags: int, raw_lv: int, calc_min: int, calc_max: int, base_hp: int, end_stat: int
) -> tuple[int, str | None, int]:
    is_pc_mult = bool(acbs_flags & 0x80)
    if is_pc_mult:
        mult = round(raw_lv / 1000.0, 2)
        eff_lv = max(1, calc_min)
        max_s = str(calc_max) if calc_max > 0 else "∞"
        lv_range = f"{eff_lv}–{max_s} (×{mult:g} ур. игрока)"
    else:
        eff_lv = max(1, raw_lv)
        lv_range = None
    hp = max(10, int(base_hp + end_stat * 5 + max(0, eff_lv - 1) * 5))
    return eff_lv, lv_range, hp


def parse_effects_from_subs(subs: list[tuple[bytes, bytes]], remap) -> list[dict[str, Any]]:
    effs: list[dict[str, Any]] = []
    cur_mgef = 0
    for st, sd in subs:
        if st == b"EFID" and len(sd) >= 4:
            cur_mgef = remap(struct.unpack_from("<I", sd, 0)[0])
        elif st == b"EFIT" and len(sd) >= 20 and cur_mgef:
            mag, area, dur, rtype, av = struct.unpack_from("<IIIIi", sd, 0)
            effs.append(
                {
                    "mgef_fid": cur_mgef,
                    "magnitude": mag,
                    "area": area,
                    "duration": dur,
                    "range": rtype,
                    "actor_value": av,
                }
            )
            cur_mgef = 0
    return effs


def format_effect_list(
    raw_effects: list[dict[str, Any]], mgefs: dict[int, dict[str, Any]]
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for ef in raw_effects:
        mg = mgefs.get(ef["mgef_fid"], {})
        mg_edid = mg.get("edid", "")
        mg_name = clean_text(mg.get("name", ""))
        mg_desc = clean_text(mg.get("desc", ""))
        mg_flags = mg.get("flags", 0)
        mag = ef["magnitude"]
        dur = ef["duration"]
        av = ef["actor_value"]

        # Skip long-duration addiction trigger dummy entries (30+ in-game hours)
        if "addict" in mg_edid.lower() and dur >= 36000 and mag <= 30 and av == -1:
            continue

        av_name = ACTOR_VALUES_RU.get(av, "")
        is_negative = bool(mg_flags & 0x04) or mg_edid.lower().startswith(
            ("reduce", "damage", "addict", "restoreradiation")
        )
        sign = "-" if is_negative else "+"

        text = ""
        if av_name and mag > 0:
            unit = "%" if av in (18, 19, 20) else ""
            if "poison" in mg_edid.lower() or "яд" in mg_name.lower():
                text = f"Яд: -{mag} {av_name}/сек"
            elif mg_name and ("сопротивлен" in mg_name.lower() or "увеличение" in mg_name.lower() or "уменьшение" in mg_name.lower() or "восстановление" in mg_name.lower()):
                text = f"{av_name} {sign}{mag}{unit}"
            elif mg_name and CYR_RE.search(mg_name):
                text = f"{mg_name}: {sign}{mag}{unit}"
            else:
                text = f"{av_name} {sign}{mag}{unit}"
        elif mg_name and CYR_RE.search(mg_name):
            text = f"{mg_name} ({mag})" if mag > 0 else mg_name
        elif mg_desc and CYR_RE.search(mg_desc):
            text = mg_desc

        if not text:
            continue
        if 0 < dur < 36000:
            text += f" ({dur} сек.)"
        if text not in seen:
            seen.add(text)
            out.append(text)
    return out


def is_clean_quote(text: str) -> bool:
    if not text or len(text) < 20 or len(text) > 220:
        return False
    if TAG_RE.search(text):
        return False
    if not CYR_RE.search(text):
        return False
    low = text.lower()
    if any(bad in low for bad in ("todo", "temp", "dummy", "тест", "placeholder")):
        return False
    return True


def parse_all_rus_esms() -> dict[str, Any]:
    avifs: dict[int, dict[str, Any]] = {}
    mgefs: dict[int, dict[str, Any]] = {}
    enchs: dict[int, dict[str, Any]] = {}
    spels: dict[int, dict[str, Any]] = {}
    factions: dict[int, dict[str, Any]] = {}
    races: dict[int, dict[str, Any]] = {}
    packages: dict[int, dict[str, Any]] = {}
    npcs: dict[int, dict[str, Any]] = {}
    creatures: dict[int, dict[str, Any]] = {}
    worlds: dict[int, dict[str, Any]] = {}
    cells: dict[int, dict[str, Any]] = {}
    markers: dict[int, dict[str, Any]] = {}
    items: dict[int, dict[str, Any]] = {}
    objects: dict[int, dict[str, Any]] = {}
    quests: dict[int, dict[str, Any]] = {}
    dialogues: dict[int, dict[str, Any]] = {}
    refs: dict[int, dict[str, Any]] = {}
    deleted_refs: set[int] = set()
    dial_infos: dict[int, list[dict[str, Any]]] = defaultdict(list)
    npc_quotes_raw: dict[int, list[str]] = defaultdict(list)

    for idx, (fname, dlc_id, _) in enumerate(ESMS):
        fpath = ESM_DIR / fname
        if not fpath.exists():
            raise FileNotFoundError(f"Missing RUS ESM: {fpath}")
        t0 = time.time()
        raw = fpath.read_bytes()
        mv = memoryview(raw)
        masters, body_start = read_tes4_masters(mv)
        remap = make_remapper(masters, idx)
        rec_count = 0

        for rtype, flags, raw_fid, wrld_fid, cell_fid, dial_fid, payload in iter_records_all(
            mv, body_start, len(raw), remap=remap
        ):
            rec_count += 1
            fid = remap(raw_fid)
            origin_dlc = DLC_BY_GLOBAL_IDX.get((fid >> 24) & 0xFF, dlc_id)

            if payload is None:
                if rtype in (b"REFR", b"ACHR", b"ACRE"):
                    deleted_refs.add(fid)
                    refs.pop(fid, None)
                    markers.pop(fid, None)
                continue

            subs = list(iter_subrecords(payload))

            if rtype == b"AVIF":
                rec = avifs.setdefault(fid, {"fid": fid, "edid": "", "name": ""})
                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")

            elif rtype == b"MGEF":
                rec = mgefs.setdefault(
                    fid, {"fid": fid, "edid": "", "name": "", "desc": "", "flags": 0, "av": -1}
                )
                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"DESC":
                        rec["desc"] = decode_zstr(sd, "cp1251")
                    elif st == b"DATA" and len(sd) >= 72:
                        rec["flags"] = struct.unpack_from("<I", sd, 0)[0]
                        rec["av"] = struct.unpack_from("<i", sd, 68)[0]

            elif rtype in (b"ENCH", b"SPEL"):
                target = enchs if rtype == b"ENCH" else spels
                rec = target.setdefault(fid, {"fid": fid, "edid": "", "name": "", "effects": []})
                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                effs = parse_effects_from_subs(subs, remap)
                if effs:
                    rec["effects"] = effs

            elif rtype == b"FACT":
                rec = factions.setdefault(fid, {"fid": fid, "edid": "", "name": ""})
                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")

            elif rtype == b"RACE":
                rec = races.setdefault(fid, {"fid": fid, "edid": "", "name": ""})
                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")

            elif rtype == b"PACK":
                rec = packages.setdefault(
                    fid, {"fid": fid, "edid": "", "ptype": None, "gflags": 0}
                )
                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"PKDT" and len(sd) >= 5:
                        rec["gflags"] = struct.unpack_from("<I", sd, 0)[0]
                        rec["ptype"] = sd[4]

            elif rtype == b"NPC_":
                rec = npcs.setdefault(
                    fid,
                    {
                        "fid": fid,
                        "dlc": origin_dlc,
                        "edid": "",
                        "name": "",
                        "race_fid": 0,
                        "level": 1,
                        "level_range": None,
                        "hp": 50,
                        "female": False,
                        "essential": False,
                        "unique": False,
                        "special": [5, 5, 5, 5, 5, 5, 5],
                        "aggression": 0,
                        "confidence": 2,
                        "mood": 0,
                        "services_flags": 0,
                        "packages": [],
                        "factions": [],
                        "inventory": [],
                        "template_fid": 0,
                    },
                )
                acbs_parsed = None
                base_hp = 10
                end_stat = 5
                pkids: list[int] = []
                facs: list[dict[str, Any]] = []
                inv: list[dict[str, Any]] = []
                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"RNAM" and len(sd) >= 4:
                        rec["race_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"TPLT" and len(sd) >= 4:
                        rec["template_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"ACBS" and len(sd) >= 16:
                        acbs_flags, _, _, raw_lv, calc_min, calc_max = struct.unpack_from(
                            "<IHHhHH", sd, 0
                        )
                        rec["female"] = bool(acbs_flags & 0x01)
                        rec["essential"] = bool(acbs_flags & 0x02)
                        rec["unique"] = bool(acbs_flags & 0x20)
                        acbs_parsed = (acbs_flags, raw_lv, calc_min, calc_max)
                    elif st == b"DATA" and len(sd) >= 11:
                        base_hp, s, p, e, c, i_st, a, l = struct.unpack_from("<I7B", sd, 0)
                        end_stat = e
                        rec["special"] = [s, p, e, c, i_st, a, l]
                    elif st == b"AIDT" and len(sd) >= 12:
                        rec["aggression"] = sd[0]
                        rec["confidence"] = sd[1]
                        rec["mood"] = sd[4]
                        rec["services_flags"] = struct.unpack_from("<I", sd, 8)[0]
                    elif st == b"PKID" and len(sd) >= 4:
                        pkids.append(remap(struct.unpack_from("<I", sd, 0)[0]))
                    elif st == b"SNAM" and len(sd) >= 5:
                        ffid, rank = struct.unpack_from("<Ib", sd, 0)
                        facs.append({"fid": remap(ffid), "rank": rank})
                    elif st == b"CNTO" and len(sd) >= 8:
                        ifid, cnt = struct.unpack_from("<Ii", sd, 0)
                        inv.append({"fid": remap(ifid), "count": cnt})
                if acbs_parsed is not None:
                    lv, lv_range, hp = compute_npc_level_and_hp(
                        *acbs_parsed, base_hp, end_stat
                    )
                    rec["level"] = lv
                    rec["level_range"] = lv_range
                    rec["hp"] = hp
                if pkids:
                    rec["packages"] = pkids
                if facs:
                    rec["factions"] = facs
                if inv:
                    rec["inventory"] = inv

            elif rtype == b"CREA":
                rec = creatures.setdefault(
                    fid,
                    {
                        "fid": fid,
                        "dlc": origin_dlc,
                        "edid": "",
                        "name": "",
                        "level": 1,
                        "level_range": None,
                        "hp": 50,
                        "attack_damage": 0,
                        "aggression": 1,
                        "confidence": 2,
                        "essential": False,
                        "modl": "",
                        "factions": [],
                        "drops": [],
                    },
                )
                facs = []
                drops = []
                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"MODL":
                        rec["modl"] = decode_zstr(sd, "cp1251")
                    elif st == b"ACBS" and len(sd) >= 16:
                        acbs_flags, _, _, raw_lv, calc_min, calc_max = struct.unpack_from(
                            "<IHHhHH", sd, 0
                        )
                        rec["essential"] = bool(acbs_flags & 0x02)
                        if acbs_flags & 0x80:
                            rec["level"] = max(1, calc_min)
                            mult = round(raw_lv / 1000.0, 2)
                            max_s = str(calc_max) if calc_max > 0 else "∞"
                            rec["level_range"] = f"{max(1, calc_min)}–{max_s} (×{mult:g} ур. игрока)"
                        else:
                            rec["level"] = max(1, raw_lv)
                            rec["level_range"] = None
                    elif st == b"DATA" and len(sd) >= 10:
                        rec["hp"] = struct.unpack_from("<H", sd, 4)[0]
                        rec["attack_damage"] = struct.unpack_from("<H", sd, 8)[0]
                    elif st == b"AIDT" and len(sd) >= 2:
                        rec["aggression"] = sd[0]
                        rec["confidence"] = sd[1]
                    elif st == b"SNAM" and len(sd) >= 5:
                        ffid, rank = struct.unpack_from("<Ib", sd, 0)
                        facs.append({"fid": remap(ffid), "rank": rank})
                    elif st == b"CNTO" and len(sd) >= 8:
                        ifid, cnt = struct.unpack_from("<Ii", sd, 0)
                        drops.append({"fid": remap(ifid), "count": cnt})
                if facs:
                    rec["factions"] = facs
                if drops:
                    rec["drops"] = drops

            elif rtype == b"WRLD":
                rec = worlds.setdefault(
                    fid, {"fid": fid, "dlc": origin_dlc, "edid": "", "name": "", "parent_wrld": 0}
                )
                for st, sd in subs:
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
                        "is_interior": wrld_fid == 0,
                        "owner_fid": 0,
                        "grid": None,
                    },
                )
                if wrld_fid and not rec["wrld_fid"]:
                    rec["wrld_fid"] = wrld_fid
                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"DATA" and len(sd) >= 1:
                        rec["is_interior"] = bool(sd[0] & 0x01)
                    elif st == b"XOWN" and len(sd) >= 4:
                        rec["owner_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"XCLC" and len(sd) >= 8:
                        rec["grid"] = list(struct.unpack_from("<ii", sd, 0))
                if rec["wrld_fid"] == 0:
                    rec["is_interior"] = True

            elif rtype in (b"REFR", b"ACHR", b"ACRE"):
                deleted_refs.discard(fid)
                prev = refs.get(fid, {})
                base_fid = prev.get("base_fid", 0)
                edid = prev.get("edid", "")
                pos_xyz = prev.get("pos")
                is_marker = prev.get("is_marker", False)
                marker_name = prev.get("marker_name", "")
                marker_type = prev.get("marker_type", 0)
                xtel_dest = prev.get("xtel_dest", 0)
                lock_level = prev.get("lock_level")
                key_fid = prev.get("key_fid", 0)
                owner_fid = prev.get("owner_fid", 0)
                r_wrld = wrld_fid or prev.get("wrld_fid", 0)
                r_cell = cell_fid or prev.get("cell_fid", 0)

                for st, sd in subs:
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
                    elif st == b"XOWN" and len(sd) >= 4:
                        owner_fid = remap(struct.unpack_from("<I", sd, 0)[0])

                refs[fid] = {
                    "fid": fid,
                    "rtype": rtype.decode("ascii"),
                    "base_fid": base_fid,
                    "wrld_fid": r_wrld,
                    "cell_fid": r_cell,
                    "edid": edid,
                    "pos": pos_xyz,
                    "is_marker": is_marker,
                    "marker_name": marker_name,
                    "marker_type": marker_type,
                    "xtel_dest": xtel_dest,
                    "lock_level": lock_level,
                    "key_fid": key_fid,
                    "owner_fid": owner_fid,
                }
                if is_marker and marker_name:
                    markers[fid] = {
                        "fid": fid,
                        "dlc": origin_dlc,
                        "wrld_fid": r_wrld,
                        "cell_fid": r_cell,
                        "edid": edid,
                        "name": marker_name,
                        "marker_type": marker_type,
                        "pos": pos_xyz,
                    }

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
                        "value": 0,
                        "weight": 0.0,
                        "health": 0,
                        "damage": 0,
                        "clip_size": 0,
                        "dr": 0.0,
                        "weapon_class": "",
                        "skill": "",
                        "fire_rate": 0.0,
                        "ap_cost": 0.0,
                        "min_spread": 0.0,
                        "max_spread": 0.0,
                        "crit_damage": 0,
                        "crit_mult": 0.0,
                        "ammo_fid": 0,
                        "ench_fid": 0,
                        "effects_raw": [],
                        "addiction_chance": 0.0,
                        "speed": 0.0,
                        "clip_rounds": 0,
                        "short_name": "",
                        "skill_taught": "",
                        "note_type": 0,
                        "tname_fid": 0,
                        "text": "",
                    },
                )
                note_type = rec["note_type"]
                tname_raw = b""
                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"DESC":
                        txt = decode_zstr(sd, "cp1251")
                        if txt:
                            rec["text"] = txt
                    elif st == b"EITM" and len(sd) >= 4:
                        rec["ench_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"NAM0" and rtype == b"WEAP" and len(sd) >= 4:
                        rec["ammo_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"ONAM" and rtype == b"AMMO":
                        rec["short_name"] = decode_zstr(sd, "cp1251")
                    elif st == b"DATA":
                        if rtype == b"WEAP" and len(sd) >= 15:
                            val, hp, wt, dmg, clip = struct.unpack_from("<IIfHB", sd, 0)
                            rec["value"] = val
                            rec["health"] = hp
                            rec["weight"] = round(wt, 2)
                            rec["damage"] = dmg
                            rec["clip_size"] = clip
                        elif rtype == b"ARMO" and len(sd) >= 12:
                            val, hp, wt = struct.unpack_from("<IIf", sd, 0)
                            rec["value"] = val
                            rec["health"] = hp
                            rec["weight"] = round(wt, 2)
                        elif rtype == b"ALCH" and len(sd) >= 4:
                            rec["weight"] = round(struct.unpack_from("<f", sd, 0)[0], 2)
                        elif rtype == b"BOOK" and len(sd) >= 10:
                            _, teaches, val, wt = struct.unpack_from("<BbIf", sd, 0)
                            rec["value"] = val
                            rec["weight"] = round(wt, 2)
                            if teaches >= 0:
                                rec["skill_taught"] = BOOK_SKILL_RU.get(teaches, "")
                        elif rtype in (b"KEYM", b"MISC") and len(sd) >= 8:
                            val, wt = struct.unpack_from("<If", sd, 0)
                            rec["value"] = val
                            rec["weight"] = round(wt, 2)
                        elif rtype == b"NOTE" and len(sd) >= 1:
                            note_type = sd[0]
                            rec["note_type"] = note_type
                        elif rtype == b"AMMO" and len(sd) >= 12:
                            spd = struct.unpack_from("<f", sd, 0)[0]
                            val = struct.unpack_from("<I", sd, 8)[0]
                            clip_r = sd[12] if len(sd) >= 13 else 0
                            rec["speed"] = round(spd, 2)
                            rec["value"] = val
                            rec["clip_rounds"] = clip_r
                    elif st == b"DNAM":
                        if rtype == b"ARMO" and len(sd) >= 2:
                            rec["dr"] = round(struct.unpack_from("<H", sd, 0)[0] / 100.0, 1)
                        elif rtype == b"WEAP" and len(sd) >= 108:
                            anim = struct.unpack_from("<I", sd, 0)[0]
                            min_sp = struct.unpack_from("<f", sd, 16)[0]
                            max_sp = struct.unpack_from("<f", sd, 20)[0]
                            ap_cost = struct.unpack_from("<f", sd, 68)[0]
                            fr_88 = struct.unpack_from("<f", sd, 88)[0]
                            fr_64 = struct.unpack_from("<f", sd, 64)[0]
                            skill_idx = struct.unpack_from("<i", sd, 104)[0]
                            rec["weapon_class"] = WEAPON_CLASS_RU.get(anim, f"Класс {anim}")
                            rec["min_spread"] = round(min_sp, 3)
                            rec["max_spread"] = round(max_sp, 3)
                            rec["ap_cost"] = round(ap_cost, 1)
                            rec["fire_rate"] = round(fr_88 if fr_88 > 0 else fr_64, 3)
                            rec["skill"] = ACTOR_VALUES_RU.get(skill_idx, "")
                    elif st == b"CRDT" and rtype == b"WEAP" and len(sd) >= 8:
                        cdmg, _, cmult = struct.unpack_from("<HHf", sd, 0)
                        rec["crit_damage"] = cdmg
                        rec["crit_mult"] = round(cmult, 2)
                    elif st == b"ENIT" and rtype == b"ALCH" and len(sd) >= 16:
                        val, _, _, add_ch = struct.unpack_from("<IIIf", sd, 0)
                        rec["value"] = val
                        rec["addiction_chance"] = round(add_ch, 2)
                    elif st == b"TNAM" and rtype == b"NOTE":
                        tname_raw = sd

                if rtype == b"ALCH":
                    effs = parse_effects_from_subs(subs, remap)
                    if effs:
                        rec["effects_raw"] = effs
                if rtype == b"NOTE" and tname_raw:
                    if note_type == 1:
                        rec["text"] = decode_zstr(tname_raw, "cp1251")
                    elif len(tname_raw) == 4:
                        rec["tname_fid"] = remap(struct.unpack_from("<I", tname_raw, 0)[0])
                    else:
                        txt = decode_zstr(tname_raw, "cp1251")
                        if CYR_RE.search(txt):
                            rec["text"] = txt

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
                        "desc": "",
                        "contents": [],
                        "menu_items": [],
                        "lock_diff": "",
                        "unlocked": False,
                        "password_fid": 0,
                        "min_level": 1,
                        "ranks": 1,
                        "conditions": [],
                    },
                )
                cur_itxt = ""
                cur_rnam = ""
                cur_inam = 0
                menu_items: list[dict[str, Any]] = []
                contents: list[dict[str, Any]] = []
                in_perk_entries = False
                perk_conds: list[dict[str, Any]] = []

                def flush_term_item():
                    nonlocal cur_itxt, cur_rnam, cur_inam
                    if cur_itxt or cur_rnam or cur_inam:
                        menu_items.append(
                            {"title": cur_itxt, "text": cur_rnam, "note_fid": cur_inam}
                        )
                        cur_itxt = ""
                        cur_rnam = ""
                        cur_inam = 0

                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"DESC":
                        rec["desc"] = decode_zstr(sd, "cp1251")
                    elif st == b"CNTO" and len(sd) >= 8:
                        ifid, cnt = struct.unpack_from("<Ii", sd, 0)
                        contents.append({"fid": remap(ifid), "count": cnt})
                    elif st == b"DNAM" and rtype == b"TERM" and len(sd) >= 2:
                        rec["unlocked"] = bool(sd[1] & 0x02)
                        rec["lock_diff"] = (
                            "Разблокирован"
                            if rec["unlocked"]
                            else TERM_LOCK_RU.get(sd[0], f"Уровень {sd[0]}")
                        )
                    elif st == b"TNAM" and rtype == b"TERM" and len(sd) >= 4:
                        rec["password_fid"] = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"ITXT" and rtype == b"TERM":
                        flush_term_item()
                        cur_itxt = decode_zstr(sd, "cp1251")
                    elif st == b"RNAM" and rtype == b"TERM":
                        if sd != b"\x00\x00\x00\x00":
                            cur_rnam = decode_zstr(sd, "cp1251")
                    elif st == b"INAM" and rtype == b"TERM" and len(sd) >= 4:
                        cur_inam = remap(struct.unpack_from("<I", sd, 0)[0])
                    elif st == b"DATA" and rtype == b"PERK" and len(sd) >= 5 and not in_perk_entries:
                        rec["min_level"] = max(1, sd[1])
                        rec["ranks"] = max(1, sd[2])
                    elif st == b"PRKE" and rtype == b"PERK":
                        in_perk_entries = True
                    elif st == b"CTDA" and rtype == b"PERK" and not in_perk_entries and len(sd) >= 20:
                        ctype, _, cval, func, _, p1, _ = struct.unpack_from("<B3sfH2sII", sd, 0)
                        perk_conds.append(
                            {"op": (ctype >> 5) & 0x7, "val": cval, "func": func, "p1": p1}
                        )
                if rtype == b"TERM":
                    flush_term_item()
                if contents:
                    rec["contents"] = contents
                if menu_items:
                    rec["menu_items"] = menu_items
                if perk_conds:
                    rec["conditions"] = perk_conds

            elif rtype == b"QUST":
                rec = quests.setdefault(
                    fid,
                    {
                        "fid": fid,
                        "dlc": origin_dlc,
                        "edid": "",
                        "name": "",
                        "stages": {},
                        "objectives": {},
                    },
                )
                cur_stage = None
                cur_obj = None
                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")
                    elif st == b"FULL":
                        rec["name"] = decode_zstr(sd, "cp1251")
                    elif st == b"INDX" and len(sd) >= 2:
                        cur_stage = struct.unpack_from("<H", sd, 0)[0]
                        cur_obj = None
                        rec["stages"].setdefault(
                            str(cur_stage),
                            {"stage": cur_stage, "flags": 0, "logs": [], "scros": []},
                        )
                    elif st == b"QSDT" and cur_stage is not None and len(sd) >= 1:
                        rec["stages"][str(cur_stage)]["flags"] |= sd[0]
                    elif st == b"CNAM" and cur_stage is not None:
                        log = clean_text(decode_zstr(sd, "cp1251"))
                        if log and log not in rec["stages"][str(cur_stage)]["logs"]:
                            rec["stages"][str(cur_stage)]["logs"].append(log)
                    elif st == b"SCRO" and cur_stage is not None and len(sd) >= 4:
                        sfid = remap(struct.unpack_from("<I", sd, 0)[0])
                        if sfid and sfid not in rec["stages"][str(cur_stage)]["scros"]:
                            rec["stages"][str(cur_stage)]["scros"].append(sfid)
                    elif st == b"QOBJ" and len(sd) >= 4:
                        cur_obj = struct.unpack_from("<i", sd, 0)[0]
                        cur_stage = None
                        rec["objectives"].setdefault(
                            str(cur_obj), {"index": cur_obj, "text": ""}
                        )
                    elif st == b"NNAM" and cur_obj is not None:
                        txt = clean_text(decode_zstr(sd, "cp1251"))
                        if txt:
                            rec["objectives"][str(cur_obj)]["text"] = txt

            elif rtype == b"DIAL":
                rec = dialogues.setdefault(fid, {"fid": fid, "edid": ""})
                for st, sd in subs:
                    if st == b"EDID":
                        rec["edid"] = decode_zstr(sd, "cp1251")

            elif rtype == b"INFO":
                nam1_texts: list[str] = []
                get_is_ids: list[int] = []
                has_bad_cond = False
                for st, sd in subs:
                    if st == b"NAM1":
                        txt = clean_text(decode_zstr(sd, "cp1251"))
                        if txt:
                            nam1_texts.append(txt)
                    elif st == b"CTDA" and len(sd) >= 20:
                        ctype, _, cval, func, _, p1, _ = struct.unpack_from("<B3sfH2sII", sd, 0)
                        op = (ctype >> 5) & 0x7
                        if func == CTDA_GET_IS_ID and p1:
                            if op == 0 and abs(cval - 1.0) < 0.01:
                                get_is_ids.append(remap(p1))
                            elif op == 1 or abs(cval) < 0.01:
                                has_bad_cond = True
                if dial_fid and nam1_texts:
                    dial_infos[dial_fid].append({"texts": nam1_texts, "speakers": get_is_ids})
                if get_is_ids and not has_bad_cond and nam1_texts:
                    for t in nam1_texts:
                        if is_clean_quote(t):
                            for sp_fid in get_is_ids:
                                npc_quotes_raw[sp_fid].append(t)

        print(f"[PARSE] {fname}: {rec_count} records in {time.time() - t0:.2f}s")

    return {
        "avifs": avifs,
        "mgefs": mgefs,
        "enchs": enchs,
        "spels": spels,
        "factions": factions,
        "races": races,
        "packages": packages,
        "npcs": npcs,
        "creatures": creatures,
        "worlds": worlds,
        "cells": cells,
        "markers": markers,
        "items": items,
        "objects": objects,
        "quests": quests,
        "dialogues": dialogues,
        "refs": refs,
        "dial_infos": dial_infos,
        "npc_quotes_raw": npc_quotes_raw,
    }


def is_junk_location(edid: str) -> bool:
    return bool(edid and IGNORED_LOC_RE.search(edid))


def build_rich_encyclopedia(esm: dict[str, Any], graph: dict[str, Any], details: dict[str, Any]) -> dict[str, Any]:
    avifs = esm["avifs"]
    mgefs = esm["mgefs"]
    enchs = esm["enchs"]
    spels = esm["spels"]
    factions = esm["factions"]
    races = esm["races"]
    packages = esm["packages"]
    npcs = esm["npcs"]
    creatures = esm["creatures"]
    worlds = esm["worlds"]
    cells = esm["cells"]
    markers = esm["markers"]
    items = esm["items"]
    objects = esm["objects"]
    quests = esm["quests"]
    refs = esm["refs"]
    dial_infos = esm["dial_infos"]
    npc_quotes_raw = esm["npc_quotes_raw"]

    nodes = graph["nodes"]
    edges = graph["edges"]
    node_by_id = {n["id"]: n for n in nodes}

    # Index markers by worldspace for nearest-marker lookup
    markers_by_wrld: dict[int, list[tuple[int, float, float, str]]] = defaultdict(list)
    for mfid, m in markers.items():
        if m["pos"] and m["wrld_fid"] and not is_junk_location(m["edid"]):
            markers_by_wrld[m["wrld_fid"]].append(
                (mfid, m["pos"][0], m["pos"][1], clean_text(m["name"]))
            )

    def nearest_marker_name(wrld_fid: int, pos: list[float] | None, radius: float = 18000.0) -> tuple[int, str]:
        if not pos or not wrld_fid:
            return 0, ""
        cands = markers_by_wrld.get(wrld_fid)
        if not cands:
            return 0, ""
        px, py = pos[0], pos[1]
        best_fid = 0
        best_name = ""
        best_d2 = radius * radius
        for mfid, mx, my, mname in cands:
            d2 = (px - mx) ** 2 + (py - my) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best_fid = mfid
                best_name = mname
        return best_fid, best_name

    def resolve_loc_name(cell_fid: int, wrld_fid: int, pos: list[float] | None) -> str:
        c = cells.get(cell_fid)
        if c:
            if is_junk_location(c["edid"]):
                return ""
            cname = clean_text(c["name"])
            if cname:
                return cname
            if not wrld_fid and c["wrld_fid"]:
                wrld_fid = c["wrld_fid"]
        if wrld_fid:
            w = worlds.get(wrld_fid)
            if w and is_junk_location(w["edid"]):
                return ""
            wname = clean_text(w["name"]) if w else ""
            _, mname = nearest_marker_name(wrld_fid, pos)
            if mname:
                if wname and wname not in mname and wname != "Пустоши":
                    return f"{mname} ({wname})"
                return mname
            if wname:
                return wname
            if w and w["edid"]:
                return w["edid"]
        return ""

    # Pre-index item/object/npc/crea placements, door links, key locks, and cell contents
    item_placements_by_base: dict[int, Counter[str]] = defaultdict(Counter)
    obj_placements_by_base: dict[int, Counter[str]] = defaultdict(Counter)
    npc_locations_by_base: dict[int, Counter[str]] = defaultdict(Counter)
    crea_locations_by_base: dict[int, Counter[str]] = defaultdict(Counter)

    key_unlocks: dict[int, list[dict[str, str]]] = defaultdict(list)
    key_unlocks_seen: dict[int, set[tuple[str, str]]] = defaultdict(set)
    obj_locks: dict[int, list[dict[str, str]]] = defaultdict(list)
    door_dests_by_base: dict[int, Counter[str]] = defaultdict(Counter)

    cell_npcs: dict[int, Counter[str]] = defaultdict(Counter)
    cell_creatures: dict[int, Counter[str]] = defaultdict(Counter)
    cell_items: dict[int, dict[int, int]] = defaultdict(dict)
    cell_doors: dict[int, Counter[str]] = defaultdict(Counter)
    cell_term_cnt: Counter[int] = Counter()
    cell_cont_cnt: Counter[int] = Counter()

    wrld_npcs: dict[int, Counter[str]] = defaultdict(Counter)
    wrld_creatures: dict[int, Counter[str]] = defaultdict(Counter)
    wrld_items: dict[int, dict[int, int]] = defaultdict(dict)
    wrld_doors: dict[int, Counter[str]] = defaultdict(Counter)
    wrld_term_cnt: Counter[int] = Counter()
    wrld_cont_cnt: Counter[int] = Counter()

    # For map markers: collect exterior refs near each marker
    marker_nearby_npcs: dict[int, Counter[str]] = defaultdict(Counter)
    marker_nearby_creatures: dict[int, Counter[str]] = defaultdict(Counter)
    marker_nearby_items: dict[int, dict[int, int]] = defaultdict(dict)
    marker_nearby_doors: dict[int, Counter[str]] = defaultdict(Counter)
    marker_term_cnt: Counter[int] = Counter()
    marker_cont_cnt: Counter[int] = Counter()

    # Interior cell parent marker via XTEL
    cell_parent_markers: dict[int, Counter[int]] = defaultdict(Counter)

    for rfid, ref in refs.items():
        bfid = ref["base_fid"]
        cfid = ref["cell_fid"]
        wfid = ref["wrld_fid"] or (cells[cfid]["wrld_fid"] if cfid in cells else 0)
        pos = ref["pos"]
        rtype = ref["rtype"]
        loc_name = resolve_loc_name(cfid, wfid, pos)

        near_mfid = 0
        if wfid and pos:
            near_mfid, _ = nearest_marker_name(wfid, pos, radius=14000.0)

        if rtype == "ACHR" and bfid in npcs:
            n_name = clean_text(npcs[bfid]["name"])
            if loc_name:
                npc_locations_by_base[bfid][loc_name] += 1
            if n_name and not is_junk_location(npcs[bfid]["edid"]):
                if cfid:
                    cell_npcs[cfid][n_name] += 1
                if wfid:
                    wrld_npcs[wfid][n_name] += 1
                if near_mfid:
                    marker_nearby_npcs[near_mfid][n_name] += 1

        elif rtype == "ACRE" and bfid in creatures:
            c_name = clean_text(creatures[bfid]["name"])
            if loc_name:
                crea_locations_by_base[bfid][loc_name] += 1
            if c_name and not is_junk_location(creatures[bfid]["edid"]):
                if cfid:
                    cell_creatures[cfid][c_name] += 1
                if wfid:
                    wrld_creatures[wfid][c_name] += 1
                if near_mfid:
                    marker_nearby_creatures[near_mfid][c_name] += 1

        elif rtype == "REFR" and bfid:
            if bfid in items:
                if loc_name:
                    item_placements_by_base[bfid][loc_name] += 1
                if cfid:
                    cell_items[cfid][bfid] = cell_items[cfid].get(bfid, 0) + 1
                if wfid:
                    wrld_items[wfid][bfid] = wrld_items[wfid].get(bfid, 0) + 1
                if near_mfid:
                    marker_nearby_items[near_mfid][bfid] = (
                        marker_nearby_items[near_mfid].get(bfid, 0) + 1
                    )
            elif bfid in objects:
                if loc_name:
                    obj_placements_by_base[bfid][loc_name] += 1
                sub = objects[bfid]["subtype"]
                if sub == "terminal":
                    if cfid:
                        cell_term_cnt[cfid] += 1
                    if wfid:
                        wrld_term_cnt[wfid] += 1
                    if near_mfid:
                        marker_term_cnt[near_mfid] += 1
                elif sub == "container":
                    if cfid:
                        cell_cont_cnt[cfid] += 1
                    if wfid:
                        wrld_cont_cnt[wfid] += 1
                    if near_mfid:
                        marker_cont_cnt[near_mfid] += 1

                # XLOC locks on placed DOOR / CONT / TERM
                kfid = ref["key_fid"]
                llvl = ref["lock_level"]
                if kfid or (llvl is not None and llvl > 0):
                    lock_str = xloc_lock_label(llvl)
                    key_name = clean_text(items.get(kfid, {}).get("name", "")) if kfid else ""
                    obj_locks[bfid].append(
                        {
                            "lockDiff": lock_str,
                            "requiredKey": key_name,
                            "location": loc_name,
                        }
                    )
                    if kfid and kfid in items:
                        target_name = clean_text(objects[bfid]["name"]) or objects[bfid]["edid"]
                        sig_key = (target_name, loc_name)
                        if sig_key not in key_unlocks_seen[kfid]:
                            key_unlocks_seen[kfid].add(sig_key)
                            key_unlocks[kfid].append(
                                {
                                    "target": target_name,
                                    "targetType": objects[bfid]["subtype"],
                                    "location": loc_name or "Неизвестная локация",
                                    "lockDiff": lock_str,
                                }
                            )

            # XTEL door destinations
            dest_rfid = ref["xtel_dest"]
            if dest_rfid and dest_rfid in refs:
                dref = refs[dest_rfid]
                d_cfid = dref["cell_fid"]
                d_wfid = dref["wrld_fid"] or (cells[d_cfid]["wrld_fid"] if d_cfid in cells else 0)
                d_name = resolve_loc_name(d_cfid, d_wfid, dref["pos"])
                if d_name:
                    if bfid in objects:
                        door_dests_by_base[bfid][d_name] += 1
                    if cfid and d_cfid != cfid:
                        cell_doors[cfid][d_name] += 1
                    if wfid:
                        wrld_doors[wfid][d_name] += 1
                    if near_mfid:
                        marker_nearby_doors[near_mfid][d_name] += 1
                # Link interior cell to exterior nearest marker
                if cfid and not wfid and d_wfid and dref["pos"]:
                    ext_m, _ = nearest_marker_name(d_wfid, dref["pos"], radius=18000.0)
                    if ext_m:
                        cell_parent_markers[cfid][ext_m] += 1

    # Also build NPC carriers / wearers index for items
    item_carriers: dict[int, Counter[str]] = defaultdict(Counter)
    for nfid, n in npcs.items():
        if is_junk_location(n["edid"]):
            continue
        nname = clean_text(n["name"])
        if not nname:
            continue
        for entry in n["inventory"]:
            ifid = entry["fid"]
            if ifid in items:
                item_carriers[ifid][nname] += 1

    # Helper to format notable items in a cell/world/marker
    def top_notable_items(item_counts: dict[int, int], limit: int = 15) -> list[str]:
        scored: list[tuple[int, str]] = []
        for ifid, cnt in item_counts.items():
            it = items.get(ifid)
            if not it:
                continue
            iname = clean_text(it["name"])
            if not iname or is_junk_location(it["edid"]):
                continue
            sub = it["subtype"]
            is_graph_node = f"itm_{ifid:08x}" in node_by_id
            prio = 0
            if is_graph_node:
                prio += 100
            if sub in ("book", "key", "note"):
                prio += 50
            elif sub in ("weapon", "armor"):
                prio += 30
            elif sub == "aid":
                prio += 15
            elif sub == "misc" and it["value"] < 15:
                prio -= 20
            prio += min(it["value"] // 10, 40)
            if "unique" in it["edid"].lower():
                prio += 80
            scored.append((prio, f"{iname} ×{cnt}" if cnt > 1 else iname))
        scored.sort(key=lambda x: (-x[0], x[1]))
        out: list[str] = []
        seen_names: set[str] = set()
        for _, label in scored:
            base_lbl = label.split(" ×")[0]
            if base_lbl not in seen_names:
                seen_names.add(base_lbl)
                out.append(label)
            if len(out) >= limit:
                break
        return out

    # Helper to resolve ENCH/SPEL effects on WEAP/ARMO
    def resolve_item_effects(it: dict[str, Any]) -> list[str]:
        if it["effects_raw"]:
            return format_effect_list(it["effects_raw"], mgefs)
        efid = it["ench_fid"]
        if not efid:
            return []
        rec = enchs.get(efid) or spels.get(efid)
        if not rec:
            return []
        effs = format_effect_list(rec["effects"], mgefs)
        if not effs and rec["name"] and CYR_RE.search(rec["name"]):
            effs = [clean_text(rec["name"])]
        return effs

    # Helper to resolve NOTE text (including Voice Holotapes via TNAM -> DIAL -> INFO NAM1)
    def resolve_note_text(it: dict[str, Any]) -> str:
        if it["text"]:
            return clean_text(it["text"])
        tfid = it["tname_fid"]
        if tfid and tfid in dial_infos:
            lines: list[str] = []
            seen: set[str] = set()
            for info in dial_infos[tfid]:
                for t in info["texts"]:
                    if t not in seen:
                        seen.add(t)
                        lines.append(t)
            return "\n".join(lines)
        return ""

    # Helper to resolve PERK conditions to Russian strings
    def resolve_perk_requirements(ob: dict[str, Any]) -> dict[str, Any]:
        conds_ru: list[str] = []
        op_map = {0: "=", 1: "≠", 2: ">", 3: "≥", 4: "<", 5: "≤"}
        for c in ob["conditions"]:
            func = c["func"]
            op_s = op_map.get(c["op"], "≥")
            val_i = int(round(c["val"]))
            if func in (CTDA_GET_AV, CTDA_GET_PERM_AV):
                av_name = ACTOR_VALUES_RU.get(c["p1"])
                if av_name:
                    conds_ru.append(f"{av_name} {op_s} {val_i}")
            elif func == CTDA_HAS_PERK:
                p_fid = c["p1"]
                pname = clean_text(objects.get(p_fid, {}).get("name", ""))
                if pname:
                    conds_ru.append(f"Способность «{pname}»")
        return {
            "minLevel": ob["min_level"],
            "ranks": ob["ranks"],
            "conditions": conds_ru,
            "description": clean_text(ob["desc"]),
        }

    # Build graph edges index for story events
    adj_by_node: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        adj_by_node[e["source"]].append(e["target"])
        adj_by_node[e["target"]].append(e["source"])

    rich: dict[str, Any] = {}

    for node in nodes:
        nid = node["id"]
        ntype = node["type"]
        nsub = node["subtype"]
        fid_str = node["fid"]
        fid = int(fid_str, 16) if fid_str.startswith("0x") else 0

        base_entry: dict[str, Any] = {
            "id": nid,
            "fid": fid_str,
            "edid": node["edid"],
            "label": node["label"],
            "type": ntype,
            "subtype": nsub,
            "dlc": node["dlc"],
        }

        if ntype == "item":
            it = items.get(fid, {})
            placements = [k for k, _ in item_placements_by_base.get(fid, Counter()).most_common(12)]
            carriers = [k for k, _ in item_carriers.get(fid, Counter()).most_common(12)]

            if nsub == "weapon":
                ammo_name = ""
                afid = it.get("ammo_fid", 0)
                if afid and afid in items:
                    ammo_name = clean_text(items[afid]["name"])
                base_entry.update(
                    {
                        "value": it.get("value", 0),
                        "weight": it.get("weight", 0.0),
                        "health": it.get("health", 0),
                        "damage": it.get("damage", 0),
                        "clipSize": it.get("clip_size", 0),
                        "weaponClass": it.get("weapon_class", ""),
                        "skill": it.get("skill", ""),
                        "fireRate": it.get("fire_rate", 0.0),
                        "apCost": it.get("ap_cost", 0.0),
                        "minSpread": it.get("min_spread", 0.0),
                        "maxSpread": it.get("max_spread", 0.0),
                        "critDamage": it.get("crit_damage", 0),
                        "critMult": it.get("crit_mult", 0.0),
                        "ammo": ammo_name,
                        "effects": resolve_item_effects(it) if it else [],
                        "placements": placements,
                        "carriers": carriers,
                    }
                )
            elif nsub == "armor":
                base_entry.update(
                    {
                        "value": it.get("value", 0),
                        "weight": it.get("weight", 0.0),
                        "health": it.get("health", 0),
                        "dr": it.get("dr", 0.0),
                        "effects": resolve_item_effects(it) if it else [],
                        "placements": placements,
                        "wearers": carriers,
                    }
                )
            elif nsub == "aid":
                base_entry.update(
                    {
                        "value": it.get("value", 0),
                        "weight": it.get("weight", 0.0),
                        "effects": resolve_item_effects(it) if it else [],
                        "addictionChance": it.get("addiction_chance", 0.0),
                        "placements": placements,
                        "carriers": carriers,
                    }
                )
            elif nsub == "ammo":
                base_entry.update(
                    {
                        "value": it.get("value", 0),
                        "weight": it.get("weight", 0.0),
                        "speed": it.get("speed", 0.0),
                        "clipRounds": it.get("clip_rounds", 0),
                        "shortName": it.get("short_name", ""),
                        "placements": placements,
                        "carriers": carriers,
                    }
                )
            elif nsub == "book":
                skill_taught = it.get("skill_taught", "")
                effs = [f"{skill_taught} (+1 / +2 с «Пониманием»)" ] if skill_taught else []
                book_txt = clean_text(BOOK_HTML_RE.sub(" ", it.get("text", "")))
                base_entry.update(
                    {
                        "value": it.get("value", 0),
                        "weight": it.get("weight", 0.0),
                        "skillTaught": skill_taught,
                        "effects": effs,
                        "text": book_txt,
                        "placements": placements,
                        "carriers": carriers,
                    }
                )
            elif nsub == "key":
                base_entry.update(
                    {
                        "value": it.get("value", 0),
                        "weight": it.get("weight", 0.0),
                        "unlocks": key_unlocks.get(fid, []),
                        "placements": placements,
                        "carriers": carriers,
                    }
                )
            elif nsub == "note":
                base_entry.update(
                    {
                        "value": it.get("value", 0),
                        "weight": it.get("weight", 0.0),
                        "noteType": NOTE_TYPE_RU.get(it.get("note_type", 1), "Заметка"),
                        "text": resolve_note_text(it) if it else "",
                        "placements": placements,
                        "carriers": carriers,
                    }
                )
            else:  # misc
                base_entry.update(
                    {
                        "value": it.get("value", 0),
                        "weight": it.get("weight", 0.0),
                        "placements": placements,
                        "carriers": carriers,
                    }
                )

        elif ntype == "character" and nsub == "npc":
            n = npcs.get(fid, {})
            race_name = clean_text(races.get(n.get("race_fid", 0), {}).get("name", "")) or "Человек"
            fac_list = []
            for fe in n.get("factions", []):
                fn = clean_text(factions.get(fe["fid"], {}).get("name", ""))
                if fn and fn not in fac_list:
                    fac_list.append(fn)

            pkg_types = []
            for pkfid in n.get("packages", []):
                pk = packages.get(pkfid)
                if pk and pk["ptype"] is not None:
                    plabel = PACKAGE_TYPE_RU.get(pk["ptype"])
                    if plabel and plabel not in pkg_types:
                        pkg_types.append(plabel)

            inv_list = []
            for entry in n.get("inventory", []):
                ifid = entry["fid"]
                if ifid in items:
                    iname = clean_text(items[ifid]["name"])
                    if iname:
                        inv_list.append(
                            {"id": f"itm_{ifid:08x}", "name": iname, "count": entry["count"]}
                        )

            # Deduplicate and rank quotes (prefer complete sentences)
            raw_q = npc_quotes_raw.get(fid, [])
            seen_q: set[str] = set()
            cands_q: list[tuple[int, str]] = []
            for qtext in raw_q:
                if qtext in seen_q:
                    continue
                seen_q.add(qtext)
                score = 0
                if END_PUNCT_RE.search(qtext):
                    score += 20
                if 45 <= len(qtext) <= 160:
                    score += 15
                cands_q.append((score, qtext))
            cands_q.sort(key=lambda x: (-x[0], -len(x[1])))
            quotes = [q for _, q in cands_q[:3]]

            base_entry.update(
                {
                    "race": race_name,
                    "level": n.get("level", 1),
                    "levelRange": n.get("level_range"),
                    "hp": n.get("hp", 50),
                    "female": n.get("female", False),
                    "essential": n.get("essential", False),
                    "unique": n.get("unique", False),
                    "special": n.get("special", [5, 5, 5, 5, 5, 5, 5]),
                    "behavior": {
                        "aggression": AGGRESSION_RU.get(n.get("aggression", 0), "Мирный"),
                        "confidence": CONFIDENCE_RU.get(n.get("confidence", 2), "Средний"),
                        "mood": MOOD_RU.get(n.get("mood", 0), "Нейтральное"),
                        "packages": pkg_types,
                    },
                    "services": decode_services(n.get("services_flags", 0)),
                    "factions": fac_list[:10],
                    "inventory": inv_list[:20],
                    "locations": [k for k, _ in npc_locations_by_base.get(fid, Counter()).most_common(10)],
                    "quotes": quotes,
                }
            )

        elif ntype == "character" and nsub == "creature":
            c = creatures.get(fid, {})
            fac_list = []
            for fe in c.get("factions", []):
                fn = clean_text(factions.get(fe["fid"], {}).get("name", ""))
                if fn and fn not in fac_list:
                    fac_list.append(fn)
            drops = []
            for entry in c.get("drops", []):
                ifid = entry["fid"]
                if ifid in items:
                    iname = clean_text(items[ifid]["name"])
                    if iname:
                        drops.append(
                            {"id": f"itm_{ifid:08x}", "name": iname, "count": entry["count"]}
                        )
            base_entry.update(
                {
                    "level": c.get("level", 1),
                    "levelRange": c.get("level_range"),
                    "hp": c.get("hp", 50),
                    "attackDamage": c.get("attack_damage", 0),
                    "aggression": AGGRESSION_RU.get(c.get("aggression", 1), "Агрессивный"),
                    "confidence": CONFIDENCE_RU.get(c.get("confidence", 2), "Средний"),
                    "drops": drops[:15],
                    "locations": [k for k, _ in crea_locations_by_base.get(fid, Counter()).most_common(10)],
                    "modl": c.get("modl", ""),
                    "factions": fac_list[:10],
                }
            )

        elif ntype == "location":
            det = details.get(nid, {})
            if nsub == "interior":
                c = cells.get(fid, {})
                ofid = c.get("owner_fid", 0)
                owner_name = ""
                if ofid:
                    owner_name = clean_text(
                        factions.get(ofid, {}).get("name") or npcs.get(ofid, {}).get("name") or ""
                    )
                parent_m_name = ""
                if fid in cell_parent_markers:
                    pmfid = cell_parent_markers[fid].most_common(1)[0][0]
                    parent_m_name = clean_text(markers.get(pmfid, {}).get("name", ""))
                base_entry.update(
                    {
                        "worldspace": parent_m_name or det.get("worldspace", "Внутренняя локация"),
                        "markerType": None,
                        "coords": None,
                        "owner": owner_name,
                        "npcsInCell": [k for k, _ in cell_npcs.get(fid, Counter()).most_common(15)],
                        "creaturesInCell": [k for k, _ in cell_creatures.get(fid, Counter()).most_common(12)],
                        "notableItems": top_notable_items(cell_items.get(fid, {})),
                        "doorsTo": [k for k, _ in cell_doors.get(fid, Counter()).most_common(12)],
                        "terminalsCount": cell_term_cnt.get(fid, 0),
                        "containersCount": cell_cont_cnt.get(fid, 0),
                    }
                )
            elif nsub == "marker":
                mk = markers.get(fid, {})
                wfid = mk.get("wrld_fid", 0)
                cfid = mk.get("cell_fid", 0)
                wname = clean_text(worlds.get(wfid, {}).get("name", "")) or det.get("worldspace", "")
                mtype = MARKER_TYPES_RU.get(mk.get("marker_type", 0), det.get("markerType", "Локация"))
                c_owner = ""
                if cfid and cells.get(cfid, {}).get("owner_fid"):
                    ofid = cells[cfid]["owner_fid"]
                    c_owner = clean_text(
                        factions.get(ofid, {}).get("name") or npcs.get(ofid, {}).get("name") or ""
                    )
                base_entry.update(
                    {
                        "worldspace": wname,
                        "markerType": mtype,
                        "coords": mk.get("pos") or det.get("coords"),
                        "owner": c_owner,
                        "npcsInCell": [k for k, _ in marker_nearby_npcs.get(fid, Counter()).most_common(15)],
                        "creaturesInCell": [k for k, _ in marker_nearby_creatures.get(fid, Counter()).most_common(12)],
                        "notableItems": top_notable_items(marker_nearby_items.get(fid, {})),
                        "doorsTo": [k for k, _ in marker_nearby_doors.get(fid, Counter()).most_common(12)],
                        "terminalsCount": marker_term_cnt.get(fid, 0),
                        "containersCount": marker_cont_cnt.get(fid, 0),
                    }
                )
            else:  # world
                w = worlds.get(fid, {})
                base_entry.update(
                    {
                        "worldspace": clean_text(w.get("name", "")) or node["label"],
                        "markerType": "Внешний мир",
                        "coords": None,
                        "owner": "",
                        "npcsInCell": [k for k, _ in wrld_npcs.get(fid, Counter()).most_common(20)],
                        "creaturesInCell": [k for k, _ in wrld_creatures.get(fid, Counter()).most_common(15)],
                        "notableItems": top_notable_items(wrld_items.get(fid, {}), limit=20),
                        "doorsTo": [k for k, _ in wrld_doors.get(fid, Counter()).most_common(15)],
                        "terminalsCount": wrld_term_cnt.get(fid, 0),
                        "containersCount": wrld_cont_cnt.get(fid, 0),
                    }
                )

        elif ntype == "object":
            ob = objects.get(fid, {})
            placements = [k for k, _ in obj_placements_by_base.get(fid, Counter()).most_common(12)]
            locks = obj_locks.get(fid, [])
            xloc_diff = next((lk["lockDiff"] for lk in locks if lk["lockDiff"]), "")
            xloc_key = next((lk["requiredKey"] for lk in locks if lk["requiredKey"]), "")

            if nsub == "terminal":
                resolved_menu = []
                for mi in ob.get("menu_items", [])[:15]:
                    mtxt = clean_text(mi["text"])
                    if not mtxt and mi["note_fid"] and mi["note_fid"] in items:
                        mtxt = resolve_note_text(items[mi["note_fid"]])
                    resolved_menu.append({"title": clean_text(mi["title"]), "text": mtxt})
                pw_fid = ob.get("password_fid", 0)
                pw_name = clean_text(items.get(pw_fid, {}).get("name", "")) if pw_fid else ""
                base_entry.update(
                    {
                        "lockDiff": ob.get("lock_diff") or xloc_diff,
                        "requiredKey": pw_name or xloc_key,
                        "text": clean_text(ob.get("desc", "")),
                        "menuItems": resolved_menu,
                        "placements": placements,
                    }
                )
            elif nsub == "activator":
                base_entry.update(
                    {
                        "lockDiff": xloc_diff,
                        "requiredKey": xloc_key,
                        "text": clean_text(ob.get("desc", "")),
                        "placements": placements,
                    }
                )
            elif nsub == "container":
                loot = []
                for entry in ob.get("contents", []):
                    ifid = entry["fid"]
                    if ifid in items:
                        iname = clean_text(items[ifid]["name"])
                        if iname:
                            loot.append(
                                {"id": f"itm_{ifid:08x}", "name": iname, "count": entry["count"]}
                            )
                base_entry.update(
                    {
                        "lockDiff": xloc_diff,
                        "requiredKey": xloc_key,
                        "notableLoot": loot[:20],
                        "placements": placements,
                    }
                )
            elif nsub == "door":
                base_entry.update(
                    {
                        "lockDiff": xloc_diff,
                        "requiredKey": xloc_key,
                        "doorsTo": [k for k, _ in door_dests_by_base.get(fid, Counter()).most_common(12)],
                        "placements": placements,
                    }
                )
            elif nsub == "perk":
                reqs = resolve_perk_requirements(ob) if ob else {
                    "minLevel": 1,
                    "ranks": 1,
                    "conditions": [],
                    "description": details.get(nid, {}).get("text", ""),
                }
                base_entry.update(
                    {
                        "text": reqs["description"],
                        "requirements": reqs,
                    }
                )

        elif ntype == "quest":
            q = quests.get(fid, {})
            objs = [
                {"index": o["index"], "text": o["text"]}
                for o in sorted(q.get("objectives", {}).values(), key=lambda x: x["index"])
                if o["text"]
            ]
            stgs = [
                {
                    "stage": s["stage"],
                    "logs": s["logs"],
                    "completes": bool(s["flags"] & 0x01),
                    "fails": bool(s["flags"] & 0x02),
                }
                for s in sorted(q.get("stages", {}).values(), key=lambda x: x["stage"])
                if s["logs"]
            ]
            base_entry.update({"objectives": objs, "stageLogs": stgs})

        elif ntype == "event":
            if nsub == "random_encounter" and fid in quests:
                q = quests[fid]
                m_stg = re.search(r"_S(\d+)$", node["edid"])
                stg_num = m_stg.group(1) if m_stg else ""
                stg = q.get("stages", {}).get(stg_num, {})
                stgs = (
                    [{"stage": int(stg_num), "logs": stg.get("logs", []), "completes": False, "fails": False}]
                    if stg.get("logs")
                    else []
                )
                base_entry.update(
                    {
                        "summary": details.get(nid, {}).get("summary", ""),
                        "objectives": [],
                        "stageLogs": stgs,
                    }
                )
            else:
                linked_q_ids = [
                    nb for nb in adj_by_node.get(nid, []) if nb.startswith("qst_") and nb in node_by_id
                ]
                base_entry.update(
                    {
                        "summary": details.get(nid, {}).get("summary", ""),
                        "linkedQuests": [
                            {"id": qid, "label": node_by_id[qid]["label"]} for qid in linked_q_ids
                        ],
                    }
                )

        rich[nid] = base_entry

    return rich


def main():
    t0 = time.time()
    print("[1/3] Parsing 6 RUS GOTY ESMs from", ESM_DIR)
    esm = parse_all_rus_esms()

    print("[2/3] Loading graph.json and details.json (read-only)...")
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    details = json.loads(DETAILS_PATH.read_text(encoding="utf-8"))

    print(f"[3/3] Building rich encyclopedia for {len(graph['nodes'])} nodes...")
    rich = build_rich_encyclopedia(esm, graph, details)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rich, ensure_ascii=False, indent=2), encoding="utf-8")
    sz_mb = OUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Done in {time.time() - t0:.2f}s -> {OUT_PATH} ({len(rich)} entries, {sz_mb:.2f} MB)")


if __name__ == "__main__":
    main()
