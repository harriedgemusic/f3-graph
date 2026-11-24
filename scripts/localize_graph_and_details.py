#!/usr/bin/env python3
"""
Localize all remaining untranslated labels and metadata in:
  - public/data/graph.json
  - public/data/details.json
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = ROOT / "public" / "data" / "graph.json"
DETAILS_PATH = ROOT / "public" / "data" / "details.json"
WALKTHROUGHS_PATH = ROOT / "public" / "data" / "walkthroughs.json"

HAS_CYRILLIC = re.compile(r"[А-Яа-яЁё]")

ENGLISH_QUEST_IDS: set[str] = {
    "qst_0009426d",
    "qst_000371d2",
    "qst_000943ec",
    "qst_000943ed",
    "qst_000943ee",
    "qst_0002fa33",
    "qst_000943eb",
    "qst_00062736",
    "qst_000173d8",
    "qst_000173d1",
    "qst_000173d9",
    "qst_0006136d",
    "qst_010034da",
    "qst_05005c70",
}

# 1. Exact Russian quest titles (14 English quests + 67 normalized literary title-case quests)
QUEST_LABELS_RU: dict[str, str] = {
    # 14 previously English quests
    "qst_0009426d": "Наём напарника: Буч Делория",
    "qst_000371d2": "Наём напарника: Харон",
    "qst_000943ec": "Наём напарника: Кловер",
    "qst_000943ed": "Наём напарника: Псина",
    "qst_000943ee": "Наём напарника: Фокс",
    "qst_0002fa33": "Наём напарника: Джерико",
    "qst_000943eb": "Наём напарника: Сержант РЛ-3",
    "qst_00062736": "Наём напарника: Паладин-звезда Кросс",
    "qst_000173d8": "Поручения и заботы Мегатонны",
    "qst_000173d1": "Исследование руин Вашингтона",
    "qst_000173d9": "Поручения в Цитадели Братства Стали",
    "qst_0006136d": "Обучение ношению силовой брони",
    "qst_010034da": "Разведданные симуляции «Анкоридж»",
    "qst_05005c70": "Крысы в трюме корабля «Зета»",
    # 67 main/side/DLC quests normalized from ALL-CAPS to Russian literary title case
    "qst_0002a274": "Оазис",
    "qst_0009b5bb": "Авраам Вашингтон — покупатель",
    "qst_000872e6": "Поиски продолжаются",
    "qst_0006f1e8": "Законник",
    "qst_0006f1e7": "Наёмный убийца",
    "qst_0005ecfd": "Наследие Линкольна",
    "qst_00014ea5": "Рейнджеры Рейли",
    "qst_00014ea4": "Песнь Агаты",
    "qst_00014ea3": "Проблемы на домашнем фронте",
    "qst_00014ea2": "Украденная независимость",
    "qst_00014ea1": "Контрольный выстрел",
    "qst_00014ea0": "Просто бизнес",
    "qst_00014e9f": "Тенпенни-Тауэр",
    "qst_00014e9e": "Сила Атома",
    "qst_00014e9c": "Узы крови",
    "qst_00014e9b": "Искусственный человек",
    "qst_00014e99": "Глава государства",
    "qst_00014e98": "Погоня за Ядер-Колой",
    "qst_00014e97": "Они!",
    "qst_00014e96": "Руководство по выживанию на Пустошах",
    "qst_00014e95": "Нечеловеческий гамбит",
    "qst_00014e94": "Большие проблемы в Большом Городе",
    "qst_00014e93": "Проект «Нечистоты»",
    "qst_00014e91": "Забери его!",
    "qst_00014e90": "Проникновение",
    "qst_00014e8f": "Американская мечта",
    "qst_00014e8e": "Поиски Эдемских кущ",
    "qst_00014e8d": "Спасение из рая",
    "qst_00014e8c": "По следам",
    "qst_00014e8b": "Живая вода",
    "qst_00014e8a": "Трэнквилити-Лейн",
    "qst_00014e89": "Гонка преследования",
    "qst_00014e88": "Радио «Новости Галактики»",
    "qst_00014e87": "След в след",
    "qst_00014e86": "Побег!",
    "qst_00014e85": "Будущее в тумане",
    "qst_00014e84": "Быстрое взросление",
    "qst_00014e83": "Первые шаги",
    "qst_010014f6": "Операция «Анкоридж»",
    "qst_010009c0": "Подготовка наступления",
    "qst_010009bf": "Орудия Анкориджа",
    "qst_010009be": "Помощь Изгоям",
    "qst_0200a358": "Найти Билла-Дикаря",
    "qst_0200108d": "Свободный труд",
    "qst_0200108c": "Проникнуть в Питт",
    "qst_0200108b": "Вредные условия труда",
    "qst_03004c75": "Святая вода",
    "qst_03003b67": "Великолепная лечебная вода!",
    "qst_03003b42": "Защита караванов",
    "qst_030011ad": "Кто смел, тот побеждает",
    "qst_03000afd": "Плата за электричество",
    "qst_03000802": "Смерть с небес",
    "qst_04009b5e": "Сафари Плика",
    "qst_0400815c": "Беспризорник Кенни",
    "qst_0400584b": "Схватка интеллектов",
    "qst_0400584a": "Схватка интеллектов",
    "qst_04005849": "Мысли под контролем",
    "qst_04005848": "Шепчущие голоса",
    "qst_04005847": "Прогулка с духами",
    "qst_04005846": "Местные нравы",
    "qst_0400436e": "Бархатный занавес",
    "qst_04003f70": "Бальзам на душу",
    "qst_04002f47": "Тёмная душа Блэкхолла",
    "qst_04002f18": "Страны далёкие",
    "qst_05000804": "Эта галактика не столь велика...",
    "qst_05000803": "Среди звёзд",
    "qst_05000802": "Не из этого мира",
}

# 2. All 42 DC* sector markers with Russian district context parsed from their summary & connected locations
DC_SECTOR_LABELS_RU: dict[str, str] = {
    "loc_00094287": "Сектор руин DC01a (Чеви-Чейз — Рок-Крик)",
    "loc_00094286": "Сектор руин DC01b (Чеви-Чейз — восток)",
    "loc_00094290": "Сектор руин DC03a (Дюпон — северо-восток)",
    "loc_00094291": "Сектор руин DC03b (Дюпон — запад)",
    "loc_00094292": "Сектор руин DC03c (Дюпон-сёркл)",
    "loc_0009428b": "Сектор руин DC05a (Такома-парк)",
    "loc_0009428c": "Сектор руин DC05b (Такома — промышленная зона)",
    "loc_0009428d": "Сектор руин DC06a (Вернон-сквер — север)",
    "loc_0009428e": "Сектор руин DC06b (Вернон-сквер — восток)",
    "loc_0001eb92": "Сектор руин DC06c (Станция «Вернон-сквер»)",
    "loc_00094295": "Сектор руин DC08a (Вернон-сквер — больница)",
    "loc_00027963": "Сектор руин DC08b (Больница Надежды)",
    "loc_00027966": "Сектор руин DC08c (Отель «Стейтсмен»)",
    "loc_00094296": "Сектор руин DC09a (Пенсильвания-авеню — северо-запад)",
    "loc_00094297": "Сектор руин DC09b (Молл — северо-запад)",
    "loc_0009429c": "Сектор руин DC09c (Пенсильвания-авеню — восток)",
    "loc_00094299": "Сектор руин DC09e (Пенсильвания-авеню — юг)",
    "loc_0009429a": "Сектор руин DC09f (Пенсильвания-авеню — Метро-центр)",
    "loc_0009429b": "Сектор руин DC09g (Пенсильвания-авеню — север)",
    "loc_0009429d": "Сектор руин DC10a (Ланфан-плаза)",
    "loc_0009429e": "Сектор руин DC10b (Мемориал Джефферсона)",
    "loc_00094288": "Сектор руин DC11a (Джорджтаун — север)",
    "loc_00094293": "Сектор руин DC11b (Джорджтаун — юг)",
    "loc_00094294": "Сектор руин DC11c (Джорджтаун — восток)",
    "loc_000942a3": "Сектор руин DC12a (Молл — Метро-центр)",
    "loc_000942a4": "Сектор руин DC12b (Молл — Капитолий)",
    "loc_000942a5": "Сектор руин DC12c (Сьюард-сквер — Капитолий)",
    "loc_000942a2": "Сектор руин DC14d (Ланфан-плаза — Анакостия)",
    "loc_00095d37": "Сектор руин DC15a (Грейдич — Анкориджский мемориал)",
    "loc_00095d40": "Сектор руин DC15a (Цитадель — внешний периметр)",
    "loc_00095d43": "Сектор руин DC15b (Арлингтонское кладбище)",
    "loc_00095d3b": "Сектор руин DC16a (Фолс-Чёрч — Станция Мэриголд)",
    "loc_00095d3c": "Сектор руин DC17a (Район Мейсон — «Хьюбрис Комикс»)",
    "loc_00027a49": "Сектор руин DC18b (Фолс-Чёрч — восток)",
    "loc_00095d44": "Сектор руин DC19a (Арлингтон — завод «Мама Дольче»)",
    "loc_00095d41": "Сектор руин DC20b (Оружейные склады Александрии)",
    "loc_00095d42": "Сектор руин DC20c (Арлингтонская библиотека — окрестности)",
    "loc_00095d3e": "Сектор руин DC21a (Завод «Ред Рейсер» — Бейлиз-Кроссроудз)",
    "loc_00095d3f": "Сектор руин DC21b (Бейлиз-Кроссроудз — юг)",
    "loc_00095d48": "Сектор руин DC23a (Завод «Ядер-Кола»)",
    "loc_00095d47": "Сектор руин DC23b (Затопленное метро — Арлингтон)",
    "loc_00095d45": "Сектор руин DC25a (Южный Арлингтон)",
}

# 3. Other Locations, Items, Objects, Companions, NPCs & Creatures
EXPLICIT_NODE_LABELS_RU: dict[str, str] = {
    # 13 Non-DC Locations
    "loc_00000a74": "Мегатонна (городское пространство)",
    "loc_000035d4": "Метро: Арлингтон — Пустошь",
    "loc_000035d3": "Узловая станция метро",
    "loc_0400c2b4": "Подводная лодка SSN-37-1A",
    "loc_05009c70": "Грузовой трюм («Зета»)",
    "loc_0400494f": "Морская пещера (Пойнт-Лукаут)",
    "loc_05000f94": "Ангар корабля «Зета»",
    "loc_0500098c": "Ремонтный отсек («Зета»)",
    "loc_0500b531": "Инженерное ядро («Зета»)",
    "loc_040072da": "Каюта парохода «Гамбит Герцогини»",
    "loc_04012c3b": "Каюта парохода «Гамбит Герцогини»",
    "loc_020010e3": "Испытательный зал (Питт)",
    "loc_0006e768": "Технический отсек медико-силовой брони",
    # Items & Objects
    "itm_0006b538": "Миниган «Юджин»",
    "itm_0400d5b3": "Двустволка «Папин помощник рыбака»",
    "itm_0007dc17": "Записка «Каракули» (Убежище 106)",
    "itm_000673d5": "Разыскивается: Одинокий Путник",
    "obj_0009d41e": "Клавиша ввода кода Очистителя",
    "obj_000553ec": "Выход",
    # Companions & Named NPCs
    "chr_00027f65": "Буч Делория",
    "chr_000156f6": "Харон",
    "chr_00000a71": "Джерико",
    "chr_000156a2": "Кловер",
    "chr_0003d34e": "Фокс",
    "chr_0001cca1": "Дэниел Эджинкорт",
    "chr_0001cca3": "Алекс Даргон",
    # Generic NPCs
    "chr_000c191a": "Солдат Анклава",
    "chr_000c1919": "Солдат Анклава",
    "chr_000bfe4c": "Солдат Анклава",
    "chr_000bfe4b": "Солдат Анклава",
    "chr_000bfe4a": "Солдат Анклава",
    "chr_0002f7a0": "Работорговец",
    "chr_0200a9c8": "Раб Питта",
    "chr_0200a96d": "Раб Питта",
    "chr_02002947": "Раб Питта",
    "chr_02002946": "Раб Питта",
    "chr_0200293f": "Раб Питта",
    "chr_0300bbbb": "Житель Подземелья",
    "chr_0300bbb6": "Житель Подземелья",
    "chr_0300bbb4": "Житель Подземелья",
    "chr_0300836d": "Охранник Ривет-Сити",
    "chr_03003730": "Охранник Ривет-Сити",
    "chr_0300341b": "Охранник Ривет-Сити",
    "chr_030013ba": "Охранник Ривет-Сити",
    "chr_0500b27d": "Обитатель Пустоши",
    "chr_0500b27c": "Обитатель Пустоши",
    # Creatures & Robots
    "chr_000c18d4": "Коготь смерти",
    "chr_000a5c6c": "Робомозг",
    "chr_0005f9d1": "Робот-охранник",
    "chr_00021ebe": "Мистер Храбрец",
    "chr_00020414": "Супермутант",
    "chr_0001cf8b": "Протектрон",
    "chr_0100ad4e": "Турель «Марк I»",
    "chr_0100a4ec": "Турель «Марк II»",
    "chr_01008cb4": "Турель «Марк IV»",
    "chr_01003387": "Бронетанк «Химера»",
    "chr_020093f2": "Дикий трог",
    "chr_02002be1": "Дикий трог (тест Питта)",
    "chr_04010add": "Дикая собака",
    "chr_0401034d": "Кротокрыс",
    "chr_0401034b": "Дутень",
    "chr_0400fcad": "Болотник",
    # Developer test / voice NPCs
    "chr_0100c166": "Актёр озвучки: Гэри",
    "chr_0100c164": "Актёр озвучки №2 (Анкоридж)",
    "chr_0100c163": "Актёр озвучки №1 (Анкоридж)",
    "chr_02001961": "Тестовый персонаж (Питт)",
    "chr_02002a55": "Тестовый персонаж №2 (Питт)",
    "chr_02002a57": "Тестовый персонаж №3 (Питт)",
    "chr_020028fc": "Тестовый персонаж Питта (Азиат, М)",
    "chr_020028fb": "Тестовый персонаж Питта (Латиноамериканец, М)",
    "chr_020028fa": "Тестовый персонаж Питта (Афроамериканец, М)",
    "chr_020028f9": "Тестовый персонаж Питта (Европеоид, М)",
    "chr_020028f8": "Тестовый персонаж Питта (Европеоид, Ж)",
    "chr_0300b958": "Звуковой диктор (Broken Steel)",
    "chr_04010a4b": "Служебный голос диалога",
    "chr_04003f2c": "Служебный голос диалога",
    "chr_0500a672": "Тестовый персонаж («Зета», ребёнок)",
    "chr_050079a0": "Тестовый персонаж («Зета»)",
}

DEV_AND_TEST_EXTENDED_IDS: set[str] = {
    "chr_0100c166",
    "chr_0100c164",
    "chr_0100c163",
    "chr_02001961",
    "chr_02002a55",
    "chr_02002a57",
    "chr_020028fc",
    "chr_020028fb",
    "chr_020028fa",
    "chr_020028f9",
    "chr_020028f8",
    "chr_02002be1",
    "chr_0300b958",
    "chr_04010a4b",
    "chr_04003f2c",
    "chr_0500a672",
    "chr_050079a0",
}

RACE_PRESET_MAP: dict[str, str] = {
    "AfricanAmerican": "Афроамериканец",
    "Asian": "Азиат",
    "Caucasian": "Европеоид",
    "Hispanic": "Латиноамериканец",
}

RACE_PRESET_RE = re.compile(r"^race(AfricanAmerican|Asian|Caucasian|Hispanic)([FM])(\d{2})$")

WORLDSPACE_TRANSLATIONS: dict[str, str] = {
    "Megaton": "Мегатонна",
    "Chevy Chase": "Чеви-Чейз",
    "Seward Square": "Сьюард-сквер",
    "L'Enfant Plaza": "Ланфан-плаза",
    "Pennsylvania Avenue": "Пенсильвания-авеню",
    "Takoma Park": "Такома-парк",
    "Dupont Circle": "Дюпон-сёркл",
    "DC15a": "Сектор руин DC15a (Грейдич — Анкориджский мемориал)",
    "DC17a": "Сектор руин DC17a (Район Мейсон — «Хьюбрис Комикс»)",
}

SOURCE_TAG_MAP: dict[str, str] = {
    "esm+wiki": "Файлы игры + Fallout Wiki",
    "Fallout 3 ESM + Wiki": "Файлы игры + Fallout Wiki",
    "Fallout3.esm + Fallout Wiki (RU)": "Файлы игры + Fallout Wiki",
    "ESM+Wiki": "Файлы игры + Fallout Wiki",
    "esm": "Файлы игры (.ESM)",
    "Fallout 3 ESM": "Файлы игры (.ESM)",
    "Fallout3.esm": "Файлы игры (.ESM)",
    "ESM": "Файлы игры (.ESM)",
    "esm+curated": "Файлы игры + Энциклопедия",
    "esm+wiki+curated": "Файлы игры + Энциклопедия",
    "ESM+Прохождение": "Файлы игры + Энциклопедия",
    "ESM+Прохождение+Wiki": "Файлы игры + Энциклопедия",
    "ESM+Справка": "Файлы игры + Энциклопедия",
    "ESM+Справка+Wiki": "Файлы игры + Энциклопедия",
    "ESM+События": "Файлы игры + Энциклопедия",
    "ESM+Встречи": "Файлы игры + Энциклопедия",
}


def parse_race_preset_label(raw_label: str) -> str | None:
    m = RACE_PRESET_RE.match(raw_label)
    if not m:
        return None
    race_en, gender_en, num = m.groups()
    race_ru = RACE_PRESET_MAP[race_en]
    gender_ru = "Ж" if gender_en == "F" else "М"
    return f"Пресет внешности: {race_ru} ({gender_ru} №{num})"


def update_summary_for_renamed_node(nid: str, new_label: str, old_label: str, summary: str) -> str:
    if not summary:
        return summary

    # 1. DC* sector markers
    if nid in DC_SECTOR_LABELS_RU:
        summary = re.sub(r"^DC\d+[a-z]?\s+—\s+", f"{new_label} — ", summary)
        return summary

    # 2. Race presets
    if RACE_PRESET_RE.match(old_label):
        summary = re.sub(r"^(?:Шаблон внешности \([^\)]+\)|Пресет внешности: [^—]+)\s+—\s+", f"{new_label} — ", summary)
        return summary

    # 3. Specific locations
    if nid == "loc_00000a74":
        return re.sub(
            r"^Мегатонна \(в файлах локализации мира отмечена как Megaton\)\s+—\s+",
            "Мегатонна (городское пространство, в файлах мира отмечена как Megaton) — ",
            summary,
        )
    if nid == "loc_000035d4":
        return re.sub(
            r"^Тоннель метро «Арлингтон — Пустошь»\s+",
            "Метро: Арлингтон — Пустошь ",
            summary,
        )
    if nid == "loc_0006e768":
        return re.sub(
            r"^MS14 Armor Voice Cell\s+—\s+",
            "Технический отсек медико-силовой брони (MS14 Armor Voice Cell) — ",
            summary,
        )
    if nid == "loc_000035d3":
        return re.sub(
            r"^Пересадочный узел метро \(Metro Junction\)\s+—\s+",
            "Узловая станция метро (Metro Junction) — ",
            summary,
        )
    if nid in (
        "loc_020010e3",
        "loc_040072da",
        "loc_04012c3b",
        "loc_0400494f",
        "loc_0500098c",
        "loc_0500b531",
        "loc_05009c70",
        "loc_05000f94",
    ):
        if summary.startswith(f"{new_label} — "):
            return summary
        return f"{new_label} — " + summary[0].lower() + summary[1:]
    if nid == "loc_0400c2b4":
        return re.sub(r"^(?:Подводная лодка )?SSN-37-1A\s+—\s+", "Подводная лодка SSN-37-1A — ", summary)

    # 4. Items & Objects
    if nid == "itm_0006b538":
        return re.sub(r"^«Юджин»\s+", "Миниган «Юджин» ", summary)
    if nid == "itm_0007dc17":
        return re.sub(r"^Scribbles\s+—\s+", "Записка «Каракули» (Убежище 106) — ", summary)
    if nid == "itm_0400d5b3":
        return re.sub(
            r"^Pa’s Fishing Aid \(Папино рыболовное ружьё\)\s+—\s+",
            "Двустволка «Папин помощник рыбака» (англ. Pa’s Fishing Aid) — ",
            summary,
        )
    if nid == "obj_0009d41e":
        return re.sub(
            r"^«Enter»\s+—\s+",
            "Клавиша ввода кода Очистителя (англ. Enter) — ",
            summary,
        )

    # 5. Characters, Companions, Creatures, Test/Voice NPCs
    if nid == "chr_00027f65":
        return summary.replace("Буч ДеЛориа", "Буч Делория")
    if nid == "chr_0001cca1":
        return re.sub(
            r"^Этот довольно грубый и сдержанный молодой инженер\s+",
            "Дэниел Эджинкорт — довольно грубый и сдержанный молодой инженер, который ",
            summary,
        )
    if nid == "chr_0002f7a0":
        if not summary.startswith("Работорговец"):
            return "Работорговец — охотник за живым товаром из Парадиз-Фоллз. " + summary
    if nid in ("chr_0200a9c8", "chr_0200a96d", "chr_02002947", "chr_02002946", "chr_0200293f"):
        if not summary.startswith("Раб Питта"):
            return "Раб Питта — подневольный рабочий сталелитейных руин Питтсбурга. " + summary
    if nid in ("chr_0300bbbb", "chr_0300bbb6", "chr_0300bbb4"):
        if not summary.startswith("Житель Подземелья"):
            return "Житель Подземелья — обитатель общины гулей в Историческом музее. " + summary
    if nid in ("chr_0300836d", "chr_03003730", "chr_0300341b", "chr_030013ba"):
        return re.sub(
            r"^Бойцы городской охраны, патрулирующие Ривет-Сити\.",
            "Охранник Ривет-Сити — боец городской службы безопасности, патрулирующий палубы Ривет-Сити.",
            summary,
        )
    if nid in ("chr_0500b27d", "chr_0500b27c"):
        if not summary.startswith("Обитатель Пустоши"):
            return "Обитатель Пустоши — независимый выживший со Столичной Пустоши. " + summary
    if nid == "chr_01003387":
        return re.sub(r"^Танк «Химера»\s+—\s+", "Бронетанк «Химера» — ", summary)
    if nid == "chr_020093f2":
        return re.sub(r"^Уличный трог\s+—\s+", "Дикий трог — ", summary)
    if nid == "chr_02002be1":
        return re.sub(r"^Тестовый уличный трог\s+—\s+", "Дикий трог (тест Питта) — ", summary)
    if nid == "chr_04010add":
        return re.sub(r"^Одичавшая собака\s+—\s+", "Дикая собака — ", summary)
    if nid in DEV_AND_TEST_EXTENDED_IDS:
        return re.sub(r"^[^—]+—\s+", f"{new_label} — ", summary, count=1)

    # 6. Quests that previously had English labels
    if nid in (
        "qst_0009426d",
        "qst_000371d2",
        "qst_000943ec",
        "qst_000943ed",
        "qst_000943ee",
        "qst_0002fa33",
        "qst_000943eb",
        "qst_00062736",
        "qst_000173d8",
        "qst_000173d1",
        "qst_000173d9",
        "qst_0006136d",
        "qst_010034da",
        "qst_05005c70",
    ):
        if nid == "qst_05005c70":
            return re.sub(
                r"^«Безбилетники» \(Steerage Rats\)",
                f"«{new_label}» (Steerage Rats)",
                summary,
            )
        if not summary.startswith(f"«{new_label}»"):
            return f"«{new_label}» — " + summary[0].lower() + summary[1:]

    return summary


def clean_role_text(role: str) -> str:
    if not role:
        return role
    role = re.sub(
        r'Автоматическая охранная турель ["«]марк ([ivx]+)["»] защиты',
        lambda m: f"Автоматическая охранная турель «Марк {m.group(1).upper()}»",
        role,
        flags=re.I,
    )
    role = role.replace("(DC15a)", "(Сектор руин DC15a)")
    role = role.replace("(DC17a)", "(Сектор руин DC17a)")
    return role


def main() -> None:
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    details = json.loads(DETAILS_PATH.read_text(encoding="utf-8"))

    # Optional cross-check with walkthroughs.json for quest titles
    wt_titles: dict[str, str] = {}
    if WALKTHROUGHS_PATH.exists():
        wt_data = json.loads(WALKTHROUGHS_PATH.read_text(encoding="utf-8"))
        if isinstance(wt_data, list):
            for item in wt_data:
                qid = item.get("id")
                title = item.get("title", "")
                if qid and HAS_CYRILLIC.search(title) and not title.isupper():
                    wt_titles[qid] = title

    translated_nodes_count = 0
    quest_title_normalized_count = 0
    dc_demoted_from_atlas = 0
    presets_and_test_extended = 0
    renamed_map: dict[str, tuple[str, str]] = {}  # nid -> (old_label, new_label)

    for node in graph["nodes"]:
        nid = node["id"]
        old_label = node.get("label", "")
        if not node.get("labelEn"):
            node["labelEn"] = old_label
        label_en = node["labelEn"]

        new_label = old_label

        # 1. Quests
        if node["type"] == "quest":
            if nid in wt_titles:
                new_label = wt_titles[nid]
            elif nid in QUEST_LABELS_RU:
                new_label = QUEST_LABELS_RU[nid]

            if nid in ENGLISH_QUEST_IDS:
                translated_nodes_count += 1
            else:
                quest_title_normalized_count += 1

        # 2. DC* sector markers
        elif nid in DC_SECTOR_LABELS_RU:
            new_label = DC_SECTOR_LABELS_RU[nid]
            translated_nodes_count += 1
            if node.get("tier") == "atlas":
                node["tier"] = "core"
                dc_demoted_from_atlas += 1

        # 3. Character generation presets (raceAfricanAmerican*, raceAsian*, raceCaucasian*, raceHispanic*)
        elif RACE_PRESET_RE.match(label_en):
            parsed = parse_race_preset_label(label_en)
            if parsed:
                new_label = parsed
                translated_nodes_count += 1
            if node.get("tier") != "extended":
                node["tier"] = "extended"
            presets_and_test_extended += 1

        # 4. Explicit translations for remaining nodes
        elif nid in EXPLICIT_NODE_LABELS_RU:
            new_label = EXPLICIT_NODE_LABELS_RU[nid]
            if not HAS_CYRILLIC.search(label_en):
                translated_nodes_count += 1

        if nid in DEV_AND_TEST_EXTENDED_IDS:
            node["tier"] = "extended"
            presets_and_test_extended += 1

        if new_label != old_label or nid in DC_SECTOR_LABELS_RU or nid in EXPLICIT_NODE_LABELS_RU or nid in QUEST_LABELS_RU or RACE_PRESET_RE.match(label_en):
            node["label"] = new_label
            renamed_map[nid] = (label_en, new_label)

    # Update graph meta counts (atlasNodes, coreNodes)
    atlas_count = sum(1 for n in graph["nodes"] if n.get("tier") == "atlas")
    core_only_count = sum(1 for n in graph["nodes"] if n.get("tier") == "core")
    graph["meta"]["atlasNodes"] = atlas_count
    graph["meta"]["coreNodes"] = atlas_count + core_only_count

    node_label_by_id = {n["id"]: n["label"] for n in graph["nodes"]}

    # Update details.json
    source_tags_localized = 0
    inventory_labels_updated = 0
    summaries_updated = 0
    worldspaces_updated = 0

    for nid, entry in details.items():
        # A. Localize sourceTag
        raw_tag = entry.get("sourceTag")
        if raw_tag in SOURCE_TAG_MAP:
            entry["sourceTag"] = SOURCE_TAG_MAP[raw_tag]
            source_tags_localized += 1

        # B. Localize worldspace if needed
        ws = entry.get("worldspace")
        if ws in WORLDSPACE_TRANSLATIONS:
            entry["worldspace"] = WORLDSPACE_TRANSLATIONS[ws]
            worldspaces_updated += 1

        # C. Clean role string
        if "role" in entry and entry["role"]:
            entry["role"] = clean_role_text(entry["role"])

        # D. Update inventory[i].label for any translated item IDs
        for inv_item in entry.get("inventory") or []:
            iid = inv_item.get("id")
            if iid and iid in node_label_by_id:
                target_lbl = node_label_by_id[iid]
                if inv_item.get("label") != target_lbl:
                    inv_item["label"] = target_lbl
                    inventory_labels_updated += 1

        # E. Clean unlocks with raw '(Мегатонна (Megaton))'
        if entry.get("unlocks"):
            entry["unlocks"] = [
                u.replace("(Мегатонна (Megaton))", "(Мегатонна)") for u in entry["unlocks"]
            ]

        # F. Ensure summary starts naturally with the Russian name for renamed nodes
        if nid in renamed_map:
            old_lbl, new_lbl = renamed_map[nid]
            old_sum = entry.get("summary", "")
            new_sum = update_summary_for_renamed_node(nid, new_lbl, old_lbl, old_sum)
            if new_sum != old_sum:
                entry["summary"] = new_sum
                summaries_updated += 1

        # Also clean raw turreted/Megaton mentions in summaries
        if "summary" in entry and entry["summary"]:
            s_clean = entry["summary"]
            s_clean = re.sub(
                r'автоматическая охранная турель «марк ([ivx]+)» защиты',
                lambda m: f"автоматическая охранная турель «Марк {m.group(1).upper()}»",
                s_clean,
                flags=re.I,
            )
            s_clean = s_clean.replace("в локации Мегатонна (Megaton)", "в локации Мегатонна")
            if s_clean != entry["summary"]:
                entry["summary"] = s_clean

    # Verify 0 nodes lack Cyrillic in graph.json
    remaining_no_cyrillic = [
        (n["id"], n["label"]) for n in graph["nodes"] if not HAS_CYRILLIC.search(n.get("label", ""))
    ]
    if remaining_no_cyrillic:
        raise RuntimeError(
            f"Still found {len(remaining_no_cyrillic)} nodes without Cyrillic: {remaining_no_cyrillic[:10]}"
        )

    GRAPH_PATH.write_text(
        json.dumps(graph, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    DETAILS_PATH.write_text(
        json.dumps(details, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(f"Total nodes verified: {len(graph['nodes'])}")
    print(f"Nodes translated from non-Cyrillic to Russian: {translated_nodes_count}")
    print(f"ALL-CAPS Russian quest titles normalized: {quest_title_normalized_count}")
    print(f"Nodes lacking Cyrillic in label after run: {len(remaining_no_cyrillic)}")
    print(f"DC* sub-markers moved from atlas -> core: {dc_demoted_from_atlas}")
    print(f"Character presets & dev/test NPCs ensured in tier='extended': {presets_and_test_extended}")
    print(f"Updated meta.atlasNodes={graph['meta']['atlasNodes']}, meta.coreNodes={graph['meta']['coreNodes']}")
    print(f"details.json sourceTag badges localized: {source_tags_localized}")
    print(f"details.json inventory labels synchronized: {inventory_labels_updated}")
    print(f"details.json summaries updated for renamed nodes: {summaries_updated}")
    print(f"details.json worldspaces localized: {worldspaces_updated}")


if __name__ == "__main__":
    main()
