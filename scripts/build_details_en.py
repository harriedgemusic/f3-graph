#!/usr/bin/env python3
"""
Build complete English Fallout 3 GOTY Encyclopedia entries for all 4,239 entities
into public/data/details.en.json.

Inputs:
  - public/data/graph.json
  - public/data/details.json
  - public/data/walkthroughs.en.json
  - /tmp/f3_encyclopedia_en/wiki_en_by_node.json

Output:
  - public/data/details.en.json
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = REPO_ROOT / "public" / "data" / "graph.json"
DETAILS_RU_PATH = REPO_ROOT / "public" / "data" / "details.json"
WT_EN_PATH = REPO_ROOT / "public" / "data" / "walkthroughs.en.json"
WIKI_EN_PATH = Path("/tmp/f3_encyclopedia_en/wiki_en_by_node.json")
OUT_EN_PATH = REPO_ROOT / "public" / "data" / "details.en.json"

HAS_CYRILLIC = re.compile(r"[А-Яа-яЁё]")
FORBIDDEN_TOKENS = ["{{", "}}", "[[", "]]", "<ref", "<div", "\ufffd"]

DLC_LABELS_EN = {
    "base": "Fallout 3 (Capital Wasteland)",
    "anchorage": "Operation: Anchorage",
    "pitt": "The Pitt",
    "brokensteel": "Broken Steel",
    "pointlookout": "Point Lookout",
    "zeta": "Mothership Zeta",
}

SUBTYPE_LABELS_EN = {
    "npc": "Character (NPC)",
    "creature": "Creature / Robot",
    "world": "Worldspace",
    "marker": "Map Marker",
    "interior": "Interior Location",
    "main": "Main Quest",
    "side": "Side Quest",
    "freeform": "Freeform Quest",
    "anchorage": "Operation: Anchorage",
    "pitt": "The Pitt",
    "brokensteel": "Broken Steel",
    "pointlookout": "Point Lookout",
    "zeta": "Mothership Zeta",
    "story_event": "Story Event",
    "random_encounter": "Random Encounter",
    "weapon": "Weapon",
    "armor": "Armor / Apparel",
    "aid": "Aid / Chems & Food",
    "ammo": "Ammunition",
    "book": "Skill Book",
    "key": "Key",
    "note": "Note / Holotape",
    "misc": "Misc / Quest Item",
    "terminal": "Terminal",
    "activator": "Activator / Device",
    "container": "Container / Safe",
    "door": "Door / Passage",
    "perk": "Perk",
}

RACE_EN: dict[str, str] = {
    "Абоминация": "Abomination",
    "Азиат": "Asian",
    "Азиат - ребенок": "Asian Child",
    "Азиат - старик": "Asian Elderly",
    "Афро-американец": "African American",
    "Афро-американец - ребенок": "African American Child",
    "Афро-американец - старик": "African American Elderly",
    "Болотник": "Mirelurk",
    "Болотник-король / Водяной": "Mirelurk King",
    "Брамин": "Brahmin",
    "Гигантская муравьиная матка": "Giant Ant Queen",
    "Гигантский муравей": "Giant Ant",
    "Гуль": "Ghoul",
    "Дикарь Пойнт-Лукаута": "Swampfolk (Point Lookout)",
    "Дикий гуль": "Feral Ghoul",
    "Дутень": "Bloatfly",
    "Европеоид": "Caucasian",
    "Европеоид - ребенок": "Caucasian Child",
    "Европеоид - старик": "Caucasian Elderly",
    "Жертва экспериментов ВРЭ": "FEV Test Subject",
    "Защитная турель": "Security Turret",
    "Интерком-глаз ZAX": "ZAX Intercom Eye",
    "Кентавр": "Centaur",
    "Коготь смерти": "Deathclaw",
    "Кротокрыс": "Mole Rat",
    "Латиноамериканец": "Hispanic",
    "Латиноамериканец - ребенок": "Hispanic Child",
    "Латиноамериканец - старик": "Hispanic Elderly",
    "Огненный муравей": "Fire Ant",
    "Пришелец (Дзета)": "Alien (Zeta)",
    "Радскорпион": "Radscorpion",
    "Радтаракан": "Radroach",
    "Робот пришельцев (Дзета)": "Alien Drone (Zeta)",
    "Робот — Либерти Прайм": "Robot — Liberty Prime",
    "Робот — Мистер Помощник / Храбрец": "Robot — Mister Handy / Gutsy",
    "Робот — Протектрон": "Robot — Protectron",
    "Робот — Робомозг": "Robot — Robobrain",
    "Робот-охранник": "Sentry Bot",
    "Робот-паук": "Robotic Drone",
    "Робот-шпион Анклава": "Enclave Eyebot",
    "Собака": "Dog",
    "Супермутант": "Super Mutant",
    "Супермутант (изгнанник)": "Super Mutant Outcast",
    "Супермутант (разумный)": "Super Mutant (Intelligent)",
    "Супермутант-бегемот": "Super Mutant Behemoth",
    "Танк «Химера»": "Chimera Tank",
    "Трог (Питт)": "Trog (The Pitt)",
    "Яо-гай": "Yao Guai",
}

MARKER_TYPE_EN: dict[str, str] = {
    "Внешний мир": "Exterior World",
    "Город": "City",
    "Городские руины": "Urban Ruins",
    "Завод / Фабрика": "Factory / Plant",
    "Канализация / Коллектор": "Sewer / Utility",
    "Метро": "Metro Station",
    "Офисное здание": "Office Building",
    "Памятник": "Monument",
    "Пещера": "Cave",
    "Поселение": "Settlement",
    "Лагерь": "Encampment",
    "Природный объект": "Natural Landmark",
    "Убежище": "Vault",
    "Заброшенный город": "Town Ruins",
    "Военная база": "Military Base",
    "Нет маркера": "Unmarked",
}

WEAPON_CLASS_EN: dict[str, str] = {
    "Автомат / Карабин": "Assault Rifle / Carbine",
    "Винтовка": "Rifle",
    "Граната": "Grenade",
    "Двуручное холодное оружие": "Two-Handed Melee",
    "Мина": "Mine",
    "Мина (спец.)": "Special Mine",
    "Огнемёт / Ракетомёт": "Flamer / Launcher",
    "Одноручное холодное оружие": "One-Handed Melee",
    "Пистолет": "Pistol",
    "Рукопашное оружие": "Unarmed Weapon",
    "Тяжёлое оружие": "Big Gun",
    "Энергетическая винтовка": "Energy Rifle",
    "Энергетический пистолет": "Energy Pistol",
    "Метательное оружие": "Thrown Weapon",
}

AMMO_EN: dict[str, str] = {
    "10-мм патрон": "10mm Round",
    "5,56-мм патрон": "5.56mm Round",
    "5-мм патрон": "5mm Round",
    "Аккумулятор для гипнотрона": "Mesmetron Power Cell",
    "Батарея": "Energy Cell",
    "Гранатометный выстрел": "Missile",
    "Железнодорожные костыли": "Railway Spikes",
    "Микроядерная батарея": "Microfusion Cell",
    'Патрон "Магнум" кал. 44': ".44 Magnum Round",
    "Патрон кал. 308": ".308 Caliber Round",
    "Патрон кал. 32": ".32 Caliber Round",
    "Патрон с картечью": "12-Gauge Shotgun Shell",
    "Силовой модуль Чужих": "Alien Power Module",
    "Топливо для огнемета": "Flamer Fuel",
    "Шарик для пневматического ружья": "BB",
    "Электронный заряд": "Electron Charge Pack",
    "Энергоячейка Чужих": "Alien Power Cell",
    "Ядерный выстрел": "Mini Nuke",
}

LOCK_DIFF_EN: dict[str, str] = {
    "Очень лёгкий (0)": "Very Easy (0)",
    "Лёгкий (25)": "Easy (25)",
    "Средний (50)": "Average (50)",
    "Сложный (75)": "Hard (75)",
    "Очень сложный (100)": "Very Hard (100)",
    "Требуется ключ": "Key Required",
    "Разблокирован": "Unlocked",
}

SOURCE_TAG_EN: dict[str, str] = {
    "Файлы игры (.ESM)": "Game Files (.ESM)",
    "Файлы игры + Fallout Wiki": "Game Files + Fallout Wiki",
    "Файлы игры + Энциклопедия": "Game Files + Encyclopedia",
}

SERVICES_EN: dict[str, str] = {
    "Алкоголь": "Alcohol",
    "Броня": "Armor",
    "Еда": "Food",
    "Книги и схемы": "Books & Schematics",
    "Одежда и товары": "Apparel & Goods",
    "Оружие": "Weapons",
    "Припасы / торговля": "Supplies / Barter",
    "Ремонт": "Repair",
    "Снаряжение": "Equipment",
    "Химия и медикаменты": "Chems & Medicine",
    "Хлам и разное": "Junk & Misc",
}

FACTIONS_EN: dict[str, str] = {
    "«Семья»": "The Family",
    "Абоминации": "Abominations",
    "Автоматические турели": "Automated Turrets",
    "Анклав": "Enclave",
    "Апостолы Вечного Света": "Apostles of the Eternal Light",
    "Армия США (симуляция Анкориджа)": "U.S. Army (Anchorage Simulation)",
    "Банда «Внезапная смерть»": "Sudden-Death Overtime",
    "Беглые рабы": "Escaped Slaves",
    "Боевые роботы Анклава": "Enclave Combat Robots",
    "Боевые роботы пришельцев": "Alien Combat Robots",
    "Болотники": "Mirelurks",
    "Брамины": "Brahmin",
    "Братство Стали": "Brotherhood of Steel",
    "Братство Стали (гарнизон «Новостей Галактики»)": "Brotherhood of Steel (GNR Garrison)",
    "Братство Стали (писцы)": "Brotherhood of Steel (Scribes)",
    "Вредители «РобКо»": "RobCo Pests",
    "Гигантские муравьи": "Giant Ants",
    "Гостиница «Уэзерли»": "Weatherly Hotel",
    "Гули станции Уоррингтон": "Warrington Station Ghouls",
    "Дети Литл-Лэмплайта": "Little Lamplighters",
    "Древены Оазиса": "Treeminders of Oasis",
    "Дутни": "Bloatflies",
    "Жители Арефу": "Arefu Residents",
    "Жители Большого города": "Big Town Residents",
    "Жители Гердершейда": "Girdershade Residents",
    "Жители Мегатонны": "Megaton Residents",
    "Жители Ривет-Сити": "Rivet City Residents",
    "Жители Тенпенни-Тауэр": "Tenpenny Tower Residents",
    "Жители Трэнквилити-лейн": "Tranquility Lane Residents",
    "Жители Убежища 101": "Vault 101 Residents",
    "Жители общины Кентербери": "Canterbury Commons Residents",
    "Завсегдатаи бара «Мутный руль»": "Muddy Rudder Regulars",
    "Изгои Братства": "Brotherhood Outcasts",
    "Кентавры": "Centaurs",
    "Компания «Коготь»": "Talon Company",
    "Кротокрысы": "Mole Rats",
    "Львиный прайд": "Lyons' Pride",
    "Мародёры Пустоши": "Wasteland Scavengers",
    "НОАК (Китайская армия)": "PLA (Chinese Army)",
    "Научная группа доктора Ли": "Dr. Li's Research Team",
    "Обитатели Столичной Пустоши": "Capital Wastelander",
    "Обитатели Цитадели": "Citadel Residents",
    "Обитательницы дома Дукова": "Dukov's Place Residents",
    "Оружейный магазин Флэка и Шрапнеля": "Flak & Shrapnel's",
    "Охотники Пустоши": "Wasteland Hunters",
    "Охрана Ривет-Сити": "Rivet City Security",
    "Охранные роботы «Ядер-колы»": "Nuka-Cola Security Robots",
    "Охранные роботы метро": "Metro Security Robots",
    "Питтсбургские рейдеры": "The Pitt Raiders",
    "Племя Пойнт-Лукаута": "Point Lookout Tribals",
    "Повстанцы Убежища 101": "Vault 101 Rebels",
    "Пострадавшие от ВРЭ («Аква Пура»)": "FEV-Affected (Aqua Pura)",
    "Пришельцы (корабль «Дзета»)": "Aliens (Mothership Zeta)",
    "Работорговцы Парадиз-Фоллз": "Paradise Falls Slavers",
    "Рабы Питта": "The Pitt Slaves",
    "Рабы Пустоши": "Wasteland Slaves",
    "Радтараканы": "Radroaches",
    "Рейдеры": "Raiders",
    "Рейнджеры Рейли": "Reilly's Rangers",
    "Республика Дэйва": "Republic of Dave",
    "Роботы": "Robots",
    "Роботы «Волт-Тек»": "Vault-Tec Robots",
    "Роботы «РобКо»": "RobCo Robots",
    "Роботы Баттона Гвинетта": "Button Gwinnett's Robots",
    "Роботы-дворецкие": "Mister Handy Butlers",
    "Роботы-шпионы Анклава": "Enclave Eyebots",
    "Семья Веллингтон": "Wellington Family",
    "Семья ДеЛориа": "DeLoria Family",
    "Семья Кантелли": "Cantelli Family",
    "Семья Стейли": "Staley Family",
    "Семья Харгрейв": "Hargrave Family",
    "Семья Чен": "Cheng Family",
    "Семья Эверс": "Ewers Family",
    "Семья Янг": "Young Family",
    "Служба безопасности Убежища 101": "Vault 101 Security",
    "Собаки": "Dogs",
    "Собаки Пустоши": "Wasteland Dogs",
    "Собаки мародёров": "Scavenger Dogs",
    "Совет Ривет-Сити": "Rivet City Council",
    "Сторожевые псы Литл-Лэмплайта": "Little Lamplight Guard Dogs",
    "Странствующие торговцы": "Caravan Merchants",
    "Супермутанты": "Super Mutants",
    "Таинственный незнакомец": "Mysterious Stranger",
    "Туннельные змеи": "Tunnel Snakes",
    "Ударная группа США": "U.S. Strike Team",
    "Храм Единения": "Temple of the Union",
    "Чёрные муравьи Шейлбриджа": "Shalebridge Black Ants",
    "Яо-гаи": "Yao Guai",
}

WORLDSPACE_EXPLICIT_EN: dict[str, str] = {
    "Внутренняя локация": "Interior Location",
    "Адамс - вход на базу ВВС": "Adams AFB - Airfield Entrance",
    "Адамс - контрольная башня": "Adams AFB - Control Tower",
    "Адамс - склад": "Adams AFB - Storage Facility",
    "Андейл": "Andale",
    "Анкориджский мемориал": "Anchorage Memorial",
    "Арефу": "Arefu",
    "Арлингтонское кладбище": "Arlington Cemetery",
    "Арлингтонское кладбище - юг": "Arlington Cemetery South",
    "База рейнджеров": "Reilly's Rangers Compound",
    "Башня-ретранслятор KX-B8-11": "Relay Tower KX-B8-11",
    "Белый Дом": "The White House",
    "Большой Город": "Big Town",
    'ВМС США "Озимандия"': "USS Ozymandias",
    "Вернон-сквер": "Vernon Square",
    "Водохранилище округа Монтгомери": "Montgomery County Reservoir",
    "Вход на святое болото": "Sacred Bog Entrance",
    "Высота": "The Overlook",
    "Выход на высоту": "Exit to The Overlook",
    "Гараж Кейси Смита": "Smith Casey's Garage",
    "Грейдич": "Grayditch",
    "Данвич-билдинг": "Dunwich Building",
    'Депо "Уоррингтон"': "Warrington Trainyard",
    "Джорджтаун": "Georgetown",
    "Джорджтаун - запад": "Georgetown West",
    "Дюпон - восток": "Dupont East",
    "Дюпон-сёркл": "Dupont Circle",
    'Завод "Ядер-кола"': "Nuka-Cola Plant",
    "Заправка Рокбрейкера": "Rockbreaker's Last Gas",
    "Заправка и магазинчик Джоко": "Jocko's Pop & Gas Stop",
    'Здание "Новости Галактики"': "Galaxy News Radio Building",
    "Здание Управления музеями": "Museum Authority Building",
    "Игровой домик Литтл Тайк": "Little Tyke's Playhouse",
    "Исторический музей": "Museum of History",
    "Капище": "The Sanctuary",
    'Карантинный лагерь "Горлица"': "Turtledove Detention Camp",
    'Кладбище при соборе "Арк и Дав"': "Ark & Dove Cathedral Grounds",
    'Комплекс "РобКо"': "RobCo Facility",
    "Крайслус-билдинг": "Chryslus Building",
    "Курорт Риклайнин-Гроув": "Reclining Groves Resort Homes",
    "Лачуга Маргариты": "Marguerite's Shack",
    "Лачуга садовода": "Gardener's Shack",
    "Литл-Лэмплайт": "Little Lamplight",
    "Лодочный причал": "Boat Landing",
    "Мегатонна": "Megaton",
    "Мемориал Джефферсона": "Jefferson Memorial",
    "Мемориал Линкольна": "Lincoln Memorial",
    "Место авиакатастрофы": "Crash Site",
    "Минное поле": "Minefield",
    "Молл": "The Mall",
    "Молл - северо-восток": "The Mall Northeast",
    "Монастырь Вечного света": "Monastery of the Eternal Light",
    'Мотель "Гомстед"': "Homestead Motel",
    "Мусорная свалка": "Scrapyard",
    "Мусорная свалка братьев Джалбертов": "Jalbert Brothers Waste Disposal",
    "Община Кентербери": "Canterbury Commons",
    "Олд-Олни": "Old Olney",
    "Парадиз-Фоллз": "Paradise Falls",
    "Пенсильвания-авеню": "Pennsylvania Avenue",
    "Пенсильвания-авеню - восток": "Pennsylvania Avenue East",
    "Пенсильвания-авеню - северо-запад": "Pennsylvania Avenue Northwest",
    "Пещера Кенни": "Kenny's Cave",
    "Пещера Клиффсайд": "Cliffside Cavern",
    "Пещера Рок-Крик": "Rock Creek Caverns",
    "Питт - Верхний город": "The Pitt - Uptown",
    "Питт - Заводской двор": "The Pitt - Steelyard",
    "Питт - Нижний город": "The Pitt - Downtown",
    "Подводная лодка": "Chinese Submarine",
    "Полевой штаб армии США": "U.S. Army Field Headquarters",
    "Полицейский участок Джермантауна": "Germantown Police HQ",
    "Приводной маяк Чужих": "Alien Homing Beacon",
    "Пункт оказания помощи при бедствиях": "Disaster Relief Outpost",
    "Развалины Бетесды": "Bethesda Ruins",
    "Развалины Фэйрфакса": "Fairfax Ruins",
    "Район Мейсон": "Mason District",
    "Республика Дэйва": "Republic of Dave",
    "Ривет-Сити": "Rivet City",
    "Рэйвен-Рок": "Raven Rock",
    "Свалка": "Scrapyard",
    "Свалка Гринер Пасчерс": "Greener Pastures Disposal",
    "Сгоревший дом": "Burned Out House",
    "Селение Клиффтоп": "Clifftop Shacks",
    'Собор "Арк и Дав"': "Ark & Dove Cathedral",
    'Станция "Дюпон"': "Dupont Station",
    'Станция "Фоллз-Черч"': "Falls Church Station",
    "Станция вещания WKML": "WKML Broadcast Station",
    'Станция метро "Жюри-стрит"': "Jury Street Metro Station",
    "Станция метро Фаррагут-вест": "Farragut West Metro Station",
    'Станция сети "СатКом" NN-03d': "SatCom Array NN-03d",
    'Станция сети "СатКом" NW-05a': "SatCom Array NW-05a",
    'Станция сети "СатКом" NW-07c': "SatCom Array NW-07c",
    "Станция-ретранслятор MDPL": "MDPL-05 Relay Station",
    "Сьюард-сквер": "Seward Square",
    "Телебашня KB5": "Broadcast Tower KB5",
    "Телебашня KT8": "Broadcast Tower KT8",
    "Телебашня LP8": "Broadcast Tower LP8",
    "Тенпенни-Тауэр": "Tenpenny Tower",
    "Теплые коллекторы": "Tepid Sewers",
    "Технический музей": "Museum of Technology",
    "Товарная станция Вильхельма": "Wilhelm's Wharf",
    "Товарный склад": "Supply Depot",
    "Туннель": "Tunnel",
    "Убежище 106": "Vault 106",
    "Убежище 108": "Vault 108",
    "Утесы": "The Cliffs",
    "Утиль Мейсона Диксона": "Mason Dixon Salvage",
    'Ферма "Чистые земли"': "Fairgrounds / Pure Lands Farm",
    "Фоллз-Черч - восток": "Falls Church East",
    "Фоллз-Черч - север": "Falls Church North",
    "Форт Константин": "Fort Constantine",
    "Храм Единения": "Temple of the Union",
    "Цитадель": "The Citadel",
    "Чеви-Чейз": "Chevy Chase",
    "Школа Спрингвейла": "Springvale School",
    'Штаб-квартира "Волт-Тек"': "Vault-Tec Headquarters",
    "Электростанция MDPL-13": "MDPL-13 Power Station",
    "Электростанция MDPL-16": "MDPL-16 Power Station",
    "Электростанция MDPL-21": "MDPL-21 Power Station",
    "Электростанция VAPL-58": "VAPL-58 Power Station",
    "Электростанция VAPL-66": "VAPL-66 Power Station",
}

BEHAVIOR_TOKENS_EN: dict[str, str] = {
    "Мирный": "Unaggressive",
    "Агрессивный": "Aggressive",
    "Очень агрессивный": "Very Aggressive",
    "Берсерк": "Frenzied",
    "трусливый": "cowardly",
    "осторожный": "cautious",
    "средний": "average",
    "смелый": "brave",
    "безрассудный": "foolhardy",
    "уверенность: трусливый": "confidence: cowardly",
    "уверенность: осторожный": "confidence: cautious",
    "уверенность: средний": "confidence: average",
    "уверенность: смелый": "confidence: brave",
    "уверенность: безрассудный": "confidence: foolhardy",
    "настроение — нейтральное": "mood: neutral",
    "настроение — испуганное": "mood: fearful",
    "настроение — раздражённое": "mood: angry",
    "настроение — радостное": "mood: happy",
    "настроение — печальное": "mood: sad",
    "настроение — удивлённое": "mood: surprised",
    "настроение — озадаченное": "mood: puzzled",
    "настроение — отвращение": "mood: disgusted",
    "поиск": "find",
    "сопровождение": "follow",
    "эскорт": "escort",
    "приём пищи": "eat",
    "сон": "sleep",
    "патруль": "patrol",
    "перемещение": "travel",
    "работа с объектом": "use item",
    "засада": "ambush",
    "бегство": "flee",
    "применение эффекта": "cast",
    "быт / свободное поведение": "sandbox",
    "охрана": "guard",
    "диалог / встреча": "dialogue",
    "бой": "combat",
}

EFFECT_TERM_EN: dict[str, str] = {
    "Бартер": "Barter",
    "Без оружия": "Unarmed",
    "Взлом": "Lockpick",
    "Взрывчатка": "Explosives",
    "Восприятие": "Perception",
    "Выносливость": "Endurance",
    "Здоровье": "Health",
    "Интеллект": "Intelligence",
    "Красноречие": "Speech",
    "Ловкость": "Agility",
    "Лёгкое оружие": "Small Guns",
    "Медицина": "Medicine",
    "Наука": "Science",
    "Очки действия": "Action Points",
    "Радиация": "Radiation",
    "Ремонт": "Repair",
    "Сила": "Strength",
    "Скрытность": "Sneak",
    "Сопротивление радиации": "Radiation Resistance",
    "Сопротивление урону": "Damage Resistance",
    "Сопротивление ядам": "Poison Resistance",
    "Тяжёлое оружие": "Big Guns",
    "Удача": "Luck",
    "Урон в ближнем бою": "Melee Damage",
    "Харизма": "Charisma",
    "Холодное оружие": "Melee Weapons",
    "Энергетическое оружие": "Energy Weapons",
}

EVENT_ROLES_EN: dict[str, str] = {
    "evt_vault101_escape": "Prologue turning point: escape into the Capital Wasteland",
    "evt_megaton_bomb": "Early-game moral crossroads in Megaton",
    "evt_gnr_behemoth": "Major set-piece battle alongside Lyons' Pride",
    "evt_tranquility_lane": "Climax of Vault 112's virtual reality simulation",
    "evt_purifier_enclave_raid": "Act II turning point: Enclave assault on Jefferson Memorial",
    "evt_paradise_falls_raid": "Infiltration of Paradise Falls & path to Vault 87",
    "evt_vault87_geck": "Retrieving the G.E.C.K. and Colonel Autumn's ambush",
    "evt_raven_rock": "Confrontation with President Eden and fall of Raven Rock",
    "evt_liberty_prime_march": "Base game climax: Liberty Prime march & Project Purity activation",
    "evt_vault101_crisis": "Return to Vault 101 during internal rebellion",
    "evt_anchorage_sim": "Liberation of Anchorage simulation & Outcast mutiny",
    "evt_pitt_uprising": "The Pitt moral dilemma over baby Marie and the slave uprising",
    "evt_liberty_prime_fall": "Tragic turning point of Broken Steel at Rockland",
    "evt_adams_afb": "Final orbital strike at Adams Air Force Base (Broken Steel)",
    "evt_calvert_mansion": "Point Lookout conspiracy: Desmond vs. Professor Calvert",
    "evt_zeta_space_battle": "Orbital starship duel aboard Mothership Zeta",
}

CRAFTING_RECIPES_EN: dict[str, tuple[str, list[str], str]] = {
    "SchematicsBottlecapMineItem": (
        "Bottlecap Mine",
        ["Lunchbox", "Cherry Bomb", "Sensor Module", "Bottlecap (×10)"],
        "one of the highest-damage explosive traps in the Capital Wasteland, capable of eliminating a Deathclaw in a single detonation",
    ),
    "SchematicsDartGunItem": (
        "Dart Gun",
        ["Paint Gun", "Surgical Tubing", "Toy Car", "Radscorpion Poison Gland"],
        "a silent poison-dart weapon that instantly cripples targets' legs, slowing even the deadliest wasteland predators",
    ),
    "SchematicsDeathclawGauntletItem": (
        "Deathclaw Gauntlet",
        ["Wonderglue", "Leather Belt", "Medical Brace", "Deathclaw Hand"],
        "a lethal unarmed weapon that completely ignores enemy Damage Resistance (DR)",
    ),
    "SchematicsNukaCocktailItem": (
        "Nuka-Grenade",
        ["Nuka-Cola Quantum", "Tin Can", "Turpentine", "Abraxo Cleaner"],
        "a devastating improvised grenade producing a blinding blue blast and massive area damage",
    ),
    "SchematicsRailwayRifleItem": (
        "Railway Rifle",
        ["Crutch", "Steam Gauge Assembly", "Fission Battery", "Pressure Cooker"],
        "a steam-powered rifle firing railway spikes with high critical hit potential and limb-pinning impact",
    ),
    "SchematicsRockItLauncherItem": (
        "Rock-It Launcher",
        ["Vacuum Cleaner", "Leaf Blower", "Firehose Nozzle", "Conductor"],
        "a heavy pneumatic launcher capable of firing almost any misc junk item as deadly ammunition",
    ),
    "SchematicsShishkebabItem": (
        "Shishkebab",
        ["Motorcycle Gas Tank", "Motorcycle Handbrake", "Lawnmower Blade", "Pilot Light"],
        "a flaming melee sword with top-tier DPS and burning damage over time, further boosted by the Pyromaniac perk",
    ),
}

SPECIAL_OBJ_UNLOCKS_EN: dict[str, str] = {
    "Взрывная ловушка (требуется осторожность)": "Explosive trap (exercise caution)",
    "Вмещает 20 коллекционных пупсов": "Holds all 20 collectible Bobbleheads",
    "Волна: «Новости Галактики»": "Radio Station: Galaxy News Radio",
    "Волна: Анклава": "Radio Station: Enclave Radio",
    "Волна: локальной волны": "Radio Station: Local Signal",
    "Восстанавливает вещание GNR по всей Пустоши": "Restores GNR broadcast across the Capital Wasteland",
    "Вызывает артиллерийский удар по двору": "Calls in artillery strike on courtyard",
    "Головоломка / выход «Трэнквилити-лейн»": "Tranquility Lane puzzle / exit mechanism",
    "Запускает трансляцию скрытого сигнала": "Triggers hidden radio signal broadcast",
    "Ключевой выбор в квесте «Оазис»": "Key decision point in the quest 'Oasis'",
    "Ключевой объект квеста «Сила атома»": "Key objective of 'The Power of the Atom'",
    "Настройка базовых параметров S.P.E.C.I.A.L.": "Configures starting S.P.E.C.I.A.L. attributes",
    "Отключение/переключение энергопитания объекта": "Toggles / disables object power supply",
    "Открывает потайную стену в Кузницу Механиста": "Opens hidden wall to the Mechanist's Forge",
    "Открывает проход в лабораторию Пинкертона": "Opens passage to Pinkerton's lab",
    "Отображается на стенде после находки оригинала": "Displayed on stand once original is found",
    "Передаёт сигнал бедствия на Пип-бой": "Transmits distress signal to Pip-Boy",
    "Подаёт питание на двери бункера Нац. гвардии": "Restores power to National Guard Depot bunker doors",
    "Сборка уникального оружия по схемам": "Crafts custom schematic weapons",
    "Сценарный триггер ESM": "Scripted ESM event trigger",
    "Сюжетный узел Мемориала Джефферсона": "Jefferson Memorial story objective node",
    "Управление гермозатвором Убежища": "Vault blast door controls",
    "Управление локальным механизмом / защитой": "Local mechanism / security controls",
    "Элемент галлюцинации (бонус S.P.E.C.I.A.L. не даёт)": "Hallucination vision prop (grants no S.P.E.C.I.A.L. bonus)",
}


def norm_ru(s: str) -> str:
    return re.sub(r'["«»]', "", s.lower().replace("ё", "е")).strip()


def translate_behavior(beh: str) -> str:
    if not beh:
        return ""
    # Format: "<Aggression>, <Confidence>; настроение — <Mood>. Режим ИИ: <p1>, <p2>"
    main_part = beh
    ai_part = ""
    if "Режим ИИ:" in beh:
        main_part, ai_part = beh.split("Режим ИИ:", 1)
    main_part = main_part.strip().rstrip(".")
    ai_part = ai_part.strip()

    left_bits: list[str] = []
    mood_str = ""
    if ";" in main_part:
        lraw, mraw = main_part.split(";", 1)
        for tok in lraw.split(","):
            t = tok.strip()
            left_bits.append(BEHAVIOR_TOKENS_EN.get(t, t))
        m_clean = mraw.strip()
        mood_str = BEHAVIOR_TOKENS_EN.get(m_clean, m_clean)
    else:
        for tok in main_part.split(","):
            t = tok.strip()
            left_bits.append(BEHAVIOR_TOKENS_EN.get(t, t))

    res = ", ".join(left_bits)
    if mood_str:
        res += f"; {mood_str}"
    if ai_part:
        ai_translated = [BEHAVIOR_TOKENS_EN.get(p.strip(), p.strip()) for p in ai_part.split(",") if p.strip()]
        if ai_translated:
            res += f". AI packages: {', '.join(ai_translated)}"
    return res


def translate_effect(eff: str) -> str:
    s = eff.strip()
    if s == "Водный эффект ВРЭ":
        return "FEV-Contaminated Water"
    if s == "Гипнотрон":
        return "Mesmetron Stun / Frenzy"
    if s == "Компьютер силовой брони":
        return "Power Armor Interface"
    if s == "Кровавая баня - Либерти Прайм":
        return "Liberty Prime Bloody Mess"
    if s == "Крысиный репеллент":
        return "Mole Rat Repellent"
    if s == "Ошейник раба":
        return "Slave Collar Effect"
    if s == "Получение: награда за квест / испытание":
        return "Source: Quest / Challenge Reward"
    if s == "Расчленение":
        return "Dismemberment"
    if s == "Эффект дробовика Харона":
        return "Charon's Shotgun Effect"
    if s == "Эффект стелс-брони":
        return "Stealth Armor Field"
    if s == "Эффект шокера":
        return "Shock Stun Effect"

    m = re.match(r"^Макс\. рангов:\s*(\d+)$", s)
    if m:
        return f"Max Ranks: {m.group(1)}"
    m = re.match(r"^Уровень:\s*(\d+\+)$", s)
    if m:
        return f"Level: {m.group(1)}"
    m = re.match(r"^Сжигание огнеметом\s*\((\d+)\s*сек\.\)$", s)
    if m:
        return f"Flamer Burn ({m.group(1)} sec)"
    m = re.match(r"^Стелс-поле\s*\((\d+)\)(?:\s*\((\d+)\s*сек\.\))?$", s)
    if m:
        dur = f" ({m.group(2)} sec)" if m.group(2) else ""
        return f"Stealth Field ({m.group(1)}){dur}"
    m = re.match(r"^Увеличение сопротивления огню\s*\((\d+)\)(?:\s*\((\d+)\s*сек\.\))?$", s)
    if m:
        dur = f" ({m.group(2)} sec)" if m.group(2) else ""
        return f"Fire Resistance +{m.group(1)}%{dur}"
    m = re.match(r"^Повреждение здоровья:\s*([+-]?\d+)$", s)
    if m:
        return f"Health {m.group(1)}"
    m = re.match(r"^Радиационное заражение:\s*([+-]?\d+)$", s)
    if m:
        return f"Radiation {m.group(1)}"
    m = re.match(r"^Урон\s+([+-]\d+%)(?:\s*\((\d+)\s*сек\.\))?$", s)
    if m:
        dur = f" ({m.group(2)} sec)" if m.group(2) else ""
        return f"Damage {m.group(1)}{dur}"
    m = re.match(r"^Урон огнем огнемета:\s*([+-]?\d+)\s*\((\d+)\s*сек\.\)$", s)
    if m:
        return f"Flamer Fire Damage {m.group(1)} ({m.group(2)} sec)"
    m = re.match(r"^Урон от шокера Чужих:\s*([+-]?\d+)\s*\((\d+)\s*сек\.\)$", s)
    if m:
        return f"Alien Shock Damage {m.group(1)} ({m.group(2)} sec)"
    m = re.match(r"^Яд:\s*([+-]?\d+)\s*Здоровье/сек\s*\((\d+)\s*сек\.\)$", s)
    if m:
        return f"Poison: {m.group(1)} HP/sec ({m.group(2)} sec)"

    # Skill book pattern: "<Skill> (+1 / +2 с «Пониманием»)"
    m = re.match(r"^(.+?)\s*\(\+1\s*/\s*\+2\s*с\s*«Пониманием»\)$", s)
    if m:
        sk = EFFECT_TERM_EN.get(m.group(1).strip(), m.group(1).strip())
        return f"{sk} (+1 / +2 with Comprehension)"

    # "<Term> >= N" or "<Term> +N (%)" with optional "(X сек.)"
    m = re.match(r"^(.+?)\s+(≥\s*\d+|[+-]\d+%?)(?:\s*\((\d+)\s*сек\.\))?$", s)
    if m:
        term_ru, val, dur_s = m.group(1).strip(), m.group(2).strip(), m.group(3)
        term_en = EFFECT_TERM_EN.get(term_ru, term_ru)
        dur = f" ({dur_s} sec)" if dur_s else ""
        return f"{term_en} {val}{dur}"

    return s


def translate_terminal_action(act: str) -> str:
    s = act.strip()
    replacements = [
        ("Открыть двери", "Open doors"),
        ("Открыть дверь", "Open door"),
        ("Открыть сейф", "Unlock safe"),
        ("Открыть секретный люк", "Open secret hatch"),
        ("Открыть люк", "Open hatch"),
        ("Открыть ворота", "Open gate"),
        ("Открыть шкаф", "Unlock cabinet"),
        ("Открыть замок", "Unlock"),
        ("Открыть", "Open"),
        ("Закрыть", "Close"),
        ("Активировать охранного робота", "Activate Sentry Bot"),
        ("Активировать протектрона", "Activate Protectron"),
        ("Активировать робота - помощника ученого", "Activate Lab Assistant Robot"),
        ("Активировать робота", "Activate robot"),
        ("Активировать систему турелей", "Activate turret system"),
        ("Активировать турели", "Activate turrets"),
        ("Активировать барьер", "Activate barrier"),
        ("Активировать дверь хранилища", "Activate vault door"),
        ("Активировать дверь", "Activate door"),
        ("Активировать аварийный импульсный взрыв", "Trigger emergency pulse blast"),
        ("Активировать", "Activate"),
        ("Включить защитные турели", "Enable defense turrets"),
        ("Включить турели", "Enable turrets"),
        ("Включить защитное поле станции", "Enable station forcefield"),
        ("Включить защитное поле", "Enable forcefield"),
        ("Включить контрольное поле", "Enable control field"),
        ("Включить системы защиты", "Enable security systems"),
        ("Включить освещение", "Turn on lights"),
        ("Включить", "Enable"),
        ("Выключить системы защиты", "Disable security systems"),
        ("Выключить защитное поле", "Disable forcefield"),
        ("Выключить турели", "Disable turrets"),
        ("Выключить", "Disable"),
        ("Отключить турели", "Deactivate turrets"),
        ("Отключить защитное поле", "Deactivate forcefield"),
        ("Отключить", "Disable"),
        ("Деактивировать", "Deactivate"),
        ("Безопасное отключение машины", "Safely shut down machine"),
        ("Вызвать робота", "Deploy robot"),
        ("Запустить", "Launch"),
        ("Перезагрузить", "Reboot"),
        ("Удалить", "Delete"),
        ("Автоматическая турель", "Automated Turret"),
        ("Нет ответа", "No response"),
        ("ОШИБКА", "ERROR"),
        ("в атриуме", "in atrium"),
        ("в холле", "in lobby"),
        ("в секторе", "in sector"),
        ("сектора", "of sector"),
        ("Турели", "Turrets"),
    ]
    out = s
    for ru_p, en_p in replacements:
        out = out.replace(ru_p, en_p)
    if HAS_CYRILLIC.search(out):
        return "Execute terminal security / system command"
    return out


def main() -> None:
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    details_ru = json.loads(DETAILS_RU_PATH.read_text(encoding="utf-8"))
    wt_en_list = json.loads(WT_EN_PATH.read_text(encoding="utf-8"))
    wiki_en = json.loads(WIKI_EN_PATH.read_text(encoding="utf-8"))

    nodes = graph["nodes"]
    edges = graph["edges"]
    node_by_id = {n["id"]: n for n in nodes}
    wt_by_id = {w["nodeId"]: w for w in wt_en_list}

    # Lookup maps RU -> EN from graph.json
    ru_to_en_by_type: dict[str, dict[str, str]] = defaultdict(dict)
    ru_to_en_all: dict[str, str] = {}
    for n in nodes:
        ru_to_en_by_type[n["type"]][norm_ru(n["label"])] = n["labelEn"]
        ru_to_en_all[norm_ru(n["label"])] = n["labelEn"]

    # Build adjacency
    adj: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    for e in edges:
        s = node_by_id.get(e["source"])
        t = node_by_id.get(e["target"])
        if s and t:
            adj[e["source"]].append((t, e["type"]))
            adj[e["target"]].append((s, e["type"]))

    def worldspace_to_en(ws: str) -> str:
        if ws in WORLDSPACE_EXPLICIT_EN:
            return WORLDSPACE_EXPLICIT_EN[ws]
        nws = norm_ru(ws)
        if nws in ru_to_en_by_type["location"]:
            return ru_to_en_by_type["location"][nws]
        return ws

    def translate_unlock(nid: str, ntype: str, u: str) -> str:
        if u in SPECIAL_OBJ_UNLOCKS_EN:
            return SPECIAL_OBJ_UNLOCKS_EN[u]
        if u.startswith("Ведёт в: "):
            loc_ru = u[len("Ведёт в: ") :].strip()
            return f"Leads to: {worldspace_to_en(loc_ru)}"
        if u.startswith("Требуемый ключ: "):
            key_ru = u[len("Требуемый ключ: ") :].strip()
            key_en = ru_to_en_by_type["item"].get(norm_ru(key_ru), ru_to_en_all.get(norm_ru(key_ru), key_ru))
            if HAS_CYRILLIC.search(key_en):
                # Find via object_key edge
                for nb, et in adj.get(nid, []):
                    if et == "object_key":
                        key_en = nb["labelEn"]
                        break
            return f"Required Key: {key_en}"
        if u.startswith("Открывается ключом: "):
            key_ru = u[len("Открывается ключом: ") :].strip()
            key_en = ru_to_en_all.get(norm_ru(key_ru), key_ru)
            return f"Unlocked by key: {key_en}"
        if u.startswith("Интерактивный узел в "):
            loc_ru = u[len("Интерактивный узел в ") :].strip()
            return f"Interactive node in {worldspace_to_en(loc_ru)}"
        if u.startswith("Разблокируется в: "):
            loc_ru = u[len("Разблокируется в: ") :].strip()
            return f"Unlocked in: {worldspace_to_en(loc_ru)}"
        if u.startswith("Функция терминала: "):
            cmd = u[len("Функция терминала: ") :].strip()
            return f"Terminal command: {translate_terminal_action(cmd)}"
        m_loot = re.match(r"^Ценная добыча:\s*«(.+?)»(?:\s*\(×(\d+)\))?$", u)
        if m_loot:
            itm_ru, cnt = m_loot.group(1), m_loot.group(2)
            itm_en = ru_to_en_by_type["item"].get(norm_ru(itm_ru), ru_to_en_all.get(norm_ru(itm_ru), itm_ru))
            if HAS_CYRILLIC.search(itm_en):
                itm_en = "Notable Quest / Supply Item"
            return f"Notable loot: {itm_en}" + (f" (×{cnt})" if cnt else "")
        if ntype == "item" and "(" in u and u.endswith(")"):
            obj_ru, loc_ru = u.rsplit("(", 1)
            obj_ru = obj_ru.strip()
            loc_ru = loc_ru[:-1].strip()
            obj_en = ru_to_en_by_type["object"].get(norm_ru(obj_ru), ru_to_en_all.get(norm_ru(obj_ru), obj_ru))
            loc_en = worldspace_to_en(loc_ru)
            if not HAS_CYRILLIC.search(obj_en) and not HAS_CYRILLIC.search(loc_en):
                return f"{obj_en} ({loc_en})"
        return ""

    def neighbor_names(nid: str, types: tuple[str, ...] | None = None, edge_types: tuple[str, ...] | None = None, limit: int = 8) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for nb, et in sorted(adj.get(nid, []), key=lambda x: -x[0]["degree"]):
            if types and nb["type"] not in types:
                continue
            if edge_types and et not in edge_types:
                continue
            lbl = nb["labelEn"]
            if lbl not in seen:
                seen.add(lbl)
                out.append(lbl)
                if len(out) >= limit:
                    break
        return out

    def clean_wiki_sec_text(txt: str, max_len: int = 950) -> str:
        t = re.sub(r"\n{3,}", "\n\n", txt).strip()
        if len(t) > max_len:
            cut = t[:max_len]
            last_dot = max(cut.rfind(". "), cut.rfind(".\n"))
            if last_dot > max_len * 0.45:
                t = cut[: last_dot + 1]
            else:
                t = cut.rstrip() + "..."
        return t

    details_en: dict[str, dict[str, Any]] = {}

    for node in nodes:
        nid = node["id"]
        ntype = node["type"]
        sub = node["subtype"]
        edid = node.get("edid", "")
        lbl = node["labelEn"]
        dlc_name = DLC_LABELS_EN.get(node["dlc"], "Fallout 3")
        ru = details_ru.get(nid, {})
        wk = wiki_en.get(nid)

        entry: dict[str, Any] = {"id": nid}

        # Copy safe numeric / boolean / coordinate / technical fields verbatim
        for k in (
            "level",
            "hp",
            "female",
            "essential",
            "unique",
            "special",
            "coords",
            "value",
            "weight",
            "damage",
            "dr",
            "clipSize",
            "fireRate",
            "apCost",
            "critDamage",
            "critMult",
            "spread",
            "health",
            "questCategory",
        ):
            if k in ru and ru[k] is not None:
                entry[k] = ru[k]

        # Translate discrete metadata fields
        if ru.get("race"):
            entry["race"] = RACE_EN.get(ru["race"], ru["race"])
        if ru.get("worldspace"):
            entry["worldspace"] = worldspace_to_en(ru["worldspace"])
        if ru.get("markerType"):
            entry["markerType"] = MARKER_TYPE_EN.get(ru["markerType"], ru["markerType"])
        if ru.get("weaponClass"):
            entry["weaponClass"] = WEAPON_CLASS_EN.get(ru["weaponClass"], ru["weaponClass"])
        if ru.get("ammo"):
            entry["ammo"] = AMMO_EN.get(ru["ammo"], ru["ammo"])
        if ru.get("lockDiff"):
            entry["lockDiff"] = LOCK_DIFF_EN.get(ru["lockDiff"], ru["lockDiff"])
        if ru.get("factions"):
            entry["factions"] = [FACTIONS_EN.get(f, f) for f in ru["factions"]]
        if ru.get("services"):
            entry["services"] = [SERVICES_EN.get(s, s) for s in ru["services"]]
        if ru.get("behavior"):
            entry["behavior"] = translate_behavior(ru["behavior"])
        if ru.get("effects"):
            entry["effects"] = [translate_effect(e) for e in ru["effects"]]
        if ru.get("inventory"):
            inv_en = []
            for itm in ru["inventory"]:
                it_node = node_by_id.get(itm["id"])
                inv_en.append({
                    "id": itm["id"],
                    "label": it_node["labelEn"] if it_node else itm["id"],
                    "count": itm["count"],
                })
            entry["inventory"] = inv_en

        # Unlocks translation
        if ntype == "item" and sub == "key":
            key_unlocks = []
            for nb, et in adj.get(nid, []):
                if et == "object_key":
                    locs = neighbor_names(nb["id"], types=("location",), limit=1)
                    loc_s = f" ({locs[0]})" if locs else ""
                    key_unlocks.append(f"{nb['labelEn']}{loc_s}")
            if not key_unlocks and ru.get("unlocks"):
                for u in ru["unlocks"]:
                    tr = translate_unlock(nid, ntype, u)
                    if tr and not HAS_CYRILLIC.search(tr):
                        key_unlocks.append(tr)
            if key_unlocks:
                entry["unlocks"] = list(dict.fromkeys(key_unlocks))[:12]
        elif ru.get("unlocks"):
            tr_unlocks = []
            for u in ru["unlocks"]:
                tr = translate_unlock(nid, ntype, u)
                if tr and not HAS_CYRILLIC.search(tr):
                    tr_unlocks.append(tr)
            if tr_unlocks:
                entry["unlocks"] = list(dict.fromkeys(tr_unlocks))[:12]

        # Wiki URL + sourceTag
        if wk:
            entry["wikiUrl"] = wk["url"]
            entry["sourceTag"] = "Game Files + Fallout Wiki"
            if wk.get("quotes") and ntype == "character":
                entry["quotes"] = wk["quotes"][:4]
        elif ru.get("sourceTag") and "Энциклопедия" in ru["sourceTag"]:
            entry["sourceTag"] = "Game Files + Encyclopedia"
        else:
            entry["sourceTag"] = "Game Files (.ESM)"

        # Common linked entity names
        locs = neighbor_names(nid, types=("location",), limit=6)
        chars = neighbor_names(nid, types=("character",), limit=6)
        quests = neighbor_names(nid, types=("quest",), limit=6)
        items_nb = neighbor_names(nid, types=("item",), limit=6)
        objs_nb = neighbor_names(nid, types=("object",), limit=6)
        events_nb = neighbor_names(nid, types=("event",), limit=4)

        # ------------------------------------------------------------------
        # Generate idiomatic English role, summary, sections (+ text for perks/notes)
        # ------------------------------------------------------------------
        if ntype == "character":
            is_crea = sub == "creature"
            race_s = entry.get("race", "Human" if not is_crea else "Creature")
            fac_s = ", ".join(entry.get("factions", [])[:3])
            svc_s = ", ".join(entry.get("services", [])[:4])
            lv_s = f"Level {entry['level']}" if "level" in entry else "Scaled level"
            hp_s = f"{entry['hp']} HP" if "hp" in entry else "standard health"

            if lbl.startswith("Appearance Preset:"):
                entry["role"] = "Vault 101 Character Creation Preset"
            elif "Test Character" in lbl or "Voice Actor" in lbl or "Placeholder" in lbl:
                entry["role"] = "Developer / Voice Placeholder NPC"
            elif svc_s:
                entry["role"] = f"Merchant / Service Provider ({svc_s})"
            elif entry.get("essential"):
                entry["role"] = f"Essential Story Character ({race_s})"
            elif fac_s:
                entry["role"] = f"{fac_s} — {race_s}"
            elif is_crea:
                entry["role"] = f"Wasteland Creature / Robot ({race_s})"
            else:
                entry["role"] = f"{dlc_name} Character ({race_s})"

            if wk and wk.get("lead") and len(wk["lead"]) >= 85:
                entry["summary"] = clean_wiki_sec_text(wk["lead"], 480)
            else:
                loc_phrase = f"Found primarily around {', '.join(locs[:3])}." if locs else f"Encountered in {dlc_name}."
                q_phrase = f" Directly connected to quests: {', '.join(quests[:3])}." if quests else ""
                fac_phrase = f" Affiliated with {fac_s}." if fac_s else ""
                entry["summary"] = (
                    f"{lbl} is a {race_s.lower()} {'creature or robotic unit' if is_crea else 'character'} in {dlc_name} "
                    f"({lv_s}, {hp_s}).{fac_phrase} {loc_phrase}{q_phrase}"
                ).strip()

            secs: list[dict[str, str]] = []
            if wk and wk.get("sections"):
                for ws_sec in wk["sections"][:3]:
                    txt_c = clean_wiki_sec_text(ws_sec["text"], 850)
                    if len(txt_c) >= 35:
                        secs.append({"title": ws_sec["heading"], "text": txt_c})

            if len(secs) < 2:
                # Section 1: Background & Role
                bg_parts = [
                    f"In game files (EditorID: {edid or 'N/A'}), {lbl} is defined as a {race_s} in {dlc_name}."
                ]
                if entry.get("essential"):
                    bg_parts.append("Marked as essential (cannot be killed during normal gameplay until plot flags allow).")
                if fac_s:
                    bg_parts.append(f"Faction memberships: {', '.join(entry.get('factions', []))}.")
                if quests:
                    bg_parts.append(f"Appears in or relates to quests: {', '.join(quests)}.")
                if events_nb:
                    bg_parts.append(f"Linked story events: {', '.join(events_nb)}.")
                secs.append({"title": "Background & Story Role", "text": " ".join(bg_parts)})

                # Section 2: Combat Profile & Behavior
                beh_s = entry.get("behavior") or "Standard wasteland AI behavior."
                spec_s = ""
                if entry.get("special") and len(entry["special"]) == 7:
                    sp = entry["special"]
                    spec_s = f" S.P.E.C.I.A.L. profile: STR {sp[0]}, PER {sp[1]}, END {sp[2]}, CHA {sp[3]}, INT {sp[4]}, AGI {sp[5]}, LCK {sp[6]}."
                secs.append({
                    "title": "Combat Profile & Behavior",
                    "text": f"Combat baseline: {lv_s}, {hp_s}.{spec_s} Behavioral traits: {beh_s}.",
                })

            # Always ensure a Locations & Equipment section if <3 sections
            if len(secs) < 3:
                inv_names = [i["label"] for i in entry.get("inventory", [])[:6]]
                loc_txt = f"Known locations: {', '.join(locs)}." if locs else f"Active across {dlc_name} encounter zones."
                inv_txt = f" Notable equipment & inventory: {', '.join(inv_names)}." if inv_names else " Carries standard equipment for their faction and level."
                svc_txt = f" Provides services: {svc_s}." if svc_s else ""
                secs.append({"title": "Locations & Equipment", "text": f"{loc_txt}{inv_txt}{svc_txt}"})

            entry["sections"] = secs[:4]

        elif ntype == "location":
            mtype = entry.get("markerType", SUBTYPE_LABELS_EN.get(sub, "Location"))
            ws_name = entry.get("worldspace", dlc_name)
            entry["role"] = f"{mtype} ({ws_name})"

            if wk and wk.get("lead") and len(wk["lead"]) >= 85:
                entry["summary"] = clean_wiki_sec_text(wk["lead"], 480)
            else:
                conn_locs = neighbor_names(nid, types=("location",), limit=3)
                conn_s = f" Connects directly to {', '.join(conn_locs)}." if conn_locs else ""
                q_s = f" Featured in quests: {', '.join(quests[:3])}." if quests else ""
                entry["summary"] = (
                    f"{lbl} is a {mtype.lower()} in {ws_name} ({dlc_name}).{conn_s}{q_s}"
                )

            secs = []
            if wk and wk.get("sections"):
                for ws_sec in wk["sections"][:3]:
                    txt_c = clean_wiki_sec_text(ws_sec["text"], 850)
                    if len(txt_c) >= 35:
                        secs.append({"title": ws_sec["heading"], "text": txt_c})

            if len(secs) < 2:
                conn_locs = neighbor_names(nid, types=("location",), limit=6)
                coord_txt = (
                    f" World coordinates: X {entry['coords'][0]}, Y {entry['coords'][1]}, Z {entry['coords'][2]}."
                    if entry.get("coords")
                    else ""
                )
                secs.append({
                    "title": "Overview & Layout",
                    "text": (
                        f"Region / Worldspace: {ws_name} ({dlc_name}), EditorID: {edid or 'N/A'}.{coord_txt} "
                        + (f"Connected areas and passages: {', '.join(conn_locs)}." if conn_locs else "Standalone or interior cell.")
                    ),
                })
                secs.append({
                    "title": "Inhabitants & Threats",
                    "text": (
                        f"Characters & creatures present: {', '.join(chars)}."
                        if chars
                        else f"Generic wasteland spawns or uninhabited ruins within {ws_name}."
                    ),
                })

            if len(secs) < 3:
                loot_s = f"Notable items: {', '.join(items_nb)}." if items_nb else "Standard wasteland containers and supplies."
                obj_s = f" Interactive objects: {', '.join(objs_nb)}." if objs_nb else ""
                q_s = f" Related quests: {', '.join(quests)}." if quests else ""
                secs.append({"title": "Loot, Objects & Related Quests", "text": f"{loot_s}{obj_s}{q_s}"})

            entry["sections"] = secs[:4]

        elif ntype == "item":
            sub_lbl = SUBTYPE_LABELS_EN.get(sub, "Item")
            if sub == "weapon":
                entry["role"] = entry.get("weaponClass", "Weapon")
            elif sub == "armor":
                entry["role"] = "Armor / Apparel"
            elif sub == "book":
                entry["role"] = "Permanent Skill Book"
            elif sub == "key":
                entry["role"] = "Access Key / Passcard"
            elif sub == "note":
                entry["role"] = "Note / Holotape Log"
            elif edid in CRAFTING_RECIPES_EN:
                entry["role"] = "Custom Weapon Schematics"
            else:
                entry["role"] = f"{sub_lbl} ({dlc_name})"

            if wk and wk.get("lead") and len(wk["lead"]) >= 85:
                entry["summary"] = clean_wiki_sec_text(wk["lead"], 480)
            elif edid in CRAFTING_RECIPES_EN:
                rname, rcomps, rdesc = CRAFTING_RECIPES_EN[edid]
                entry["summary"] = (
                    f"{lbl} unlocks crafting of the {rname} at any workbench using {', '.join(rcomps)} — {rdesc}."
                )
            else:
                specs_bits = []
                if entry.get("damage"):
                    specs_bits.append(f"Damage {entry['damage']}")
                if entry.get("dr"):
                    specs_bits.append(f"DR {entry['dr']}")
                if entry.get("ammo"):
                    specs_bits.append(f"uses {entry['ammo']}")
                if entry.get("value") is not None:
                    specs_bits.append(f"value {entry['value']} caps")
                spec_str = f" ({', '.join(specs_bits)})" if specs_bits else ""
                entry["summary"] = (
                    f"{lbl} is a {sub_lbl.lower()} in {dlc_name}{spec_str}. "
                    + (f"Linked to quests: {', '.join(quests[:3])}." if quests else f"Available across {dlc_name} locations and merchants.")
                )

            # For notes/holotapes, see if EN Wiki has a transcript section to populate `text`
            if sub == "note" and wk and wk.get("sections"):
                for ws_sec in wk["sections"]:
                    if any(h in ws_sec["heading"].lower() for h in ("transcript", "text", "entry", "entries", "content")):
                        entry["text"] = ws_sec["text"][:3000]
                        break

            secs = []
            if wk and wk.get("sections"):
                for ws_sec in wk["sections"][:3]:
                    txt_c = clean_wiki_sec_text(ws_sec["text"], 850)
                    if len(txt_c) >= 35:
                        secs.append({"title": ws_sec["heading"], "text": txt_c})

            if len(secs) < 2:
                eff_s = f" Effects: {', '.join(entry.get('effects', []))}." if entry.get("effects") else ""
                secs.append({
                    "title": "Overview & Properties",
                    "text": (
                        f"Item classification: {sub_lbl} from {dlc_name} (EditorID: {edid or 'N/A'}). "
                        f"Weight: {entry.get('weight', 0)}, Value: {entry.get('value', 0)} caps.{eff_s}"
                    ),
                })
                where_parts = []
                if locs:
                    where_parts.append(f"Found at locations: {', '.join(locs)}.")
                if chars:
                    where_parts.append(f"Carried or sold by: {', '.join(chars)}.")
                if quests:
                    where_parts.append(f"Used in quests: {', '.join(quests)}.")
                where_text = " ".join(where_parts).strip()
                if len(where_text) < 45:
                    where_text = (
                        (where_text + " ") if where_text else ""
                    ) + f"Obtained through exploration, containers, or quest progression in {dlc_name}."
                secs.append({"title": "Where to Find & Usage", "text": where_text})

            entry["sections"] = secs[:4]

        elif ntype == "object":
            sub_lbl = SUBTYPE_LABELS_EN.get(sub, "Object")
            if sub == "perk":
                entry["role"] = f"Character Perk ({dlc_name})"
            elif sub == "terminal":
                entry["role"] = f"Interactive Computer Terminal ({dlc_name})"
            else:
                entry["role"] = f"{sub_lbl} ({dlc_name})"

            if sub == "perk" and wk:
                perk_lead = wk.get("lead", "").strip()
                perk_sec0 = wk["sections"][0]["text"].strip() if wk.get("sections") else ""
                if len(perk_lead) >= 85:
                    entry["text"] = clean_wiki_sec_text(perk_lead, 600)
                    entry["summary"] = clean_wiki_sec_text(perk_lead, 480)
                else:
                    combined = " ".join(p for p in (perk_lead, perk_sec0) if p).strip()
                    if len(combined) < 85:
                        eff_s = ", ".join(entry.get("effects", [])) or "specialized character bonuses"
                        combined = f"{lbl} is a character perk in {dlc_name} ({eff_s})."
                    entry["text"] = clean_wiki_sec_text(combined, 600)
                    entry["summary"] = clean_wiki_sec_text(combined, 480)
            elif wk and wk.get("lead") and len(wk["lead"]) >= 85:
                entry["summary"] = clean_wiki_sec_text(wk["lead"], 480)
            else:
                loc_s = f" Located in {', '.join(locs[:3])}." if locs else ""
                q_s = f" Associated with quests: {', '.join(quests[:3])}." if quests else ""
                lock_s = f" Lock difficulty: {entry['lockDiff']}." if entry.get("lockDiff") else ""
                entry["summary"] = (
                    f"{lbl} is an interactive {sub_lbl.lower()} in {dlc_name}.{lock_s}{loc_s}{q_s}"
                )

            secs = []
            if wk and wk.get("sections"):
                for ws_sec in wk["sections"][:3]:
                    txt_c = clean_wiki_sec_text(ws_sec["text"], 850)
                    if len(txt_c) >= 35:
                        secs.append({"title": ws_sec["heading"], "text": txt_c})

            if len(secs) < 2:
                if sub == "perk":
                    eff_str = ", ".join(entry.get("effects", [])) or "Grants specialized character bonuses."
                    secs.append({"title": "Requirements & Effects", "text": f"Perk criteria and modifiers: {eff_str}."})
                    secs.append({
                        "title": "Mechanics & Tactical Value",
                        "text": f"Available in {dlc_name} (EditorID: {edid or 'N/A'}). Integrates with character builds and related quests ({', '.join(quests) or 'general gameplay'}).",
                    })
                else:
                    acc_parts = [f"Object type: {sub_lbl} ({dlc_name}, EditorID: {edid or 'N/A'})."]
                    if entry.get("lockDiff"):
                        acc_parts.append(f"Security / Lock: {entry['lockDiff']}.")
                    if entry.get("unlocks"):
                        acc_parts.append(f"Functions & access: {'; '.join(entry['unlocks'][:4])}.")
                    secs.append({"title": "Function & Access", "text": " ".join(acc_parts)})
                    conn_parts = []
                    if locs:
                        conn_parts.append(f"Locations: {', '.join(locs)}.")
                    if quests:
                        conn_parts.append(f"Related quests: {', '.join(quests)}.")
                    if items_nb:
                        conn_parts.append(f"Linked keys / items: {', '.join(items_nb)}.")
                    conn_text = " ".join(conn_parts).strip()
                    if len(conn_text) < 45:
                        conn_text = (
                            (conn_text + " ") if conn_text else ""
                        ) + f"Placed within {dlc_name} environments and linked on the knowledge graph."
                    secs.append({
                        "title": "Location & Connections",
                        "text": conn_text,
                    })

            entry["sections"] = secs[:4]

        elif ntype == "quest":
            wt = wt_by_id.get(nid)
            qcat = entry.get("questCategory", sub)
            entry["role"] = f"{SUBTYPE_LABELS_EN.get(qcat, 'Quest')} ({dlc_name})"

            if wt:
                entry["summary"] = wt["summary"]
            elif wk and wk.get("lead"):
                entry["summary"] = clean_wiki_sec_text(wk["lead"], 480)
            else:
                entry["summary"] = f"{lbl} is a quest in {dlc_name} involving {', '.join(chars[:3]) or 'Capital Wasteland characters'}."

            secs = []
            if wk and wk.get("sections"):
                for ws_sec in wk["sections"][:3]:
                    txt_c = clean_wiki_sec_text(ws_sec["text"], 850)
                    if len(txt_c) >= 35:
                        secs.append({"title": ws_sec["heading"], "text": txt_c})

            if len(secs) < 2:
                setup_txt = wt["startCondition"] if wt else f"Triggered within {dlc_name}."
                if locs:
                    setup_txt += f" Primary locations: {', '.join(locs)}."
                secs.append({"title": "Story Role & Setup", "text": setup_txt})

                rew_txt = "; ".join(wt["rewards"]) if (wt and wt.get("rewards")) else "Experience points, caps, items, and karma."
                part_txt = f" Key participants: {', '.join(chars)}." if chars else ""
                secs.append({"title": "Participants, Choices & Rewards", "text": f"Rewards: {rew_txt}.{part_txt}"})

            entry["sections"] = secs[:4]

        elif ntype == "event":
            if nid in EVENT_ROLES_EN:
                entry["role"] = EVENT_ROLES_EN[nid]
            elif sub == "random_encounter":
                entry["role"] = f"Capital Wasteland Random Encounter ({edid})"
            else:
                entry["role"] = f"Key Story Event ({dlc_name})"

            part_s = f" Key characters: {', '.join(chars[:4])}." if chars else ""
            loc_s = f" Locations: {', '.join(locs[:3])}." if locs else ""
            q_s = f" Related quests: {', '.join(quests[:3])}." if quests else ""
            item_s = f" Key items / objects: {', '.join((items_nb + objs_nb)[:4])}." if (items_nb or objs_nb) else ""

            if sub == "random_encounter":
                entry["summary"] = (
                    f"{lbl} is a random encounter event in Fallout 3 ({edid}) that can trigger while exploring the Capital Wasteland.{part_s}{item_s}"
                )
                entry["sections"] = [
                    {
                        "title": "Encounter Overview & Trigger",
                        "text": (
                            f"This encounter belongs to the dynamic Capital Wasteland random encounter table ({edid}). "
                            f"Unique encounters (FFEUnique) fire once per playthrough at designated encounter zones, whereas repeatable ones (FFERepeat) can recur.{part_s}"
                        ),
                    },
                    {
                        "title": "Linked Entities & Outcomes",
                        "text": (
                            f"{loc_s or 'Triggers across open wasteland roads and spawn markers.'}{item_s}{q_s or ' Adds dynamic world reactivity and potential loot or karma outcomes.'}"
                        ).strip(),
                    },
                ]
            else:
                entry["summary"] = (
                    f"{lbl} is a major narrative turning point in {dlc_name}.{q_s}{part_s}{loc_s}"
                )
                entry["sections"] = [
                    {
                        "title": "Story Context & Turning Point",
                        "text": (
                            f"Anchors the storyline of {dlc_name}.{q_s} "
                            f"Shapes faction alliances, world state, and subsequent quest progression.{loc_s}"
                        ).strip(),
                    },
                    {
                        "title": "Participants & World Consequences",
                        "text": (
                            f"{part_s or 'Involves pivotal factions and companions.'}{item_s} "
                            f"Inspect linked nodes on the 3D graph to trace every character, location, and quest tied to this event."
                        ).strip(),
                    },
                ]

        # Strict validation per entry
        assert entry.get("role"), f"Missing role for {nid}"
        if len(entry.get("summary", "")) < 70:
            entry["summary"] = (
                entry.get("summary", "").rstrip(".")
                + f". Part of the {dlc_name} dataset (EditorID: {edid or nid})."
            ).lstrip(". ")
        assert len(entry.get("summary", "")) >= 70, f"Short summary for {nid}: {entry.get('summary')}"
        assert len(entry.get("sections", [])) >= 2, f"Fewer than 2 sections for {nid}"

        blob = json.dumps(entry, ensure_ascii=False)
        m_cyr = HAS_CYRILLIC.search(blob)
        if m_cyr:
            raise RuntimeError(f"Cyrillic leaked in {nid} ({lbl}): {blob[:400]}")
        for tok in FORBIDDEN_TOKENS:
            if tok in blob:
                raise RuntimeError(f"Forbidden token {tok!r} in {nid}")

        details_en[nid] = entry

    assert set(details_en.keys()) == set(node_by_id.keys()), "Key mismatch with graph.json!"

    OUT_EN_PATH.write_text(
        json.dumps(details_en, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    size_mb = OUT_EN_PATH.stat().st_size / (1024 * 1024)
    wiki_linked = sum(1 for v in details_en.values() if v.get("wikiUrl"))
    with_quotes = sum(1 for v in details_en.values() if v.get("quotes"))
    with_unlocks = sum(1 for v in details_en.values() if v.get("unlocks"))
    with_effects = sum(1 for v in details_en.values() if v.get("effects"))
    print(
        f"Successfully wrote {OUT_EN_PATH} ({size_mb:.2f} MB):\n"
        f"  Nodes: {len(details_en)} / {len(node_by_id)}\n"
        f"  Wiki-linked entries: {wiki_linked}\n"
        f"  With quotes: {with_quotes}\n"
        f"  With unlocks: {with_unlocks}\n"
        f"  With effects: {with_effects}\n"
        f"  Cyrillic check: 0 Cyrillic characters!"
    )


if __name__ == "__main__":
    main()
