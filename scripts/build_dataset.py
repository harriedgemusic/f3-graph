#!/usr/bin/env python3
"""
Curate, link, lay out, and export Fallout 3 GOTY knowledge graph + walkthroughs
from /tmp/f3_extract/parsed_raw.json into public/data/{graph,details,walkthroughs}.json.
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from walkthrough_guides import CURATED_GUIDES

RAW_PATH = Path("/tmp/f3_extract/parsed_raw.json")
OUT_DIR = Path("/Users/harriedgemusic/Documents/repos/f3-graph/public/data")

MARKER_TYPES = {
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

LOCK_DIFF_MAP = {
    1: "Очень лёгкий (0)",
    2: "Лёгкий (25)",
    3: "Средний (50)",
    4: "Сложный (75)",
    5: "Очень сложный (100)",
    255: "Требуется ключ",
}

IGNORED_EDID_RE = re.compile(
    r"(?:^test|^zz|^aa[a-z]|dummy|holding|warehouse|template|chargen|preview|deadbody|corpseprop|generic|mq00|audioholotape|trigger|marker|default|sound)",
    re.I,
)

GENERIC_NPC_NAMES = {
    "рейдер",
    "супермутант",
    "супермутант-громила",
    "супермутант-мастер",
    "дикий гуль",
    "светящийся",
    "солдат анклава",
    "офицер анклава",
    "послушник",
    "рыцарь братства стали",
    "паладин братства стали",
    "писец",
    "изгой",
    "обитатель пустоши",
    "поселенец",
    "беженец",
    "работорговец",
    "раб",
    "наемник",
    "наёмник компании «коготь»",
    "наемник компании «коготь»",
    "стрелок",
    "китайский солдат",
    "охранник",
    "охранник убежища 101",
    "житель убежища 101",
    "житель ривет-сити",
    "житель мегатонны",
    "обитатель тенпенни-тауэр",
    "болотник",
    "дикарь",
    "контрабандист",
    "пришелец",
    "рейнджер",
    "регулятор",
    "паладин",
    "мародер",
    "бродяга",
    "охотник",
}

GENERIC_CREA_NAMES = {
    "радтаракан",
    "кротокрыс",
    "дутень",
    "огненный муравей",
    "гигантский муравей",
    "радскорпион",
    "гигантский радскорпион",
    "дикая собака",
    "собака",
    "яо-гай",
    "коготь смерти",
    "болотник",
    "болотник-охотник",
    "кентавр",
    "трог",
    "дикий трог",
    "протектрон",
    "мистер храбрец",
    "охранный робот",
    "робомозг",
    "робоглаз",
    "турель",
    "брамин",
}

# Major Story Events anchoring quests, characters, and locations
STORY_EVENTS = [
    {
        "id": "evt_vault101_escape",
        "label": "Побег из Убежища 101 и выход на Пустошь",
        "labelEn": "Vault 101 Escape",
        "dlc": "base",
        "summary": "Исчезновение Джеймса запускает кризис в Убежище 101: гибель Джонаса, тревога Смотрителя и выход Одинокого Путника в открытый мир Столичной Пустоши.",
        "quests": ["CG04", "MQ01"],
        "keywords": ["Vault101", "James", "Amata", "Jonas", "Overseer"],
    },
    {
        "id": "evt_megaton_bomb",
        "label": "Судьба атомной бомбы в Мегатонне",
        "labelEn": "Fate of Megaton Atomic Bomb",
        "dlc": "base",
        "summary": "Ключевой моральный выбор начала игры: обезвредить неразорвавшуюся боеголовку в центре Мегатонны ради спасения города или подорвать её по заказу Алистера Тенпенни и мистера Берка.",
        "quests": ["MS11"],
        "keywords": ["Megaton", "Simms", "Burke", "Tenpenny"],
    },
    {
        "id": "evt_gnr_behemoth",
        "label": "Бой с Бегемотом у «Новостей Галактики»",
        "labelEn": "GNR Plaza Behemoth Battle",
        "dlc": "base",
        "summary": "Совместная оборона здания радиостанции «Новости Галактики» вместе со Львиным Прайдом Сары Лайонс против супермутантов и Бегемота.",
        "quests": ["MQ02"],
        "keywords": ["ThreeDog", "GNR", "SarahLyons", "Behemoth"],
    },
    {
        "id": "evt_tranquility_lane",
        "label": "Симуляция «Трэнквилити-Лейн» в Убежище 112",
        "labelEn": "Tranquility Lane Simulation",
        "dlc": "base",
        "summary": "Освобождение отца из ловушки виртуальной реальности доктора Станислава Брауна (Бетти) через садистские задания или секретный протокол «Китайское вторжение».",
        "quests": ["MQ04"],
        "keywords": ["Vault112", "Braun", "Betty", "Tranquility"],
    },
    {
        "id": "evt_purifier_enclave_raid",
        "label": "Штурм Мемориала Джефферсона и гибель Джеймса",
        "labelEn": "Enclave Assault & James's Sacrifice",
        "dlc": "base",
        "summary": "Высадка Анклава с полковником Отемом прерывает запуск проекта «Чистота». Джеймс жертвует собой, перегружая камеру радиацией, а учёные эвакуируются в Цитадель.",
        "quests": ["MQ05"],
        "keywords": ["JeffersonMemorial", "Autumn", "MadisonLi", "Taft"],
    },
    {
        "id": "evt_paradise_falls_raid",
        "label": "Спасение детей из Парадиз-Фоллз",
        "labelEn": "Rescue from Paradise Falls",
        "dlc": "base",
        "summary": "Проникновение в оплот работорговцев Парадиз-Фоллз ради освобождения юных жителей Литл-Лэмплайта и открытия пути к Убежищу 87.",
        "quests": ["MQ07", "MS13"],
        "keywords": ["ParadiseFalls", "MacCready", "Grouse", "Eulogy"],
    },
    {
        "id": "evt_vault87_geck",
        "label": "Добыча ГЭКК в Убежище 87 и пленение",
        "labelEn": "Vault 87 G.E.C.K. & Enclave Ambush",
        "dlc": "base",
        "summary": "Экспедиция в заражённый источник ВРЭ Убежища 87, знакомство с Фоксом, получение ГЭКК и засада полковника Отема.",
        "quests": ["MQ08"],
        "keywords": ["Vault87", "Fawkes", "GECK"],
    },
    {
        "id": "evt_raven_rock",
        "label": "Побег и падение базы Анклава Рэйвен-Рок",
        "labelEn": "Fall of Raven Rock",
        "dlc": "base",
        "summary": "Встреча с президентом-суперкомпьютером Джоном Генри Эдемом (ZAX), передача модифицированного вируса ВРЭ и возможная самоуничтожительная развязка базы Анклава.",
        "quests": ["MQ09"],
        "keywords": ["RavenRock", "Eden", "Autumn"],
    },
    {
        "id": "evt_liberty_prime_march",
        "label": "Марш Либерти Прайма и запуск «Чистоты»",
        "labelEn": "Liberty Prime March & Project Purity Activation",
        "dlc": "base",
        "summary": "Решающее наступление Братства Стали под прикрытием гигантского робота Либерти Прайма на мемориал Джефферсона и активация очистителя кодом 2-1-6.",
        "quests": ["MQ11"],
        "keywords": ["LibertyPrime", "SarahLyons", "ElderLyons", "JeffersonMemorial"],
    },
    {
        "id": "evt_vault101_crisis",
        "label": "Гражданский кризис в Убежище 101",
        "labelEn": "Vault 101 Rebellion",
        "dlc": "base",
        "summary": "Возвращение в родное Убежище по аварийному сигналу Аматы и окончательный выбор между открытием дверей Пустоши, эвакуацией или изоляцией.",
        "quests": ["MS16"],
        "keywords": ["Vault101", "Amata"],
    },
    {
        "id": "evt_anchorage_sim",
        "label": "Освобождение виртуального Анкориджа и бунт Изгоев",
        "labelEn": "Operation Anchorage Climax & Outcast Mutiny",
        "dlc": "anchorage",
        "summary": "Победа над генералом Чингвеем в военной симуляции армии США, открытие оружейного склада и раскол внутри Братства Изгоев.",
        "quests": ["DLC02OA4"],
        "keywords": ["Outcast", "McGraw", "Sibley", "Jingwei", "Chase"],
    },
    {
        "id": "evt_pitt_uprising",
        "label": "Восстание в Питте и судьба малышки Мари",
        "labelEn": "The Pitt Uprising & Cure Choice",
        "dlc": "pitt",
        "summary": "Кульминация противостояния лорда Ашура и лидера рабов Вернера вокруг лекарства от болезни трогов, заключённого в иммунитете ребёнка Мари.",
        "quests": ["DLC01Quest03"],
        "keywords": ["Ashur", "Wernher", "Midea", "Haven", "Pitt"],
    },
    {
        "id": "evt_liberty_prime_fall",
        "label": "Гибель Либерти Прайма у станции Рокланд",
        "labelEn": "Destruction of Liberty Prime",
        "dlc": "brokensteel",
        "summary": "Орбитальный удар Анклава со спутника «Брэдли-Геркулес» уничтожает боевого робота Либерти Прайма во время прорыва к ретранслятору Рокланд.",
        "quests": ["DLC03BS1"],
        "keywords": ["Rockland", "LibertyPrime", "Rothschild"],
    },
    {
        "id": "evt_adams_afb",
        "label": "Орбитальный удар на авиабазе ВВС Адамс",
        "labelEn": "Adams Air Force Base Orbital Strike",
        "dlc": "brokensteel",
        "summary": "Штурм мобильного краулера Анклава и выбор цели орбитальной бомбардировки: уничтожение последних сил Анклава или предательский удар по Цитадели.",
        "quests": ["DLC03BS3"],
        "keywords": ["Adams", "Crawler", "Citadel"],
    },
    {
        "id": "evt_calvert_mansion",
        "label": "Осада особняка Калверта и похищение фрагмента мозга",
        "labelEn": "Calvert Mansion Siege & Brain Surgery",
        "dlc": "pointlookout",
        "summary": "Тройной заговор между Десмондом Локхартом, мозгом профессора Калверта и капитаном Тобаром в болотах Пойнт-Лукаута.",
        "quests": ["DLC04MQ01", "DLC04MQ04", "DLC04MQ05a"],
        "keywords": ["Desmond", "Calvert", "Tobar", "Cathedral"],
    },
    {
        "id": "evt_zeta_space_battle",
        "label": "Дуэль космических кораблей на орбите Земли",
        "labelEn": "Mothership Zeta Orbital Duel",
        "dlc": "zeta",
        "summary": "Захват капитанского мостика инопланетного корабля «Дзета» разношёрстной командой пленных из разных эпох и космическая битва с вражеским флагманом.",
        "quests": ["DLC05MZ3"],
        "keywords": ["Somah", "Sally", "Elliot", "Toshiro", "Paulson", "Zeta"],
    },
]

# Translation & curation of key Fallout 3 Random Encounter events (from FFEUniqueA/B, FFERepeatA/B)
RE_TITLES_RU = {
    ("FFEUniqueA", 1): ("Умирающий от жажды путник", "Уникальная случайная встреча: обезвоженный житель Пустоши умоляет о чистой воде."),
    ("FFEUniqueA", 2): ("Коготь смерти преследует поселенцев", "Стычка в Пустоши: беженцы спасаются от разъярённого Когтя Смерти."),
    ("FFEUniqueA", 3): ("Спор поселенцев из-за источника воды", "Вооружённый конфликт между бродягами за обладание запасами чистой воды."),
    ("FFEUniqueA", 4): ("Логово и останки Когтя Смерти", "Место недавней охоты Когтя Смерти с останками добычи."),
    ("FFEUniqueA", 5): ("Патруль Братства Стали и рейдеры", "Небольшая боевая группа Братства отражает засаду рейдеров."),
    ("FFEUniqueA", 6): ("Дядя Лео — дружелюбный супермутант", "Редчайшая встреча с мирным супермутантом-философом Дядей Лео, отвергшим насилие (дарит костюм!)."),
    ("FFEUniqueA", 7): ("Раненый Коготь Смерти и охотники", "Ослабленный Коготь Смерти и погибший отряд охотников (источник чертежа Перчатки Когтя Смерти!)."),
    ("FFEUniqueA", 8): ("Крушение инопланетного зонда («Огнестрел»)", "Сверхредкое событие: взрыв НЛО в небе, разбросанные энергоячейки чужих и уникальный пистолет «Огнестрел»!"),
    ("FFEUniqueA", 9): ("Курьер Анклава с разведданными", "Встреча с солдатом-офицером Анклава или шпионом."),
    ("FFEUniqueA", 10): ("Беглый раб с взрывным ошейником", "Отчаявшийся беглец просит обезвредить ошейник работорговцев до взрыва."),
    ("FFEUniqueA", 11): ("Сэм Уоррик — охотник в ловушке", "Одинокий охотник Сэм Уоррик и его яо-гай в горах Пустоши."),
    ("FFEUniqueA", 12): ("Охотник и приручённый яо-гай", "Загадочный следопыт с яо-гаем на поводке."),
    ("FFEUniqueA", 13): ("Мэл и его безумная афера с брамином", "Нелепый грабитель Мэл требует деньги, прикрываясь «взрывным» брамином."),
    ("FFEUniqueA", 14): ("Бен Хейз — беглый учёный", "Выживший лаборант с важными заметками."),
    ("FFEUniqueA", 15): ("Одержимый минами психопат (Грязный Джо)", "Ловушка подрывника на заминированном участке дороги."),
    ("FFEUniqueA", 16): ("Одинокий проповедник Святого Огня", "Странствующий фанатик или выживший."),
    ("FFEUniqueA", 17): ("Потерпевший крушение винтокрыл Анклава", "Обломки сбитого винтокрыла Анклава с редким снаряжением."),
    ("FFEUniqueB", 51): ("Каннибалы-торговцы мясом", "Странные торговцы в Пустоши предлагают купить подозрительную «странную мясную нарезку»."),
    ("FFEUniqueB", 52): ("Охота каннибалов на путника", "Засада каннибалов, выслеживающих очередную жертву."),
    ("FFEUniqueB", 53): ("Снайпер с приманкой", "Маскированный снайпер подстреливает собственную приманку и переводит огонь на игрока."),
    ("FFEUniqueB", 54): ("«Живая бомба» и засада рейдеров", "Беспомощный пленник со взрывчаткой как приманка для засады рейдеров."),
    ("FFEUniqueB", 55): ("Торговец-шарлатан из Пустоши", "Подозрительный странствующий делец."),
    ("FFERepeatA", 1): ("Схватка муравьёв и радскорпиона", "Случайное столкновение мутировавших насекомых в дикой природе."),
    ("FFERepeatA", 2): ("Гигантские муравьи у токсичной бочки", "Муравей мутирует прямо в бочке с радиоактивными отходами."),
    ("FFERepeatB", 51): ("Патруль Братства Изгоев", "Столкновение с патрулём Братства Изгоев, собирающих довоенные технологии."),
    ("FFERepeatB", 52): ("Стычка Изгоев с рейдерами", "Боевое столкновение отряда Изгоев и банды рейдеров."),
    ("FFERepeatB", 53): ("Разведчик Изгоев убегает от Когтей Смерти", "Отряд Изгоев вступает в отчаянный бой с Когтями Смерти."),
}


def clean_str(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def is_russian_text(s: str) -> bool:
    return bool(re.search(r"[А-Яа-яЁё]", s))


def is_junk_edid(edid: str) -> bool:
    if not edid:
        return True
    return bool(IGNORED_EDID_RE.search(edid))


def classify_quest(edid: str, dlc: str, obj_count: int, log_count: int, has_curated: bool) -> str | None:
    u = edid.upper()
    if u.startswith(("FFE", "AUDIO", "GENERIC", "CONV", "DIALOGUE", "CREATURE", "ENDING", "ACHIEVEMENT", "RADI", "UNIQUEFRIENDLY", "HD00", "CG03TEST", "CGTUTORIAL", "MUSEUMTECH", "NQLVL", "DLC02AUDIO", "DLC02CHINESE", "DLC02CONV", "DLC02RADIO", "DLC02STRIKE", "DLC02VOICES", "DLC01CONV", "DLC03AUDIO", "DLC03BS00", "DLC03CONV", "DLC03CREATOR", "DLC03DIALOGUE", "DLC03ENCLAVE", "DLC03ENCOUNTER", "DLC03NQLVL", "DLC03POST", "DLC03WQFUNCTIONS", "DLC03WQSICK", "DLC04FF02GRAVE", "DLC04FF03A", "DLC04GENERIC", "DLC04MUCK", "DLC05ALIEN", "DLC05ASM", "DLC05CONV", "DLC05CORE", "DLC05EXLAB", "DLC05GENERIC", "DLC05HQ", "DLC05POST", "DLC05SAMURAI", "MS02FIN", "MS08FIN", "MS10FIN", "MS11FIN", "MS13SLAVES", "MS16FIN", "MS17RADIO", "MS18RADIO", "MS16RADIO", "MS05NUKA", "MS01ESCORT", "MSOBJECTIVES", "MQ01LD", "MQ04RADIO", "MQ05LD", "MQ00", "MAINQUESTCONVERSATIONS", "DLC03WQ01FIN", "DLC01FFCOLLECTION")):
        return None
    if u.endswith("FIN") or u.endswith("RADIO") or u.endswith("LD") and not has_curated:
        return None
    if has_curated:
        return CURATED_GUIDES[edid]["category"]
    if u.startswith(("CG01", "CG02", "CG03", "CG04", "MQ0", "MQ11", "MQSEARCH", "MQA")):
        return "main"
    if u.startswith("MS"):
        return "side"
    if dlc == "anchorage" and ("OA" in u or obj_count > 0):
        return "anchorage"
    if dlc == "pitt" and ("QUEST" in u or "FFLD" in u or obj_count > 0):
        return "pitt"
    if dlc == "brokensteel" and (obj_count > 0 or "WQ" in u or "BS" in u):
        return "brokensteel"
    if dlc == "pointlookout" and (obj_count > 0 or "MQ" in u or "FF" in u):
        return "pointlookout"
    if dlc == "zeta" and (obj_count > 0 or "MZ" in u or "FF" in u):
        return "zeta"
    if (obj_count > 0 or log_count >= 2 or u.startswith(("FREEFORM", "PERK", "FOLLOWERSHIRE"))) and not is_junk_edid(edid):
        return "freeform"
    return None


def main():
    t0 = time.time()
    print("[1/5] Loading parsed_raw.json ...")
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))

    factions = raw["factions"]
    races = raw["races"]
    npcs = raw["npcs"]
    creatures = raw["creatures"]
    worlds = raw["worlds"]
    cells = raw["cells"]
    markers = raw["markers"]
    items = raw["items"]
    objects = raw["objects"]
    quests = raw["quests"]
    scripts = raw["scripts"]
    refs = raw["refs"]

    # Map EDID -> FID for script text scanning
    quest_by_edid = {q["edid"].lower(): int(k) for k, q in quests.items() if q["edid"]}
    edid_to_fid: dict[str, int] = {}
    for coll in (quests, npcs, creatures, items, objects, cells, markers):
        for k, v in coll.items():
            if v.get("edid"):
                edid_to_fid[v["edid"].lower()] = int(k)

    # ------------------------------------------------------------------
    # Step A: Identify playable quests and collect quest-referenced FIDs
    # ------------------------------------------------------------------
    print("[2/5] Extracting playable quests & quest links ...")
    playable_quests: dict[int, dict[str, Any]] = {}
    quest_cat_map: dict[int, str] = {}

    for k, q in quests.items():
        fid = int(k)
        edid = q["edid"]
        obj_cnt = len(q["objectives"])
        log_cnt = sum(len(s["logs"]) for s in q["stages"].values())
        cat = classify_quest(edid, q["dlc"], obj_cnt, log_cnt, edid in CURATED_GUIDES)
        if cat is not None and (q["name"] or edid in CURATED_GUIDES):
            playable_quests[fid] = q
            quest_cat_map[fid] = cat

    print(f"      Playable quests selected: {len(playable_quests)}")

    # Helper to resolve any FormID (including placed REFR/ACHR/ACRE) to a base entity FID + optional cell/world
    def resolve_ref_or_base(sfid: int) -> tuple[str | None, int, int, int]:
        """Returns (kind, base_fid, cell_fid, wrld_fid)."""
        ks = str(sfid)
        if ks in refs:
            r = refs[ks]
            bfid = r["base_fid"]
            bks = str(bfid)
            if bks in npcs:
                return ("npc", bfid, r["cell_fid"], r["wrld_fid"])
            if bks in creatures:
                return ("crea", bfid, r["cell_fid"], r["wrld_fid"])
            if bks in items:
                return ("item", bfid, r["cell_fid"], r["wrld_fid"])
            if bks in objects:
                return ("obj", bfid, r["cell_fid"], r["wrld_fid"])
            if ks in markers:
                return ("marker", sfid, r["cell_fid"], r["wrld_fid"])
            return (None, bfid, r["cell_fid"], r["wrld_fid"])
        if ks in npcs:
            return ("npc", sfid, 0, 0)
        if ks in creatures:
            return ("crea", sfid, 0, 0)
        if ks in items:
            return ("item", sfid, 0, 0)
        if ks in objects:
            return ("obj", sfid, 0, 0)
        if ks in markers:
            return ("marker", sfid, markers[ks]["cell_fid"], markers[ks]["wrld_fid"])
        if ks in cells:
            return ("cell", sfid, sfid, cells[ks]["wrld_fid"])
        if ks in worlds:
            return ("world", sfid, 0, sfid)
        if ks in playable_quests:
            return ("quest", sfid, 0, 0)
        return (None, 0, 0, 0)

    # Track all quest-referenced FIDs so we NEVER prune a quest-critical entity
    quest_ref_npcs: set[int] = set()
    quest_ref_creas: set[int] = set()
    quest_ref_items: set[int] = set()
    quest_ref_objs: set[int] = set()
    quest_ref_cells: set[int] = set()
    quest_ref_markers: set[int] = set()

    q_links: dict[int, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))

    # Build quick keyword/EDID index for quest scripts
    quest_edid_pattern = re.compile(r"\b(" + "|".join(re.escape(q["edid"]) for q in playable_quests.values() if len(q["edid"]) >= 3) + r")\b", re.I)

    for qfid, q in playable_quests.items():
        all_scros: list[int] = []
        all_sctxs: list[str] = []

        if q["script_fid"]:
            sc = scripts.get(str(q["script_fid"]))
            if sc:
                all_scros.extend(sc["scros"])
                if sc["sctx"]:
                    all_sctxs.append(sc["sctx"])

        for st in q["stages"].values():
            all_scros.extend(st["scros"])
            all_sctxs.extend(st["sctxs"])

        for obj in q["objectives"].values():
            for tfid in obj["targets"]:
                all_scros.append(tfid)

        for sfid in all_scros:
            kind, bfid, cfid, wfid = resolve_ref_or_base(sfid)
            if kind == "npc":
                quest_ref_npcs.add(bfid)
                q_links[qfid]["npcs"].add(bfid)
            elif kind == "crea":
                quest_ref_creas.add(bfid)
                q_links[qfid]["creas"].add(bfid)
            elif kind == "item":
                quest_ref_items.add(bfid)
                q_links[qfid]["items"].add(bfid)
            elif kind == "obj":
                quest_ref_objs.add(bfid)
                q_links[qfid]["objs"].add(bfid)
            elif kind == "marker":
                quest_ref_markers.add(bfid)
                q_links[qfid]["markers"].add(bfid)
            elif kind == "cell":
                quest_ref_cells.add(bfid)
                q_links[qfid]["cells"].add(bfid)
            elif kind == "quest" and bfid != qfid:
                q_links[qfid]["quests"].add(bfid)
            if cfid:
                q_links[qfid]["cells"].add(cfid)

        # Scan SCTX for quest transitions (StartQuest/SetStage/CompleteQuest)
        for sctx in all_sctxs:
            for m in quest_edid_pattern.finditer(sctx):
                other_fid = quest_by_edid.get(m.group(1).lower())
                if other_fid and other_fid != qfid:
                    q_links[qfid]["quests"].add(other_fid)

    # Dialogue links (QSTI + CTDA GetIsID + INFO SCRO)
    for dl in raw["quest_dialogue_links"]:
        qfid = dl["quest_fid"]
        if qfid not in playable_quests:
            continue
        for sp in dl["speakers"]:
            if str(sp) in npcs:
                quest_ref_npcs.add(sp)
                q_links[qfid]["npcs"].add(sp)
            elif str(sp) in creatures:
                quest_ref_creas.add(sp)
                q_links[qfid]["creas"].add(sp)
        for sfid in dl["scros"]:
            kind, bfid, cfid, _ = resolve_ref_or_base(sfid)
            if kind == "item":
                quest_ref_items.add(bfid)
                q_links[qfid]["items"].add(bfid)
            elif kind == "obj":
                quest_ref_objs.add(bfid)
                q_links[qfid]["objs"].add(bfid)
            elif kind == "npc":
                quest_ref_npcs.add(bfid)
                q_links[qfid]["npcs"].add(bfid)
            elif kind == "quest" and bfid != qfid:
                q_links[qfid]["quests"].add(bfid)

    # ------------------------------------------------------------------
    # Step B: Select curated Nodes for Locations, Characters, Items, Objects, Events
    # ------------------------------------------------------------------
    print("[3/5] Selecting curated gameplay nodes & resolving spatial map coordinates ...")

    nodes_dict: dict[str, dict[str, Any]] = {}
    details_dict: dict[str, dict[str, Any]] = {}
    fid_to_node_id: dict[int, str] = {}

    def add_node(
        nid: str,
        fid_int: int,
        edid: str,
        label: str,
        label_en: str,
        ntype: str,
        subtype: str,
        dlc: str,
        tier: str,
        detail: dict[str, Any] | None = None,
    ):
        if not label:
            label = label_en or edid
        if not label:
            return
        nodes_dict[nid] = {
            "id": nid,
            "fid": f"0x{fid_int:08X}" if fid_int else "EVENT",
            "edid": edid,
            "label": clean_str(label),
            "labelEn": clean_str(label_en or label),
            "type": ntype,
            "subtype": subtype,
            "dlc": dlc,
            "tier": tier,
            "degree": 0,
            "x": 0.0,
            "y": 0.0,
            "mapX": 0.0,
            "mapY": 0.0,
        }
        if fid_int:
            fid_to_node_id[fid_int] = nid
        if detail:
            detail["id"] = nid
            details_dict[nid] = detail

    # 1. Locations: Worlds + Map Markers + Named Interior Cells
    usable_worlds: dict[int, dict[str, Any]] = {}
    for k, w in worlds.items():
        fid = int(k)
        ed = w["edid"]
        if not ed or ed.lower().startswith(("t", "test")) or "test" in ed.lower() or "dummy" in ed.lower():
            continue
        if w["name"] or ed in ("Wasteland", "AnchorageWorld", "ThePittWorld", "PointLookoutWorld", "ZetaWorld", "AdamsAFB"):
            usable_worlds[fid] = w

    # Select top Worldspaces (distinct major regions)
    for fid, w in usable_worlds.items():
        ed = w["edid"]
        if ed in ("Wasteland", "MegatonWorld", "CitadelWorld", "TranquilityLane", "DLC02AnchorageWorld", "DLC01ThePittWorld", "DLC04PointLookoutWorld", "DLC05MothershipZetaWorld", "DLC03AdamsAFB01") or w["name"] in ("Пустоши", "Трэнквилити-Лейн", "Авиабаза Адамс", "Питт", "Пойнт-Лукаут"):
            nid = f"loc_{fid:08x}"
            add_node(
                nid,
                fid,
                ed,
                w["name"] or w["name_en"] or ed,
                w["name_en"] or ed,
                "location",
                "world",
                w["dlc"],
                "core",
                {"worldspace": w["name"] or ed, "summary": f"Игровой мир / крупная внешняя область ({w['edid']})."},
            )

    # All 268 Map Markers!
    wasteland_markers: list[tuple[int, float, float]] = []
    dlc_markers_by_wrld: dict[int, list[tuple[int, float, float]]] = defaultdict(list)
    marker_world_fid: dict[int, int] = {}

    # Check duplicate marker labels -> disambiguate if needed
    marker_label_counts: dict[str, int] = defaultdict(int)
    for m in markers.values():
        marker_label_counts[clean_str(m["name"])] += 1

    for k, m in markers.items():
        fid = int(k)
        if not m["name"] or is_junk_edid(m["edid"]):
            continue
        w = worlds.get(str(m["wrld_fid"]), {})
        w_name = w.get("name") or w.get("edid") or "Столичная Пустошь"
        mtype_str = MARKER_TYPES.get(m["marker_type"], "Локация")
        label = clean_str(m["name"])
        if marker_label_counts[label] > 1 and w_name and w_name not in label and w.get("edid") != "Wasteland":
            label = f"{label} ({w_name})"
        nid = f"loc_{fid:08x}"
        add_node(
            nid,
            fid,
            m["edid"] or f"Marker_{fid:08X}",
            label,
            m["name_en"] or label,
            "location",
            "marker",
            m["dlc"],
            "core",
            {
                "worldspace": w_name,
                "markerType": mtype_str,
                "coords": m["pos"],
                "summary": f"{mtype_str} в регионе «{w_name}».",
            },
        )
        marker_world_fid[fid] = m["wrld_fid"]
        if m["pos"] and m["wrld_fid"]:
            if w.get("edid") == "Wasteland" or m["dlc"] == "base" and not w.get("edid", "").startswith("DCworld"):
                wasteland_markers.append((fid, m["pos"][0], m["pos"][1]))
            else:
                dlc_markers_by_wrld[m["wrld_fid"]].append((fid, m["pos"][0], m["pos"][1]))

    # Named Interior Cells (playable)
    selected_cells: dict[int, dict[str, Any]] = {}
    for k, c in cells.items():
        fid = int(k)
        if not c["is_interior"] or not c["name"]:
            continue
        ed = c["edid"]
        nm = clean_str(c["name"])
        if is_junk_edid(ed) or "dummy" in nm.lower() or "test" in nm.lower() or "holding" in nm.lower():
            continue
        selected_cells[fid] = c
        nid = f"loc_{fid:08x}"
        is_core = fid in quest_ref_cells or len(nm) > 2 and any(
            kw in ed.lower()
            for kw in ["megaton", "rivet", "citadel", "vault101", "vault87", "vault112", "vault92", "tenpenny", "underworld", "paradisefalls", "littler", "lamplight", "gnr", "jefferson", "ravenrock", "adams", "pitt", "calvert", "zeta"]
        )
        add_node(
            nid,
            fid,
            ed,
            nm,
            c["name_en"] or nm,
            "location",
            "interior",
            c["dlc"],
            "core" if is_core else "extended",
            {"worldspace": "Внутренняя локация", "summary": f"Внутреннее помещение ({ed})."},
        )

    # 2. Characters (NPCs + Notable/Quest Creatures)
    selected_npcs: set[int] = set()
    for k, n in npcs.items():
        fid = int(k)
        nm = clean_str(n["name"])
        ed = n["edid"]
        if not nm or is_junk_edid(ed):
            continue
        is_q = fid in quest_ref_npcs
        is_generic = nm.lower() in GENERIC_NPC_NAMES
        if is_q or n["essential"] or not is_generic:
            selected_npcs.add(fid)
            race_name = races.get(str(n["race_fid"]), {}).get("name") or "Человек"
            fac_names = []
            for f_entry in n["factions"]:
                fn = factions.get(str(f_entry["fid"]), {}).get("name")
                if fn and fn not in fac_names:
                    fac_names.append(fn)
            tier = "core" if (is_q or n["essential"]) else "extended"
            nid = f"chr_{fid:08x}"
            add_node(
                nid,
                fid,
                ed,
                nm,
                n["name_en"] or nm,
                "character",
                "npc",
                n["dlc"],
                tier,
                {
                    "race": race_name,
                    "level": n["level"],
                    "female": n["female"],
                    "essential": n["essential"],
                    "factions": fac_names[:8],
                    "summary": f"{'Ключевой персонаж' if tier == 'core' else 'Обитатель Пустоши'} ({race_name}, ур. {n['level']}).",
                },
            )

    selected_creas: set[int] = set()
    seen_crea_names: set[str] = set()
    for k, c in creatures.items():
        fid = int(k)
        nm = clean_str(c["name"])
        ed = c["edid"]
        if not nm or is_junk_edid(ed):
            continue
        is_q = fid in quest_ref_creas
        is_generic = nm.lower() in GENERIC_CREA_NAMES
        if is_q or not is_generic:
            # Keep at most 1 representative of a repeated generic creature name unless quest-linked
            if is_generic and not is_q:
                continue
            if not is_q and nm in seen_crea_names and "уник" not in ed.lower():
                continue
            seen_crea_names.add(nm)
            selected_creas.add(fid)
            tier = "core" if (is_q or c["essential"] or "liberty" in ed.lower() or "dogmeat" in ed.lower() or "behemoth" in ed.lower() or "rl3" in ed.lower()) else "extended"
            nid = f"chr_{fid:08x}"
            add_node(
                nid,
                fid,
                ed,
                nm,
                c["name_en"] or nm,
                "character",
                "creature",
                c["dlc"],
                tier,
                {
                    "race": "Существо / Робот",
                    "level": c["level"],
                    "essential": c["essential"],
                    "summary": f"Существо или робот ({ed}, ур. {c['level']}).",
                },
            )

    # 3. Items (Keep playable items & quest-referenced items, excluding unplayable clutter)
    # Count placements & NPC ownership to score item importance
    item_place_counts: dict[int, int] = defaultdict(int)
    for p in raw["item_placements"]:
        item_place_counts[p["base_fid"]] += 1

    selected_items: set[int] = set()
    for k, it in items.items():
        fid = int(k)
        nm = clean_str(it["name"])
        ed = it["edid"]
        if not nm or is_junk_edid(ed):
            continue
        is_q = fid in quest_ref_items
        if not it["playable"] and not is_q:
            continue
        # Skip raw system note templates with pure ASCII EDID-like names unless quest-linked
        if it["subtype"] == "note" and not is_q and not is_russian_text(nm) and not it["text"]:
            continue
        if it["subtype"] == "note" and not is_q and nm == ed:
            continue
        # Include all quest items, keys, books, unique/named weapons & armors, or placed items
        is_unique_gear = ("unique" in ed.lower() or it["subtype"] in ("book", "key") or (it["subtype"] == "note" and is_russian_text(nm) and bool(it["text"])))
        if is_q or is_unique_gear or item_place_counts[fid] > 0 or it["value"] >= 50:
            selected_items.add(fid)
            tier = "core" if (is_q or "unique" in ed.lower() or "bobble" in ed.lower() or it["subtype"] == "book") else "extended"
            nid = f"itm_{fid:08x}"
            det: dict[str, Any] = {
                "value": it["value"],
                "weight": it["weight"],
                "damage": it["damage"],
                "dr": it["dr"],
                "summary": f"Предмет категории «{it['subtype']}» ({ed}).",
            }
            if it["text"]:
                det["text"] = it["text"][:3500]
            add_node(
                nid,
                fid,
                ed,
                nm,
                it["name_en"] or nm,
                "item",
                it["subtype"],
                it["dlc"],
                tier,
                det,
            )

    # Populate NPC inventory lists in details_dict (only selected items)
    for fid in selected_npcs:
        nid = f"chr_{fid:08x}"
        n = npcs[str(fid)]
        inv_items = []
        for entry in n["inventory"]:
            ifid = entry["fid"]
            if ifid in selected_items and f"itm_{ifid:08x}" in nodes_dict:
                inv_items.append(
                    {
                        "id": f"itm_{ifid:08x}",
                        "label": nodes_dict[f"itm_{ifid:08x}"]["label"],
                        "count": entry["count"],
                    }
                )
        if inv_items and nid in details_dict:
            details_dict[nid]["inventory"] = inv_items[:15]

    # 4. Objects (Perks, Terminals, Quest/Notable Activators, Notable Containers, Quest/Locked Doors)
    obj_place_counts: dict[int, int] = defaultdict(int)
    for p in raw["obj_placements"]:
        obj_place_counts[p["base_fid"]] += 1

    locked_base_fids = {lk["base_fid"] for lk in raw["object_locks"] if lk["key_fid"]}
    selected_objs: set[int] = set()

    for k, ob in objects.items():
        fid = int(k)
        nm = clean_str(ob["name"])
        ed = ob["edid"]
        sub = ob["subtype"]
        is_q = fid in quest_ref_objs
        if is_junk_edid(ed) and not is_q:
            continue

        if sub == "perk":
            if not nm or not ob["playable"]:
                continue
            selected_objs.add(fid)
            nid = f"obj_{fid:08x}"
            add_node(
                nid,
                fid,
                ed,
                nm,
                ob["name_en"] or nm,
                "object",
                "perk",
                ob["dlc"],
                "core",
                {
                    "text": ob["desc"],
                    "summary": f"Способность (Перк), доступна с {max(1, ob['min_level'])} уровня." if ob["min_level"] else "Способность (Перк) Одинокого Путника.",
                },
            )
        elif sub == "terminal":
            if not nm:
                continue
            if not (is_q or ob["menu_items"] or obj_place_counts[fid] > 0):
                continue
            # Avoid dozens of identical unlinked generic "Терминал"
            if nm.lower() in ("терминал", "компьютер") and not is_q and not ob["menu_items"]:
                continue
            selected_objs.add(fid)
            nid = f"obj_{fid:08x}"
            tier = "core" if (is_q or len(ob["menu_items"]) >= 2) else "extended"
            add_node(
                nid,
                fid,
                ed,
                nm,
                ob["name_en"] or nm,
                "object",
                "terminal",
                ob["dlc"],
                tier,
                {
                    "lockDiff": LOCK_DIFF_MAP.get(ob["lock_diff"], "") if ob["lock_diff"] else "",
                    "menuItems": ob["menu_items"][:10],
                    "summary": f"Терминал ({ed}), записей меню: {len(ob['menu_items'])}.",
                },
            )
        elif sub == "activator":
            if not nm:
                continue
            if not (is_q or any(kw in ed.lower() for kw in ["bobble", "bomb", "geck", "purifier", "radio", "vault", "switch", "button", "workbench", "reload", "alarm"])):
                continue
            selected_objs.add(fid)
            nid = f"obj_{fid:08x}"
            add_node(
                nid,
                fid,
                ed,
                nm,
                ob["name_en"] or nm,
                "object",
                "activator",
                ob["dlc"],
                "core" if is_q or "bobble" in ed.lower() or "bomb" in ed.lower() else "extended",
                {"summary": f"Интерактивный объект-активатор ({ed})."},
            )
        elif sub == "container":
            if not nm:
                continue
            has_sel_items = any(c["fid"] in selected_items for c in ob["contents"])
            if not (is_q or fid in locked_base_fids or (has_sel_items and ("safe" in ed.lower() or "stash" in ed.lower() or "chest" in ed.lower() or "сейф" in nm.lower() or "тайник" in nm.lower()))):
                continue
            selected_objs.add(fid)
            nid = f"obj_{fid:08x}"
            add_node(
                nid,
                fid,
                ed,
                nm,
                ob["name_en"] or nm,
                "object",
                "container",
                ob["dlc"],
                "core" if is_q else "extended",
                {"summary": f"Контейнер / тайник ({ed})."},
            )
        elif sub == "door":
            if not nm:
                continue
            if not (is_q or fid in locked_base_fids):
                continue
            selected_objs.add(fid)
            nid = f"obj_{fid:08x}"
            add_node(
                nid,
                fid,
                ed,
                nm,
                ob["name_en"] or nm,
                "object",
                "door",
                ob["dlc"],
                "core" if is_q else "extended",
                {"summary": f"Особая / запертая дверь или шлюз ({ed})."},
            )

    # 5. Quests (All playable quests)
    for qfid, q in playable_quests.items():
        ed = q["edid"]
        nid = f"qst_{qfid:08x}"
        guide = CURATED_GUIDES.get(ed, {})
        nm = clean_str(q["name"]) or guide.get("title") or ed
        cat = quest_cat_map[qfid]
        add_node(
            nid,
            qfid,
            ed,
            nm,
            q["name_en"] or nm,
            "quest",
            cat,
            q["dlc"],
            "core",
            {
                "questCategory": cat,
                "summary": guide.get("summary") or f"Игровое задание ({ed}) с {len(q['objectives'])} целями и {len(q['stages'])} этапами.",
            },
        )
        nodes_dict[nid]["walkthroughId"] = nid

    # ------------------------------------------------------------------
    # Step C: Create Edges + Events
    # ------------------------------------------------------------------
    print("[4/5] Building typed edges & curating events ...")
    edges_map: dict[tuple[str, str, str], int] = {}

    def add_edge(src: str, tgt: str, etype: str, weight: int = 1):
        if src == tgt or src not in nodes_dict or tgt not in nodes_dict:
            return
        key = (src, tgt, etype)
        edges_map[key] = max(edges_map.get(key, 0), weight)

    # Helper: nearest Wasteland marker to (x, y)
    marker_coords_by_wrld: dict[int, list[tuple[int, float, float]]] = defaultdict(list)
    for mfid, x, y in wasteland_markers:
        marker_coords_by_wrld[marker_world_fid[mfid]].append((mfid, x, y))
    for wfid, lst in dlc_markers_by_wrld.items():
        marker_coords_by_wrld[wfid].extend(lst)

    def find_nearest_marker(wrld_fid: int, pos: list[float] | None) -> int:
        if not pos or not wrld_fid:
            return 0
        cands = marker_coords_by_wrld.get(wrld_fid)
        if not cands:
            return 0
        px, py = pos[0], pos[1]
        best_fid = 0
        best_d2 = 16000.0 * 16000.0  # ~4 cells radius
        for mfid, mx, my in cands:
            d2 = (px - mx) ** 2 + (py - my) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best_fid = mfid
        return best_fid

    # Track world coords for every node so mapX/mapY has real spatial anchors
    node_world_pos: dict[str, tuple[str, float, float]] = {}

    # Seed map marker world coordinates
    for k, m in markers.items():
        fid = int(k)
        nid = f"loc_{fid:08x}"
        if nid in nodes_dict and m["pos"]:
            w = worlds.get(str(m["wrld_fid"]), {})
            wed = w.get("edid", "Wasteland")
            region = "wasteland" if (m["dlc"] == "base" and not wed.startswith("Tranquility")) else m["dlc"]
            if "Tranquility" in wed:
                region = "tranquility"
            node_world_pos[nid] = (region, m["pos"][0], m["pos"][1])

    # Door links: interior cell <-> exterior marker / interior cell
    cell_to_parent_marker: dict[int, int] = {}
    cell_adj: dict[int, list[int]] = defaultdict(list)
    for dl in raw["door_links"]:
        src_cell = dl["cell_fid"]
        dest_ref = refs.get(str(dl["dest_ref_fid"]))
        if not dest_ref:
            continue
        dest_cell = dest_ref["cell_fid"]
        src_nid = fid_to_node_id.get(src_cell)
        dest_nid = fid_to_node_id.get(dest_cell)

        # If one side is exterior, map interior cell to nearest exterior marker
        if src_cell in selected_cells and dest_cell not in selected_cells and dest_ref["wrld_fid"]:
            mfid = find_nearest_marker(dest_ref["wrld_fid"], dest_ref["pos"])
            if mfid:
                cell_to_parent_marker[src_cell] = mfid
                mnid = f"loc_{mfid:08x}"
                if src_nid and mnid in nodes_dict:
                    add_edge(src_nid, mnid, "location_connection")
        elif dest_cell in selected_cells and src_cell not in selected_cells and dl["wrld_fid"]:
            mfid = find_nearest_marker(dl["wrld_fid"], dl["pos"])
            if mfid:
                cell_to_parent_marker[dest_cell] = mfid
                mnid = f"loc_{mfid:08x}"
                if dest_nid and mnid in nodes_dict:
                    add_edge(dest_nid, mnid, "location_connection")
        elif src_cell in selected_cells and dest_cell in selected_cells and src_cell != dest_cell:
            cell_adj[src_cell].append(dest_cell)
            cell_adj[dest_cell].append(src_cell)
            if src_nid and dest_nid:
                add_edge(src_nid, dest_nid, "location_connection")

    # Propagate parent map marker through multi-level interior cells (BFS)
    bfs_q = deque(cell_to_parent_marker.keys())
    while bfs_q:
        cur = bfs_q.popleft()
        for nxt in cell_adj.get(cur, []):
            if nxt not in cell_to_parent_marker:
                cell_to_parent_marker[nxt] = cell_to_parent_marker[cur]
                bfs_q.append(nxt)

    # Also match cells without door parent by DLC/EDID prefix to markers
    for cfid, c in selected_cells.items():
        if cfid not in cell_to_parent_marker:
            ced = c["edid"].lower()
            for m in markers.values():
                if m["dlc"] == c["dlc"] and m["edid"] and ced[:6] in m["edid"].lower():
                    cell_to_parent_marker[cfid] = m["fid"]
                    break

    # Assign world pos to interior cells from parent markers
    for cfid, mfid in cell_to_parent_marker.items():
        cnid = f"loc_{cfid:08x}"
        mnid = f"loc_{mfid:08x}"
        if cnid in nodes_dict and mnid in node_world_pos:
            node_world_pos[cnid] = node_world_pos[mnid]

    # Helper to find location node ID for a placement
    def placement_to_loc_nid(cell_fid: int, wrld_fid: int, pos: list[float] | None) -> str | None:
        if cell_fid in selected_cells:
            return f"loc_{cell_fid:08x}"
        mfid = find_nearest_marker(wrld_fid, pos)
        if mfid and f"loc_{mfid:08x}" in nodes_dict:
            return f"loc_{mfid:08x}"
        if wrld_fid and f"loc_{wrld_fid:08x}" in nodes_dict:
            return f"loc_{wrld_fid:08x}"
        return None

    # NPC -> Location placements
    for p in raw["npc_placements"]:
        bfid = p["base_fid"]
        if bfid not in selected_npcs and bfid not in selected_creas:
            continue
        cnid = f"chr_{bfid:08x}"
        lnid = placement_to_loc_nid(p["cell_fid"], p["wrld_fid"], p["pos"])
        if lnid:
            add_edge(cnid, lnid, "npc_location")

    # NPC -> Item inventory edges
    for fid in selected_npcs:
        cnid = f"chr_{fid:08x}"
        n = npcs[str(fid)]
        for entry in n["inventory"]:
            ifid = entry["fid"]
            if ifid in selected_items:
                it_sub = items[str(ifid)]["subtype"]
                if it_sub in ("weapon", "armor", "key", "note", "book", "misc") or ifid in quest_ref_items:
                    add_edge(cnid, f"itm_{ifid:08x}", "npc_item")

    # Location -> Item placements (limit to notable items + avoid cluttering 50k generic ammo)
    for p in raw["item_placements"]:
        bfid = p["base_fid"]
        if bfid not in selected_items:
            continue
        it = items[str(bfid)]
        if it["subtype"] in ("ammo", "aid") and bfid not in quest_ref_items:
            continue
        lnid = placement_to_loc_nid(p["cell_fid"], p["wrld_fid"], p["pos"])
        if lnid:
            add_edge(lnid, f"itm_{bfid:08x}", "location_item")

    # Location -> Object placements
    for p in raw["obj_placements"]:
        bfid = p["base_fid"]
        if bfid not in selected_objs:
            continue
        lnid = placement_to_loc_nid(p["cell_fid"], p["wrld_fid"], p["pos"])
        if lnid:
            add_edge(lnid, f"obj_{bfid:08x}", "location_object")

    # Object -> Key locks
    for lk in raw["object_locks"]:
        obid = lk["base_fid"]
        kfid = lk["key_fid"]
        if obid in selected_objs and kfid in selected_items:
            add_edge(f"obj_{obid:08x}", f"itm_{kfid:08x}", "object_key")

    # Quest -> NPC, Location, Item, Object, Quest edges
    for qfid, links in q_links.items():
        qnid = f"qst_{qfid:08x}"
        for nfid in links["npcs"]:
            add_edge(qnid, f"chr_{nfid:08x}", "quest_npc")
        for cfid in links["creas"]:
            add_edge(qnid, f"chr_{cfid:08x}", "quest_npc")
        for ifid in links["items"]:
            add_edge(qnid, f"itm_{ifid:08x}", "quest_item")
        for obid in links["objs"]:
            add_edge(qnid, f"obj_{obid:08x}", "quest_object")
        for mfid in links["markers"]:
            add_edge(qnid, f"loc_{mfid:08x}", "quest_location")
        for cfid in links["cells"]:
            if cfid in selected_cells:
                add_edge(qnid, f"loc_{cfid:08x}", "quest_location")
                if cfid in cell_to_parent_marker:
                    add_edge(qnid, f"loc_{cell_to_parent_marker[cfid]:08x}", "quest_location")
        for other_q in links["quests"]:
            add_edge(qnid, f"qst_{other_q:08x}", "quest_chain")

    # Also add quest_chain edges from curated prerequisites
    for qfid, q in playable_quests.items():
        guide = CURATED_GUIDES.get(q["edid"])
        if guide:
            for pre_edid in guide.get("prerequisites", []):
                pre_fid = quest_by_edid.get(pre_edid.lower())
                if pre_fid and pre_fid in playable_quests:
                    add_edge(f"qst_{pre_fid:08x}", f"qst_{qfid:08x}", "quest_chain")

    # Infer quest_location from primary quest NPCs when a quest has few direct cell/marker links
    npc_locs: dict[str, list[str]] = defaultdict(list)
    for (s, t, et) in list(edges_map.keys()):
        if et == "npc_location":
            npc_locs[s].append(t)
    for (s, t, et) in list(edges_map.keys()):
        if et == "quest_npc":
            for lnid in npc_locs.get(t, [])[:2]:
                add_edge(s, lnid, "quest_location")

    # 6. Events (Major Story Turning Points + Curated Random Encounters)
    for ev in STORY_EVENTS:
        ev_id = ev["id"]
        add_node(
            ev_id,
            0,
            ev_id.upper(),
            ev["label"],
            ev["labelEn"],
            "event",
            "story_event",
            ev["dlc"],
            "core",
            {"summary": ev["summary"]},
        )
        for qed in ev["quests"]:
            qfid = quest_by_edid.get(qed.lower())
            if qfid and f"qst_{qfid:08x}" in nodes_dict:
                qnid = f"qst_{qfid:08x}"
                add_edge(qnid, ev_id, "quest_event")
                # Connect event to top NPCs and Locations of its quest
                for (s, t, et) in list(edges_map.keys()):
                    if s == qnid and et in ("quest_npc", "quest_location"):
                        add_edge(ev_id, t, "event_entity")
        # Also match keywords
        for kw in ev["keywords"]:
            kwl = kw.lower()
            for nid, nd in list(nodes_dict.items()):
                if nd["type"] in ("character", "location", "object", "item") and kwl in nd["edid"].lower():
                    add_edge(ev_id, nid, "event_entity")

    # Random Encounter Events from FFEUniqueA/B & FFERepeatA/B stages
    for (qed, stg_num), (ru_title, ru_desc) in RE_TITLES_RU.items():
        qfid = quest_by_edid.get(qed.lower())
        if not qfid:
            continue
        q = quests[str(qfid)]
        stg = q["stages"].get(str(stg_num))
        if not stg:
            continue
        ev_id = f"evt_re_{qed.lower()}_{stg_num}"
        add_node(
            ev_id,
            qfid,
            f"{qed}_S{stg_num}",
            ru_title,
            stg["logs"][0][:60] if stg["logs"] else f"{qed} #{stg_num}",
            "event",
            "random_encounter",
            "base",
            "core",
            {"summary": ru_desc},
        )
        for sfid in stg["scros"]:
            kind, bfid, cfid, _ = resolve_ref_or_base(sfid)
            if kind in ("npc", "crea") and f"chr_{bfid:08x}" in nodes_dict:
                add_edge(ev_id, f"chr_{bfid:08x}", "event_entity")
            elif kind == "item" and f"itm_{bfid:08x}" in nodes_dict:
                add_edge(ev_id, f"itm_{bfid:08x}", "event_entity")
            elif kind == "obj" and f"obj_{bfid:08x}" in nodes_dict:
                add_edge(ev_id, f"obj_{bfid:08x}", "event_entity")

    # Prune completely isolated extended-tier items/objects/locations (degree 0)
    deg_counter: dict[str, int] = defaultdict(int)
    for (s, t, _) in edges_map:
        deg_counter[s] += 1
        deg_counter[t] += 1

    pruned_nodes = {}
    for nid, nd in nodes_dict.items():
        deg = deg_counter[nid]
        nd["degree"] = deg
        if deg == 0 and nd["tier"] == "extended" and nd["type"] in ("item", "object", "location"):
            continue
        pruned_nodes[nid] = nd
    nodes_dict = pruned_nodes

    final_edges = []
    final_deg: dict[str, int] = defaultdict(int)
    for idx, ((s, t, et), w) in enumerate(edges_map.items()):
        if s in nodes_dict and t in nodes_dict:
            final_edges.append({"id": f"e{idx}", "source": s, "target": t, "type": et, "weight": w})
            final_deg[s] += 1
            final_deg[t] += 1

    for nid, nd in nodes_dict.items():
        nd["degree"] = final_deg[nid]

    # Re-balance core tier: keep core crisp (~1200-1800 nodes)
    # Any non-quest/non-event/non-marker node with degree >= 3 stays core, plus top quest neighbors
    for nid, nd in nodes_dict.items():
        if nd["type"] in ("quest", "event"):
            nd["tier"] = "core"
        elif nd["type"] == "location" and nd["subtype"] in ("marker", "world"):
            nd["tier"] = "core"
        elif nd["degree"] >= 3:
            nd["tier"] = "core"

    # ------------------------------------------------------------------
    # Step D: Compute 2 Deterministic Layouts (Clustered Force + Wasteland Map)
    # ------------------------------------------------------------------
    print("[5/5] Computing layouts & generating walkthroughs ...")
    node_ids = list(nodes_dict.keys())
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    n_nodes = len(node_ids)

    # 1) Wasteland Map Coordinates (mapX, mapY)
    # Normalize Wasteland markers to [-750, 750] and place DLCs in clean outer sectors
    wl_coords = [(x, y) for reg, x, y in node_world_pos.values() if reg == "wasteland"]
    if wl_coords:
        xs = [c[0] for c in wl_coords]
        ys = [c[1] for c in wl_coords]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span = max(max_x - min_x, max_y - min_y, 1.0)
        cx = (min_x + max_x) / 2.0
        cy = (min_y + max_y) / 2.0
    else:
        cx, cy, span = 0.0, 0.0, 1.0

    dlc_anchors = {
        "anchorage": (-850.0, 720.0),
        "pitt": (850.0, 720.0),
        "brokensteel": (850.0, -720.0),
        "pointlookout": (-850.0, -720.0),
        "zeta": (0.0, 920.0),
        "tranquility": (-900.0, 0.0),
    }

    # Precompute neighbor lists
    adj_idx: list[list[int]] = [[] for _ in range(n_nodes)]
    for e in final_edges:
        si = id_to_idx[e["source"]]
        ti = id_to_idx[e["target"]]
        adj_idx[si].append(ti)
        adj_idx[ti].append(si)

    rng = np.random.default_rng(42)
    map_pos = np.zeros((n_nodes, 2), dtype=np.float64)
    has_map_pos = np.zeros(n_nodes, dtype=bool)

    for i, nid in enumerate(node_ids):
        if nid in node_world_pos:
            reg, wx, wy = node_world_pos[nid]
            if reg == "wasteland":
                map_pos[i, 0] = ((wx - cx) / span) * 1450.0
                map_pos[i, 1] = ((wy - cy) / span) * 1450.0
            else:
                ax, ay = dlc_anchors.get(reg, (0.0, 0.0))
                map_pos[i, 0] = ax + rng.normal(0, 85.0)
                map_pos[i, 1] = ay + rng.normal(0, 85.0)
            has_map_pos[i] = True
        else:
            nd = nodes_dict[nid]
            if nd["dlc"] != "base":
                ax, ay = dlc_anchors.get(nd["dlc"], (0.0, 0.0))
                map_pos[i, 0] = ax + rng.normal(0, 75.0)
                map_pos[i, 1] = ay + rng.normal(0, 75.0)
                has_map_pos[i] = True

    # Propagate map coords along edges (3 passes)
    for _ in range(4):
        new_pos = map_pos.copy()
        new_has = has_map_pos.copy()
        for i in range(n_nodes):
            if has_map_pos[i]:
                continue
            pts = [map_pos[j] for j in adj_idx[i] if has_map_pos[j]]
            if pts:
                mean_pt = np.mean(pts, axis=0)
                new_pos[i] = mean_pt + rng.normal(0, 22.0, size=2)
                new_has[i] = True
        map_pos = new_pos
        has_map_pos = new_has

    for i in range(n_nodes):
        if not has_map_pos[i]:
            map_pos[i] = rng.normal(0, 120.0, size=2)
        else:
            # Slight deterministic jitter for nodes sharing exact marker/cell
            if nodes_dict[node_ids[i]]["type"] != "location" or nodes_dict[node_ids[i]]["subtype"] != "marker":
                map_pos[i] += rng.normal(0, 14.0, size=2)

    # 2) Clustered Force-Directed Layout (x, y) via fast NumPy vectorized grid/batch repulsion
    cluster_centers = {
        ("quest", "base"): (0.0, 0.0),
        ("event", "base"): (0.0, -240.0),
        ("character", "base"): (-380.0, 220.0),
        ("location", "base"): (380.0, 220.0),
        ("item", "base"): (-380.0, -280.0),
        ("object", "base"): (380.0, -280.0),
        "anchorage": (-820.0, 620.0),
        "pitt": (820.0, 620.0),
        "brokensteel": (820.0, -620.0),
        "pointlookout": (-820.0, -620.0),
        "zeta": (0.0, 820.0),
    }
    pos = np.zeros((n_nodes, 2), dtype=np.float64)
    for i, nid in enumerate(node_ids):
        nd = nodes_dict[nid]
        if nd["dlc"] != "base":
            base_c = cluster_centers[nd["dlc"]]
        else:
            base_c = cluster_centers.get((nd["type"], "base"), (0.0, 0.0))
        pos[i, 0] = base_c[0] + rng.normal(0, 130.0)
        pos[i, 1] = base_c[1] + rng.normal(0, 130.0)

    src_idx = np.array([id_to_idx[e["source"]] for e in final_edges], dtype=np.int32)
    tgt_idx = np.array([id_to_idx[e["target"]] for e in final_edges], dtype=np.int32)
    degrees = np.array([max(1, nodes_dict[nid]["degree"]) for nid in node_ids], dtype=np.float64)

    # Fast force layout: edge spring attraction + sampled/chunked Barnes-Hut-style repulsion
    iters = 65
    for it in range(iters):
        disp = np.zeros_like(pos)
        # Edge springs
        if len(src_idx) > 0:
            diff = pos[tgt_idx] - pos[src_idx]
            dist = np.linalg.norm(diff, axis=1) + 1e-6
            # Ideal edge length ~55
            force = (dist - 55.0) * 0.06
            fvec = (diff / dist[:, None]) * force[:, None]
            np.add.at(disp, src_idx, fvec)
            np.add.at(disp, tgt_idx, -fvec)

        # Chunked exact repulsion (fast in NumPy for ~5k nodes: 5000x512 chunks)
        chunk = 512
        rep_strength = 1600.0
        for s in range(0, n_nodes, chunk):
            e = min(s + chunk, n_nodes)
            d = pos[s:e, None, :] - pos[None, :, :]  # (chunk, N, 2)
            d2 = np.sum(d * d, axis=2) + 25.0
            inv = rep_strength / (d2 * np.sqrt(d2))
            disp[s:e] += np.sum(d * inv[:, :, None], axis=1)

        # Gentle centering gravity
        disp -= pos * 0.015

        # Cap step size (simulated annealing cooling)
        max_step = 45.0 * (1.0 - it / (iters + 5.0))
        norms = np.linalg.norm(disp, axis=1) + 1e-6
        scale = np.minimum(1.0, max_step / norms)
        pos += disp * scale[:, None]

    # Normalize clustered pos to [-1000, 1000]
    p_min = pos.min(axis=0)
    p_max = pos.max(axis=0)
    p_span = max(p_max[0] - p_min[0], p_max[1] - p_min[1], 1.0)
    pos = ((pos - (p_min + p_max) / 2.0) / p_span) * 1900.0

    # Normalize map pos cleanly too
    mp_min = map_pos.min(axis=0)
    mp_max = map_pos.max(axis=0)
    mp_span = max(mp_max[0] - mp_min[0], mp_max[1] - mp_min[1], 1.0)
    map_pos = ((map_pos - (mp_min + mp_max) / 2.0) / mp_span) * 1900.0

    for i, nid in enumerate(node_ids):
        nodes_dict[nid]["x"] = round(float(pos[i, 0]), 2)
        nodes_dict[nid]["y"] = round(float(pos[i, 1]), 2)
        nodes_dict[nid]["mapX"] = round(float(map_pos[i, 0]), 2)
        nodes_dict[nid]["mapY"] = round(float(map_pos[i, 1]), 2)

    # ------------------------------------------------------------------
    # Step E: Assemble Walkthroughs JSON
    # ------------------------------------------------------------------
    adj_by_node: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for e in final_edges:
        adj_by_node[e["source"]].append((e["target"], e["type"]))
        adj_by_node[e["target"]].append((e["source"], e["type"]))

    walkthroughs: list[dict[str, Any]] = []
    for qfid, q in playable_quests.items():
        qnid = f"qst_{qfid:08x}"
        if qnid not in nodes_dict:
            continue
        nd = nodes_dict[qnid]
        edid = q["edid"]
        guide = CURATED_GUIDES.get(edid)
        cat = quest_cat_map[qfid]

        # Official ESM Objectives
        esm_objs = [
            {"index": o["index"], "text": clean_str(o["text"])}
            for o in sorted(q["objectives"].values(), key=lambda x: x["index"])
            if clean_str(o["text"])
        ]

        # Official ESM Stage Logs
        esm_stages = []
        for st in sorted(q["stages"].values(), key=lambda x: x["stage"]):
            logs = [clean_str(l) for l in st["logs"] if clean_str(l)]
            if logs:
                esm_stages.append(
                    {
                        "stage": st["stage"],
                        "logs": logs,
                        "completes": bool(st["flags"] & 0x01),
                        "fails": bool(st["flags"] & 0x02),
                    }
                )

        # Linked entity IDs categorized
        linked = {
            "characters": [],
            "locations": [],
            "events": [],
            "items": [],
            "objects": [],
            "quests": [],
        }
        seen_link: set[str] = set()
        for nb_id, _ in adj_by_node.get(qnid, []):
            if nb_id in seen_link or nb_id not in nodes_dict:
                continue
            seen_link.add(nb_id)
            nt = nodes_dict[nb_id]["type"]
            if nt == "character":
                linked["characters"].append(nb_id)
            elif nt == "location":
                linked["locations"].append(nb_id)
            elif nt == "event":
                linked["events"].append(nb_id)
            elif nt == "item":
                linked["items"].append(nb_id)
            elif nt == "object":
                linked["objects"].append(nb_id)
            elif nt == "quest":
                linked["quests"].append(nb_id)

        if guide:
            steps = guide["steps"]
            summary = guide["summary"]
            start_cond = guide["startCondition"]
            prereqs = guide.get("prerequisites", [])
            rewards = guide["rewards"]
            warnings = guide.get("missableWarnings", [])
            order = guide["order"]
            curated = True
        else:
            # Synthesize structured steps from ESM Objectives + Journal Logs + Linked Entities
            curated = False
            order = 200
            steps = []
            for o in esm_objs:
                steps.append(
                    {
                        "title": f"Цель #{o['index']}",
                        "description": o["text"],
                    }
                )
            if not steps and esm_stages:
                for st in esm_stages[:8]:
                    steps.append(
                        {
                            "title": f"Этап {st['stage']}",
                            "description": " ".join(st["logs"]),
                        }
                    )
            if not steps:
                loc_names = [nodes_dict[i]["label"] for i in linked["locations"][:3]]
                char_names = [nodes_dict[i]["label"] for i in linked["characters"][:3]]
                steps.append(
                    {
                        "title": "Выполнение свободного поручения",
                        "description": f"Поговорите с ключевыми персонажами ({', '.join(char_names) or 'см. граф'}) в локациях: {', '.join(loc_names) or 'см. карту'} и выполните условия задания.",
                    }
                )
            loc_str = ", ".join(nodes_dict[i]["label"] for i in linked["locations"][:2])
            char_str = ", ".join(nodes_dict[i]["label"] for i in linked["characters"][:2])
            summary = f"Задание «{nd['label']}» ({edid}) из модуля «{nd['dlc']}»."
            if char_str:
                summary += f" Ключевые участники: {char_str}."
            if loc_str:
                summary += f" Локации: {loc_str}."
            start_cond = f"Начинается при взаимодействии с {char_str or 'ключевым объектом/NPC'} ({loc_str or 'Столичная Пустошь'})."
            prereqs = []
            rewards = ["Очки опыта", "Предметы / крышки / репутация (см. связанные сущности)"]
            warnings = []

        walkthroughs.append(
            {
                "id": qnid,
                "nodeId": qnid,
                "fid": nd["fid"],
                "edid": edid,
                "title": nd["label"],
                "titleEn": nd["labelEn"],
                "dlc": nd["dlc"],
                "category": cat,
                "order": order,
                "curated": curated,
                "summary": summary,
                "startCondition": start_cond,
                "prerequisites": prereqs,
                "rewards": rewards,
                "missableWarnings": warnings,
                "steps": steps,
                "objectives": esm_objs,
                "stageLogs": esm_stages,
                "linkedEntities": linked,
            }
        )

    walkthroughs.sort(key=lambda w: (w["order"], w["title"]))

    # Meta counters
    counts_by_type: dict[str, int] = defaultdict(int)
    counts_by_dlc: dict[str, int] = defaultdict(int)
    core_count = 0
    for nd in nodes_dict.values():
        counts_by_type[nd["type"]] += 1
        counts_by_dlc[nd["dlc"]] += 1
        if nd["tier"] == "core":
            core_count += 1

    counts_by_edge: dict[str, int] = defaultdict(int)
    for e in final_edges:
        counts_by_edge[e["type"]] += 1

    graph_out = {
        "meta": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "source": "Fallout 3 GOTY (RUS + ENG ESM)",
            "countsByType": dict(counts_by_type),
            "countsByDlc": dict(counts_by_dlc),
            "countsByEdgeType": dict(counts_by_edge),
            "coreNodes": core_count,
            "totalNodes": len(nodes_dict),
            "totalEdges": len(final_edges),
        },
        "nodes": list(nodes_dict.values()),
        "edges": final_edges,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "graph.json").write_text(json.dumps(graph_out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT_DIR / "details.json").write_text(json.dumps(details_dict, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT_DIR / "walkthroughs.json").write_text(json.dumps(walkthroughs, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Done in {time.time() - t0:.2f}s!")
    print("Meta:", json.dumps(graph_out["meta"], ensure_ascii=False, indent=2))
    print(f"Walkthroughs exported: {len(walkthroughs)} (curated={sum(1 for w in walkthroughs if w['curated'])})")
    for fn in ("graph.json", "details.json", "walkthroughs.json"):
        sz = (OUT_DIR / fn).stat().st_size / 1024.0
        print(f"  {fn}: {sz:.1f} KB")


if __name__ == "__main__":
    main()
