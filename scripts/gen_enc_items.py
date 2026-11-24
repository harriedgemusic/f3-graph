#!/usr/bin/env python3
"""
Generate complete Russian Fallout 3 Encyclopedia entries for all 1,059 `item`
nodes in public/data/graph.json into /tmp/f3_encyclopedia/parts/items.json.
"""

from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path("/Users/harriedgemusic/Documents/repos/f3-graph")
GRAPH_PATH = REPO_ROOT / "public" / "data" / "graph.json"
DETAILS_PATH = REPO_ROOT / "public" / "data" / "details.json"
WALKTHROUGHS_PATH = REPO_ROOT / "public" / "data" / "walkthroughs.json"
ESM_RICH_PATH = Path("/tmp/f3_encyclopedia/esm_rich.json")
WIKI_RU_PATH = Path("/tmp/f3_encyclopedia/wiki_ru.json")
OUT_PATH = Path("/tmp/f3_encyclopedia/parts/items.json")

DLC_NAMES_RU: dict[str, str] = {
    "base": "базовая игра Fallout 3",
    "anchorage": "дополнение Operation: Anchorage",
    "pitt": "дополнение The Pitt",
    "brokensteel": "дополнение Broken Steel",
    "pointlookout": "дополнение Point Lookout",
    "zeta": "дополнение Mothership Zeta",
}

DLC_GEN_RU: dict[str, str] = {
    "base": "базовой игры Fallout 3",
    "anchorage": "дополнения Operation: Anchorage",
    "pitt": "дополнения The Pitt",
    "brokensteel": "дополнения Broken Steel",
    "pointlookout": "дополнения Point Lookout",
    "zeta": "дополнения Mothership Zeta",
}

DLC_DAT_RU: dict[str, str] = {
    "base": "базовой игре Fallout 3",
    "anchorage": "дополнению Operation: Anchorage",
    "pitt": "дополнению The Pitt",
    "brokensteel": "дополнению Broken Steel",
    "pointlookout": "дополнению Point Lookout",
    "zeta": "дополнению Mothership Zeta",
}

DLC_SHORT_RU: dict[str, str] = {
    "base": "Fallout 3",
    "anchorage": "Operation: Anchorage",
    "pitt": "The Pitt",
    "brokensteel": "Broken Steel",
    "pointlookout": "Point Lookout",
    "zeta": "Mothership Zeta",
}

TEST_CELLS = {
    "granttestworld",
    "test cell",
    "test tony",
    "test01raiders",
    "dlc04testphil",
    "захороненные склады",
}

TEST_NPCS = {
    "dlc01testhiulaimc",
    "dlc05testnpc",
    "testperson",
    "testperson03",
}

LOC_OVERRIDES: dict[str, str] = {
    "Cargo Hold": "Грузовой отсек (Mothership Zeta)",
    "Hangar": "Ангар (Mothership Zeta)",
    "DC09b": "Руины округа Колумбия",
    "DC21a": "Руины округа Колумбия",
    "DC23b": "Руины округа Колумбия",
    "DCStreet02": "Улицы округа Колумбия",
}

NPC_OVERRIDES: dict[str, str] = {
    "Butch": "Буч",
    "Charon": "Харон",
    "Clover": "Кловер",
    "Daniel Agincourt": "Дэниел Аджинкорт",
    "Rivet City Security": "охранник Ривет-Сити",
    "Slaver": "работорговец",
    "Underworld Resident": "житель Подземелья",
}

QUEST_TITLE_MAP: dict[str, str] = {
    "FreeformDC": "Свободные события в руинах Вашингтона",
    "DLC02FF": "Дополнительные события Operation: Anchorage",
    "FollowersHireButch": "Найм Буча в напарники",
    "FollowersHireCharon": "Найм Харона в напарники",
    "FollowersHireClover": "Найм Кловер в напарники",
    "FollowersHireJericho": "Найм Джерико в напарники",
    "FollowersHireRL3": "Найм робота РЛ-3 в напарники",
    "FreeformMegaton": "Поручения жителей Мегатонны",
    "MS15Museum": "Авраам Вашингтон — покупатель",
    "MQ09": "Американская мечта",
    "DLC04FF03": "Бальзам на душу",
    "DLC04FF05": "Бархатный занавес",
    "DLC04FF04": "Беспризорник Кенни",
    "MS01": "Большие проблемы в Большом Городе",
    "CG03": "Будущее в тумане",
    "CG02": "Быстрое взросление",
    "DLC03WQ02": "Великолепная лечебная вода!",
    "DLC01Quest02": "Вредные условия труда",
    "MS06": "Глава государства",
    "MQ03": "Гонка преследования",
    "MQ05": "Живая вода",
    "MQ11": "Забери его!",
    "PerkLawbringer": "Законник",
    "DLC03WQ01": "Защита караванов",
    "MS08": "Искусственный человек",
    "MS14": "Контрольный выстрел",
    "DLC03BS3": "Кто смел, тот побеждает",
    "DLC04MQ01": "Местные нравы",
    "DLC04MQ04": "Мысли под контролем",
    "PerkContractKiller": "Наёмный убийца",
    "DLC01FFLD": "Найти Билла-Дикаря",
    "MS06LincolnArtifacts": "Наследие Линкольна",
    "DLC05MZ1": "Не из этого мира",
    "MS02": "Нечеловеческий гамбит",
    "MS10": "Оазис",
    "MS04": "Они!",
    "DLC02OA2": "Орудия Анкориджа",
    "MS17": "Песнь Агаты",
    "DLC03BS2": "Плата за электричество",
    "CG04": "Побег!",
    "MS05": "Погоня за ядер-колой",
    "DLC02OA3": "Подготовка наступления",
    "MQ08": "Поиски Эдемских кущ",
    "DLC02OA1": "Помощь Изгоям",
    "MS16": "Проблемы на домашнем фронте",
    "DLC04MQ02": "Прогулка с духами",
    "DLC01Quest01": "Проникнуть в Питт",
    "MS13": "Просто бизнес",
    "MQ02": "Радио «Новости Галактики»",
    "MS18": "Рейнджеры Рейли",
    "MS03": "Руководство по выживанию на Пустошах",
    "DLC04FF06": "Сафари Плика",
    "DLC01Quest03": "Свободный труд",
    "DLC03WQ03": "Святая вода",
    "MS11": "Сила Атома",
    "MQ01": "След в след",
    "DLC03BS1": "Смерть с небес",
    "MQ07": "Спасение из рая",
    "DLC05MZ2": "Среди звёзд",
    "DLC04FF01": "Страны далёкие",
    "DLC04MQ05b": "Схватка интеллектов",
    "DLC04FF02": "Тёмная душа Блэкхолла",
    "MS12": "Тенпенни-Тауэр",
    "MQ04": "Трэнквилити-Лейн",
    "MS09": "Узы крови",
    "MS15": "Украденная независимость",
    "DLC04MQ03": "Шепчущие голоса",
    "DLC05MZ3": "Эта галактика не столь велика…",
}

GENERIC_LOC_LABELS = {
    "офис",
    "подвал",
    "резиденция командования",
    "запечатанная цистерна",
    "научная лаборатория",
    "верхняя палуба",
    "средняя палуба",
    "лестница",
    "жилые помещения",
    "склад",
    "казармы",
    "оружейная",
}

IGNORED_WIKI_HEADINGS = {
    "fallout: new vegas",
    "fallout new vegas",
    "fallout 2",
    "fallout 4",
    "fallout 76",
    "fallout tactics",
    "fallout",
    "fallout shelter",
    "появление",
    "галерея",
    "звуки",
    "за кулисами",
    "разновидности",
    "уникальные варианты",
    "уникальные версии",
    "другие варианты",
    "варианты",
    "варианты комбинезона",
    "варианты головного убора",
    "виды",
    "баги",
}

COMPOSITE_NOTE_WIKIS = {
    "Голодиски искусственного человека",
    "Личный журнал Хайме",
    "Семейный архив Келлеров",
    "Журнал проекта «Чистота»",
    "Исследование почвы. Запись",
    "Дневник Джейсона Гранта",
    "Дневник Керри Дилэни",
}

CRAFTING_RECIPES: dict[str, tuple[str, list[str], str]] = {
    "SchematicsBottlecapMineItem": (
        "Крышко-мина",
        ["Ланчбокс", "Петарда", "Сенсорный модуль", "Бутылочная крышка (10 шт.)"],
        "один из самых мощных взрывных зарядов Пустошей, способный одним срабатыванием уничтожить даже когтя смерти",
    ),
    "SchematicsDartGunItem": (
        "Дротикомёт",
        [
            "Пульверизатор",
            "Резиновый хирургический жгут",
            "Игрушечная машинка",
            "Ядовитая железа радскорпиона",
        ],
        "бесшумное оружие для стрельбы отравленными дротиками, мгновенно калечащее ноги цели и замедляющее даже самых опасных противников",
    ),
    "SchematicsDeathclawGauntletItem": (
        "Перчатка когтя смерти",
        ["Чудо-клей", "Кожаный ремень", "Медицинская шина", "Лапа когтя смерти"],
        "смертоносное рукопашное оружие, полностью игнорирующее сопротивляемость урону (СУ) брони противника",
    ),
    "SchematicsNukaCocktailItem": (
        "Молотов-кола",
        [
            "Квантовая ядер-кола",
            "Жестяная банка",
            "Скипидар",
            "Чистящее средство «Абраксо»",
        ],
        "мощная самодельная граната с ослепляющей синей вспышкой и экстремальным уроном по площади",
    ),
    "SchematicsRailwayRifleItem": (
        "Железнодорожная винтовка",
        ["Костыль", "Манометр", "Ядерная батарея", "Скороварка"],
        "пневматическая паровая винтовка, стреляющая железнодорожными костылями с высоким шансом критического удара и пригвождением конечностей",
    ),
    "SchematicsRockItLauncherItem": (
        "Ракетка",
        ["Пылесос", "Листодув", "Насадка пожарного шланга", "Проводник"],
        "тяжёлая пневматическая пушка, позволяющая заряжать и выстреливать любые весомые предметы из категории «Разное»",
    ),
    "SchematicsShishkebabItem": (
        "Шиш-кебаб",
        [
            "Бензобак от мотоцикла",
            "Ручной тормоз от мотоцикла",
            "Лезвие газонокосилки",
            "Запальник",
        ],
        "огненный меч ближнего боя с лучшим показателем урона в секунду среди холодного оружия и дополнительным горением, усиливаемый перком «Пироман»",
    ),
}

COMPONENT_RECIPES: dict[str, list[str]] = {
    "Lunchbox": ["Крышко-мина"],
    "CherryBomb": ["Крышко-мина"],
    "SensorModule": ["Крышко-мина"],
    "Caps001": ["Крышко-мина"],
    "PaintGun": ["Дротикомёт"],
    "SurgicalTubing": ["Дротикомёт"],
    "ToyCar": ["Дротикомёт"],
    "RadscorpionPoisonGland": ["Дротикомёт"],
    "WonderGlue": ["Перчатка когтя смерти"],
    "LeatherBelt": ["Перчатка когтя смерти"],
    "MedicalBrace": ["Перчатка когтя смерти"],
    "MedicalBraceNew": ["Перчатка когтя смерти"],
    "DeathclawHand": ["Перчатка когтя смерти"],
    "TinCan01": ["Молотов-кола"],
    "Turpentine": ["Молотов-кола"],
    "AbraxoCleaner": ["Молотов-кола"],
    "Crutch": ["Железнодорожная винтовка"],
    "SteamGaugeAssembly": ["Железнодорожная винтовка"],
    "FissionBattery": ["Железнодорожная винтовка"],
    "PressureCooker": ["Железнодорожная винтовка"],
    "VacuumCleaner": ["Ракетка"],
    "LeafBlower": ["Ракетка"],
    "FirehoseNozzle": ["Ракетка"],
    "Conductor": ["Ракетка"],
    "MotorcycleGasTank": ["Шиш-кебаб"],
    "MotorcycleHandbrake": ["Шиш-кебаб"],
    "LawnmowerBlade": ["Шиш-кебаб"],
    "PilotLight": ["Шиш-кебаб"],
}

BOBBLEHEAD_EFFECTS: dict[str, tuple[str, str]] = {
    "BobbleheadSTR": ("Сила", "+1 к параметру «Сила» навсегда"),
    "BobbleheadPER": ("Восприятие", "+1 к параметру «Восприятие» навсегда"),
    "BobbleheadEND": ("Выносливость", "+1 к параметру «Выносливость» навсегда"),
    "BobbleheadCHA": ("Харизма", "+1 к параметру «Харизма» навсегда"),
    "BobbleheadINT": ("Интеллект", "+1 к параметру «Интеллект» навсегда"),
    "BobbleheadAGL": ("Ловкость", "+1 к параметру «Ловкость» навсегда"),
    "BobbleheadLUK": ("Удача", "+1 к параметру «Удача» навсегда"),
    "BobbleheadBART": ("Бартер", "+10 к навыку «Бартер» навсегда"),
    "BobbleheadBGUN": ("Тяжёлое оружие", "+10 к навыку «Тяжёлое оружие» навсегда"),
    "BobbleheadERGW": ("Энергетическое оружие", "+10 к навыку «Энергетическое оружие» навсегда"),
    "BobbleheadEXPL": ("Взрывчатка", "+10 к навыку «Взрывчатка» навсегда"),
    "BobbleheadLOCK": ("Взлом", "+10 к навыку «Взлом» навсегда"),
    "BobbleheadMEDI": ("Медицина", "+10 к навыку «Медицина» навсегда"),
    "BobbleheadMELE": ("Холодное оружие", "+10 к навыку «Холодное оружие» навсегда"),
    "BobbleheadREPR": ("Ремонт", "+10 к навыку «Ремонт» навсегда"),
    "BobbleheadSCNC": ("Наука", "+10 к навыку «Наука» навсегда"),
    "BobbleheadSGUN": ("Лёгкое оружие", "+10 к навыку «Лёгкое оружие» навсегда"),
    "BobbleheadSNEK": ("Скрытность", "+10 к навыку «Скрытность» навсегда"),
    "BobbleheadSPCH": ("Красноречие", "+10 к навыку «Красноречие» навсегда"),
    "BobbleheadUARM": ("Без оружия", "+10 к навыку «Без оружия» навсегда"),
}

MISC_SPECIAL_LORE: dict[str, tuple[str, str, str]] = {
    "PreWarBook": (
        "Коллекционная довоенная литература",
        "Уцелевший том довоенной литературы, представляющий особую историческую ценность для Братства Стали и скупаемый по фиксированной высокой цене.",
        "В отличие от обгоревших и испорченных книг, нетронутые довоенные экземпляры можно продавать писцу Йерлинг в Арлингтонской библиотеке по 100 крышек за штуку с получением опыта (причём цена выкупа не зависит от навыка «Бартер»).",
    ),
    "SpareParts": (
        "Ремонтный ресурс и квестовый товар",
        "Универсальный технический ресурс Столичной Пустоши, востребованный инженерами поселений и Изгоями Братства Стали.",
        "Металлолом принимает Уолтер на водоочистной станции Мегатонны (после починки труб он платит 10 крышек за единицу и даёт карму с опытом), а также хранитель Касдин в форте Индепенденс в рамках сборов Изгоев; кроме того, металлолом можно продать торговцам или сдать в Питте.",
    ),
    "FissionBattery": (
        "Компонент верстака и квестовый ресурс",
        "Тяжёлый довоенный энергетический элемент питания, пригодный для сборки самодельного оружия и обмена с Изгоями Братства Стали.",
        "Ядерные батареи необходимы для создания «Железнодорожной винтовки» на верстаке по схеме, а также входят в список высокотехнологичных трофеев, которые можно сдать хранителю Касдину в форте Индепенденс в обмен на стимуляторы, рад-X, антирадин и боеприпасы.",
    ),
    "SensorModule": (
        "Компонент верстака и технологический трофей",
        "Компактный довоенный сенсорный узел, используемый в самодельной взрывчатке и принимаемый техниками Изгоев Братства Стали.",
        "Сенсорный модуль является обязательной деталью при сборке «Крышко-мины» на верстаке и также принимается хранителем Касдином в форте Индепенденс по программе «Изгои Братства».",
    ),
    "TeddyBear01": (
        "Памятная игрушка и квестовый предмет (The Pitt)",
        "Сохранившаяся довоенная мягкая игрушка, встречающаяся в жилых кварталах, детских комнатах и тайниках по всей Столичной Пустоши.",
        "В дополнении The Pitt плюшевых мишек можно приносить Милли для утешения маленькой Мари и получения денежного вознаграждения; на базовой Пустоши они служат декоративным трофеем для дома или лёгким снарядом для «Ракетки».",
    ),
    "PrewarMoney": (
        "Невесомая валюта и предмет обмена",
        "Пачки довоенных бумажных долларов США, утративших платёжную силу, но охотно выкупаемых торговцами и довоенными автоматами.",
        "Благодаря нулевому весу и базовой цене 10 крышек довоенные деньги фактически выступают невесомым финансовым резервом, который удобно накапливать и обменивать у любых торговцев без нагрузки на инвентарь.",
    ),
    "CigaretteCarton": (
        "Высоколиквидный товар для бартера",
        "Запечатанный блок довоенных сигарет — один из самых выгодных по соотношению цены и веса обменных товаров на Столичной Пустоши.",
        "При весе всего 2 фунта блок оценивается в 50 крышек, что делает его удобной «крупной купюрой» при обмене у караванщиков и городских торговцев.",
    ),
    "CigarettePack": (
        "Компактный бартерный товар",
        "Уцелевшая пачка довоенных сигарет, ценящаяся на Столичной Пустоши как дефицитный обменный ресурс.",
        "При малом весе (0,5 фунта) и стоимости 10 крышек пачки сигарет выгодно собирать для доплаты при бартере, а также использовать как сверхлёгкие снаряды.",
    ),
    "Lockpick": (
        "Универсальный инструмент взлома",
        "Обычная металлическая заколка — единственный в игре инструмент для механического вскрытия запертых дверей, сейфов и ящиков.",
        "При каждой неудачной попытке взлома в мини-игре заколка может сломаться от неаккуратного поворота отвёртки; при наличии нужного навыка «Взлом» (25/50/75/100) достаточно иметь в инвентаре хотя бы одну заколку.",
    ),
    "MS10Liniment": (
        "Квестовый артефакт Оазиса",
        "Особая мазь, приготовленная друидами Оазиса для ритуального воздействия на сердце Гарольда в финале одноимённого задания.",
        "Используется в квесте «Оазис»: если Одинокий Путник решит применить мазь Берёзы к сердцу Гарольда в Затопленных пещерах, рост дерева ускорится и Оазис начнёт стремительно разрастаться по Столичной Пустоши.",
    ),
    "MS10TestTubeFull": (
        "Квестовый артефакт Оазиса",
        "Флакон со специальным составом, созданным Лавром для прекращения разрастания Гарольда в квесте «Оазис».",
        "Применяется в ходе квеста «Оазис» на сердце Гарольда в пещерах, если игрок поддерживает позицию Лавра и хочет остановить распространение зелени за пределы рощи.",
    ),
    "FollowersCharonContract": (
        "Квестовый документ найма спутника",
        "Юридический контракт на службу гуля-телохранителя Харона, которым владеет трактирщик Азрухал в баре «Девятый круг» Подземелья.",
        "Чтобы нанять Харона в спутники, Одинокому Путнику необходимо либо выкупить этот контракт у Азрухала в «Девятом круге» (за 2000 или 1000 крышек при проверке навыка), либо выполнить поручение по устранению Греты.",
    ),
    "MS13CollarMiscObj": (
        "Квестовое снаряжение работорговцев",
        "Взрывной рабский ошейник с дистанционным детонатором, выдаваемый Гробовщиком Джонсом в Парадиз-Фоллз для охоты на цели.",
        "Используется в задании «Просто бизнес» для поимки и отправки в рабство целей из списка (Сьюзен Ланкастер, Флак, Красный, Арканзас): после оглушения жертвы гипнотроном на неё надевается ошейник.",
    ),
    "DLC05ButtercupToy": (
        "Уникальная коллекционная игрушка (Mothership Zeta)",
        "Редкая довоенная механическая лошадка «Лютик», оказавшаяся на борту инопланетного корабля Дзета среди похищенных образцов земной культуры.",
        "Одинокий Путник может найти несколько экземпляров на корабле пришельцев; при возвращении на Землю игрушку можно выгодно продать (базовая стоимость 150 крышек) или украсить ею дом в Мегатонне или люкс в Тенпенни-Тауэр.",
    ),
    "DLC05AlienCrystalLarge": (
        "Высокоценный инопланетный трофей",
        "Крупный кристаллический образец неизвестного происхождения, обнаруженный в отсеках корабля пришельцев Дзета (Mothership Zeta).",
        "Не требуется напрямую для квестов, но имеет солидную стоимость продажи (20 крышек) и позволяет выгодно обменять лишний груз у торговцев после завершения дополнения Mothership Zeta.",
    ),
    "DLC05AlienCrystalSmall": (
        "Невесомый инопланетный трофей",
        "Компактный фрагмент кристаллической породы Чужих, собранный на борту материнского корабля Дзета (Mothership Zeta).",
        "Благодаря нулевому весу малые кристаллы (по 10 крышек за штуку) можно собирать в любых количествах и продавать торговцам без малейшего перегруза.",
    ),
    "DLC02Charges": (
        "Квестовая взрывчатка симуляции (Operation: Anchorage)",
        "Специальные диверсионные заряды для подрыва артиллерийских орудий и топливных хранилищ в виртуальной симуляции освобождения Анкориджа.",
        "Применяются исключительно по ходу сюжетных заданий внутри виртуальной симуляции Анкориджа для саботажа китайских укреплений и артиллерийских батарей.",
    ),
    "DLC01MideaNoteItem": (
        "Сюжетное послание (The Pitt)",
        "Тайная записка от Вернера, адресованная Медее и передаваемая через Одинокого Путника в начале проникновения в Питт.",
        "Ключевой связной предмет для продвижения по сюжетной ветке The Pitt при контакте с подпольем рабов в Даунтауне.",
    ),
    "BrassLanternPasswordAdder": (
        "Записка с подсказкой (Мегатонна)",
        "Смятый листок бумаги, связанный с обстановкой закусочной «Латунный фонарь» в Мегатонне.",
        "При подборе передаёт игроку служебную информацию, используемую для взаимодействия с терминалом или тайником «Латунного фонаря».",
    ),
    "MS08Note": (
        "Служебная голографическая запись квеста",
        "Информационная голозапись, фигурирующая в расследовании обстоятельств побега андроида из Содружества.",
        "Хранится в игровых ресурсах квеста «Искусственный человек» и дополняет цепочку улик вокруг доктора Зиммера и таинственного беглеца в Ривет-Сити.",
    ),
    "xMS03survivalGuideBookItem": (
        "Альтернативный экземпляр книги",
        "Технический вариант «Руководства по выживанию на пустошах» в категории «Разное», сопутствующий итоговому изданию Мойры Браун.",
        "В финальной игре игрок получает итоговое пособие по завершении квеста Мойры Браун и может встретить путешественников, обсуждающих его в случайных встречах.",
    ),
}

HTML_TAG_RE = re.compile(r"</?[a-zA-Z!][^>]*>")
SEE_GALLERY_RE = re.compile(
    r"\s*\((?:см\.?\s*(?:«?галере[юя]»?|«?баг[и]?»?|ниже|выше|след\.\s*заметку))\)",
    re.I,
)
WS_RE = re.compile(r"[ \t]+")
NON_F3_SENT_RE = re.compile(
    r"(Fallout:?\s*New\s*Vegas|New\s*Vegas|Fallout\s*4|Fallout\s*76|Fallout\s*Shelter|Fallout\s*Tactics|Fallout\s*2|Creation\s*Club|Automatron|Old\s*World\s*Blues|Honest\s*Hearts|Lonesome\s*Road|Dead\s*Money|Classic\s*Pack|Мохав\w*|\bКурьер\w*|Выходец из Убежища)",
    re.I,
)


def clean_display_name(label: str) -> str:
    """Normalize straight quotes in an item/location name and strip outer quotes."""
    s = label.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("«") and s.endswith("»")):
        if len(s) > 2:
            s = s[1:-1].strip()
    if '"' in s:
        s = re.sub(r'"([^"]+)"', r"„\1“", s)
    if "«" in s or "»" in s:
        s = re.sub(r"«([^»]+)»", r"„\1“", s)
    s = s.replace("&PCName;", "[имя Путника]")
    return s


def quote_ru(label: str) -> str:
    """Wrap a Russian title in guillemets «...» while turning any inner quotes into „...“."""
    return f"«{clean_display_name(label)}»"


def strip_raw_markup(text: str) -> str:
    """Aggressively strip HTML tags, entities, and stray wikitext markers."""
    if not text:
        return ""
    s = html.unescape(text)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("(<Ложь>)", "(проверка «Лжи»)")
    s = HTML_TAG_RE.sub(" ", s)
    s = SEE_GALLERY_RE.sub("", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = s.replace("{{", "").replace("}}", "").replace("[[", "").replace("]]", "")
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S | re.I)
    s = re.sub(r"<ref[^>]*/?>", "", s, flags=re.I)
    # Fix common wiki double-period after acronyms like V.A.T.S.. or англ..32
    s = re.sub(r"\bV\.A\.T\.S\.\.+", "V.A.T.S.", s)
    s = re.sub(r"\bангл\.\.(\d)", r"англ. .\1", s)
    s = s.replace("относится к категории «»", "относится к категории «Без оружия»")
    s = s.replace("«Третейский судья;", "«Третейский судья»;")
    # Clean leftover wiki technical ID template remnants
    s = s.replace("уникальную версию патронов с Base ID.", "уникальную неиссякаемую версию патронов.")
    s = re.sub(r"модель с base ID\s*—\s*", "базовая модель — ", s, flags=re.I)
    s = re.sub(r"включая base ID\s*—\s*", "включая базовую модель — ", s, flags=re.I)
    s = re.sub(r"модель с base ID\b", "базовая модель", s, flags=re.I)
    s = re.sub(r"\s*\((?:base[ _]id|Editor_ID)\s*=?\s*[0-9a-fA-F]+\)", "", s, flags=re.I)
    s = re.sub(r"Имеет Editor_ID\s+(\w+)", r"Имеет внутренний идентификатор \1", s, flags=re.I)
    # Replace nested quotes inside «...» with proper Russian „...“
    s = re.sub(r'«([^»]*?)"([^»"]+?)"([^»]*?)»', r"«\1„\2“\3»", s)
    s = re.sub(r"«([^«»]*?)«([^«»]+?)»([^«»]*?)»", r"«\1„\2“\3»", s)
    s = re.sub(r"«\s*«([^»]+)»\s*»", r"«\1»", s)
    s = re.sub(r"(?<!\.)\.\.(?!\.)", ".", s)
    s = WS_RE.sub(" ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def clean_note_text(text: str) -> str:
    """Clean ESM NOTE/BOOK text and substitute runtime &PC*; tokens."""
    s = strip_raw_markup(text)
    s = s.replace("&PCName;", "[имя Путника]")
    s = s.replace("&PCRace;", "[раса]")
    s = s.replace("&PCSex;", "[пол]")
    return s.strip()


OTHER_GAME_LINE_RE = re.compile(
    r"^(?:Fallout(?::?\s*New Vegas|\s*2|\s*4|\s*76|\s*Tactics|\s*Shelter|\s*1))\s*:",
    re.I,
)
FO3_SUBHEADER_RE = re.compile(
    r"^(?:Fallout\s*3|Operation:\s*Anchorage|The\s*Pitt|Broken\s*Steel|Point\s*Lookout|Mothership\s*Zeta)\s*:$",
    re.I,
)


def clean_lead_games(s: str) -> str:
    """Strip other-game mentions from Fallout Wiki article leads."""
    s = re.sub(
        r"в Point Lookout,\s*дополнении к Fallout 3,\s*и Fallout:\s*New Vegas",
        "в дополнении Point Lookout к Fallout 3",
        s,
        flags=re.I,
    )
    s = re.sub(
        r"разновидность одежды наёмников Fallout 3 и лёгкой брони Fallout:\s*New Vegas",
        "разновидность одежды наёмников в Fallout 3",
        s,
        flags=re.I,
    )
    s = re.sub(
        r"(?:в\s+)?Fallout,\s*Fallout Tactics,\s*Fallout 3,\s*Fallout:\s*New Vegas,\s*Fallout 4\s*и\s*Fallout 76",
        "в Fallout 3",
        s,
        flags=re.I,
    )
    s = re.sub(
        r"Fallout 3,\s*Fallout:\s*New Vegas и других игр серии Fallout",
        "в Fallout 3",
        s,
        flags=re.I,
    )
    s = re.sub(
        r",\s*и Ошейник раба\s*—\s*броня Fallout:\s*New Vegas",
        "",
        s,
        flags=re.I,
    )
    s = re.sub(
        r"(?:;\s*|,\s*|\s+и\s+)(?:уникальный\s+головной\s+убор|вырезанный\s+контент|вырезанная\s+еда|медпрепарат|химикат)\s+(?:в\s+)?Fallout:\s*New Vegas",
        "",
        s,
        flags=re.I,
    )
    s = re.sub(
        r"(?:в\s+)?Fallout 3\s+и\s+(?:в\s+)?Fallout:?\s*New Vegas",
        "в Fallout 3",
        s,
        flags=re.I,
    )
    s = re.sub(
        r"уникальная лёгкая броня Fallout:\s*New Vegas",
        "вырезанный уникальный защитный костюм в файлах Fallout 3",
        s,
        flags=re.I,
    )
    sents = re.split(r"(?<=[.!?])\s+", s)
    sents = [st for st in sents if not NON_F3_SENT_RE.search(st)]
    return " ".join(sents).strip()


def sanitize_f3_prose(s: str) -> str:
    """Remove non-Fallout-3 game sentences and inline Mojave/FNV mentions from wiki prose."""
    s = re.sub(
        r"как на просторах Мохавской и Столичной Пустошей",
        "как на просторах Столичной Пустоши",
        s,
        flags=re.I,
    )
    s = re.sub(
        r"во многих местах Столичной и Мохавской Пустошей",
        "во многих местах Столичной Пустоши",
        s,
        flags=re.I,
    )
    s = re.sub(
        r"на Мохавской и Столичной Пустошах",
        "на Столичной Пустоши",
        s,
        flags=re.I,
    )
    s = re.sub(
        r"самым тяжёлым предметом Fallout 3 и Fallout:\s*New Vegas",
        "самым тяжёлым предметом в Fallout 3",
        s,
        flags=re.I,
    )
    s = re.sub(r"\s*\(за исключением табачной жвачки в Fallout:\s*New Vegas\)", "", s, flags=re.I)
    s = re.sub(r"\s*и встречается значительно реже,\s*чем в Fallout:\s*New Vegas", "", s, flags=re.I)
    s = re.sub(r"Одинокий Путник и Курьер присоединятся", "Одинокий Путник присоединится", s, flags=re.I)
    s = re.sub(r"\s*\(а также на его аналоге в Fallout:\s*New Vegas.*?\)\)", "", s, flags=re.I)
    s = re.sub(r"\s*Из Fallout:?\s*New Vegas:.*$", "", s, flags=re.I | re.M)

    out_lines: list[str] = []
    for line in s.splitlines():
        line_s = line.strip()
        if not line_s:
            if out_lines and out_lines[-1] != "":
                out_lines.append("")
            continue
        if line_s.startswith("— ") or line_s.startswith("• "):
            if NON_F3_SENT_RE.search(line_s):
                continue
            out_lines.append(line_s)
        else:
            sents = re.split(r"(?<=[.!?])\s+", line_s)
            kept = [st for st in sents if not NON_F3_SENT_RE.search(st)]
            if kept:
                out_lines.append(" ".join(kept))
    return "\n".join(out_lines).strip()


def clean_wiki_prose(text: str, max_chars: int = 1100, is_quest_sec: bool = False) -> str:
    """Clean a Fallout Wiki section into fluent Fallout 3 Russian prose without other-game leaks."""
    if not text:
        return ""
    s = strip_raw_markup(text)
    lines: list[str] = []
    skip_other_game = False
    for raw_line in s.splitlines():
        line = raw_line.strip()
        if OTHER_GAME_LINE_RE.match(line):
            skip_other_game = True
            continue
        if FO3_SUBHEADER_RE.match(line):
            skip_other_game = False
            continue
        if skip_other_game:
            continue
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if line in {"• Персонажи", "Персонажи:", "Персонажи"}:
            continue
        if line.startswith("• ") and " • " in line[2:]:
            line = line[2:].strip()
        if " • " in line and not line.startswith("•"):
            left, right = line.split(" • ", 1)
            left_clean = left.strip().strip("«»\"")
            right_clean = right.strip()
            if right_clean:
                line = f"В квесте {quote_ru(left_clean)}: {right_clean}"
            else:
                line = f"Связан с квестом {quote_ru(left_clean)}."
        elif line.startswith("• ") and "•" not in line[2:]:
            item_txt = line[2:].strip()
            if is_quest_sec and item_txt.startswith("«") and item_txt.endswith("»"):
                line = f"Связан с квестом {quote_ru(item_txt)}."
            else:
                line = f"— {item_txt}"
        lines.append(line)

    cleaned = sanitize_f3_prose("\n".join(lines).strip())
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"(?<!\.)\.\.(?!\.)", ".", cleaned)
    if len(cleaned) <= max_chars:
        return cleaned

    paragraphs = cleaned.split("\n\n")
    acc: list[str] = []
    total = 0
    for p in paragraphs:
        if total + len(p) + (2 if acc else 0) <= max_chars:
            acc.append(p)
            total += len(p) + (2 if acc else 0)
        else:
            if not acc:
                sents = re.split(r"(?<=[.!?])\s+", p)
                sent_acc: list[str] = []
                stotal = 0
                for sent in sents:
                    if stotal + len(sent) + 1 <= max_chars:
                        sent_acc.append(sent)
                        stotal += len(sent) + 1
                    else:
                        break
                if sent_acc:
                    acc.append(" ".join(sent_acc))
            break
    result = "\n\n".join(acc).strip()
    return result if result else cleaned[:max_chars].rsplit(" ", 1)[0].rstrip(",;:") + "."


def clean_quest_title(edid: str, label: str) -> str:
    """Return clean Title Case Russian quest name."""
    if edid in QUEST_TITLE_MAP:
        return QUEST_TITLE_MAP[edid]
    if label.isupper() and len(label) > 3:
        return label.capitalize()
    return clean_display_name(label)


def format_list_ru(items: list[str], limit: int = 10, more_word: str = "других") -> str:
    """Format a Russian list naturally without dangling numbers or punctuation."""
    uniq: list[str] = []
    seen: set[str] = set()
    for it in items:
        it_clean = it.strip()
        if it_clean and it_clean not in seen:
            seen.add(it_clean)
            uniq.append(it_clean)
    if not uniq:
        return ""
    head = uniq[:limit]
    if len(uniq) > limit:
        return ", ".join(head) + f" и ещё {len(uniq) - limit} {more_word}"
    if len(head) == 1:
        return head[0]
    return ", ".join(head[:-1]) + " и " + head[-1]


def fmt_num(val: float | int) -> str:
    """Format floats cleanly without noisy .0."""
    if isinstance(val, int):
        return str(val)
    if abs(val - round(val)) < 1e-6:
        return str(int(round(val)))
    return f"{val:.2f}".rstrip("0").rstrip(".")


def fmt_spread(min_s: float, max_s: float) -> str:
    """Format weapon min/max spread cleanly."""
    if abs(min_s - max_s) < 1e-6:
        return fmt_num(min_s)
    return f"{fmt_num(min_s)}–{fmt_num(max_s)}"


def plural_caps(n: int) -> str:
    """Russian declension for Bottle Caps."""
    n_abs = abs(n)
    if 11 <= n_abs % 100 <= 19:
        return f"{n} крышек"
    last = n_abs % 10
    if last == 1:
        return f"{n} крышка"
    if 2 <= last <= 4:
        return f"{n} крышки"
    return f"{n} крышек"


@dataclass
class ItemContext:
    node: dict[str, Any]
    esm: dict[str, Any]
    details: dict[str, Any]
    wiki: dict[str, Any] | None
    quests: list[str]
    npcs: list[str]
    locations: list[str]
    objects: list[str]
    events: list[str]
    placements: list[str]
    carriers: list[str]
    unlocks_raw: list[dict[str, str]]
    unlocks_clean: list[str]
    is_cut: bool
    is_sim: bool
    is_unique: bool
    wiki_url: str
    source_tag: str

    def wiki_sec(self, *names: str) -> str:
        if not self.wiki:
            return ""
        name_low = {n.lower() for n in names}
        for s in self.wiki.get("sections", []):
            h = (s.get("heading") or "").strip().lower()
            if h in IGNORED_WIKI_HEADINGS:
                continue
            if h in name_low:
                is_q = h in {"квесты", "связанные квесты"}
                return clean_wiki_prose(s.get("text", ""), is_quest_sec=is_q)
        return ""

    def wiki_lead_clean(self) -> str:
        if not self.wiki:
            return ""
        lead = strip_raw_markup(self.wiki.get("lead") or "")
        if not lead:
            return ""
        parts = [p.strip() for p in lead.split("\n\n") if p.strip()]
        if len(parts) > 1 and parts[0].startswith("«"):
            if len(parts[1]) >= 40:
                return clean_lead_games(" ".join(parts[1:]))
        return clean_lead_games(" ".join(parts))


def build_contexts(
    graph: dict[str, Any],
    details: dict[str, Any],
    walkthroughs: list[dict[str, Any]],
    esm_rich: dict[str, Any],
    wiki_ru: dict[str, Any],
) -> tuple[dict[str, ItemContext], dict[str, list[str]]]:
    """Assemble enriched ItemContext for all 1,059 items plus ammo-to-weapons index."""
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    wt_by_quest_node = {
        w["nodeId"]: clean_quest_title(w.get("edid", ""), w["title"])
        for w in walkthroughs
        if w.get("nodeId")
    }
    wt_by_item: dict[str, list[str]] = defaultdict(list)
    for w in walkthroughs:
        qname = clean_quest_title(w.get("edid", ""), w["title"])
        for iid in w.get("linkedEntities", {}).get("items", []):
            if qname not in wt_by_item[iid]:
                wt_by_item[iid].append(qname)

    loc_display_cache: dict[str, str] = {}
    loc_neighbors: dict[str, list[str]] = defaultdict(list)
    for e in graph["edges"]:
        if e["type"] == "location_connection":
            s_node = nodes_by_id.get(e["source"])
            t_node = nodes_by_id.get(e["target"])
            if s_node and t_node:
                loc_neighbors[s_node["id"]].append(t_node["label"])
                loc_neighbors[t_node["id"]].append(s_node["label"])

    def resolve_loc_node(loc_id: str) -> str | None:
        if loc_id in loc_display_cache:
            return loc_display_cache[loc_id]
        ln = nodes_by_id.get(loc_id)
        if not ln:
            return None
        lbl = LOC_OVERRIDES.get(ln["label"], ln["label"]).strip()
        if lbl.lower() in TEST_CELLS or lbl.lower().startswith("test"):
            return None
        lbl = clean_display_name(lbl)
        if lbl.lower() in GENERIC_LOC_LABELS:
            le = esm_rich.get(loc_id, {})
            ws = (le.get("worldspace") or "").strip()
            if ws and ws not in {"Внутренняя локация", lbl} and ws.lower() not in TEST_CELLS:
                lbl = f"{lbl} ({clean_display_name(ws)})"
            else:
                doors = [clean_display_name(d) for d in le.get("doorsTo", []) if d and d != lbl]
                if not doors:
                    doors = [clean_display_name(d) for d in loc_neighbors.get(loc_id, []) if d and d != lbl]
                if doors:
                    lbl = f"{lbl} ({doors[0]})"
        loc_display_cache[loc_id] = lbl
        return lbl

    edges_by_item: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    item_ids = {n["id"] for n in graph["nodes"] if n["type"] == "item"}
    for e in graph["edges"]:
        s, t = e["source"], e["target"]
        if s in item_ids and t in nodes_by_id:
            edges_by_item[s].append((e["type"], nodes_by_id[t]))
        if t in item_ids and s in nodes_by_id:
            edges_by_item[t].append((e["type"], nodes_by_id[s]))

    ammo_to_weapons: dict[str, list[str]] = defaultdict(list)
    for n in graph["nodes"]:
        if n["type"] == "item" and n["subtype"] == "weapon":
            e = esm_rich.get(n["id"], {})
            aname = (e.get("ammo") or "").strip()
            if aname:
                wname = clean_display_name(n["label"])
                if wname not in ammo_to_weapons[aname]:
                    ammo_to_weapons[aname].append(wname)

    contexts: dict[str, ItemContext] = {}
    for n in graph["nodes"]:
        if n["type"] != "item":
            continue
        nid = n["id"]
        e = esm_rich.get(nid, {})
        d = details.get(nid, {})
        w = wiki_ru.get(nid)

        quests: list[str] = []
        npcs: list[str] = []
        locations: list[str] = []
        objects: list[str] = []
        events: list[str] = []

        for _, other in edges_by_item.get(nid, []):
            otype = other["type"]
            olbl = other["label"].strip()
            if otype == "quest":
                qtitle = wt_by_quest_node.get(other["id"], clean_quest_title(other.get("edid", ""), olbl))
                if qtitle not in quests:
                    quests.append(qtitle)
            elif otype == "character":
                if olbl.lower() in TEST_NPCS:
                    continue
                olbl = clean_display_name(NPC_OVERRIDES.get(olbl, olbl))
                if olbl not in npcs:
                    npcs.append(olbl)
            elif otype == "location":
                resolved = resolve_loc_node(other["id"])
                if resolved and resolved not in locations:
                    locations.append(resolved)
            elif otype == "object":
                olbl_clean = clean_display_name(olbl)
                if olbl_clean not in objects:
                    objects.append(olbl_clean)
            elif otype == "event":
                ev_clean = clean_display_name(olbl)
                if ev_clean not in events:
                    events.append(ev_clean)

        for qtitle in wt_by_item.get(nid, []):
            if qtitle not in quests:
                quests.append(qtitle)

        placements: list[str] = []
        for p in e.get("placements", []):
            p_clean = clean_display_name(LOC_OVERRIDES.get(p, p).strip())
            if not p_clean or p_clean.lower() in TEST_CELLS or p_clean.lower().startswith("test"):
                continue
            matched_rich = next(
                (loc for loc in locations if loc == p_clean or loc.startswith(f"{p_clean} (")),
                None,
            )
            final_p = matched_rich or p_clean
            if final_p not in placements:
                placements.append(final_p)
        for loc in locations:
            if loc not in placements:
                placements.append(loc)

        raw_carriers = e.get("carriers", e.get("wearers", []))
        carriers: list[str] = []
        for c in raw_carriers:
            c_clean = clean_display_name(NPC_OVERRIDES.get(c, c).strip())
            if not c_clean or c_clean.lower() in TEST_NPCS or c_clean.lower().startswith("test"):
                continue
            if c_clean not in carriers:
                carriers.append(c_clean)
        for npc in npcs:
            if npc not in carriers:
                carriers.append(npc)

        unlocks_raw: list[dict[str, str]] = []
        unlocks_clean: list[str] = []
        seen_unlock_str: set[str] = set()
        for u in e.get("unlocks", []):
            tgt = clean_display_name((u.get("target") or "").strip())
            loc_raw = (u.get("location") or "").strip()
            loc = clean_display_name(LOC_OVERRIDES.get(loc_raw, loc_raw))
            diff = (u.get("lockDiff") or "").strip()
            if tgt.startswith("VendorChestBuried") or loc.lower() in TEST_CELLS:
                continue
            unlocks_raw.append(
                {
                    "target": tgt,
                    "location": loc,
                    "lockDiff": diff,
                    "targetType": u.get("targetType", ""),
                }
            )
            u_str = f"{tgt} ({loc})" if loc else tgt
            if u_str not in seen_unlock_str:
                seen_unlock_str.add(u_str)
                unlocks_clean.append(u_str)

        cats = [c.lower() for c in (w.get("categories") or [])] if w else []
        edid = n["edid"]
        is_cut = (
            any("вырезан" in c or "недопущен" in c for c in cats)
            or (w and "вырезан" in (w.get("lead") or "").lower())
            or (
                edid.startswith(("ArmorUnique", "OutfitUnique", "UniqueArmor"))
                and not placements
                and not carriers
                and not quests
            )
            or edid in {"DLC04GhoulEcologyBook", "DLC04MirelurkEcologyBook"}
        )
        is_sim = edid in {
            "DLC02WeapGaussRifle",
            "DLC02WeapShockSword",
            "DLC02WeapAssaultRifle",
            "DLC02WeapMontgomeryAssaultRifle",
            "DLC02Weap10mmPistolSilenced",
            "DLC02WeapMinigun",
            "DLC02WeapFlamer",
            "DLC02WeapKnifeCombat",
            "DLC02ArmorPowerT51b",
            "DLC02ArmorPowerT51bHelmet",
            "DLC02ArmorCombatSnowHelmet",
            "DLC02ArmorChineseHelmet",
            "DLC02ArmorStealthHelmet",
            "DLC02ArmorCombatSnow",
        }
        is_unique = (
            "Unique" in edid
            or any("уникальн" in c for c in cats)
            or n["label"].startswith('"')
        )
        wiki_url = w.get("wikiUrl", "") if w else ""
        source_tag = "esm+wiki" if w else "esm"

        contexts[nid] = ItemContext(
            node=n,
            esm=e,
            details=d,
            wiki=w,
            quests=quests,
            npcs=npcs,
            locations=locations,
            objects=objects,
            events=events,
            placements=placements,
            carriers=carriers,
            unlocks_raw=unlocks_raw,
            unlocks_clean=unlocks_clean,
            is_cut=bool(is_cut),
            is_sim=bool(is_sim),
            is_unique=bool(is_unique),
            wiki_url=wiki_url,
            source_tag=source_tag,
        )

    return contexts, ammo_to_weapons


def common_where_text(
    ctx: ItemContext,
    noun_acc: str = "предмет",
    is_wearer: bool = False,
    include_wiki_quests: bool = True,
) -> str:
    """Build factual acquisition/location prose combining Wiki, ESM placements, carriers, and quests."""
    parts: list[str] = []
    w_loc = ctx.wiki_sec("Местонахождение", "Местоположение", "Местонахождения", "Получение")
    w_quest = ctx.wiki_sec("Квесты", "Связанные квесты") if include_wiki_quests else ""
    w_craft = ctx.wiki_sec("Изготовление")

    if w_craft:
        parts.append(w_craft)
    if w_loc:
        parts.append(w_loc)
    if w_quest and w_quest != w_loc:
        parts.append(w_quest)

    if ctx.placements:
        pl_str = format_list_ru(ctx.placements, limit=8, more_word="других мест")
        if not w_loc:
            parts.append(
                f"По данным игровых архивов {noun_acc} можно обнаружить в следующих точках ({DLC_SHORT_RU[ctx.node['dlc']]}): {pl_str}."
            )
        elif len(ctx.placements) >= 2:
            parts.append(f"Среди зафиксированных в мире точек обнаружения: {pl_str}.")

    if ctx.carriers:
        ca_str = format_list_ru(ctx.carriers, limit=8, more_word="других персонажей")
        if is_wearer:
            parts.append(f"Экипировку носят и используют следующие персонажи: {ca_str}.")
        else:
            parts.append(f"Встречается в инвентаре и экипировке персонажей: {ca_str}.")

    if ctx.quests and not w_quest:
        q_str = format_list_ru([quote_ru(q) for q in ctx.quests], limit=6, more_word="других заданий")
        parts.append(f"Непосредственно задействован при прохождении заданий: {q_str}.")

    if ctx.events:
        ev_str = format_list_ru([quote_ru(ev) for ev in ctx.events], limit=4, more_word="других событий")
        parts.append(f"Пересекается с ключевыми событиями Столичной Пустоши: {ev_str}.")

    if ctx.is_sim and not w_loc:
        parts.append(
            "Данный экземпляр относится к виртуальной симуляции освобождения Анкориджа (Operation: Anchorage) "
            "и используется внутри программы; на Столичной Пустоши после прохождения симуляции "
            "доступен отдельный реальный аналог в арсенале аванпоста Изгоев."
        )
    elif ctx.is_cut:
        if not parts:
            parts.append(
                f"Экземпляр относится к вырезанному контенту ({DLC_GEN_RU[ctx.node['dlc']]}) и не размещён в доступных локациях или у персонажей. "
                "В обычном прохождении предмет недоступен и выдаётся исключительно консольной командой."
            )
        elif sum(len(p) for p in parts) < 95:
            parts.append(
                f"Так как предмет относится к вырезанному контенту {DLC_GEN_RU[ctx.node['dlc']]}, легально в мире игры он не появляется."
            )
    elif not parts:
        parts.append(
            f"Предмет относится к {DLC_DAT_RU[ctx.node['dlc']]} и выдаётся по ходу скриптов, торговых списков "
            "или специальных игровых сцен, не имея постоянной открытой выкладки на карте."
        )
    elif sum(len(p) for p in parts) < 85:
        parts.append(
            f"Относится к {DLC_DAT_RU[ctx.node['dlc']]}; при посещении указанной точки стоит осмотреть контейнеры, столы и инвентарь охраны."
        )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Subtype Builders
# ---------------------------------------------------------------------------


def build_weapon(ctx: ItemContext) -> dict[str, Any]:
    n, e = ctx.node, ctx.esm
    name = clean_display_name(n["label"])
    edid = n["edid"]
    wclass = e.get("weaponClass") or "Оружие"
    skill = e.get("skill") or "Боевой навык"
    dmg = e.get("damage", 0)
    hp = e.get("health", 0)
    val = e.get("value", 0)
    wt = e.get("weight", 0.0)
    clip = e.get("clipSize", 0)
    fr = e.get("fireRate", 0.0)
    ap = e.get("apCost", 0.0)
    min_s = e.get("minSpread", 0.0)
    max_s = e.get("maxSpread", 0.0)
    crit_d = e.get("critDamage", 0)
    crit_m = e.get("critMult", 0.0)
    ammo = (e.get("ammo") or "").strip()
    effects = e.get("effects", [])
    spread_str = fmt_spread(min_s, max_s)

    is_melee_or_unarmed = skill in {"Холодное оружие", "Без оружия"}
    is_explosive = skill == "Взрывчатка" and not ammo

    extra_role = ""
    extra_lead = ""
    extra_where = ""
    extra_tactic = ""
    if n["id"] == "itm_0006b538":  # Eugene
        extra_role = "Уникальное тяжёлое оружие (миниган)"
        extra_lead = (
            "«Юджин» (англ. Eugene) — уникальный миниган наёмницы Кирпич из отряда «Рейнджеры Рейли», "
            "обладающий увеличенным базовым уроном (7 ед. за выстрел против 5 у стандартной модели) и повышенной прочностью."
        )
        extra_where = (
            "Принадлежит Кирпичу и задействован в квесте «Рейнджеры Рейли» (в отеле «Стейтсмен» можно передать Кирпичу 150 патронов 5 мм для обороны). "
            "После спасения отряда «Юджин» можно выбрать в качестве награды у Рейли, либо подобрать с тела Кирпича в случае её гибели."
        )
        extra_tactic = (
            "Среди пулемётов калибра 5 мм «Юджин» отличается высоким DPS (140 ед./с при темпе стрельбы 20 выстр./с) и ремонтопригодностью "
            "за счёт обычных миниганов. Лучше всего проявляет себя на ближней и средней дистанции при стрельбе в реальном времени."
        )
    elif edid == "FollowersCharonShotgunScene":
        extra_role = "Персональный боевой дробовик напарника (Харон)"
        extra_lead = (
            "Личный боевой дробовик гуля-наёмника Харона — особая версия с исключительно кучной стрельбой и модификатором «Эффект дробовика Харона», "
            "превращающим дробовик в дальнобойное оружие."
        )
    elif edid == "FollowersButch10mmPistol":
        extra_role = "Персональный 10-мм пистолет напарника (Буч)"
        extra_lead = "Личный 10-мм пистолет Буча Делории, которым он пользуется в качестве напарника Одинокого Путника."
    elif edid == "FollowersFawkesGatlingLaser":
        extra_role = "Персональный гатлинг-лазер напарника (Фокс)"
        extra_lead = "Штатный гатлинг-лазер супермутанта Фокса с повышенным уроном (9 ед.) и высокой прочностью для подавления плотных групп врагов."
    elif edid == "MQ04RollingPin":
        extra_role = "Квестовое холодное оружие симуляции (Трэнквилити-Лейн)"
        extra_lead = "Особая скалка из виртуальной симуляции «Трэнквилити-Лейн», наносящая 20 ед. урона (вместо 3 у обычной) для выполнения поручения Бетти."
    elif edid == "CG02WeapBBGun":
        extra_role = "Учебное пневматическое ружьё (Убежище 101)"
        extra_lead = "Пневматическое ружьё, которое Джонас и отец дарят герою на десятилетие в Убежище 101 для первой стрельбы по мишени и радтараканам."
    elif edid == "DLC01WernherWeap44MagnumScoped":
        extra_role = "Персональный револьвер Вернера (The Pitt)"
        extra_lead = "Штатный «Магнум» кал. 44 с оптическим прицелом, которым вооружён лидер подполья Вернер в дополнении The Pitt."
    elif edid == "DLC02WeapMontgomeryAssaultRifle":
        extra_role = "Штурмовая винтовка сержанта Монтгомери (симуляция)"
        extra_lead = "Особый вариант штурмовой винтовки командира ударной группы сержанта Бенджамина Монтгомери внутри симуляции освобождения Анкориджа."

    if extra_role:
        role = extra_role
    elif ctx.is_cut:
        role = f"Вырезанное {'уникальное ' if ctx.is_unique else ''}оружие ({wclass.lower()})"
    elif ctx.is_sim:
        role = f"Оружие симуляции Operation: Anchorage ({wclass.lower()})"
    elif ctx.is_unique:
        role = f"Уникальное оружие навыка «{skill}» ({wclass.lower()})"
    else:
        role = f"Оружие навыка «{skill}» ({wclass.lower()})"

    lead_w = ctx.wiki_lead_clean()
    if extra_lead:
        s1 = extra_lead
    elif lead_w:
        s1 = lead_w
    else:
        s1 = f"«{name}» — {role.lower()} из {DLC_GEN_RU[n['dlc']]}."

    if ammo:
        s2 = (
            f"При базовом уроне {dmg} ед., использовании боеприпасов «{clean_display_name(ammo)}» (магазин на {clip}) "
            f"и расходе {fmt_num(ap)} ОД в V.A.T.S. оно опирается на навык «{skill}»."
        )
    else:
        s2 = (
            f"Наносит {dmg} ед. базового урона при расходе {fmt_num(ap)} ОД в режиме V.A.T.S. "
            f"и масштабируется от навыка «{skill}»."
        )
    summary = f"{s1} {s2}".strip()
    if len(summary) < 120:
        summary += f" Запас прочности составляет {hp} ед., масса — {fmt_num(wt)} фнт, базовая цена — {plural_caps(val)}."

    sec1_parts: list[str] = []
    if ammo:
        sec1_parts.append(
            f"Оружие относится к классу «{wclass}» (навык «{skill}») и питается боеприпасами «{clean_display_name(ammo)}» с ёмкостью магазина {clip}. "
            f"Базовый урон — {dmg} ед., темп огня — {fmt_num(fr)} выстр./с, разброс — {spread_str}, "
            f"стоимость выстрела в V.A.T.S. — {fmt_num(ap)} ОД. Критический удар добавляет +{crit_d} ед. урона "
            f"при множителе шанса крита ×{fmt_num(crit_m)}; запас прочности равен {hp} ед., вес — {fmt_num(wt)} фнт, цена — {plural_caps(val)}."
        )
    elif is_explosive:
        sec1_parts.append(
            f"Оружие относится к классу «{wclass}» (навык «{skill}») и не требует сменных патронов, расходуясь поштучно. "
            f"Базовый урон взрыва — {dmg} ед., стоимость применения в V.A.T.S. — {fmt_num(ap)} ОД, "
            f"бонус критического урона — +{crit_d} ед. (множитель ×{fmt_num(crit_m)}). Вес единицы — {fmt_num(wt)} фнт, цена — {plural_caps(val)}."
        )
    else:
        sec1_parts.append(
            f"Оружие ближнего действия класса «{wclass}» (навык «{skill}») наносит {dmg} ед. базового урона "
            f"при скорости ударов {fmt_num(fr)}/с и расходе {fmt_num(ap)} ОД в V.A.T.S. "
            f"Дополнительный критический урон составляет +{crit_d} ед. при множителе шанса ×{fmt_num(crit_m)}; "
            f"прочность — {hp} ед., масса — {fmt_num(wt)} фнт, стоимость — {plural_caps(val)}."
        )
    if effects:
        sec1_parts.append(f"Особые эффекты при попадании: {format_list_ru(effects)}.")
    w_desc = ctx.wiki_sec("Описание")
    w_stats = ctx.wiki_sec("Характеристики")
    if w_desc:
        sec1_parts.append(w_desc)
    if w_stats and w_stats != w_desc:
        sec1_parts.append(w_stats)

    sec2 = extra_where if extra_where else common_where_text(ctx, "оружие")
    if extra_where and ctx.carriers:
        sec2 += f"\n\nВ игровых данных также отмечен у персонажа: {format_list_ru(ctx.carriers)}."

    sec3_parts: list[str] = []
    if extra_tactic:
        sec3_parts.append(extra_tactic)
    else:
        dps = dmg * fr
        tac_notes: list[str] = []
        if ammo:
            if max_s <= 0.5:
                tac_notes.append(
                    f"Низкий разброс ({spread_str}) позволяет уверенно вести прицельный огонь на средней и дальней дистанции, "
                    "выцеливая уязвимые зоны вроде головы или оружия врага."
                )
            elif max_s >= 2.5:
                tac_notes.append(
                    f"Заметный разброс ({spread_str}) ограничивает эффективную дальность ближней и средне-ближней дистанцией, "
                    "где плотность огня компенсирует рассеивание."
                )
            else:
                tac_notes.append(
                    f"Умеренный разброс ({spread_str}) делает это оружие сбалансированным для боёв на коротких и средних дистанциях."
                )
            if ap <= 22:
                tac_notes.append(
                    f"Умеренная цена выстрела в V.A.T.S. ({fmt_num(ap)} ОД) позволяет выполнить несколько прицельных атак за одну очередь."
                )
            elif ap >= 35:
                tac_notes.append(
                    f"Высокая стоимость выстрела в V.A.T.S. ({fmt_num(ap)} ОД) требует тщательного выбора момента или ведения огня в реальном времени."
                )
        elif is_melee_or_unarmed:
            tac_notes.append(
                f"Живучесть в ближнем бою обеспечивается показателем прочности {hp} ед. и стоимостью удара {fmt_num(ap)} ОД в V.A.T.S. "
                f"(при скорости {fmt_num(fr)} уд./с расчётный урон в секунду достигает ~{fmt_num(dps)} ед.)."
            )
            if skill == "Без оружия":
                tac_notes.append("Урон дополнительно повышается способностями «Железный кулак» и «Стальной кулак» (после прохождения The Pitt).")
            else:
                tac_notes.append("Одинокий Путник с высоким параметром «Сила» и способностью «Ниндзя» раскрывает максимальный потенциал сближения и скрытных атак.")
        else:
            tac_notes.append(
                f"Боевой урон {dmg} ед. при усилении способностью «Эксперт-сапёр» позволяет быстро пробивать группы плотных целей и технику."
            )

        if crit_m >= 2.0 or crit_d >= 30:
            tac_notes.append(
                f"Повышенный критический профиль (+{crit_d} урона, множитель ×{fmt_num(crit_m)}) отлично сочетается с «Удачей», «Точностью» и «Критическим уроном»."
            )
        if 800 <= hp < 90000:
            tac_notes.append(f"Высокий запас прочности ({hp} ед.) снижает зависимость от частого ремонта в затяжных рейдах.")
        elif 0 < hp <= 150 and not is_explosive:
            tac_notes.append(f"Относительно невысокая прочность ({hp} ед.) требует регулярно носить запасные аналоги для ремонта или пользоваться услугами торговцев.")

        sec3_parts.append(" ".join(tac_notes))

    w_repair = ctx.wiki_sec("Ремонт")
    w_notes = ctx.wiki_sec("Заметки", "Примечание", "Особенности")
    if w_repair:
        sec3_parts.append(w_repair)
    if w_notes:
        sec3_parts.append(w_notes)

    source_tag = "esm+curated" if (extra_lead and not ctx.wiki) else ctx.source_tag
    entry: dict[str, Any] = {
        "id": n["id"],
        "role": role,
        "summary": summary,
        "sections": [
            {"title": "Стрельба и боевые особенности", "text": "\n\n".join(sec1_parts)},
            {"title": "Где найти и у кого встречается", "text": sec2},
            {"title": "Применение и тактика", "text": "\n\n".join(sec3_parts)},
        ],
        "value": val,
        "weight": wt,
        "health": hp,
        "damage": dmg,
        "clipSize": clip,
        "weaponClass": wclass,
        "skill": skill,
        "fireRate": fr,
        "apCost": ap,
        "spread": spread_str,
        "critDamage": crit_d,
        "critMult": crit_m,
        "ammo": ammo,
        "effects": effects,
        "sourceTag": source_tag,
    }
    if ctx.wiki_url:
        entry["wikiUrl"] = ctx.wiki_url
    return entry


def classify_armor(ctx: ItemContext) -> tuple[str, bool, bool]:
    """Return (category_ru, is_headgear, is_power_armor) from label, icon, and DR."""
    lbl = ctx.node["label"].lower()
    icon = (ctx.node.get("icon") or "").lower()
    dr = ctx.esm.get("dr", 0.0)
    is_head = any(
        kw in lbl
        for kw in (
            "шлем",
            "маска",
            "очки",
            "головной убор",
            "капюшон",
            "шляпа",
            "кепка",
            "берет",
            "повязка",
            "парик",
            "хвостики",
            "пирошлем",
            "корона",
            "бандана",
            "колпак",
            "фуражка",
            "цилиндр",
            "каска",
            "стелс-шлем",
        )
    ) or any(kw in icon for kw in ("helmet", "hat", "coif", "glasses", "mask", "wig", "head"))
    is_pa = (
        any(
            kw in lbl
            for kw in (
                "силовая",
                "силовой",
                "тесла",
                "геенна",
                "медброня",
                "робо-тор",
                "штурмовика анклава",
            )
        )
        or (not is_head and dr >= 35)
    )
    if is_head and is_pa:
        return ("шлем силовой брони", True, True)
    if is_head:
        return ("головной убор / защитный элемент", True, False)
    if is_pa:
        return ("силовая броня", False, True)
    if dr >= 18:
        return ("средняя или тяжёлая броня", False, False)
    if dr >= 8:
        return ("лёгкая боевая экипировка", False, False)
    return ("повседневная одежда или костюм", False, False)


def build_armor(ctx: ItemContext) -> dict[str, Any]:
    n, e = ctx.node, ctx.esm
    name = clean_display_name(n["label"])
    dr = e.get("dr", 0.0)
    hp = e.get("health", 0)
    wt = e.get("weight", 0.0)
    val = e.get("value", 0)
    effects = e.get("effects", [])
    cat_ru, is_head, is_pa = classify_armor(ctx)

    if ctx.is_cut:
        role = f"Вырезанный уникальный элемент ({cat_ru})" if ctx.is_unique else f"Вырезанная экипировка ({cat_ru})"
    elif ctx.is_sim:
        role = f"Экипировка симуляции Operation: Anchorage ({cat_ru})"
    elif ctx.is_unique:
        role = f"Уникальный предмет: {cat_ru}"
    else:
        role = f"Защитная экипировка ({cat_ru})"

    lead_w = ctx.wiki_lead_clean()
    if lead_w:
        if is_head and "головн" not in lead_w.lower() and "шлем" not in lead_w.lower() and "маск" not in lead_w.lower():
            s1 = f"«{name}» — {cat_ru} из комплекта, описанного в статье «{clean_display_name(ctx.wiki['wikiTitle'])}»."
        else:
            s1 = lead_w
    else:
        if ctx.is_cut:
            s1 = f"«{name}» — {cat_ru}, сохранившийся в файлах {DLC_GEN_RU[n['dlc']]}, но вырезанный из финальной версии игры."
        else:
            s1 = f"«{name}» — {cat_ru} из {DLC_GEN_RU[n['dlc']]}."

    eff_txt = f" и даёт бонусы ({format_list_ru(effects)})" if effects else ""
    s2 = f"Обеспечивает сопротивляемость урону (СУ) {fmt_num(dr)} ед.{eff_txt} при запасе прочности {hp} ед. и массе {fmt_num(wt)} фнт."
    summary = f"{s1} {s2}".strip()
    if len(summary) < 120:
        summary += f" Базовая рыночная стоимость предмета составляет {plural_caps(val)}."

    sec1_parts: list[str] = [
        f"Предмет обеспечивает показатель сопротивляемости урону (СУ) {fmt_num(dr)} ед. при прочности {hp} ед., "
        f"массе {fmt_num(wt)} фнт и базовой стоимости {plural_caps(val)}."
    ]
    if effects:
        sec1_parts.append(f"Постоянные бонусы и модификаторы при ношении: {format_list_ru(effects)}.")
    else:
        sec1_parts.append("Дополнительных модификаторов к характеристикам S.P.E.C.I.A.L. или навыкам этот предмет не даёт.")

    if is_pa and not is_head:
        sec1_parts.append(
            "Для ношения силовой брони в большинстве случаев требуется способность «Ношение силовой брони», "
            "которую выдаёт паладин Ганни в Цитадели после получения разрешения или после завершения симуляции Operation: Anchorage."
        )
    elif is_head:
        sec1_parts.append(
            "Занимает слот головного убора; лёгкие маски и очки нередко сочетаются с другими элементами, тогда как закрытые шлемы занимают всю голову."
        )

    w_desc = ctx.wiki_sec("Описание", "Характеристики", "Характеристика")
    w_notes = ctx.wiki_sec("Заметки", "Примечание", "Ремонт")
    if w_desc:
        sec1_parts.append(w_desc)
    if w_notes and w_notes != w_desc:
        sec1_parts.append(w_notes)

    sec2 = common_where_text(ctx, "снаряжение", is_wearer=True)

    entry: dict[str, Any] = {
        "id": n["id"],
        "role": role,
        "summary": summary,
        "sections": [
            {"title": "Защита и свойства", "text": "\n\n".join(sec1_parts)},
            {"title": "Где добыть и кто носит", "text": sec2},
        ],
        "value": val,
        "weight": wt,
        "health": hp,
        "dr": dr,
        "effects": effects,
        "sourceTag": ctx.source_tag,
    }
    if ctx.wiki_url:
        entry["wikiUrl"] = ctx.wiki_url
    return entry


def build_aid(ctx: ItemContext) -> dict[str, Any]:
    n, e = ctx.node, ctx.esm
    name = clean_display_name(n["label"])
    val = e.get("value", 0)
    wt = e.get("weight", 0.0)
    effects = e.get("effects", [])
    addict = e.get("addictionChance", 0.0)
    addict_pct = int(round(addict * 100))
    lbl_low = name.lower()

    if any(x in lbl_low for x in ("вино", "виски", "водка", "пиво", "самогон", "скотч")):
        role = "Алкогольный напиток (временное усиление Силы и Харизмы)"
    elif any(x in lbl_low for x in ("мясо", "пирог", "рулет", "панга")):
        role = "Пища / восстановительный припас Пустошей"
    elif "стелс-бой" in lbl_low:
        role = "Тактическое устройство оптической маскировки"
    elif "ядер-кол" in lbl_low:
        role = "Тонизирующий газированный напиток (Ядер-кола)"
    elif "стимулятор" in lbl_low or "рад-x" in lbl_low:
        role = "Базовый медицинский препарат"
    elif any(x in lbl_low for x in ("ментат", "винт", "психо", "баффаут", "мед-x")):
        role = "Боевой или интеллектуальный химический препарат"
    else:
        role = "Особый препарат / расходуемый предмет"

    lead_w = ctx.wiki_lead_clean()
    s1 = lead_w if lead_w else f"«{name}» — {role.lower()} из {DLC_GEN_RU[n['dlc']]}."
    eff_str = format_list_ru(effects) if effects else "особые ситуативные эффекты"
    add_str = f", но несёт риск привыкания ({addict_pct}%)" if addict_pct > 0 else " и не вызывает зависимости"
    s2 = f"При применении даёт следующие эффекты: {eff_str}{add_str}."
    summary = f"{s1} {s2}".strip()
    if len(summary) < 120:
        summary += f" Масса единицы составляет {fmt_num(wt)} фнт, базовая цена — {plural_caps(val)}."

    sec1_parts: list[str] = [
        f"Основные игровые эффекты при употреблении: {eff_str}. "
        f"Шанс развития химической или алкогольной зависимости: {addict_pct}% "
        f"({'при появлении ломки её можно вылечить у любого доктора на Пустоши или через домашний медотсек «Мой дом»' if addict_pct > 0 else 'зависимость не формируется'}). "
        f"Вес — {fmt_num(wt)} фнт, базовая стоимость — {plural_caps(val)}."
    ]
    for sec_name in ("Описание", "Эффекты", "Использование", "Применение"):
        txt = ctx.wiki_sec(sec_name)
        if txt and txt not in sec1_parts:
            sec1_parts.append(txt)

    sec2_parts = [common_where_text(ctx, "препарат")]
    w_notes = ctx.wiki_sec("Заметки", "Примечание")
    if w_notes:
        sec2_parts.append(w_notes)

    entry: dict[str, Any] = {
        "id": n["id"],
        "role": role,
        "summary": summary,
        "sections": [
            {"title": "Эффект и назначение", "text": "\n\n".join(sec1_parts)},
            {"title": "Где найти и как использовать", "text": "\n\n".join(sec2_parts)},
        ],
        "value": val,
        "weight": wt,
        "effects": effects,
        "addictionChance": addict,
        "sourceTag": ctx.source_tag,
    }
    if ctx.wiki_url:
        entry["wikiUrl"] = ctx.wiki_url
    return entry


def build_book(ctx: ItemContext) -> dict[str, Any]:
    n, e = ctx.node, ctx.esm
    name = clean_display_name(n["label"])
    edid = n["edid"]
    val = e.get("value", 0)
    wt = e.get("weight", 0.0)
    skill_taught = e.get("skillTaught") or ""
    effects = e.get("effects", [])
    raw_text = e.get("text") or ctx.details.get("text") or ""
    clean_txt = clean_note_text(raw_text)

    if edid == "BabyBookStatic":
        role = "Стартовая книга распределения параметров S.P.E.C.I.A.L."
    elif ctx.is_cut:
        role = f"Вырезанная книга эффектов ({DLC_SHORT_RU[n['dlc']]})"
    elif skill_taught:
        role = f"Обучающая книга навыка «{skill_taught}»"
    else:
        role = "Уникальное справочное или сюжетное издание"

    lead_w = ctx.wiki_lead_clean()
    s1 = lead_w if lead_w else f"«{name}» — {role.lower()} из {DLC_GEN_RU[n['dlc']]}."
    if skill_taught:
        s2 = f"Прочтение навсегда повышает навык «{skill_taught}» на 1 пункт (или на 2 пункта при взятой способности «Понимание»)."
    elif edid == "BabyBookStatic":
        s2 = "В прологе игры в Убежище 101 позволяет игроку впервые распределить 40 стартовых очков S.P.E.C.I.A.L. между семью базовыми характеристиками."
    elif ctx.is_cut:
        s2 = "В релизной версии Point Lookout книга была вырезана и заменена журналом Плика (квест с испытаниями)."
    else:
        s2 = "Связана с прохождением задания Мойры Браун «Руководство по выживанию на Пустошах» и подводит итог исследования Столичной Пустоши."
    summary = f"{s1} {s2}".strip()

    sec1_parts: list[str] = []
    if skill_taught:
        sec1_parts.append(
            f"Обучает навыку «{skill_taught}»: при чтении из раздела «Помощь» (или сразу при взятии, если выбрано) "
            f"повышает его навсегда на +1 (или на +2 при наличии способности 4-го уровня «Понимание» — Comprehension). "
            f"Масса книги — {fmt_num(wt)} фнт, базовая цена — {plural_caps(val)}."
        )
    else:
        sec1_parts.append(
            f"Не является стандартным учебником навыков; масса — {fmt_num(wt)} фнт, базовая оценка — {plural_caps(val)}."
        )
    for sec_name in ("Описание", "Игровой механизм", "Отзывы и критика"):
        txt = ctx.wiki_sec(sec_name)
        if txt and txt not in sec1_parts:
            sec1_parts.append(txt)

    sec2_parts: list[str] = []
    if skill_taught:
        sec2_parts.append(
            "Оптимальная тактика — откладывать чтение найденных учебных книг до получения способности «Понимание» (4-й уровень, Интеллект 4), "
            "чтобы удвоить прирост каждого экземпляра до +2 и сэкономить очки при повышении уровня."
        )
    sec2_parts.append(common_where_text(ctx, "книгу"))
    w_notes = ctx.wiki_sec("Заметки", "Заметка")
    if w_notes:
        sec2_parts.append(w_notes)

    entry: dict[str, Any] = {
        "id": n["id"],
        "role": role,
        "summary": summary,
        "sections": [
            {"title": "Эффект и назначение", "text": "\n\n".join(sec1_parts)},
            {"title": "Где найти и как использовать", "text": "\n\n".join(sec2_parts)},
        ],
        "value": val,
        "weight": wt,
        "skillTaught": skill_taught,
        "effects": effects,
        "sourceTag": ctx.source_tag,
    }
    if clean_txt:
        entry["text"] = clean_txt
    if ctx.wiki_url:
        entry["wikiUrl"] = ctx.wiki_url
    return entry


def build_ammo(ctx: ItemContext, ammo_to_weapons: dict[str, list[str]]) -> dict[str, Any]:
    n, e = ctx.node, ctx.esm
    name = clean_display_name(n["label"])
    val = e.get("value", 0)
    wt = e.get("weight", 0.0)
    speed = e.get("speed", 1.0)
    clip_rounds = e.get("clipRounds", 1)
    short_name = (e.get("shortName") or "").strip()
    compat_weapons = ammo_to_weapons.get(n["label"], [])

    if "заряд" in name.lower() or "батарея" in name.lower() or "аккумулятор" in name.lower():
        role = f"Энергетический или специальный боеприпас ({short_name or name})"
    elif "выстрел" in name.lower():
        role = "Тяжёлый тактический ядерный боеприпас"
    else:
        role = f"Огнестрельный боеприпас ({short_name or name})"

    lead_w = ctx.wiki_lead_clean()
    s1 = lead_w if lead_w else f"«{name}» — {role.lower()} в Fallout 3."
    compat_str = format_list_ru(compat_weapons, limit=8) if compat_weapons else "профильного оружия соответствующего калибра"
    s2 = (
        f"Используется для стрельбы из такого оружия, как {compat_str}; базовая цена одного выстрела — {plural_caps(val)}, "
        f"а в базовой игре боеприпасы имеют нулевой вес."
    )
    summary = f"{s1} {s2}".strip()

    sec1_parts: list[str] = [
        f"Сокращённое обозначение в интерфейсе — «{short_name or name}», условный размер пачки/обоймы в данных ESM — {clip_rounds} ед., "
        f"множитель скорости снаряда — {fmt_num(speed)}, базовая цена за единицу — {plural_caps(val)}, вес — {fmt_num(wt)} фнт."
    ]
    if compat_weapons:
        sec1_parts.append(f"Совместимое оружие в базе игры: {format_list_ru(compat_weapons, limit=15)}.")
    for sec_name in ("Описание", "Характеристика", "Характеристики"):
        txt = ctx.wiki_sec(sec_name)
        if txt and txt not in sec1_parts:
            sec1_parts.append(txt)

    sec2_parts = [common_where_text(ctx, "боеприпасы")]
    w_notes = ctx.wiki_sec("Заметки", "Примечание")
    if w_notes:
        sec2_parts.append(w_notes)

    entry: dict[str, Any] = {
        "id": n["id"],
        "role": role,
        "summary": summary,
        "sections": [
            {"title": "Эффект и назначение", "text": "\n\n".join(sec1_parts)},
            {"title": "Где найти и как использовать", "text": "\n\n".join(sec2_parts)},
        ],
        "value": val,
        "weight": wt,
        "speed": speed,
        "clipRounds": clip_rounds,
        "shortName": short_name,
        "sourceTag": ctx.source_tag,
    }
    if ctx.wiki_url:
        entry["wikiUrl"] = ctx.wiki_url
    return entry


def build_key(ctx: ItemContext) -> dict[str, Any]:
    n, e = ctx.node, ctx.esm
    name = clean_display_name(n["label"])
    lbl_low = name.lower()
    val = e.get("value", 0)
    wt = e.get("weight", 0.0)
    unlocks = ctx.unlocks_clean
    unlocks_raw = ctx.unlocks_raw

    if "шифр-ключ" in lbl_low or "карта" in lbl_low or "ключ-карта" in lbl_low:
        role = "Электронная ключ-карта / шифр-ключ доступа"
    elif any(k in lbl_low for k in ("сейф", "сундук", "тайник", "шкаф", "холодильник")):
        role = "Ключ от личного сейфа, шкафа или тайника"
    elif "оружейн" in lbl_low or "арсенал" in lbl_low:
        role = "Ключ от оружейного хранилища"
    elif any(k in lbl_low for k in ("комнат", "дом", "люкс", "кают")):
        role = "Ключ от жилых помещений и личных апартаментов"
    elif any(k in lbl_low for k in ("клиник", "аптек", "бар", "магазин", "витрин")):
        role = "Ключ от торгового заведения или клиники"
    else:
        role = "Служебный или сюжетный ключ доступа"

    if unlocks_raw:
        first_u = unlocks_raw[0]
        tgt_count = len(unlocks)
        locs = format_list_ru([u["location"] for u in unlocks_raw if u["location"]], limit=3)
        loc_clause = f" в локации {locs}" if locs else ""
        if tgt_count == 1:
            cnt_clause = f"объект {quote_ru(first_u['target'])}"
        elif 2 <= tgt_count % 10 <= 4 and not (11 <= tgt_count % 100 <= 19):
            cnt_clause = f"{tgt_count} запертых объекта"
        else:
            cnt_clause = f"{tgt_count} запертых объектов"
        s1 = f"{quote_ru(name)} — {role.lower()} из {DLC_GEN_RU[n['dlc']]}, открывающий {cnt_clause}{loc_clause}."
    else:
        s1 = f"{quote_ru(name)} — {role.lower()} из {DLC_GEN_RU[n['dlc']]}."

    where_bits: list[str] = []
    if ctx.carriers:
        where_bits.append(f"хранится в инвентаре персонажей ({format_list_ru(ctx.carriers, limit=3, more_word='других персонажей')})")
    elif ctx.placements:
        where_bits.append(f"находится в локации {format_list_ru(ctx.placements, limit=2, more_word='других мест')}")
    if ctx.quests:
        where_bits.append(f"связан с заданием {quote_ru(ctx.quests[0])}")
    if where_bits:
        s2 = "В игре " + " и ".join(where_bits) + "."
    else:
        s2 = "Не занимает полезный вес (0 фнт) и позволяет открывать соответствующие замки без траты заколок."

    summary = f"{s1} {s2}".strip()
    if len(summary) < 120:
        summary += " После попадания в связку ключей Пип-боя срабатывает автоматически при взаимодействии с замком."

    sec1_parts: list[str] = []
    if unlocks_raw:
        lines: list[str] = []
        for u in unlocks_raw[:15]:
            t_type = "дверь" if u["targetType"] == "door" else "контейнер/сейф"
            loc_part = f" — локация {quote_ru(u['location'])}" if u["location"] else ""
            diff_part = f" (исходная сложность замка: {u['lockDiff']})" if u["lockDiff"] else ""
            lines.append(f"• {u['target']} ({t_type}{loc_part}){diff_part}")
        if len(unlocks_raw) > 15:
            lines.append(f"• …и ещё {len(unlocks_raw) - 15} объектов.")
        sec1_parts.append("Данный ключ автоматически отпирает следующие объекты:\n" + "\n".join(lines))
        has_key_only = any("Требуется ключ" in u["lockDiff"] for u in unlocks_raw)
        if has_key_only:
            sec1_parts.append(
                "Как минимум часть замков имеет статус «Требуется ключ» — их принципиально невозможно взломать заколкой даже при навыке «Взлом» 100."
            )
        else:
            sec1_parts.append(
                "Наличие ключа позволяет пройти или открыть содержимое без прохождения мини-игры взлома и без риска сломать заколку."
            )
    else:
        assoc_parts: list[str] = []
        if ctx.objects:
            assoc_parts.append(f"связан с объектами: {format_list_ru(ctx.objects, limit=4)}")
        if ctx.carriers:
            assoc_parts.append(f"относится к помещениям и имуществу персонажей: {format_list_ru(ctx.carriers, limit=6, more_word='других персонажей')}")
        if ctx.locations:
            assoc_parts.append(f"зафиксирован в локации {format_list_ru(ctx.locations, limit=4, more_word='других мест')}")
        if ctx.events:
            assoc_parts.append(f"фигурирует в событии {quote_ru(ctx.events[0])}")
        sec1_parts.append(
            f"Ключ {quote_ru(name)} предназначен для доступа к одноимённым помещениям или торговым хранилищам; в данных мира "
            + (", ".join(assoc_parts) if assoc_parts else "он выступает служебным ключом владельца заведения")
            + ". В инвентаре помещается в связку ключей с нулевым весом."
        )

    if ctx.quests:
        sec1_parts.append(f"Упоминается в рамках заданий: {format_list_ru([quote_ru(q) for q in ctx.quests], limit=5)}.")

    sec2_parts: list[str] = []
    if ctx.carriers:
        sec2_parts.append(
            f"Ключ можно получить (украсть в режиме скрытности, получить по ходу диалога/квеста или забрать с тела) у следующих персонажей: "
            f"{format_list_ru(ctx.carriers, limit=10, more_word='других персонажей')}."
        )
    if ctx.placements:
        sec2_parts.append(
            f"Свободно лежащий экземпляр либо контейнер с ключом зафиксирован в локациях: {format_list_ru(ctx.placements, limit=8, more_word='других мест')}."
        )
    if not sec2_parts:
        if ctx.events:
            sec2_parts.append(
                f"Ключ привязан к поселению или событию {quote_ru(ctx.events[0])} и выдаётся при получении доступа либо хранится у владельца помещения."
            )
        else:
            sec2_parts.append(
                f"Ключ относится к ресурсам {DLC_GEN_RU[n['dlc']]} и доступен в рамках соответствующей сюжетной сцены или у профильного владельца."
            )

    return {
        "id": n["id"],
        "role": role,
        "summary": summary,
        "sections": [
            {"title": "Что открывает и назначение", "text": "\n\n".join(sec1_parts)},
            {"title": "Где получить ключ", "text": "\n\n".join(sec2_parts)},
        ],
        "value": val,
        "weight": wt,
        "unlocks": unlocks,
        "sourceTag": ctx.source_tag,
    }


def extract_note_preview(clean_txt: str) -> str:
    """Extract a meaningful 1–3 sentence preview up to ~170 chars without stopping on 3-char salutations."""
    sents = re.split(r"(?<=[.!?])\s+", clean_txt)
    acc: list[str] = []
    total = 0
    for s in sents:
        s = s.strip()
        if not s:
            continue
        if not acc:
            acc.append(s)
            total = len(s)
        elif total < 55 and total + len(s) + 1 <= 175:
            acc.append(s)
            total += len(s) + 1
        else:
            break
    out = " ".join(acc).strip()
    if len(out) > 175:
        out = out[:175].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return out


def build_note(ctx: ItemContext) -> dict[str, Any]:
    n, e = ctx.node, ctx.esm
    name = clean_display_name(n["label"])
    edid = n["edid"]
    val = e.get("value", 0)
    wt = e.get("weight", 0.0)
    note_type = e.get("noteType") or "Текстовая заметка"
    raw_text = e.get("text") or ctx.details.get("text") or ""
    clean_txt = clean_note_text(raw_text)

    custom_lead = ""
    custom_context = ""
    if edid.startswith("MS03SurvivalGuideText"):
        m = re.match(r"MS03SurvivalGuideText(\d+)([A-E])", edid)
        tier = m.group(1) if m else "?"
        tone_code = m.group(2) if m else "A"
        tone_map = {
            "A": "нейтральный и деловой тон ответов",
            "B": "резкий или саркастичный тон ответов",
            "C": "стойкий, ориентированный на выживание тон",
            "D": "рациональный и аналитический тон",
            "E": "хитрый и насмешливый тон",
        }
        role = f"Итоговая рецензия на «Руководство по выживанию» (уровень {tier}, вариант {tone_code})"
        custom_lead = (
            f"«{name}» — финальная персонализированная рецензия на «Руководство по выживанию на Пустошах» "
            f"(уровень качества {tier}/8, редакция «{tone_code}»), получаемая после завершения квеста Мойры Браун в Мегатонне."
        )
        custom_context = (
            f"Эта версия итогового отзыва формируется автоматически по завершении всех трёх глав квеста Мойры Браун: "
            f"выпуск уровня {tier}/8 отражает количество выполненных дополнительных задач, а редакция «{tone_code}» "
            f"соответствует преобладающему стилю реплик Одинокого Путника ({tone_map.get(tone_code, 'особый тон')})."
        )
    elif edid.startswith("Vault101Classroom"):
        role = "Учебная запись школьного терминала Убежища 101"
        custom_lead = (
            f"«{name}» — шуточная учебная запись из компьютерного класса Убежища 101, доступная перед сдачей экзамена К.О.З.А."
        )
        custom_context = (
            "Запись хранится в школьном терминале Убежища 101 и может быть загружена в Пип-бой Одинокого Путника "
            "во время прохождения вступительной сцены тестирования К.О.З.А. у мистера Бротча."
        )
    elif edid == "HitSquadNoteGoodGuys":
        role = "Контракт на устранение игрока («Коготь»)"
        custom_lead = (
            "«Контракт!» — боевой приказ на ликвидацию Одинокого Путника с вознаграждением в 1000 крышек, "
            "обнаруживаемый у командиров отрядов наёмников компании «Коготь»."
        )
        custom_context = (
            "Официальная ориентировка на голову героя появляется у ударных групп компании «Коготь», которые начинают "
            "устраивать засады на Столичной Пустоши, если Одинокий Путник поддерживает положительную или очень добрую карму."
        )
    elif edid.startswith("DLC03CitadelArmory"):
        role = "Архивная ведомость или рапорт Цитадели (Broken Steel)"
        custom_lead = (
            f"«{name}» — архивный документ из терминалов оружейной и командного крыла Цитадели Братства Стали в дополнении Broken Steel."
        )
        custom_context = (
            "Запись загружается из терминалов Цитадели (бывшего здания Пентагона) в дополнении Broken Steel "
            "и раскрывает довоенные инциденты в военном ведомстве либо внутренний учёт экспериментального вооружения Братства "
            "(пушка «Тесла», гатлинг-лазер и партии ядерных выстрелов)."
        )
    elif edid.startswith("MS11BurkeLoveLetter"):
        role = "Личное письмо мистера Берка (Мегатонна)"
        custom_lead = (
            f"«{name}» — одно из личных посланий мистера Берка, отправляемых героине при наличии способности «Чёрная вдова»."
        )
        custom_context = (
            "Письмо связано с квестом «Сила Атома»: если женщина-персонаж со способностью «Чёрная вдова» очарует мистера Берка "
            "в салуне Мориарти, он откажется от подрыва Мегатонны и впоследствии будет оставлять ей романтические письма."
        )
    elif edid.startswith("MQ04BraunNote"):
        role = "Научные записи доктора Станисласа Брона (Трэнквилити-Лейн)"
        custom_lead = (
            f"«{name}» — лабораторная запись доктора Станисласа Брона из Убежища 112, посвящённая симуляции «Трэнквилити-Лейн»."
        )
        custom_context = (
            "Рабочие заметки руководителя проекта «Волт-Тек» доктора Брона в Убежище 112 раскрывают историю ранних виртуальных миров "
            "и жестокие психологические эксперименты над запертыми в капсулах резидентами."
        )
    elif edid.startswith("CitadelWeaponsTerminal"):
        role = "Техническая справка Цитадели по вооружению"
        custom_lead = (
            f"«{name}» — справочная карточка из оружейного терминала Цитадели Братства Стали с описанием штатного вооружения."
        )
        custom_context = (
            "Военно-техническая характеристика составлена писцами и оружейниками Цитадели Братства Стали "
            "в качестве памятки по эксплуатации и обслуживанию оружия для рыцарей и послушников."
        )
    elif edid.startswith("SatComData"):
        role = "Довоенные координаты спутниковой сети «СатКом»"
        custom_lead = (
            f"«{name}» — навигационная запись с координатами довоенного спутникового комплекса сети «СатКом»."
        )
        custom_context = (
            "Техническая сводка указывает расположение антенн спутникового комплекса «СатКом» на северо-западе Столичной Пустоши, "
            "включающего серию укреплённых станций ретрансляции с орбитальными ударными терминалами."
        )
    elif note_type == "Изображение":
        role = "Изображение / визуальная ориентировка в Пип-бое"
    elif note_type == "Голосовая голозапись":
        role = "Голосовая голозапись (аудиодневник / запись)"
    else:
        role = "Текстовая заметка или документ"

    wiki_title = ctx.wiki["wikiTitle"] if ctx.wiki else ""
    lead_w = ctx.wiki_lead_clean()

    if custom_lead:
        s1 = custom_lead
    elif lead_w and wiki_title not in COMPOSITE_NOTE_WIKIS:
        s1 = lead_w
    elif wiki_title in COMPOSITE_NOTE_WIKIS:
        s1 = f"«{name}» — {note_type.lower()} из серии «{clean_display_name(wiki_title)}» ({DLC_NAMES_RU[n['dlc']]})."
    else:
        s1 = f"«{name}» — {note_type.lower()} из {DLC_GEN_RU[n['dlc']]}."

    if ctx.quests and "квест" not in s1.lower():
        s2 = f"Документ хранится в разделе заметок Пип-боя и связан с заданием {quote_ru(ctx.quests[0])}."
    elif clean_txt and len(clean_txt) > 30 and "Бла-бла" not in clean_txt:
        preview = extract_note_preview(clean_txt)
        s2 = f"В содержании затрагиваются события Пустоши: {quote_ru(preview)}."
    else:
        s2 = "Добавляется в соответствующий раздел Пип-боя для изучения улик, предыстории или паролей."

    summary = f"{s1} {s2}".strip()
    if len(summary) < 120:
        summary += f" Запись относится к типу «{note_type}» и помогает глубже понять предысторию мира игры."

    sec1_parts: list[str] = []
    if custom_context:
        sec1_parts.append(custom_context)

    w_desc = ctx.wiki_sec("Описание", "История", "Содержание", "Общая информация", "Использование")
    if w_desc and w_desc not in sec1_parts:
        sec1_parts.append(w_desc)

    if wiki_title not in COMPOSITE_NOTE_WIKIS:
        w_quest = ctx.wiki_sec("Квесты", "Связанные квесты")
        if w_quest:
            sec1_parts.append(w_quest)
    elif not w_desc:
        sec1_parts.append(f"Входит в общую серию записей {quote_ru(wiki_title)}.")

    if ctx.quests and not any("квест" in p.lower() for p in sec1_parts):
        sec1_parts.append(f"Связано с прохождением задания: {format_list_ru([quote_ru(q) for q in ctx.quests], limit=4)}.")

    if not sec1_parts:
        sec1_parts.append(
            f"Запись типа «{note_type}» ({DLC_NAMES_RU[n['dlc']]}), сохраняемая в Пип-бое Одинокого Путника для ориентирования, паролей или истории локации."
        )

    if clean_txt:
        sec1_parts.append(f"Текст записи:\n{clean_txt}")
    else:
        if note_type == "Изображение":
            sec1_parts.append(
                "Запись не содержит текстовой расшифровки и представляет собой графическое изображение, просматриваемое в разделе «Заметки» Пип-боя."
            )
        else:
            sec1_parts.append(
                "Данный предмет используется в системе заметок как электронная карта доступа или идентификатор без дополнительного текста."
            )

    w_notes = ctx.wiki_sec("Заметки", "Примечание")
    if w_notes:
        sec1_parts.append(w_notes)

    sec2 = common_where_text(ctx, "заметку", include_wiki_quests=False)

    entry: dict[str, Any] = {
        "id": n["id"],
        "role": role,
        "summary": summary,
        "sections": [
            {"title": "Содержание и значение в игре", "text": "\n\n".join(sec1_parts)},
            {"title": "Где встречается", "text": sec2},
        ],
        "value": val,
        "weight": wt,
        "noteType": note_type,
        "text": clean_txt,
        "sourceTag": ctx.source_tag,
    }
    if ctx.wiki_url:
        entry["wikiUrl"] = ctx.wiki_url
    return entry


def build_misc(ctx: ItemContext) -> dict[str, Any]:
    n, e = ctx.node, ctx.esm
    name = clean_display_name(n["label"])
    edid = n["edid"]
    val = e.get("value", 0)
    wt = e.get("weight", 0.0)

    is_bobble = edid in BOBBLEHEAD_EFFECTS
    is_schematic = edid in CRAFTING_RECIPES
    is_component = edid in COMPONENT_RECIPES
    special = MISC_SPECIAL_LORE.get(edid)

    sec1_parts: list[str] = []
    if is_bobble:
        stat_name, bonus_desc = BOBBLEHEAD_EFFECTS[edid]
        role = f"Коллекционный пупс Vault-Tec («{stat_name}»)"
        s1 = (
            f"«{name}» — один из 20 уникальных коллекционных пупсов корпорации «Волт-Тек», разбросанных по Столичной Пустоши. "
            f"Подбор этой фигурки немедленно и навсегда даёт бонус: {bonus_desc}."
        )
        sec1_parts.append(
            f"Как и вся коллекционная серия Vault-Tec, пупс «{stat_name}» активирует постоянный прирост ({bonus_desc}) сразу в момент взятия в инвентарь. "
            "Фигурку можно выставить на специальный коллекционный стенд в собственном доме в Мегатонне или люксе в Тенпенни-Тауэр."
        )
        source_tag = "esm+wiki+curated" if ctx.wiki else "esm+curated"
    elif is_schematic:
        wname, ingredients, wdesc = CRAFTING_RECIPES[edid]
        role = f"Схема сборки самодельного оружия («{wname}»)"
        ing_str = format_list_ru(ingredients)
        s1 = (
            f"«{name}» — чертёж для верстака, открывающий сборку уникального самодельного оружия «{wname}» ({wdesc}). "
            f"Для изготовления требуются: {ing_str}."
        )
        sec1_parts.append(
            f"Наличие первой копии схемы позволяет изготавливать «{wname}» на любом верстаке, используя набор деталей: {ing_str}. "
            "Каждая дополнительно найденная версия этой схемы повышает состояние создаваемого оружия (или выход боеприпасов/зарядов за одну сборку), "
            "поэтому стоит собрать все доступные копии на Пустоши."
        )
        source_tag = "esm+wiki+curated" if ctx.wiki else "esm+curated"
    elif special:
        role, s1, special_sec1 = special
        sec1_parts.append(special_sec1)
        if is_component:
            comps = ", ".join(f"«{c}»" for c in COMPONENT_RECIPES[edid])
            sec1_parts.append(f"Также служит базовой деталью на верстаке при сборке оружия {comps}.")
        source_tag = "esm+wiki+curated" if ctx.wiki else "esm+curated"
    elif is_component:
        comps = ", ".join(f"«{c}»" for c in COMPONENT_RECIPES[edid])
        role = f"Компонент для сборки на верстаке ({comps})"
        s1 = (
            f"«{name}» — важная ремесленная деталь в Fallout 3, необходимая для создания самодельного оружия {comps} на верстаке. "
            f"При весе {fmt_num(wt)} фнт и цене {plural_caps(val)} предмет также подходит как снаряд для пневматической «Ракетки»."
        )
        sec1_parts.append(
            f"Основная практическая ценность предмета — участие в рецепте самодельного оружия {comps} при наличии соответствующей схемы на верстаке. "
            f"Излишки детали удобно продавать (базовая цена {plural_caps(val)}) или использовать в качестве бесплатного боезапаса для «Ракетки»."
        )
        source_tag = "esm+wiki+curated" if ctx.wiki else "esm+curated"
    else:
        lead_w = ctx.wiki_lead_clean()
        if edid.startswith("MS06") or edid in {"CapPresEmancRolled", "CapPresGettysburgRolled"}:
            role = "Исторический артефакт Авраама Линкольна"
        elif edid.startswith("MS15"):
            role = "Исторический документ (квест «Украденная независимость»)"
        elif edid.startswith("BurnedBook"):
            role = "Повреждённая книга (боеприпас для «Ракетки»)"
        elif edid.startswith("pool"):
            role = "Бильярдный инвентарь (боеприпас для «Ракетки»)"
        elif edid.endswith("ID") or "ID-карта" in name:
            role = "Идентификационная карта доступа"
        elif ctx.quests:
            role = f"Квестовый предмет ({quote_ru(ctx.quests[0])})"
        elif wt > 0:
            role = "Бытовой или промышленный предмет (боеприпас для «Ракетки»)"
        else:
            role = "Невесомый коллекционный или сюжетный предмет"

        if lead_w:
            s1 = lead_w
        elif ctx.quests:
            s1 = f"«{name}» — {role.lower()} из {DLC_GEN_RU[n['dlc']]}, используемый в задании {quote_ru(ctx.quests[0])}."
        else:
            s1 = f"«{name}» — {role.lower()} из {DLC_GEN_RU[n['dlc']]} с массой {fmt_num(wt)} фнт и базовой стоимостью {plural_caps(val)}."
        source_tag = ctx.source_tag

    w_desc = ctx.wiki_sec("Описание", "Использование", "Применение")
    w_quest = ctx.wiki_sec("Квесты", "Связанные квесты")
    w_notes = ctx.wiki_sec("Заметки", "Примечание")
    if w_desc:
        sec1_parts.append(w_desc)
    if w_quest and w_quest != w_desc:
        sec1_parts.append(w_quest)
    if w_notes:
        sec1_parts.append(w_notes)

    if sum(len(p) for p in sec1_parts) < 100:
        if ctx.quests and not any("задани" in p.lower() or "квест" in p.lower() for p in sec1_parts):
            sec1_parts.append(
                f"Предмет напрямую задействован в прохождении задания: {format_list_ru([quote_ru(q) for q in ctx.quests], limit=4)}."
            )
        if edid.startswith("BurnedBook"):
            sec1_parts.append(
                "В отличие от целых «Довоенных книг», обгоревшие, опалённые, испорченные и разодранные книги "
                "не принимает писец Йерлинг в Арлингтонской библиотеке — их можно лишь продавать торговцам за символическую плату "
                "или заряжать в «Ракетку»."
            )
        elif wt > 0:
            sec1_parts.append(
                f"Предмет относится к разделу «Разное» Пип-боя (масса {fmt_num(wt)} фнт, цена {plural_caps(val)}). "
                "Не участвует в рецептах верстака, однако при наличии «Ракетки» может использоваться в качестве многоразового снаряда, "
                "который после выстрела обычно можно снова подобрать с земли."
            )
        else:
            sec1_parts.append(
                f"Невесомый артефакт из раздела «Разное» (цена {plural_caps(val)}), не нагружающий инвентарь Одинокого Путника."
            )
    elif ctx.quests and not w_quest and not any("задани" in p.lower() or "квест" in p.lower() for p in sec1_parts):
        sec1_parts.append(
            f"Задействован в прохождении задания {format_list_ru([quote_ru(q) for q in ctx.quests], limit=4)}."
        )

    summary = s1
    if len(summary) < 125:
        extra_bits: list[str] = []
        if ctx.quests and ctx.quests[0] not in summary:
            extra_bits.append(f"задействован в задании {quote_ru(ctx.quests[0])}")
        if ctx.placements:
            extra_bits.append(f"встречается в локациях вроде {quote_ru(ctx.placements[0])}")
        extra_bits.append(f"имеет массу {fmt_num(wt)} фнт и базовую цену {plural_caps(val)}")
        summary = summary.rstrip(".") + "; " + ", ".join(extra_bits) + "."

    sec2 = common_where_text(ctx, "предмет", include_wiki_quests=False)

    entry: dict[str, Any] = {
        "id": n["id"],
        "role": role,
        "summary": summary,
        "sections": [
            {"title": "Содержание и значение в игре", "text": "\n\n".join(sec1_parts)},
            {"title": "Где встречается", "text": sec2},
        ],
        "value": val,
        "weight": wt,
        "sourceTag": source_tag,
    }
    if ctx.wiki_url:
        entry["wikiUrl"] = ctx.wiki_url
    return entry


def generate_items_encyclopedia() -> dict[str, dict[str, Any]]:
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    details = json.loads(DETAILS_PATH.read_text(encoding="utf-8"))
    walkthroughs = json.loads(WALKTHROUGHS_PATH.read_text(encoding="utf-8"))
    esm_rich = json.loads(ESM_RICH_PATH.read_text(encoding="utf-8"))
    wiki_ru = json.loads(WIKI_RU_PATH.read_text(encoding="utf-8"))

    contexts, ammo_to_weapons = build_contexts(graph, details, walkthroughs, esm_rich, wiki_ru)
    out: dict[str, dict[str, Any]] = {}

    for nid, ctx in contexts.items():
        sub = ctx.node["subtype"]
        if sub == "weapon":
            out[nid] = build_weapon(ctx)
        elif sub == "armor":
            out[nid] = build_armor(ctx)
        elif sub == "aid":
            out[nid] = build_aid(ctx)
        elif sub == "book":
            out[nid] = build_book(ctx)
        elif sub == "ammo":
            out[nid] = build_ammo(ctx, ammo_to_weapons)
        elif sub == "key":
            out[nid] = build_key(ctx)
        elif sub == "note":
            out[nid] = build_note(ctx)
        elif sub == "misc":
            out[nid] = build_misc(ctx)
        else:
            raise ValueError(f"Unknown item subtype {sub!r} for {nid}")

    return out


def verify_output(out: dict[str, dict[str, Any]], graph: dict[str, Any]) -> None:
    expected_items = [n for n in graph["nodes"] if n["type"] == "item"]
    expected_ids = {n["id"] for n in expected_items}
    assert set(out.keys()) == expected_ids, (
        f"ID mismatch: got {len(out)}, expected {len(expected_ids)}"
    )
    assert len(out) == 1059, f"Expected 1059 items, got {len(out)}"

    bad_markup_re = re.compile(
        r"(\{\{|\}\}|\[\[|\]\]|<ref|<div|<br|<font|<span|<img|Предмет категории «|&PCName;|&PCRace;|&PCSex;|GrantTestWorld|test01raiders|VendorChestBuried|««|»»|«»|«\"|\"»|\(\s*\)|и ещё \d+\.|V\.A\.T\.S\.\.|Fallout\s*4|Fallout\s*76|Fallout\s*Shelter|Fallout:?\s*New\s*Vegas|New\s*Vegas|Creation\s*Club)",
        re.I,
    )

    for n in expected_items:
        nid = n["id"]
        sub = n["subtype"]
        entry = out[nid]
        assert entry["id"] == nid
        assert isinstance(entry["role"], str) and len(entry["role"]) >= 5, f"Bad role on {nid}"
        assert isinstance(entry["summary"], str) and len(entry["summary"]) > 110, (
            f"Summary too short ({len(entry['summary'])}) on {nid}: {entry['summary']!r}"
        )
        secs = entry["sections"]
        exp_sec_count = 3 if sub == "weapon" else 2
        assert len(secs) == exp_sec_count, f"Expected {exp_sec_count} sections on {nid}"
        for sec in secs:
            assert sec["title"] and len(sec["text"]) >= 80, (
                f"Short section ({len(sec['text'])}) on {nid} [{sec['title']}]: {sec['text']!r}"
            )

        if sub == "key":
            assert isinstance(entry.get("unlocks"), list)
            assert all(isinstance(u, str) for u in entry["unlocks"])

        def walk_strings(obj: Any) -> list[str]:
            res: list[str] = []
            if isinstance(obj, str):
                res.append(obj)
            elif isinstance(obj, list):
                for x in obj:
                    res.extend(walk_strings(x))
            elif isinstance(obj, dict):
                for v in obj.values():
                    res.extend(walk_strings(v))
            return res

        for stxt in walk_strings(entry):
            m = bad_markup_re.search(stxt)
            assert not m, f"Forbidden token {m.group(0)!r} in {nid}: {stxt[:200]!r}"


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    out = generate_items_encyclopedia()
    verify_output(out, graph)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Successfully wrote and verified {len(out)} item entries -> {OUT_PATH}")


if __name__ == "__main__":
    main()
