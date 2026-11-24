#!/usr/bin/env python3
"""Extract real Fallout 3 GOTY DDS icons from BSAs, map all graph.json nodes, and pack public/icons/atlas.{png,json}."""

import io
import json
import math
import os
import re
import struct
import subprocess
import zlib
from collections import Counter
from pathlib import Path
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path("/tmp/f3_icons_src/data/RUS/Data")
GRAPH_JSON = REPO_ROOT / "public" / "data" / "graph.json"
OUT_ICONS_DIR = REPO_ROOT / "public" / "icons"
CELL_SIZE = 96
INNER_SIZE = 78

BSAS = [
    "Fallout - Textures.bsa",
    "Anchorage - Main.bsa",
    "ThePitt - Main.bsa",
    "BrokenSteel - Main.bsa",
    "PointLookout - Main.bsa",
    "Zeta - Main.bsa",
]

ESMS = [
    ("Fallout3.esm", 0),
    ("Anchorage.esm", 1),
    ("ThePitt.esm", 2),
    ("BrokenSteel.esm", 3),
    ("PointLookout.esm", 4),
    ("Zeta.esm", 5),
]
MOD_ORDER = {name: idx for name, idx in ESMS}


def read_bsa_entries(path: Path):
    entries = {}
    with open(path, "rb") as f:
        hdr = f.read(36)
        _, _, off, aflags, fcnt, _, _, tfn_len2, _ = struct.unpack("<4sIIIIIIII", hdr)
        f.seek(off)
        folders = [struct.unpack("<QII", f.read(16))[1:] for _ in range(fcnt)]
        file_recs = []
        for cnt, _ in folders:
            nl = f.read(1)[0]
            fname = f.read(nl).rstrip(b"\x00").decode("latin1").replace("\\", "/")
            recs = [struct.unpack("<QII", f.read(16))[1:] for _ in range(cnt)]
            file_recs.append((fname, recs))
        names = f.read(tfn_len2).split(b"\x00")
        idx = 0
        for folder, recs in file_recs:
            for fsz, foff in recs:
                nm = names[idx].decode("latin1")
                idx += 1
                full = (folder + "/" + nm).lower()
                entries[full] = (path, aflags, fsz, foff)
    return entries


def extract_bsa_bytes(entry) -> bytes:
    path, aflags, fsz, foff = entry
    with open(path, "rb") as f:
        f.seek(foff)
        actual = fsz & 0x3FFFFFFF
        comp = bool(aflags & 0x004) ^ bool(fsz & 0x40000000)
        raw = f.read(actual)
        if aflags & 0x100:
            raw = raw[1 + raw[0] :]
        if comp:
            raw = zlib.decompress(raw[4:])
        return raw


def decode_dds_to_rgba(raw: bytes) -> Image.Image:
    try:
        return Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception:
        p = subprocess.run(
            ["ffmpeg", "-v", "error", "-f", "dds", "-i", "pipe:0", "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
            input=raw,
            capture_output=True,
            check=True,
        )
        return Image.open(io.BytesIO(p.stdout)).convert("RGBA")


def iter_esm_records(path: Path):
    data = path.read_bytes()
    _, sz = struct.unpack_from("<4sI", data, 0)
    tes4_end = 24 + sz
    masts = []
    sp = 24
    while sp + 6 <= tes4_end:
        ssig, ssz = struct.unpack_from("<4sH", data, sp)
        sp += 6
        val = data[sp : sp + ssz]
        sp += ssz
        if ssig == b"MAST":
            masts.append(val.rstrip(b"\x00").decode("latin1"))

    def walk(start: int, end: int):
        p = start
        while p < end:
            rsig, rsz = struct.unpack_from("<4sI", data, p)
            if rsig == b"GRUP":
                yield from walk(p + 24, p + rsz)
                p += rsz
            else:
                flags, fid = struct.unpack_from("<II", data, p + 8)
                body = data[p + 24 : p + 24 + rsz]
                if flags & 0x00040000:
                    body = zlib.decompress(body[4:])
                yield rsig.decode("ascii", "ignore"), fid, body
                p += 24 + rsz

    return masts, walk(tes4_end, len(data))


def remap_fid(raw_fid: int, masts: list[str], self_idx: int) -> str:
    mid = raw_fid >> 24
    low = raw_fid & 0x00FFFFFF
    real_idx = MOD_ORDER.get(masts[mid], self_idx) if mid < len(masts) else self_idx
    return f"0x{(real_idx << 24) | low:08X}"


def parse_subrecords(body: bytes):
    sp = 0
    xxxx = None
    subs = []
    while sp + 6 <= len(body):
        ssig, ssz = struct.unpack_from("<4sH", body, sp)
        sp += 6
        if xxxx is not None:
            ssz = xxxx
            xxxx = None
        if ssig == b"XXXX":
            xxxx = struct.unpack_from("<I", body, sp)[0]
            sp += 4
            continue
        subs.append((ssig, body[sp : sp + ssz]))
        sp += ssz
    return subs


def normalize_tex_path(p: str) -> str:
    p = p.strip().replace("\\", "/").lower()
    if not p:
        return ""
    if not p.startswith("textures/"):
        p = "textures/" + p.lstrip("/")
    return p


def build_bsa_resolver(bsa_files: dict):
    by_basename = {}
    for full in bsa_files:
        if not full.endswith(".dds"):
            continue
        if "_small/" in full or "/inverted/" in full:
            continue
        base = full.rsplit("/", 1)[-1]
        # Prefer sharper non-glow pipboyimages/dlc icons over small/glow variants
        prio = 0
        if "pipboyimages/" in full:
            prio = 3
        elif "/interface/icons/" in full:
            prio = 2
        if base not in by_basename or prio > by_basename[base][0]:
            by_basename[base] = (prio, full)

    def resolve(path_hint: str) -> str | None:
        if not path_hint:
            return None
        norm = normalize_tex_path(path_hint)
        if norm in bsa_files:
            return norm
        base = norm.rsplit("/", 1)[-1]
        if base in by_basename:
            return by_basename[base][1]
        return None

    return resolve


MAP_TYPE_ICONS = {
    1: "textures/interface/icons/world map/icon_map_city.dds",
    2: "textures/interface/icons/world map/icon_map_settlement.dds",
    3: "textures/interface/icons/world map/icon_map_encampment.dds",
    4: "textures/interface/icons/world map/icon_map_natural_landmark.dds",
    5: "textures/interface/icons/world map/icon_map_metro.dds",
    6: "textures/interface/icons/world map/icon_map_military.dds",
    7: "textures/interface/icons/world map/icon_map_office.dds",
    8: "textures/interface/icons/world map/icon_map_factory.dds",
    9: "textures/interface/icons/world map/icon_map_monument.dds",
    10: "textures/interface/icons/world map/icon_map_ruins_urban.dds",
    11: "textures/interface/icons/world map/icon_map_ruins_town.dds",
    12: "textures/interface/icons/world map/icon_map_ruins_sewer.dds",
    13: "textures/interface/icons/world map/icon_map_cave.dds",
    14: "textures/interface/icons/world map/icon_map_vault.dds",
}


def make_icon_key(dds_path: str) -> str:
    rel = dds_path.lower().replace("textures/interface/icons/", "").replace("textures/", "")
    rel = rel.removesuffix(".dds")
    # Prefix DLC folder if present so names never collide
    slug = re.sub(r"[^a-z0-9]+", "_", rel).strip("_")
    slug = slug.replace("pipboyimages_", "").replace("world_map_", "map_").replace("message_icons_", "msg_")
    return slug


def process_dds_to_tile(img: Image.Image) -> tuple[Image.Image, bool]:
    bbox = img.getbbox()
    if bbox:
        cropped = img.crop(bbox)
    else:
        cropped = img

    w, h = cropped.size
    if w <= 0 or h <= 0:
        cropped = img
        w, h = cropped.size
    scale = min(INNER_SIZE / w, INNER_SIZE / h)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    resized = cropped.resize((nw, nh), Image.Resampling.LANCZOS)

    tile = Image.new("RGBA", (CELL_SIZE, CELL_SIZE), (0, 0, 0, 0))
    ox = (CELL_SIZE - nw) // 2
    oy = (CELL_SIZE - nh) // 2
    tile.paste(resized, (ox, oy), resized)

    px = [p for p in tile.getdata() if p[3] > 24]
    is_color = False
    if px:
        avg_chroma = sum(max(r, g, b) - min(r, g, b) for r, g, b, _ in px) / len(px)
        is_color = avg_chroma > 18.0
    return tile, is_color


def main():
    print("Reading BSA indexes...")
    bsa_files = {}
    for bsa_name in BSAS:
        bsa_files.update(read_bsa_entries(DATA_DIR / bsa_name))
    resolve_dds = build_bsa_resolver(bsa_files)

    print("Parsing ESM icon/equipment/faction/marker metadata...")
    item_icons: dict[str, str] = {}
    item_models: dict[str, str] = {}
    note_types: dict[str, int] = {}
    race_edids: dict[str, str] = {}
    fact_edids: dict[str, str] = {}
    npc_meta: dict[str, dict] = {}
    crea_meta: dict[str, dict] = {}
    obj_models: dict[str, str] = {}
    marker_by_edid: dict[str, int] = {}

    for esm_name, self_idx in ESMS:
        masts, recs = iter_esm_records(DATA_DIR / esm_name)
        for sig, rfid, body in recs:
            if sig not in (
                "WEAP", "ARMO", "ALCH", "AMMO", "BOOK", "KEYM", "NOTE", "MISC",
                "PERK", "RACE", "FACT", "NPC_", "CREA", "TERM", "ACTI", "CONT", "DOOR", "REFR",
            ):
                continue
            fid = remap_fid(rfid, masts, self_idx)
            subs = parse_subrecords(body)

            if sig in ("WEAP", "ARMO", "ALCH", "AMMO", "BOOK", "KEYM", "NOTE", "MISC", "PERK"):
                ic = ""
                ic2 = ""
                modl = ""
                for ss, v in subs:
                    if ss == b"ICON" and not ic:
                        ic = v.rstrip(b"\x00").decode("latin1", "ignore")
                    elif ss == b"ICO2" and not ic2:
                        ic2 = v.rstrip(b"\x00").decode("latin1", "ignore")
                    elif ss == b"MODL" and not modl:
                        modl = v.rstrip(b"\x00").decode("latin1", "ignore").lower()
                    elif sig == "NOTE" and ss == b"TNAM" and len(v) >= 1:
                        note_types[fid] = v[0]
                chosen = resolve_dds(ic) or resolve_dds(ic2)
                if chosen:
                    item_icons[fid] = chosen
                if modl:
                    item_models[fid] = modl

            elif sig == "RACE":
                for ss, v in subs:
                    if ss == b"EDID":
                        race_edids[fid] = v.rstrip(b"\x00").decode("latin1", "ignore").lower()

            elif sig == "FACT":
                for ss, v in subs:
                    if ss == b"EDID":
                        fact_edids[fid] = v.rstrip(b"\x00").decode("latin1", "ignore").lower()

            elif sig == "NPC_":
                cntos, facts, race, female, tpl = [], [], None, False, None
                for ss, v in subs:
                    if ss == b"CNTO" and len(v) >= 4:
                        cntos.append(remap_fid(struct.unpack("<I", v[:4])[0], masts, self_idx))
                    elif ss == b"SNAM" and len(v) >= 4:
                        facts.append(remap_fid(struct.unpack("<I", v[:4])[0], masts, self_idx))
                    elif ss == b"RNAM" and len(v) >= 4:
                        race = remap_fid(struct.unpack("<I", v[:4])[0], masts, self_idx)
                    elif ss == b"TPLT" and len(v) >= 4:
                        tpl = remap_fid(struct.unpack("<I", v[:4])[0], masts, self_idx)
                    elif ss == b"ACBS" and len(v) >= 4:
                        female = bool(struct.unpack("<I", v[:4])[0] & 1)
                npc_meta[fid] = {"cntos": cntos, "facts": facts, "race": race, "female": female, "tpl": tpl}

            elif sig == "CREA":
                modl = ""
                for ss, v in subs:
                    if ss == b"MODL":
                        modl = v.rstrip(b"\x00").decode("latin1", "ignore").lower()
                crea_meta[fid] = {"modl": modl}

            elif sig in ("TERM", "ACTI", "CONT", "DOOR"):
                for ss, v in subs:
                    if ss == b"MODL":
                        obj_models[fid] = v.rstrip(b"\x00").decode("latin1", "ignore").lower()

            elif sig == "REFR":
                is_mk = False
                tnam = None
                edid = ""
                for ss, v in subs:
                    if ss == b"XMRK":
                        is_mk = True
                    elif ss == b"TNAM" and len(v) >= 2:
                        tnam = struct.unpack("<H", v[:2])[0]
                    elif ss == b"EDID":
                        edid = v.rstrip(b"\x00").decode("latin1", "ignore").lower()
                if is_mk and tnam and edid:
                    marker_by_edid[edid] = tnam

    print("Loading graph.json...")
    graph_data = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
    nodes = graph_data["nodes"]

    def must(path: str) -> str:
        res = resolve_dds(path)
        assert res and res in bsa_files, f"Missing DDS in BSA: {path}"
        return res

    # Distinct armor/uniform icons worth showing on armored/faction characters directly
    ICONIC_CHAR_ARMORS = (
        "power_armor", "enclavehellfire", "enclave_power_armor", "enclave_officer",
        "colonel_autmn", "brotherhood_scribe", "initiate_armor", "vault_suit",
        "lucas_simms", "tenpennys_outfit", "eulogy_jones", "mechanist", "antagonizer",
        "rivet_city_scientist", "enclave_scientist", "wasteland_medic", "chinese_officer",
        "stealthsuit", "raider", "pittraider", "slaver", "slave_outfit", "ghoul_mask",
        "hockey_mask", "combat_armor", "ashur_armor", "tobar", "native", "oasis", "cowboy",
        "samurai", "spacesuit", "red_jumpsuit",
    )

    def pick_item_icon(n: dict) -> str:
        fid = n["fid"]
        if fid in item_icons:
            return item_icons[fid]
        sub = n.get("subtype", "")
        ed = n.get("edid", "").lower()
        lbl = (n.get("label", "") + " " + n.get("labelEn", "")).lower()
        if sub == "weapon":
            if "pistol" in ed or "пистолет" in lbl or "револьвер" in lbl or "magnum" in ed:
                return must("textures/interface/icons/pipboyimages/weapons/weapons_10mm_pistol.dds")
            if "laser" in ed or "лазер" in lbl:
                return must("textures/interface/icons/pipboyimages/weapons/weapons_laser_rifle.dds")
            if "plasma" in ed or "плазм" in lbl:
                return must("textures/interface/icons/pipboyimages/weapons/weapons_plasma_rifle.dds")
            if "shotgun" in ed or "дробовик" in lbl or "обрез" in lbl:
                return must("textures/interface/icons/pipboyimages/weapons/weapons_combat_shotgun.dds")
            if "sniper" in ed or "снайпер" in lbl or "rifle" in ed or "винтов" in lbl:
                return must("textures/interface/icons/pipboyimages/weapons/weapons_hunting_rifle.dds")
            if "grenade" in ed or "гранат" in lbl:
                return must("textures/interface/icons/pipboyimages/weapons/weapons_frag_grenade.dds")
            if "mine" in ed or "мина" in lbl:
                return must("textures/interface/icons/pipboyimages/weapons/weapons_mine.dds")
            if "knife" in ed or "sword" in ed or "baton" in ed or "дубин" in lbl or "нож" in lbl:
                return must("textures/interface/icons/pipboyimages/weapons/weapons_combat_knife.dds")
            return must("textures/interface/icons/pipboyimages/weapons/assault_rifle.dds")
        if sub == "armor":
            return must("textures/interface/icons/pipboyimages/apparel/appearal_combat_armor.dds")
        if sub == "note":
            if note_types.get(fid, 0) == 2 or "holo" in ed or "голо" in lbl or "audio" in lbl or "запис" in lbl:
                return must("textures/interface/icons/pipboyimages/items/item_holotap.dds")
            if "pass" in ed or "ключ" in lbl or "парол" in lbl or "code" in lbl:
                return must("textures/interface/icons/pipboyimages/items/item_passcard .dds")
            return must("textures/interface/icons/pipboyimages/items/items_note.dds")
        if sub == "book":
            return must("textures/interface/icons/pipboyimages/items/items_skill_books.dds")
        if sub == "key":
            return must("textures/interface/icons/pipboyimages/items/item_key.dds")
        if sub == "ammo":
            return must("textures/interface/icons/pipboyimages/items/items_5mm_box.dds")
        if sub == "aid":
            if "stim" in ed or "стимулятор" in lbl:
                return must("textures/interface/icons/pipboyimages/items/items_stimpack.dds")
            if "rad" in ed or "рад" in lbl:
                return must("textures/interface/icons/pipboyimages/items/items_radaway.dds")
            if "nuka" in ed or "ядер-кол" in lbl:
                return must("textures/interface/icons/pipboyimages/items/items_cola.dds")
            return must("textures/interface/icons/pipboyimages/items/item_morphine.dds")
        # misc
        if "bobble" in ed or "пупс" in lbl:
            return must("textures/interface/icons/pipboyimages/items/items_action_abe_figure.dds")
        if "ingot" in ed or "слиток" in lbl:
            return must("textures/dlcpitt/interface/icons/item_ingot.dds")
        if "cap" in ed or "крыш" in lbl:
            return must("textures/interface/icons/pipboyimages/items/items_nuka_cola_cap.dds")
        if "schem" in ed or "схем" in lbl:
            return must("textures/interface/icons/pipboyimages/items/items_schematics_railway_rifle.dds")
        return must("textures/interface/icons/pipboyimages/items/item_junk.dds")

    def pick_creature_icon(n: dict) -> str:
        fid = n["fid"]
        modl = crea_meta.get(fid, {}).get("modl", "")
        ed = n.get("edid", "").lower()
        lbl = (n.get("label", "") + " " + n.get("labelEn", "")).lower()
        combo = f"{modl} {ed} {lbl}"
        if any(k in combo for k in ("mistergutsy", "handy", "protectron", "sentrybot", "robobrain", "eyebot", "turret", "libertyprime", "робот", "протектрон", "мистер храбрец", "турель")):
            return must("textures/interface/icons/pipboyimages/perks/perk_robotics expert.dds")
        if any(k in combo for k in ("alien", "zetan", "чужой", "пришелец")):
            return must("textures/dlc05/interface/icons/items_aliensquid.dds")
        if "deathclaw" in combo or "коготь смерти" in combo:
            return must("textures/interface/icons/pipboyimages/weapons/weapons_deathclaw.dds")
        if any(k in combo for k in ("dog", "dogmeat", "vicious", "псина", "собака")):
            return must("textures/interface/icons/pipboyimages/perks/perk_animal friend.dds")
        if any(k in combo for k in ("ghoul", "feral", "гуль", "свеч")):
            return must("textures/interface/icons/pipboyimages/apparel/apperal_ghoul_mask.dds")
        if any(k in combo for k in ("mirelurk", "болотник")):
            return must("textures/interface/icons/pipboyimages/items/items_crab_meat.dds")
        if any(k in combo for k in ("giantant", "antqueen", "fireant", "мурав")):
            return must("textures/interface/icons/pipboyimages/items/items_ant_meat.dds")
        if "bloatfly" in combo or "дутень" in combo:
            return must("textures/interface/icons/pipboyimages/items/items_fly_meat.dds")
        if "radroach" in combo or "радтаракан" in combo:
            return must("textures/interface/icons/pipboyimages/items/items_roach_meat.dds")
        if "radscorpion" in combo or "радскорпион" in combo:
            return must("textures/interface/icons/pipboyimages/perks/perk_entomologist.dds")
        if "molerat" in combo or "кротокрыс" in combo:
            return must("textures/interface/icons/pipboyimages/items/items_steak.dds")
        if "yaoguai" in combo or "яо-гай" in combo:
            return must("textures/interface/icons/pipboyimages/items/items_yew_bear_charm.dds")
        if "brahmin" in combo or "брамин" in combo:
            return must("textures/interface/icons/pipboyimages/items/items_steak.dds")
        if any(k in combo for k in ("behemoth", "supermutant", "fawkes", "супермутант", "бегемот", "фокс")):
            return must("textures/interface/icons/pipboyimages/perks/perk_ms04strength.dds")
        if "trog" in combo or "трог" in combo:
            return must("textures/dlcpitt/interface/icons/perk_pitt fighter.dds")
        if "hillfolk" in combo or "болотн" in combo or "дикар" in combo:
            return must("textures/dlc04/interface/icons/perk_anatomy.dds")
        return must("textures/interface/icons/pipboyimages/perks/perk_animal friend.dds")

    def pick_npc_icon(n: dict) -> str:
        fid = n["fid"]
        meta = npc_meta.get(fid, {})
        cntos = meta.get("cntos", [])
        facts = [fact_edids.get(f, "") for f in meta.get("facts", [])]
        race = race_edids.get(meta.get("race") or "", "")
        female = meta.get("female", False)
        ed = n.get("edid", "").lower()
        lbl = (n.get("label", "") + " " + n.get("labelEn", "")).lower()
        dlc = n.get("dlc", "base")

        # Named iconic NPCs & companions first
        if "simms" in ed or "симмс" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/apperal_lucas_simms_hat.dds")
        if "tenpenny" in ed or "тенпенни" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/apperal_tenpennys_outfit.dds")
        if "eulogy" in ed or "владимир" in lbl or "гробовщик" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/apperal_eulogy_jones_suit.dds")
        if "autumn" in ed or "отем" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/apperal_colonel_autmn_uniform.dds")
        if "mechanist" in ed or "механист" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/apperal_mechanist_helmet.dds")
        if "antagonizer" in ed or "немир" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/apperal_antagonizer_helmet.dds")
        if "threedog" in ed or "тридогнайт" in lbl:
            return must("textures/interface/icons/message icons/glow_message_radio_tower.dds")
        if "ashur" in ed or "ашур" in lbl:
            return must("textures/dlcpitt/interface/icons/apparel_ashur_armor.dds")
        if "fawkes" in ed or "фокс" in lbl:
            return must("textures/interface/icons/pipboyimages/perks/perk_ms04strength.dds")
        if "charon" in ed or "харон" in lbl or "ghoul" in race:
            return must("textures/interface/icons/pipboyimages/apparel/apperal_ghoul_mask.dds")
        if "moira" in ed or "мойра" in lbl:
            return must("textures/interface/icons/pipboyimages/perks/perk_survival guru.dds")
        if "burke" in ed or "берк" in lbl or "stranger" in ed:
            return must("textures/interface/icons/pipboyimages/perks/perk_mysterious stranger.dds")

        # Check iconic worn/carried armor first (BoS, Enclave, Vault Suit, Raiders, Scientists)
        for cfid in cntos:
            ic = item_icons.get(cfid, "")
            if ic and any(tag in ic for tag in ICONIC_CHAR_ARMORS):
                return ic

        fblob = " ".join(facts) + " " + ed + " " + lbl
        if "child" in race or "kid" in ed or "ребенок" in lbl or "девоч" in lbl or "мальч" in lbl:
            return must("textures/interface/icons/pipboyimages/perks/perk_child at heart.dds")
        if "enclave" in fblob or "анклав" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/apperal_enclave_power_armor.dds")
        if "brotherhood" in fblob or "outcast" in fblob or "lyons" in fblob or "братств" in lbl or "изго" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/power_armor.dds")
        if "vault101" in fblob or "overseer" in fblob or "убежищ" in lbl or "смотрител" in lbl or "буч" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/vault_suit_101.dds")
        if "talon" in fblob or "коготь" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/appearal_combat_armor.dds")
        if "regulator" in fblob or "регулятор" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/appearal_cowboy_duster_outfit.dds")
        if "raider" in race or "raider" in fblob or "рейдер" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/apperal_raider_armor_2.dds")
        if "slaver" in fblob or "работорг" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/apperal_slaver_outfit_1.dds")
        if "slave" in fblob or "раб " in lbl or dlc == "pitt":
            if "pitt" in dlc:
                return must("textures/dlcpitt/interface/icons/apparel_slave_outfit.dds")
        if "doctor" in fblob or "medic" in fblob or "доктор" in lbl or "врач" in lbl:
            return must("textures/interface/icons/stats/skills_medicine.dds")
        if "scien" in fblob or "учен" in lbl or "лабор" in lbl or "scribe" in fblob or "писц" in lbl:
            return must("textures/interface/icons/pipboyimages/apparel/apperal_rivet_city_scientist.dds")
        if "merchant" in fblob or "vendor" in fblob or "trader" in fblob or "торгов" in lbl or "караван" in lbl:
            return must("textures/interface/icons/pipboyimages/perks/perk_master trader.dds")
        if "paladin" in fblob or "knight" in fblob or "soldier" in fblob or "guard" in fblob or "security" in fblob or "солдат" in lbl or "охран" in lbl:
            return must("textures/interface/icons/pipboyimages/perks/perk_commando.dds")
        if dlc == "anchorage":
            if "chinese" in fblob or "китай" in lbl:
                return must("textures/interface/icons/pipboyimages/apparel/apperal_chinese_officer_jumpsuit.dds")
            return must("textures/interface/icons/pipboyimages/perks/perk_commando.dds")
        if dlc == "pointlookout":
            return must("textures/dlc04/interface/icons/apparel_native.dds")
        if dlc == "zeta":
            return must("textures/dlc05/interface/icons/apparel_spacesuit.dds")
        if female:
            return must("textures/interface/icons/pipboyimages/perks/perk_black_widow.dds")
        if "old" in race:
            return must("textures/interface/icons/pipboyimages/perks/perk_impartial mediation.dds")
        return must("textures/interface/icons/message icons/glow_message_vaultboy_neutral.dds")

    def pick_location_icon(n: dict) -> str:
        ed = n.get("edid", "").lower()
        lbl = (n.get("label", "") + " " + n.get("labelEn", "")).lower()
        # Direct map marker type match by substring
        for mk_edid, tnam in marker_by_edid.items():
            if len(mk_edid) > 6 and (ed in mk_edid or mk_edid.replace("mapmarker", "") in ed):
                if tnam in MAP_TYPE_ICONS:
                    return must(MAP_TYPE_ICONS[tnam])
        combo = f"{ed} {lbl}"
        if "vault" in combo or "убежищ" in combo or re.search(r"\bv\d{2,3}\b", combo):
            return must("textures/interface/icons/world map/icon_map_vault.dds")
        if any(k in combo for k in ("metro", "station", "tunnel", "subway", "метро", "станц", "туннел", "тоннел")):
            return must("textures/interface/icons/world map/icon_map_metro.dds")
        if any(k in combo for k in ("citadel", "fort", "bunker", "pentagon", "military", "adams", "cit", "арсенал", "форт", "бункер", "цитадел", "база", "анклав")):
            return must("textures/interface/icons/world map/icon_map_military.dds")
        if any(k in combo for k in ("rivet", "megaton", "tenpenny", "paradise", "underworld", "megatown", "ривет", "мегатон", "тенпенни", "парадиз", "подземел")):
            return must("textures/interface/icons/world map/icon_map_city.dds")
        if any(k in combo for k in ("arefu", "bigtown", "canterbury", "andale", "republic", "oasis", "арефу", "большой город", "оазис", "поселен", "общин")):
            return must("textures/interface/icons/world map/icon_map_settlement.dds")
        if any(k in combo for k in ("factory", "plant", "mill", "steel", "foundry", "refinery", "завод", "фабрик", "пит", "сталел")):
            return must("textures/interface/icons/world map/icon_map_factory.dds")
        if any(k in combo for k in ("monument", "capitol", "memorial", "jefferson", "museum", "lincoln", "мемориал", "музей", "капитол", "монумент")):
            return must("textures/interface/icons/world map/icon_map_monument.dds")
        if any(k in combo for k in ("cave", "cavern", "grotto", "mine", "пещер", "шахт")):
            return must("textures/interface/icons/world map/icon_map_cave.dds")
        if any(k in combo for k in ("sewer", "utility", "drain", "канализ", "коллектор")):
            return must("textures/interface/icons/world map/icon_map_ruins_sewer.dds")
        if any(k in combo for k in ("camp", "encamp", "лагер", "блокпост")):
            return must("textures/interface/icons/world map/icon_map_encampment.dds")
        if any(k in combo for k in ("office", "building", "hq", "robco", "gnr", "library", "clinic", "hospital", "офис", "библиот", "госпитал", "больниц", "здани")):
            return must("textures/interface/icons/world map/icon_map_office.dds")
        if n.get("subtype") == "world":
            return must("textures/interface/icons/message icons/glow_message_map.dds")
        return must("textures/interface/icons/world map/icon_map_ruins_urban.dds")

    def pick_object_icon(n: dict) -> str:
        fid = n["fid"]
        if fid in item_icons:
            return item_icons[fid]
        sub = n.get("subtype", "")
        ed = n.get("edid", "").lower()
        lbl = (n.get("label", "") + " " + n.get("labelEn", "")).lower()
        modl = obj_models.get(fid, "")
        combo = f"{ed} {lbl} {modl}"
        if sub == "perk":
            return must("textures/interface/icons/pipboyimages/perks/perk_intense training.dds")
        if sub == "terminal":
            return must("textures/interface/icons/pipboyimages/perks/perk_l33t haxx0r.dds")
        if sub == "door":
            if "vault" in combo:
                return must("textures/interface/icons/world map/icon_map_vault.dds")
            return must("textures/interface/icons/pipboyimages/perks/perk_infiltrator.dds")
        if sub == "container":
            if "safe" in combo or "сейф" in combo:
                return must("textures/interface/icons/message icons/glow_message_padlock.dds")
            if "firstaid" in combo or "мед" in combo or "аптеч" in combo:
                return must("textures/interface/icons/stats/skills_medicine.dds")
            if "ammo" in combo or "патрон" in combo:
                return must("textures/interface/icons/pipboyimages/items/items_5mm_box.dds")
            return must("textures/interface/icons/message icons/glow_message_giftbox.dds")
        # activator
        if any(k in combo for k in ("radio", "радио", "трансляц", "вышка")):
            return must("textures/interface/icons/message icons/glow_message_radio_tower.dds")
        if any(k in combo for k in ("bomb", "nuke", "бомб", "заряд")):
            return must("textures/interface/icons/pipboyimages/perks/perk_demolition expert.dds")
        if any(k in combo for k in ("bobble", "пупс")):
            return must("textures/interface/icons/pipboyimages/items/items_action_abe_figure.dds")
        if any(k in combo for k in ("water", "purifier", "вод", "очист")):
            return must("textures/interface/icons/pipboyimages/items/items_water.dds")
        if any(k in combo for k in ("switch", "valve", "lever", "button", "рубил", "переключ", "кнопк", "рычаг", "клапан")):
            return must("textures/interface/icons/stats/skills_repair.dds")
        return must("textures/interface/icons/stats/skills_science.dds")

    def pick_quest_or_event_icon(n: dict) -> str:
        sub = n.get("subtype", "")
        ed = n.get("edid", "").lower()
        lbl = (n.get("label", "") + " " + n.get("labelEn", "")).lower()
        dlc = n.get("dlc", "base")
        combo = f"{ed} {lbl}"
        if any(k in combo for k in ("бомб", "atom", "megaton", "атом", "ядер")):
            return must("textures/dlc03/interface/icons/perk_nuclear.dds")
        if any(k in combo for k in ("радио", "radio", "galaxy", "gnr", "тридог", "новости")):
            return must("textures/interface/icons/message icons/glow_message_radio_tower.dds")
        if any(k in combo for k in ("убежищ", "vault", "отец", "father", "pitt", "побег", "escape", "g.o.a.t", "коза")):
            if "dad" in combo or "отец" in combo or "след" in combo or "mq04" in combo or "mq08" in combo:
                return must("textures/interface/icons/pipboyimages/perks/perk_like father_like son.dds")
            return must("textures/interface/icons/world map/icon_map_vault.dds")
        if any(k in combo for k in ("оазис", "oasis", "дерев", "harold")):
            return must("textures/interface/icons/pipboyimages/perks/perk_ms10_barkskin.dds")
        if any(k in combo for k in ("вампир", "blood", "кров", "семья", "family", "ms09")):
            return must("textures/interface/icons/pipboyimages/perks/perk_ms09_hematophage.dds")
        if any(k in combo for k in ("механист", "немир", "гамбит", "gambit", "robot", "робот")):
            return must("textures/interface/icons/pipboyimages/perks/perk_robotics expert.dds")
        if any(k in combo for k in ("андроид", "replicated", "человек", "синтет")):
            return must("textures/interface/icons/pipboyimages/perks/perk_ms08_wired_reflexes.dds")
        if any(k in combo for k in ("руководств", "survival", "guide", "выживан")):
            return must("textures/interface/icons/pipboyimages/perks/perk_survival guru.dds")
        if any(k in combo for k in ("tenpenny", "тенпенни", "гул", "ghoul")):
            return must("textures/interface/icons/pipboyimages/apparel/apperal_ghoul_mask.dds")
        if any(k in combo for k in ("бегемот", "мутант", "mutant", "mutant")):
            return must("textures/interface/icons/pipboyimages/perks/perk_ms04strength.dds")
        if any(k in combo for k in ("симул", "tranquility", "112", "вирт")):
            return must("textures/interface/icons/pipboyimages/apparel/vault_suit_112.dds")
        if any(k in combo for k in ("очист", "проект", "чистот", "purifier", "purity", "geck", "гэкк")):
            return must("textures/interface/icons/pipboyimages/items/items_water.dds")
        if any(k in combo for k in ("линкольн", "рабовладел", "рабов", "slaver", "голова")):
            return must("textures/interface/icons/pipboyimages/perks/perk_lawbringer.dds")
        if dlc == "anchorage":
            return must("textures/dlcanch/interface/icons/dlc02_perk_covert_ops.dds")
        if dlc == "pitt":
            return must("textures/dlcpitt/interface/icons/perk_pitt fighter.dds")
        if dlc == "brokensteel":
            return must("textures/interface/icons/pipboyimages/apparel/power_armor.dds")
        if dlc == "pointlookout":
            return must("textures/dlc04/interface/icons/perk_defender.dds")
        if dlc == "zeta":
            return must("textures/dlc05/interface/icons/perk_zenotech.dds")
        if n["type"] == "event":
            if sub == "random_encounter":
                return must("textures/interface/icons/message icons/glow_message_vaultboy_surprised.dds")
            return must("textures/interface/icons/pipboyimages/perks/perk_explorer.dds")
        if sub == "main":
            return must("textures/interface/icons/pipboyimages/perks/perk_action boy.dds")
        if sub == "side":
            return must("textures/interface/icons/pipboyimages/perks/perk_explorer.dds")
        return must("textures/interface/icons/message icons/glow_message_vaultboy_thinking.dds")

    node_dds: dict[str, str] = {}
    for n in nodes:
        t = n["type"]
        if t == "item":
            dds = pick_item_icon(n)
        elif t == "character":
            dds = pick_creature_icon(n) if n.get("subtype") == "creature" else pick_npc_icon(n)
        elif t == "location":
            dds = pick_location_icon(n)
        elif t == "object":
            dds = pick_object_icon(n)
        else:
            dds = pick_quest_or_event_icon(n)
        assert dds in bsa_files, f"Unresolved DDS for {n['id']}: {dds}"
        node_dds[n["id"]] = dds

    used_dds = sorted(set(node_dds.values()))
    print(f"Mapped all {len(nodes)} nodes across {len(used_dds)} unique official Fallout 3 DDS textures!")

    OUT_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    # Clean previous pngs in public/icons/ so stale files don't linger
    for old_png in OUT_ICONS_DIR.glob("*.png"):
        old_png.unlink()

    key_for_dds: dict[str, str] = {}
    used_keys: set[str] = set()
    tiles: list[tuple[str, Image.Image, bool]] = []

    for dds in used_dds:
        key = make_icon_key(dds)
        if key in used_keys:
            idx = 2
            while f"{key}_{idx}" in used_keys:
                idx += 1
            key = f"{key}_{idx}"
        used_keys.add(key)
        key_for_dds[dds] = key

        raw = extract_bsa_bytes(bsa_files[dds])
        rgba = decode_dds_to_rgba(raw)
        tile, is_color = process_dds_to_tile(rgba)
        tile.save(OUT_ICONS_DIR / f"{key}.png", optimize=True)
        tiles.append((key, tile, is_color))

    # Pack into power-of-two sprite atlas
    count = len(tiles)
    cols = math.ceil(math.sqrt(count))
    rows = math.ceil(count / cols)
    atlas_w = 1 << math.ceil(math.log2(cols * CELL_SIZE))
    atlas_h = 1 << math.ceil(math.log2(rows * CELL_SIZE))
    # Expand cols to match atlas_w capacity if helpful
    cols = atlas_w // CELL_SIZE
    rows = math.ceil(count / cols)
    atlas_h = 1 << math.ceil(math.log2(rows * CELL_SIZE))

    atlas_img = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))
    atlas_icons = {}
    for idx, (key, tile, is_color) in enumerate(tiles):
        col = idx % cols
        row = idx // cols
        x0 = col * CELL_SIZE
        y0 = row * CELL_SIZE
        atlas_img.paste(tile, (x0, y0))
        atlas_icons[key] = {
            "col": col,
            "row": row,
            "u": round(x0 / atlas_w, 6),
            # Three.js flipY=true expects bottom edge in GL bottom-up coords
            "v": round(1.0 - (y0 + CELL_SIZE) / atlas_h, 6),
            "uw": round(CELL_SIZE / atlas_w, 6),
            "vh": round(CELL_SIZE / atlas_h, 6),
            "url": f"/icons/{key}.png",
            "isColor": is_color,
        }

    atlas_path = OUT_ICONS_DIR / "atlas.png"
    atlas_img.save(atlas_path, optimize=True)

    atlas_json = {
        "cols": cols,
        "rows": rows,
        "cellSize": CELL_SIZE,
        "atlasWidth": atlas_w,
        "atlasHeight": atlas_h,
        "icons": atlas_icons,
    }
    (OUT_ICONS_DIR / "atlas.json").write_text(json.dumps(atlas_json, ensure_ascii=False, indent=2), encoding="utf-8")

    # Update graph.json nodes in-place with "icon" field
    for n in nodes:
        n["icon"] = key_for_dds[node_dds[n["id"]]]
    GRAPH_JSON.write_text(json.dumps(graph_data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    type_icon_counts = Counter()
    for n in nodes:
        type_icon_counts[(n["type"], len({n2["icon"] for n2 in nodes if n2["type"] == n["type"]}))] += 1
    print(f"Atlas saved: {atlas_path} ({atlas_w}x{atlas_h}, {count} icons, {atlas_path.stat().st_size // 1024} KB)")
    print("Distinct icons per category:", {t: len({n["icon"] for n in nodes if n["type"] == t}) for t in sorted({n["type"] for n in nodes})})


if __name__ == "__main__":
    main()
