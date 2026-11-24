#!/usr/bin/env python3
"""
Generate complete Russian Fallout 3 encyclopedia entries for all 576 location nodes
(5 worlds, 78 map markers, 493 interiors) into /tmp/f3_encyclopedia/parts/locations.json.

Sources used strictly:
  - public/data/graph.json (nodes & edges)
  - public/data/details.json (existing markerType, coords, worldspace)
  - public/data/walkthroughs.json (quest titles & categories)
  - /tmp/f3_encyclopedia/esm_rich.json (ESM cells, NPCs, creatures, items, doors, counts)
  - /tmp/f3_encyclopedia/wiki_ru.json (harvested Russian Fallout Wiki articles)
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = REPO_ROOT / "public" / "data" / "graph.json"
DETAILS_PATH = REPO_ROOT / "public" / "data" / "details.json"
WALKTHROUGHS_PATH = REPO_ROOT / "public" / "data" / "walkthroughs.json"
ESM_RICH_PATH = Path("/tmp/f3_encyclopedia/esm_rich.json")
WIKI_RU_PATH = Path("/tmp/f3_encyclopedia/wiki_ru.json")
OUT_PATH = Path("/tmp/f3_encyclopedia/parts/locations.json")

SECTION_TITLES = (
    "Особенности и устройство",
    "Обитатели и опасности",
    "Находки, объекты и связанные миссии",
)

DLC_LABELS_RU: dict[str, str] = {
    "base": "основная кампания, Столичная Пустошь",
    "anchorage": "дополнение Operation: Anchorage",
    "pitt": "дополнение The Pitt",
    "brokensteel": "дополнение Broken Steel",
    "pointlookout": "дополнение Point Lookout",
    "zeta": "дополнение Mothership Zeta",
}

DLC_SHORT_RU: dict[str, str] = {
    "base": "Fallout 3",
    "anchorage": "Operation: Anchorage",
    "pitt": "The Pitt",
    "brokensteel": "Broken Steel",
    "pointlookout": "Point Lookout",
    "zeta": "Mothership Zeta",
}

WORLDSPACE_RU: dict[str, str] = {
    "Megaton": "Мегатонна",
    "MegatonWorld": "Мегатонна",
    "Chevy Chase": "Чеви-Чейз",
    "Dupont Circle": "Дюпон-серкл",
    "Pennsylvania Avenue": "Пенсильвания-авеню",
    "Seward Square": "Сьюард-сквер",
    "Takoma Park": "Такома-парк",
    "L'Enfant Plaza": "Ланфан-плаза",
    "Внутренняя локация": "внутреннее помещение",
}

OWNER_RU: dict[str, str] = {
    "Dukov's Faction": "Дуков и его окружение",
    "Ewers Family in Arefu": "семья Юэрсов (Арефу)",
    "Jericho": "Джерико",
    "ParadiseFallsResidentFaction": "работорговцы Парадиз-Фоллз",
    "Republic of Dave": "Республика Дэйва",
    "RivetCityResidentFaction": "жители и охрана Ривет-Сити",
    "Temple of the Union": "Храм Единения",
    "TenpennyTowerResidentFaction": "жители и охрана Тенпенни-Тауэр",
    "The Family Friendly": "община «Семьи»",
}

ENTITY_RU: dict[str, str] = {
    "Alex Dargon": "Алекс Даргон",
    "Butch": "Буч",
    "Charon": "Харон",
    "Clover": "Кловер",
    "Daniel Agincourt": "Дэниел Аженкур",
    "Enclave Soldier": "Солдат Анклава",
    "Jericho": "Джерико",
    "Rivet City Security": "Охранник Ривет-Сити",
    "Underworld Resident": "Житель Подземелья",
    "Wastelander": "Обитатель пустошей",
    "Deathclaw": "Коготь смерти",
    "Fawkes": "Фокс",
    "Mister Gutsy": "Мистер Храбрец",
    "Protectron": "Протектрон",
    "Sentry Bot": "Робот-охранник",
    "Street Trog": "Уличный трог",
    "Super Mutant": "Супермутант",
    "Vicious Dog": "Злобный пёс",
}

DOOR_CLEAN_RU: dict[str, str] = {
    "Arlington/Wasteland Metro": "тоннель метро «Арлингтон — Пустошь»",
    "Metro Junction": "пересадочный узел метро (Metro Junction)",
    "DC15a": "выход в сектор DC15a (окрестности Арлингтона)",
    "DC17a": "выход в сектор DC17a (район Фоллз-Черч)",
    "DC21a": "выход в сектор DC21a (Бейлиз-Кроссроудз)",
}

QUEST_TITLE_RU: dict[str, str] = {
    "qst_00014e83": "«Первые шаги»",
    "qst_00014e84": "«Быстрое взросление»",
    "qst_00014e85": "«Будущее в тумане»",
    "qst_00014e86": "«Побег!»",
    "qst_00014e87": "«След в след»",
    "qst_00014e88": "«Радио „Новости Галактики“»",
    "qst_00014e89": "«Гонка преследования»",
    "qst_00014e8a": "«Трэнквилити-лейн»",
    "qst_00014e8b": "«Живая вода»",
    "qst_00014e8c": "«По следам»",
    "qst_00014e8d": "«Спасение из рая»",
    "qst_00014e8e": "«Поиски Эдемских кущ»",
    "qst_00014e8f": "«Американская мечта»",
    "qst_00014e90": "«Проникновение»",
    "qst_00014e91": "«Забери его!»",
    "qst_00014e93": "«Проект „Нечистоты“»",
    "qst_00014e94": "«Большие проблемы в Большом Городе»",
    "qst_00014e95": "«Нечеловеческий гамбит»",
    "qst_00014e96": "«Руководство по выживанию на Пустошах»",
    "qst_00014e97": "«Они!»",
    "qst_00014e98": "«Погоня за Ядер-Колой»",
    "qst_00014e99": "«Глава государства»",
    "qst_00014e9b": "«Искусственный человек»",
    "qst_00014e9c": "«Узы крови»",
    "qst_00014e9e": "«Сила атома»",
    "qst_00014e9f": "«Тенпенни-Тауэр»",
    "qst_00014ea0": "«Просто бизнес»",
    "qst_00014ea1": "«Контрольный выстрел»",
    "qst_00014ea2": "«Украденная независимость»",
    "qst_00014ea3": "«Проблемы на домашнем фронте»",
    "qst_00014ea4": "«Песнь Агаты»",
    "qst_00014ea5": "«Рейнджеры Рейли»",
    "qst_000173d1": "«Исследование руин Вашингтона» (свободное задание)",
    "qst_000173d8": "«Поручения в Мегатонне» (свободное задание)",
    "qst_000173d9": "«Поручения в Цитадели» (свободное задание)",
    "qst_0002a274": "«Оазис»",
    "qst_0002fa33": "«Найм Джерико»",
    "qst_000371d2": "«Найм Харона»",
    "qst_0005ecfd": "«Наследие Линкольна»",
    "qst_0006136d": "«Освоение силовой брони» (свободное задание)",
    "qst_00062736": "«Найм Звёздного паладина Кросс»",
    "qst_0006f1e7": "«Наёмный убийца»",
    "qst_0006f1e8": "«Законник»",
    "qst_000872e6": "«Поиски продолжаются»",
    "qst_0009426d": "«Найм Буча»",
    "qst_000943eb": "«Найм сержанта РЛ-3»",
    "qst_000943ec": "«Найм Кловер»",
    "qst_000943ed": "«Найм Псины»",
    "qst_000943ee": "«Найм Фокса»",
    "qst_0009b5bb": "«Авраам Вашингтон — покупатель»",
    "qst_010009be": "«Помощь Изгоям»",
    "qst_010009bf": "«Орудия Анкориджа»",
    "qst_010009c0": "«Подготовка наступления»",
    "qst_010014f6": "«Операция „Анкоридж“»",
    "qst_010034da": "«Задания в лагере симуляции Анкориджа»",
    "qst_0200108b": "«Вредные условия труда»",
    "qst_0200108c": "«Проникнуть в Питт»",
    "qst_0200108d": "«Свободный труд»",
    "qst_0200a358": "«Найти Билла-Дикаря»",
    "qst_03000802": "«Смерть с небес»",
    "qst_03000afd": "«Плата за электричество»",
    "qst_030011ad": "«Кто смел, тот побеждает»",
    "qst_03003b42": "«Защита караванов»",
    "qst_03003b67": "«Великолепная лечебная вода!»",
    "qst_03004c75": "«Святая вода»",
    "qst_04002f18": "«Страны далёкие»",
    "qst_04002f47": "«Тёмная душа Блэкхолла»",
    "qst_04003f70": "«Бальзам на душу»",
    "qst_0400436e": "«Бархатный занавес»",
    "qst_04005846": "«Местные нравы»",
    "qst_04005847": "«Прогулка с духами»",
    "qst_04005848": "«Шепчущие голоса»",
    "qst_04005849": "«Мысли под контролем»",
    "qst_0400584a": "«Схватка интеллектов»",
    "qst_0400584b": "«Схватка интеллектов»",
    "qst_0400815c": "«Беспризорник Кенни»",
    "qst_04009b5e": "«Сафари Плика»",
    "qst_05000802": "«Не из этого мира»",
    "qst_05000803": "«Среди звёзд»",
    "qst_05000804": "«Эта галактика не столь велика…»",
    "qst_05005c70": "«Записи пленных на „Дзете“»",
}

FRIENDLY_CREATURE_NAMES = {
    "Фокс",
    "Баттон Гвинетт",
    "Годфри",
    "Уодсворт",
    "Бригадир Мило",
    "Мистер Бекингем",
    "Спарки",
    "Энди",
    "Фреки",
    "Цербер",
    "Этил",
    "Помощник Стил",
    "Самуэль",
    "Рекс",
    "Пит",
    "Мясо",
    "Имбирь",
    "Пушок",
    "Скальпель",
    "Шейкс",
    "Гувер",
    "Декан Деви",
    "Рузка",
    "Тыква",
}

AMBIENT_CREATURE_NAMES = {
    "Брамин",
    "Разлагающийся труп брамина",
    "Интерком-глаз",
    "Служебный робот",
}

JUNK_ITEM_PATTERNS = (
    "вилка",
    "ложка",
    "тарелка",
    "кружка",
    "кофейник",
    "пепельница",
    "жестяная банка",
    "мятая жестяная",
    "бутылка из-под",
    "пустая бутылка",
    "молочная бутылка",
    "обгоревшая книга",
    "испорченная книга",
    "опаленная книга",
    "разодранная книга",
    "карандаш",
    "планшет",
    "расчеты прибылей",
    "финансовые расчеты",
    "медицинские записи",
    "пачка сигарет",
    "блок сигарет",
    "вантуз",
    "швабра",
    "ведро",
    "метла",
    "стеклянный кувшин",
    "стеклянный стакан",
    "стакан",
    "горшок",
    "костыль",
    "сковорода",
    "кастрюля",
    "столовый нож",
    "стопка",
    "плитка",
    "ножницы",
    "утюг",
    "губная гармошка",
    "гаечный ключ",
    "молоток",
    "мяч",
    "скипидар",
    "стиральный порошок",
    "чудо-клей",
    "щетка",
    "зубная",
    "половая",
    "лопата",
    "кий",
    "бильярдный шар",
    "точильный камень",
    "плюшевый мишка",
    "шахматная доска",
    "бумажный",
    "тряпка",
    "проводник",
    "резиновый хирургический",
    "игрушечная машинка",
    "лезвие газонокосилки",
    "пульверизатор",
    "разделочная доска",
    "камера",
)

GENERIC_OBJECTS = {
    "Дверь",
    "Ворота",
    "Люк",
    "Лестница",
    "Металлическая дверь",
    "Деревянная дверь",
    "Аптечка первой помощи",
    "Запертый стол",
    "Картотечный шкаф",
    "Контейнер",
    "Металлический ящик",
    "Мусорный контейнер",
    "Напольный сейф",
    "Оружейный шкаф",
    "Письменный стол",
    "Почтовый ящик",
    "Сейф",
    "Стенной сейф",
    "Сундук",
    "Фиктивный взрывающийся объект",
    "Холодильник",
    "Чемодан",
    "Шкаф",
    "Ящик",
    "Ящик для брони",
    "Ящик с боеприпасами",
    "Ящик с гранатами",
    "Ящик с инструментами",
}

INVALID_WIKI_EDIDS = {
    "Vault101Demo",
    "Vault92b",
    "Vault87b",
    "zToxicDump01",
    "zToxicDump02",
    "zDCint17a",
    "zDCint17b",
    "zWastelandSewer01",
    "zDCint05a",
    "DLC02TEMPArtilleryBase",
    "DLC01TestJeffQuest",
    "FFRadioCache08",
    "FFRadioCache02",
    "FFRadioCache05",
    "FFRadioCache01",
    "MS14ArmorVoice",
    "DLCPittTestPurkey",
    "DLC04zTestDuchessGambitCabin",
    "DLC04zTestSeaCave",
    "DLC04zTestDar",
    "DLC05TestRepairBay",
    "DLC05testCoreOverhaul",
    "DLC05TestJeffB02",
    "DLC05testJesse",
    "RedRacer03COPY0000",
}

TEST_EDID_PREFIXES = (
    "DLC01Test",
    "DLCPittTest",
    "DLC04zTest",
    "DLC05Test",
    "DLC05test",
)

NON_F3_MARKERS = (
    "Fallout 76",
    "Expeditions: The Pitt",
    "Fallout: Board Game",
    "Fallout 4",
    "New Vegas",
    "Van Buren",
    "Fallout Shelter",
    "настольн",
    "Аппалачи",
    "Убежища 79",
    "Убежища 76",
    "Убежище 76",
    "Союз Питтсбурга",
    "2103 год",
    "2104 год",
    "Опора",
    "Содружеств",
    "ГЕЛИОС Один",
    "Мохаве",
    "накладных № 9021",
    "Курсивом выделены",
    "выделены курсивом",
    "Одинокий Путник был замечен в Пойнт-Лукауте",
    "Питт также Хранителем Каденом",
    "TestQAItems",
    "All Books and Notes",
)

WORLD_CURATED: dict[str, dict[str, str]] = {
    "loc_0000003c": {
        "role": "Основной игровой мир — Столичная Пустошь и руины Вашингтона",
        "summary": (
            "Главное открытое пространство Fallout 3, объединяющее выжженные земли бывших штатов "
            "Мэриленд и Вирджиния с разрушенной федеральной столицей США — Вашингтоном. "
            "Регион разделён между укреплёнными поселениями выживших, аванпостами Братства Стали, "
            "базами Анклава, лагерями рейдеров и плотной сетью туннелей метрополитена, соединяющих изолированные кварталы города."
        ),
        "sec1_extra": (
            "Столичная Пустошь выступает связующим пространством для большинства наземных маркеров, "
            "убежищ «Волт-Тек», заброшенных заводов и городских районов округа Колумбия, включая "
            "Джорджтаун, Дюпон-серкл, Вернон-сквер, Пенсильвания-авеню, Молл и Арлингтон."
        ),
    },
    "loc_00000a74": {
        "role": "Укреплённый город выживших вокруг неразорвавшейся атомной бомбы",
        "summary": (
            "Мегатонна (в файлах локализации мира отмечена как Megaton) — крупнейшее раннее поселение "
            "выживших на Столичной Пустоши, построенное в глубокой воронке вокруг неразорвавшейся атомной бомбы C-12. "
            "Стены города собраны из обшивки старых самолётов, порядок охраняет шериф Лукас Симмс, "
            "а судьба всей общины становится главным нравственным выбором на старте игры."
        ),
        "sec1_extra": (
            "Внутреннее пространство города устроено кольцевыми ярусами вокруг центрального кратера: "
            "на верхнем уровне расположены «Магазин на кратере» Мойры Браун, салун Мориарти, "
            "дом игрока, клиника и дома горожан, а на самом дне у бомбы проповедует культ Детей Атома. "
            "Через городские ворота и входы внутри кратера область связана с 17 внутренними помещениями."
        ),
    },
    "loc_00015145": {
        "role": "Укреплённая штаб-квартира Братства Стали в руинах Пентагона",
        "summary": (
            "Внешний двор Цитадели — сердце укреплений восточного отделения Братства Стали под командованием "
            "старейшины Оуэнса Лайонса, возведённое в руинах довоенного Пентагона на берегу Потомака. "
            "Здесь тренируются послушники и паладины, базируется гигантский робот Либерти Прайм и "
            "разворачиваются ключевые события второй половины основного сюжета и дополнения Broken Steel."
        ),
        "sec1_extra": "",
    },
    "loc_020008c0": {
        "role": "Ключевая промышленная область дополнения The Pitt",
        "summary": (
            "Питт — отравленная индустриальная пустошь на месте довоенного Питтсбурга, "
            "куда Одинокий Путник добирается на дрезине через железнодорожный туннель по просьбе беглого раба Вернера. "
            "Город окутан токсичным смогом, поделён между подневольным Заводским двором и Крепостью рейдеров Исмаила Ашура "
            "и страдает от загадочной мутации, превращающей людей в диких трогов."
        ),
        "sec1_extra": (
            "Внешняя стартовая зона Питта охватывает разрушенный мост и подступы к воротам Нижнего города, "
            "через которые проходит вся дальнейшая цепочка испытаний рабского квартала, "
            "металлургического завода и арены «Дыры»."
        ),
    },
    "loc_04000802": {
        "role": "Болотистое побережье Мэриленда — основной мир дополнения Point Lookout",
        "summary": (
            "Пойнт-Лукаут — полуостров и бывший прибрежный парк развлечений на юге Мэриленда, "
            "уцелевший после Великой войны без прямых ядерных ударов, но поглощённый туманными топями и дикими болотниками. "
            "Добраться сюда можно на пароходе «Герцогиня Гамбит» капитана Тобара; остров полон тайн, "
            "сект почитателей панги, старинных особняков и подземных тайн довоенных агентов."
        ),
        "sec1_extra": "",
    },
}

SPECIAL_INTERIORS: dict[str, dict[str, str]] = {
    "loc_000035d4": {
        "role": "Подземный пересадочный коридор метро между Арлингтоном и Пустошью",
        "summary": (
            "Тоннель метро «Арлингтон — Пустошь» (Arlington/Wasteland Metro) — компактный подземный переход, "
            "соединяющий Затопленное метро на берегах Потомака с северным сектором Арлингтонского кладбища. "
            "Через этот короткий, но важный перегон путники выходят из столичной подземки на правый берег реки к мемориалам и «Маме Дольче»."
        ),
        "parent": "Затопленное метро и Арлингтонское кладбище",
    },
    "loc_000035d3": {
        "role": "Подземный пересадочный узел метро центрального Вашингтона",
        "summary": (
            "Пересадочный узел метро (Metro Junction) — развязка столичной подземки, связывающая сразу три ключевых "
            "городских района: северо-восток Дюпон-серкл, станцию «Вернон-сквер» и восток Чеви-Чейз. "
            "Именно здесь пересекаются подземные маршруты сквозь заваленные проспекты центрального Вашингтона."
        ),
        "parent": "столичная система метрополитена (Дюпон-серкл, Вернон-сквер и Чеви-Чейз)",
    },
    "loc_0400c2b4": {
        "role": "Затопленная китайская разведывательная подлодка в бухте Пойнт-Лукаута",
        "summary": (
            "SSN-37-1A — довоенная китайская подводная лодка, укрывшаяся у побережья Пойнт-Лукаута "
            "и связанная с секретным шпионским делом агента Яна из квеста «Бархатный занавес». "
            "Чтобы попасть на борт и активировать самоуничтожение подлодки, Одинокому Путнику предстоит "
            "раскрыть старую разведывательную сеть в отеле и местном морге."
        ),
        "parent": "прибрежные воды Пойнт-Лукаута",
    },
    "loc_0006e768": {
        "role": "Служебная ячейка озвучки для говорящей силовой брони (техническая зона)",
        "summary": (
            "MS14 Armor Voice Cell — внутренняя служебная ячейка движка Fallout 3, не предназначенная для "
            "обычного посещения игроком. Она используется игрой для хранения и воспроизведения реплик "
            "говорящей медицинской силовой брони из побочного квеста «Контрольный выстрел» (MS14)."
        ),
        "parent": "служебная техническая зона движка вне игровой карты",
    },
    "loc_0001852e": {
        "role": "Демонстрационная техническая копия Убежища 101",
        "summary": (
            "Техническая демонстрационная ячейка Убежища 101 (Vault101Demo), созданная разработчиками при "
            "подготовке игровых сцен и презентаций, и изолированная от основного маршрута прохождения. "
            "Внутри воссозданы типовые медицинские и жилые декорации убежища с терминалами и базовыми предметами."
        ),
        "parent": "служебная техническая ячейка вне основного маршрута игры",
    },
    "loc_0004ae05": {
        "role": "Дублирующая техническая ячейка завода «Ред Рейсер»",
        "summary": (
            "Резервная копия служебной зоны завода «Ред Рейсер» (RedRacer03COPY0000), оставшаяся в ресурсах игры "
            "от переработки внутренних помещений фабрики. Она не имеет активных дверных переходов в мир и "
            "не участвует в обычном исследовании Столичной Пустоши."
        ),
        "parent": "завод «Ред Рейсер» (резервная техническая копия)",
    },
    "loc_010058d6": {
        "role": "Черновая ячейка китайского артиллерийского поста (Operation: Anchorage)",
        "summary": (
            "Временная рабочая версия китайского артиллерийского поста (DLC02TEMPArtilleryBase) из ресурсов "
            "дополнения Operation: Anchorage. Итоговая игровая версия артиллерийской базы, штурмуемая в ходе "
            "симуляции, вынесена в отдельную связанную ячейку на Анкориджских утёсах."
        ),
        "parent": "ресурсы симуляции Operation: Anchorage (черновая ячейка)",
    },
    "loc_010019f5": {
        "role": "Склад и ремонтный отсек китайских танков «Химера» в симуляции Анкориджа",
        "summary": (
            "База «Химер» — внутренняя область виртуальной симуляции освобождения Анкориджа, "
            "где сосредоточены китайские тяжёлые танки «Химера», разрушающие оборону американских сил. "
            "Уничтожение топливных баков и танков в этом секторе напрямую ослабляет вражескую технику перед финальным штурмом."
        ),
        "parent": "виртуальная симуляция Operation: Anchorage",
    },
    "loc_02009f44": {
        "role": "Тестовая ячейка разработчиков для квеста в Заброшенной зоне (The Pitt)",
        "summary": (
            "Служебная тестовая ячейка (DLC01TestJeffQuest), созданная дизайнерами дополнения The Pitt "
            "при отладке маршрута и заданий в Заброшенной зоне. Не имеет выходов на карту Питта и не посещается при обычной игре."
        ),
        "parent": "служебная техническая зона дополнения The Pitt",
    },
    "loc_020010e3": {
        "role": "Тестовая ячейка разработчиков дополнения The Pitt («Mango power!»)",
        "summary": (
            "Отладочная ячейка разработчиков (DLCPittTestPurkey) с шуточным названием «Mango power!», "
            "содержащая элементы арены и строительных лесов Питта для тестирования механик дополнения The Pitt. "
            "Изолирована от игрового мира и недоступна без консольных команд."
        ),
        "parent": "служебная тестовая ячейка дополнения The Pitt",
    },
    "loc_03000804": {
        "role": "Борт винтокрыла Братства Стали при вылете на базу ВВС Адамс",
        "summary": (
            "Интерьер транспортного винтокрыла Братства Стали из дополнения Broken Steel, в котором Одинокий Путник "
            "вместе со стражем Сарой Лайонс совершает перелёт над пустошью во время финального наступления на Анклав. "
            "Сцены на борту служат переходными эпизодами между заданиями в Цитадели и операцией на базе ВВС Адамс."
        ),
        "parent": "воздушная операция Братства Стали (Broken Steel)",
    },
    "loc_03005559": {
        "role": "Вторая бортовая сцена винтокрыла Братства Стали (Broken Steel)",
        "summary": (
            "Второй вариант интерьера транспортного винтокрыла Братства Стали из дополнения Broken Steel, "
            "сопровождающего Одинокого Путника и стража Сару Лайонс во время переброски сил между Цитаделью и авиабазой Адамс. "
            "Ячейка задействуется для сюжетного перелёта на этапе развязки войны с Анклавом."
        ),
        "parent": "воздушная операция Братства Стали (Broken Steel)",
    },
    "loc_03005709": {
        "role": "Третья бортовая сцена винтокрыла Братства Стали (Broken Steel)",
        "summary": (
            "Третий вариант интерьера транспортного винтокрыла Братства Стали из дополнения Broken Steel, "
            "в котором страж Сара Лайонс сопровождает героя при эвакуации или завершающем вылете в ходе финала на базе ВВС Адамс. "
            "Внутри размещены только сюжетные декорации салона без свободных выходов в мир."
        ),
        "parent": "воздушная операция Братства Стали (Broken Steel)",
    },
    "loc_040072da": {
        "role": "Тестовая ячейка каюты парохода «Герцогиня Гамбит» (Point Lookout)",
        "summary": (
            "Служебная тестовая ячейка (DLC04zTestDuchessGambitCabin) из ресурсов дополнения Point Lookout, "
            "использовавшаяся для проверки пассажирской койки перехода между Столичной Пустошью и Мэрилендом. "
            "В обычном прохождении игрок пользуется койкой непосредственно на самом пароходе у речного пирса."
        ),
        "parent": "служебная тестовая зона дополнения Point Lookout",
    },
    "loc_04012c3b": {
        "role": "Вторая тестовая ячейка каюты «Герцогини Гамбит» (Point Lookout)",
        "summary": (
            "Дополнительная отладочная ячейка каюты парохода «Герцогиня Гамбит» (DLC04zTestDar) в файлах "
            "дополнения Point Lookout для проверки механики морского перехода между мирами. "
            "В самой игре не имеет открытых переходов и остаётся технической заготовкой."
        ),
        "parent": "служебная тестовая зона дополнения Point Lookout",
    },
    "loc_0400494f": {
        "role": "Тестовая морская пещера разработчиков (Point Lookout)",
        "summary": (
            "Отладочная тестовая ячейка «Sea Cave» (DLC04zTestSeaCave) в ресурсах дополнения Point Lookout, "
            "где разработчики проверяли бой с наёмниками, рейдерами и муравьями, а также размещение контейнеров и рации. "
            "На карте Пойнт-Лукаута эта ячейка не связана дверями с внешним миром."
        ),
        "parent": "служебная тестовая зона дополнения Point Lookout",
    },
    "loc_0500098c": {
        "role": "Тестовая ячейка ремонтного отсека корабля «Дзета» (Mothership Zeta)",
        "summary": (
            "Техническая тестовая ячейка «Repair Bay» (DLC05TestRepairBay) из дополнения Mothership Zeta, "
            "содержащая набор инопланетных дверей и переключатель для отладки интерьеров материнского корабля чужих. "
            "Не подключена к основной карте отсеков «Дзеты»."
        ),
        "parent": "служебная тестовая зона дополнения Mothership Zeta",
    },
    "loc_0500b531": {
        "role": "Тестовая ячейка инженерного ядра корабля «Дзета» (Mothership Zeta)",
        "summary": (
            "Отладочная ячейка «Engineering Core» (DLC05testCoreOverhaul), использовавшаяся авторами Mothership Zeta "
            "при доработке реакторного ядра и проверке столкновений с пришельцами на борту летающей тарелки. "
            "В обычном прохождении недоступна."
        ),
        "parent": "служебная тестовая зона дополнения Mothership Zeta",
    },
    "loc_05009c70": {
        "role": "Тестовый грузовой отсек корабля «Дзета» с коллекцией вещей (Mothership Zeta)",
        "summary": (
            "Отладочная ячейка «Cargo Hold» (DLC05TestJeffB02) в ресурсах Mothership Zeta, служившая испытательной "
            "витриной множества довоенных костюмов, шляп, игрушек и предметов быта на борту корабля пришельцев. "
            "Изолирована от игровых переходов."
        ),
        "parent": "служебная тестовая зона дополнения Mothership Zeta",
    },
    "loc_05000f94": {
        "role": "Тестовая ячейка ангара корабля «Дзета» (Mothership Zeta)",
        "summary": (
            "Техническая ячейка «Hangar» (DLC05testJesse) из ресурсов дополнения Mothership Zeta, применявшаяся "
            "для тестовой сборки дверей и геометрии ангара без подключения к игровым квестам и внешнему миру."
        ),
        "parent": "служебная тестовая зона дополнения Mothership Zeta",
    },
}


def clean_spaces(text: str) -> str:
    """Normalize whitespace, nested guillemets, and punctuation glitches."""
    # Replace inner guillemets «...» inside outer guillemets with „...“
    def fix_nested_guillemets(match: re.Match[str]) -> str:
        inner = match.group(1)
        inner = inner.replace("«", "„").replace("»", "“")
        return f"«{inner}»"

    text = re.sub(r"«([^»]*«[^»]*»[^»]*)»", fix_nested_guillemets, text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\.{2,}(?!\.)", ".", text)
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r";\s*;+", ";", text)
    text = re.sub(r"([.!?])\s*;", r"\1", text)
    # Fix isolated missing opening guillemet artifacts from wiki
    text = re.sub(r"(?<![«„])Американская мечта»", "«Американская мечта»", text)
    text = re.sub(r"(?<!«)\b(Подземелье — хорошая стартовая точка[^»]*»)", r"«\1", text)
    text = re.sub(r"(» — Из записки Данбара)\s+", r"\1. ", text)
    return text.strip()


def translate_worldspace(ws: str) -> str:
    """Return Russian name for a worldspace string."""
    if not ws:
        return "Столичная Пустошь"
    return WORLDSPACE_RU.get(ws, ws)


def translate_owner(owner: str) -> str:
    """Translate ESM owner faction or keep clean Russian NPC name."""
    if not owner:
        return ""
    return OWNER_RU.get(owner, owner)


def translate_entity(name: str) -> str:
    """Translate untranslated ESM NPC or creature names."""
    return ENTITY_RU.get(name, name)


def clean_door_name(door: str) -> str:
    """Clean parenthetical English worldspace tags from doorsTo labels."""
    if door in DOOR_CLEAN_RU:
        return DOOR_CLEAN_RU[door]
    cleaned = re.sub(
        r"\s*\((Megaton|Takoma Park|Chevy Chase|Dupont Circle|Pennsylvania Avenue|Seward Square|L'Enfant Plaza)\)\s*$",
        "",
        door,
    )
    return cleaned.strip()


def format_quest_name(qnode: dict[str, Any]) -> str:
    """Format a quest node label into clean Russian title case in quotes."""
    qid = qnode["id"]
    if qid in QUEST_TITLE_RU:
        return QUEST_TITLE_RU[qid]
    lbl = qnode.get("label", "").strip()
    if not lbl:
        return f"задание {qnode.get('edid', qid)}"
    if lbl.isupper():
        lbl = lbl[0] + lbl[1:].lower()
    return f"«{lbl}»"


def lc_phrase(phrase: str) -> str:
    """Lowercase only the first character of a phrase when appropriate, keeping acronyms intact."""
    if not phrase:
        return ""
    if phrase.startswith(('"', "«")) or (len(phrase) >= 2 and phrase[:2].isupper()):
        return phrase
    return phrase[0].lower() + phrase[1:]


def is_junk_item(label: str) -> bool:
    """Return True if an item label represents low-value everyday clutter."""
    base = label.split(" ×")[0].strip().lower()
    return any(pat in base for pat in JUNK_ITEM_PATTERNS)


def is_valid_wiki(node: dict[str, Any], w: dict[str, Any] | None) -> bool:
    """Check whether wiki_ru match truly belongs to this specific location node."""
    if not w:
        return False
    edid = node.get("edid", "")
    if edid in INVALID_WIKI_EDIDS or any(edid.startswith(p) for p in TEST_EDID_PREFIXES):
        return False
    cats_str = " ".join(w.get("categories", []))
    wt = w.get("wikiTitle", "")
    dlc = node.get("dlc", "base")
    dlc_markers = {
        "pitt": "The Pitt",
        "anchorage": "Anchorage",
        "brokensteel": "Broken Steel",
        "pointlookout": "Point Lookout",
        "zeta": "Mothership Zeta",
    }
    if dlc == "base":
        for dname in dlc_markers.values():
            if dname in wt:
                return False
            if dname in cats_str and "Fallout 3" not in cats_str and "упоминаемые" not in cats_str:
                return False
    else:
        exp = dlc_markers.get(dlc, "")
        if exp and exp not in cats_str and "Fallout 3" not in cats_str:
            return False
    return True


def strip_epigraph_and_notices(lead: str) -> str:
    """Remove leading wiki disambiguation notices and epigraph quote lines."""
    lines = [ln.strip() for ln in lead.splitlines() if ln.strip()]
    kept: list[str] = []
    for ln in lines:
        if ln.startswith("Эта статья о конкретной локации"):
            continue
        if re.match(r"^[«\"].+[»\"]\s*[—–-]\s*.+$", ln):
            continue
        if any(tok in ln for tok in NON_F3_MARKERS):
            continue
        kept.append(ln)
    text = " ".join(kept)
    text = re.sub(
        r"\s+и\s+Expeditions:\s*The Pitt[^.]*\.",
        ".",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*\(англ\.[^)]*\)", "", text)
    return clean_spaces(text)


def filter_f3_wiki_text(text: str, edid: str = "", heading: str = "") -> str:
    """Clean wiki section text, stripping non-F3 game mentions and formatting bullets into prose."""
    if not text:
        return ""

    # Isolate specific numbered site when the Wiki article covers #1/#2/#3 variants
    m_hole = re.match(r"DLC04surveyHole0([123])$", edid)
    if m_hole and f"Почвенный разрез #{m_hole.group(1)}:" in text:
        num = m_hole.group(1)
        m_blk = re.search(
            rf"Почвенный разрез #{num}:(.*?)(?=Почвенный разрез #\d+:|\Z)",
            text,
            flags=re.DOTALL,
        )
        if m_blk:
            text = f"Почвенный разрез #{num}: " + m_blk.group(1).strip()

    # For FFRadioCache03 (Телебашня KB5), strip the wiki's erroneous KX-B8-11 / Shalebridge lines
    if edid == "FFRadioCache03":
        text = re.sub(r"Попасть в неё можно через канализационный люк[^.\n]*\.\s*", "", text)
        text = re.sub(r"Ещё две одноимённые локации[^.\n]*\.\s*", "", text)
        text = re.sub(r"Рядом с ними ловится[^.\n]*\.\s*", "", text)

    lines = text.splitlines()
    clean_lines: list[str] = []
    skip_non_f3_block = False

    for raw in lines:
        ln = raw.strip()
        if not ln:
            continue
        # Strip standalone epigraph quote lines like "«...» — Загрузочные экраны"
        if re.match(r"^[«\"].+[»\"]\s*[—–-]\s*[^.]{2,45}$", ln):
            continue
        if re.match(r"^(Fallout 76|Expeditions:|Fallout: Board Game|Fallout 4)\s*:?$", ln):
            skip_non_f3_block = True
            continue
        if skip_non_f3_block and ln.endswith(":") and not ln.startswith("•"):
            skip_non_f3_block = False
        if skip_non_f3_block:
            continue
        if any(tok in ln for tok in NON_F3_MARKERS):
            continue
        if ln.startswith("•"):
            item = ln.lstrip("•").strip().rstrip(";.")
            item = re.sub(r"\s*•\s*", " — ", item).rstrip(" —•")
            if item:
                clean_lines.append(f"• {item}")
        else:
            ln = re.sub(r"\s+•\s+", " — ", ln)
            ln = re.sub(r"\s*•\s*$", "", ln).replace("•", "")
            if ln.strip():
                clean_lines.append(ln.strip())

    paragraphs: list[str] = []
    bullets: list[str] = []

    def flush_bullets() -> None:
        nonlocal bullets
        if not bullets:
            return
        # Decide whether bullet items are short noun items or full descriptive sentences
        are_sentences = any(len(b) > 55 or "." in b or " — " in b for b in bullets)
        if len(bullets) == 1:
            b0 = bullets[0]
            paragraphs.append(b0 if b0.endswith((".", "!", "?")) else b0 + ".")
        elif are_sentences:
            sent_parts = [b if b.endswith((".", "!", "?")) else b + "." for b in bullets]
            paragraphs.append(" ".join(sent_parts))
        else:
            paragraphs.append(", ".join(bullets) + ".")
        bullets = []

    for ln in clean_lines:
        if ln.startswith("• "):
            bullets.append(ln[2:])
        else:
            flush_bullets()
            paragraphs.append(ln)
    flush_bullets()

    out = " ".join(paragraphs)
    out = re.sub(r":\s+", ": ", out)
    # Capitalize start if lowercase artifact
    out = clean_spaces(out)
    if out and out[0].islower():
        out = out[0].upper() + out[1:]
    return out


def extract_wiki_sections(w: dict[str, Any] | None, edid: str) -> dict[str, str]:
    """Group cleaned wiki sections into semantic buckets."""
    buckets: dict[str, list[str]] = {
        "desc": [],
        "layout": [],
        "lore": [],
        "inhab": [],
        "loot": [],
        "quests": [],
        "notes": [],
    }
    if not w:
        return {k: "" for k in buckets}

    skip_headings = {
        "Локации Expeditions: The Pitt",
        "Fallout: Board Game",
        "Появлениe",
        "Появления",
    }
    for sec in w.get("sections", []):
        h = sec.get("heading", "").strip()
        if h in skip_headings:
            continue
        txt = filter_f3_wiki_text(sec.get("text", ""), edid=edid, heading=h)
        if not txt:
            continue
        hl = h.lower()
        if hl in ("описание", "общая информация", "внутри", "внутри здания", "интерьер"):
            buckets["desc"].append(txt)
        elif hl in (
            "планировка",
            "планировка the pitt",
            "строение",
            "местоположение",
            "местонахождение",
            "месторасположение",
            "расположение",
            "окрестности",
            "локации",
            "локации the pitt",
            "здания",
            "места",
            "сопутствующие помещения",
            "северная часть туннелей",
            "центральная часть туннелей",
            "южный склад",
            "склад",
            "туннели",
            "кладовка гэлоу",
            "пост управления коллектором",
            "хранилище",
        ):
            prefix = "" if hl in ("планировка", "описание", "местоположение", "местонахождение") else f"{h}: "
            buckets["layout"].append(prefix + txt)
        elif hl in ("история", "обелиск", "судьба особняка", "файл с терминала «волт-тек»"):
            if hl == "файл с терминала «волт-тек»":
                txt = re.sub(
                    r"^Заметка,\s*находящаяся[^:]*:\s*",
                    "",
                    txt,
                )
            prefix = f"{h}: " if hl != "история" else ""
            buckets["lore"].append(prefix + txt)
        elif hl in ("обитатели", "существа", "персонажи", "враги", "охрана", "население", "жители", "обитатели и находки"):
            # Prefix bare comma-separated name lists cleanly
            if len(txt) < 120 and "." not in txt[:-1]:
                txt = f"В хрониках локации упоминаются: {txt}"
            buckets["inhab"].append(txt)
        elif hl in ("находки", "ценные находки", "значимые находки", "контейнеры", "радио"):
            if re.match(r"^\d+\s", txt):
                txt = f"Среди примечательных находок отмечены: {txt}"
            buckets["loot"].append(txt)
        elif hl in ("квесты", "связанные квесты"):
            buckets["quests"].append(txt)
        elif hl in ("заметки", "возможности", "реакция напарников"):
            buckets["notes"].append(txt)
        else:
            buckets["desc"].append(f"{h}: {txt}")

    return {k: clean_spaces(" ".join(v)) for k, v in buckets.items()}


def infer_role(
    node: dict[str, Any],
    esm: dict[str, Any],
    parent_place: str,
    quests: list[dict[str, Any]],
) -> str:
    """Create a concise, accurate, varied Russian role subtitle for a location node."""
    nid = node["id"]
    edid = node.get("edid", "")
    lbl = node.get("label", "")
    sub = node.get("subtype", "")
    dlc = node.get("dlc", "base")
    mtype = esm.get("markerType") or ""
    ll = lbl.lower()

    if nid in WORLD_CURATED:
        return WORLD_CURATED[nid]["role"]
    if nid in SPECIAL_INTERIORS:
        return SPECIAL_INTERIORS[nid]["role"]

    if sub == "marker":
        if re.match(r"^DC\d+", lbl, re.I):
            if parent_place:
                return f"Секторный маркер карты в руинах Вашингтона (район {parent_place})"
            return "Секторный маркер карты на территории руин Вашингтона"
        if "эвергрин" in ll:
            return "Крупный укреплённый лагерь рейдеров и работорговцев"
        if "церков" in ll or "собор" in ll or "часовн" in ll:
            return "Разрушенная довоенная церковь и точка укрытия на Пустоши"
        if "депо" in ll:
            return "Железнодорожное депо и подземный узел переходов метрополитена"
        if "библиотек" in ll or "архив" in ll or "музей" in ll:
            return "Знаковое историческое и культурное здание довоенного Вашингтона"
        if "кладбищ" in ll:
            return "Крупный исторический мемориал и некрополь в Арлингтоне"
        if "больниц" in ll or "госпитал" in ll:
            return "Разрушенный довоенный госпиталь в центре Вашингтона"
        if "убежище" in ll:
            return "Подземное убежище корпорации «Волт-Тек»"
        if "станция" in ll or "метро" in ll:
            return "Станция метрополитена и подземная развязка Вашингтона"
        if "форт" in ll or "база" in ll:
            return "Укреплённый довоенный военный объект"
        if "такома" in ll or "мама дольче" in ll or "корвега" in ll or "фабрика" in ll:
            return "Крупный довоенный промышленный комплекс"
        if "капитолий" in ll or "белый дом" in ll:
            return "Разрушенный правительственный комплекс столицы США"
        mt_roles = {
            "Город": f"Ключевая городская локация ({translate_worldspace(esm.get('worldspace', ''))})",
            "Поселение": "Укреплённое поселение выживших на Столичной Пустоши",
            "Метро": "Наземный ориентир и узел сообщения столичного метрополитена",
            "Канализация / Коллектор": "Разрушенный городской квартал и узел переходов метрополитена",
            "Офисное здание": "Довоенное офисное здание в руинах округа Колумбия",
            "Памятник": "Знаковый довоенный монумент или исторический комплекс",
            "Городские руины": "Разрушенный городской квартал Столичной Пустоши",
            "Пещера": "Подземная пещера или природное укрытие на Пустоши",
            "Завод / Фабрика": "Крупный довоенный промышленный комплекс",
        }
        return mt_roles.get(mtype, "Отмечаемая локация на карте Столичной Пустоши")

    ctx = parent_place or translate_worldspace(esm.get("worldspace", ""))
    ctx_clean = "" if ctx in ("внутреннее помещение", "Внутренняя локация", "Пустоши", "") else ctx
    # Never append redundant parenthetical like "(Больница Надежды)" to "Больница Надежды"
    if ctx_clean and ctx_clean.strip('"«» ').lower() == lbl.strip('"«» ').lower():
        ctx_clean = ""
    in_ctx = f" ({ctx_clean})" if ctx_clean else ""

    if "FFRadioCache" in edid:
        return f"Потайная дренажная камера с радиомаяком и тайником{in_ctx}"
    if "SatComArray" in edid:
        if edid.endswith("Top"):
            return f"Верхняя смотровая площадка башни связи{in_ctx}"
        return f"Служебный корпус узла спутниковой связи{in_ctx}"
    if edid == "zMq11skybridgeAccess":
        return "Подземный переход к крытому переходу и Заражённому метро"
    if "когтей смерти" in ll:
        return f"Подземная пещера и логово когтей смерти{in_ctx}"
    if "яо-га" in ll:
        return f"Подземная пещера и логово яо-гаев{in_ctx}"
    if "убежище" in ll and "вернера" not in ll and dlc == "base":
        return f"Внутренний сектор подземного комплекса «Волт-Тек»{in_ctx}"
    if edid == "UnderworldConcourse":
        return "Главный зал подземного города гулей в Историческом музее"
    if any(k in ll for k in ("водоочист", "насосн", "подстанц", "электроснабж", "электростанц", "реактор", "вещан", "ретранслят", "мама дольче")):
        return f"Инженерный, промышленный или энергетический объект{in_ctx}"
    if "лодочная станция" in ll or "причал" in ll or "пирс" in ll:
        return f"Прибрежная пристань и технические постройки у воды{in_ctx}"
    if any(k in ll for k in ("коллектор", "канализац", "дренаж")) or re.search(r"\bсточн", ll):
        if "промежуточная станция" in ll or "коллектор" in ll or "канализац" in ll:
            return f"Подземный городской коллектор и технические туннели{in_ctx}"
    if "автомобильный туннель" in ll:
        return f"Обрушенный довоенный автомобильный туннель{in_ctx}"
    if any(k in ll for k in ("метро", "туннел", "перегон", "ветка")) or re.search(r"\bстанция\b", ll):
        return f"Подземная зона: станция или перегон метрополитена{in_ctx}"
    if any(k in ll for k in ("салун", "кафе", "закусоч", "бистро", "ресторан", "клуб", "латунный фонарь")) or re.search(r"\bбар\b", ll):
        return f"Питейное заведение, закусочная или место встреч обитателей{in_ctx}"
    if any(k in ll for k in ("клиника", "больниц", "лазарет", "медицин", "морг")):
        return f"Медицинский или санитарный отсек{in_ctx}"
    if any(k in ll for k in ("магазин", "лавка", "товары", "рынок", "бакалея", "арсенал", "оружейн", "заряжай", "автосалон", "супермарт")):
        return f"Торговая лавка, супермаркет, склад или оружейный зал{in_ctx}"
    if any(k in ll for k in ("штаб-квартира", "бункер", "командован", "аванпост", "укреплен", "крепост", "кольцо", "база ")) or re.search(r"\b(пост|база)\b", ll):
        return f"Укреплённый сектор, командный пункт или военный объект{in_ctx}"
    if any(k in ll for k in ("гостиниц", "мотел", "отель")):
        return f"Довоенная гостиница или мотель{in_ctx}"
    if any(k in ll for k in ("дом ", "хижина", "апартамент", "пентхаус", "номер ", "берлога", "жилище", "жилые", "барак", "казарм", "каюта", "усадьба", "поместье", "комната", "общежити", "палатка", "тайник")) or re.search(r"\bквартира\b", ll):
        return f"Жилое помещение, лагерь или укрытие{in_ctx}"
    if any(k in ll for k in ("завод", "цех", "фабрика", "плавильн", "литей", "сервис-центр", "гараж")):
        return f"Промышленный комплекс или ремонтная мастерская{in_ctx}"
    if any(k in ll for k in ("лаборатор", "институт", "крио", "биологич", "эксперимент")):
        return f"Исследовательская или техническая лаборатория{in_ctx}"
    if any(k in ll for k in ("офис", "кабинет", "администрац", "редакц", "приемн", "архив", "библиотек", "музей", "капитолий", "мемориал", "монумент", "полицейск", "упр-е", "управлен", "диспетчерск", "данвич", "билдинг")):
        return f"Административное, историческое или деловое здание{in_ctx}"
    if any(k in ll for k in ("пещера", "пещеры", "грот", "логово", "шахта", "разрез", "подземел")):
        return f"Подземная пещера, шахта или логово обитателей Пустоши{in_ctx}"
    if any(k in ll for k in ("туалет", "подвал", "погреб", "склад", "кладов", "холл")):
        return f"Подсобное или внутреннее помещение{in_ctx}"
    if dlc == "zeta":
        return f"Отсек инопланетного материнского корабля «Дзета»{in_ctx}"
    if dlc == "pitt":
        return f"Внутренняя зона промышленного Питта{in_ctx}"
    if dlc == "pointlookout":
        return f"Внутренняя локация побережья Пойнт-Лукаут{in_ctx}"
    if dlc == "anchorage":
        return f"Объект виртуальной симуляции освобождения Анкориджа{in_ctx}"
    if dlc == "brokensteel":
        return f"Внутренняя зона кампании Broken Steel{in_ctx}"
    if quests:
        return f"Сюжетно значимая внутренняя локация{in_ctx}"
    return f"Внутренняя локация{in_ctx}"


def summarize_nearest_landmarks(
    node: dict[str, Any],
    coords: list[float] | None,
    named_markers: list[tuple[str, str, list[float]]],
) -> list[str]:
    """Find 3 closest named Wasteland/DC markers by Euclidean XY distance."""
    if not coords or len(coords) < 2:
        return []
    x, y = coords[0], coords[1]
    dists: list[tuple[float, str, str]] = []
    for nid, lbl, mc in named_markers:
        if nid == node["id"]:
            continue
        d = math.hypot(x - mc[0], y - mc[1])
        dists.append((d, lbl, nid))
    dists.sort(key=lambda t: t[0])
    return [lbl for _, lbl, _ in dists[:3]]


def split_creatures(creatures_raw: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Split creature list into hostile/combat threats, friendly/named bots, and ambient livestock/props."""
    hostile: list[str] = []
    friendly: list[str] = []
    ambient: list[str] = []
    seen: set[str] = set()
    for raw in creatures_raw:
        c = translate_entity(raw)
        if c in seen:
            continue
        seen.add(c)
        if c in FRIENDLY_CREATURE_NAMES:
            friendly.append(c)
        elif c in AMBIENT_CREATURE_NAMES:
            ambient.append(c)
        else:
            hostile.append(c)
    return hostile, friendly, ambient


def build_danger_tail(
    node: dict[str, Any],
    esm: dict[str, Any],
    parent_place: str,
    conn_locs: list[dict[str, Any]],
    npcs_clean: list[str],
    crea_hostile: list[str],
    crea_friendly: list[str],
) -> str:
    """Provide grounded tactical/environmental danger context when live details are sparse."""
    edid = node.get("edid", "")
    lbl = node.get("label", "")
    ll = lbl.lower()
    dlc = node.get("dlc", "base")

    if edid == "DLC05SpaceBridge02":
        return (
            "На внешней обшивке корабля «Дзета» прямое оружие и рукопашные атаки недоступны, "
            "а основную опасность представляет падение за красные сигнальные огни в открытый космос."
        )
    if edid == "MS14ArmorVoice":
        return (
            "Присутствующий в служебной ячейке Мистер Храбрец выполняет исключительно техническую роль "
            "озвучивания реплик говорящей силовой брони и не участвует в бою."
        )
    if edid in INVALID_WIKI_EDIDS and (
        "Test" in edid or "test" in edid or "Demo" in edid or "TEMP" in edid or "COPY" in edid
    ):
        return (
            "Зона носит служебный характер в ресурсах игры и не предназначена для боевых столкновений при обычном прохождении."
        )
    if edid.startswith("FFRadioCache"):
        return (
            "Сам подземный тайник закрыт от случайных патрулей, однако подходы к его люку на поверхности "
            "могут контролироваться враждебными обитателями Пустоши."
        )
    if edid.startswith("TL") or "Трэнквилити" in parent_place:
        return (
            "Обычные боевые враги Пустоши в симуляции отсутствуют: угрозу здесь несёт лишь контроль программы Бетти "
            "или запуск аварийного сценария «Китайское вторжение»."
        )
    if re.match(r"^DC\d+", lbl, re.I):
        return (
            "На прилегающих улицах разрушенного Вашингтона регулярно сталкиваются патрули супермутантов, "
            "рейдеров, наёмников «Когтя», а в поздней части кампании — отряды Анклава и Братства Стали."
        )
    if dlc == "zeta":
        return (
            "Отсеки материнского корабля «Дзета» патрулируются чужими, чужими-рабочими, абоминациями, "
            "охранными роботами и потолочными турелями, применяющими энергетическое оружие."
        )
    if dlc == "anchorage":
        return (
            "Внутри виртуальной симуляции Анкориджа ключевыми противниками выступают бойцы китайской армии, "
            "снайперы, невидимые «Красные драгуны», пулемётные доты и бронетехника."
        )
    if dlc == "pointlookout":
        if crea_hostile or npcs_clean:
            return (
                "Как и в других прибрежных районах Пойнт-Лукаута, бой требует осторожности из-за высокой "
                "стойкости болотных дикарей, отравления или радиации у воды и скрытых засад."
            )
        return (
            "Прямых точек появления врагов в этой зоне не прописано, однако на болотах Пойнт-Лукаута "
            "главными угрозами остаются болотные дикари, водяные, болотные гули и радиация."
        )
    if "убежище 106" in ll or "Vault106" in edid:
        return (
            "Сектора Убежища 106 пропитаны психотропным газом, вызывающим галлюцинации и приводящим к стычкам "
            "с обезумевшими обитателями комплекса в узких коридорах."
        )
    if any(k in ll for k in ("метро", "коллектор", "туннел", "пещер", "шахт")):
        return (
            "В замкнутых подземных коридорах путнику стоит учитывать риск засад диких гулей, радтараканов, "
            "рейдеров или супермутантов, а также скопления ловушек и очаги радиации."
        )
    if any("братств" in n.lower() for n in npcs_clean) or "цитадел" in ll or "Цитадель" in parent_place:
        return (
            "Территория строго охраняется бойцами Братства Стали в силовой броне и остаётся мирной "
            "для союзников до тех пор, пока герой не проявит враждебности."
        )
    if crea_hostile:
        return (
            "Учитывая присутствие вооружённых противников или опасных мутантов, осмотр локации требует "
            "боеготовности и запаса медикаментов."
        )
    if npcs_clean:
        return (
            "Обстановка на территории зависит от репутации героя и хода связанных заданий: при соблюдении "
            "местных порядков контакт с обитателями остаётся мирным."
        )
    if conn_locs:
        nbrs = ", ".join(clean_door_name(c["label"]) for c in conn_locs[:3])
        return (
            f"Постоянные враждебные NPC внутри этого помещения не размещены, но боевые угрозы могут ожидать "
            f"сразу за переходами к соседним секторам ({nbrs})."
        )
    return (
        "В ESM внутри этой точки не зафиксировано агрессивных врагов или опасных существ: "
        "локация служит спокойным помещением без прямых боевых столкновений."
    )


def build_summary(
    node: dict[str, Any],
    esm: dict[str, Any],
    wiki_lead: str,
    wiki_buckets: dict[str, str],
    parent_place: str,
    nearest_markers: list[str],
    quests: list[dict[str, Any]],
    npcs_clean: list[str],
    crea_hostile: list[str],
    notable_loot: list[str],
) -> tuple[str, bool]:
    """Compose a vivid 2-4 sentence summary (>110 chars) and return whether desc's first sentence was reused."""
    nid = node["id"]
    lbl = node["label"]
    sub = node.get("subtype", "")
    dlc = node.get("dlc", "base")
    edid = node.get("edid", "")

    if nid in WORLD_CURATED:
        return WORLD_CURATED[nid]["summary"], False
    if nid in SPECIAL_INTERIORS:
        return SPECIAL_INTERIORS[nid]["summary"], False

    sentences: list[str] = []
    reused_desc_first = False

    if wiki_lead and len(wiki_lead) >= 45:
        first = wiki_lead.split(". ")[0].strip()
        if not first.endswith((".", "!", "?")):
            first += "."
        sentences.append(first)
        rest_lead = wiki_lead[len(first) :].strip()
        if rest_lead and len(rest_lead) >= 35:
            second = rest_lead.split(". ")[0].strip()
            if not second.endswith((".", "!", "?")):
                second += "."
            sentences.append(second)
    else:
        ws = translate_worldspace(esm.get("worldspace", ""))
        if sub == "marker" and re.match(r"^DC\d+", lbl, re.I):
            near_txt = f" вблизи ориентиров {', '.join(nearest_markers[:2])}" if nearest_markers else ""
            sentences.append(
                f"{lbl} — служебный маркер карты и путевой ориентир в руинах Вашингтона{near_txt} "
                f"(мир «{ws}», {DLC_LABELS_RU[dlc]})."
            )
        elif sub == "marker":
            mtype = esm.get("markerType") or "локация"
            sentences.append(
                f"«{lbl}» — отмечаемая локация типа «{mtype.lower()}» в регионе «{ws}» ({DLC_LABELS_RU[dlc]})."
            )
        elif "FFRadioCache" in edid:
            sentences.append(
                f"«{lbl}» ({ws}) — потайная подземная дренажная камера на Столичной Пустоши, "
                f"служащая источником одного из зашифрованных радиосигналов."
            )
        elif "SatComArray" in edid:
            part = "верхняя смотровая платформа" if edid.endswith("Top") else "внутренний служебный корпус"
            sentences.append(
                f"«{lbl}» — {part} довоенного комплекса спутниковой связи сети «СатКом» NN-03d на севере Пустоши."
            )
        else:
            place_ctx = parent_place or (ws if ws not in ("внутреннее помещение", "Пустоши") else "")
            if place_ctx:
                sentences.append(
                    f"«{lbl}» — внутренняя локация, относящаяся к комплексу «{place_ctx}» ({DLC_LABELS_RU[dlc]})."
                )
            else:
                sentences.append(
                    f"«{lbl}» — внутренняя локация мира Fallout 3 ({DLC_LABELS_RU[dlc]})."
                )

    doors = [clean_door_name(d) for d in esm.get("doorsTo", [])[:3] if clean_door_name(d) != lbl]
    owner = translate_owner(esm.get("owner", ""))
    if len(sentences) < 2 and wiki_buckets.get("desc"):
        d_first = wiki_buckets["desc"].split(". ")[0].strip()
        if d_first and d_first not in sentences[0]:
            if not d_first.endswith((".", "!", "?")):
                d_first += "."
            sentences.append(d_first)
            reused_desc_first = True

    if doors and len(sentences) < 3:
        sentences.append(f"Локация связана переходами со следующими зонами: {', '.join(doors)}.")
    elif owner and len(sentences) < 3:
        sentences.append(f"Территория контролируется стороной: {owner}.")

    detail_bits: list[str] = []
    if npcs_clean:
        detail_bits.append(f"здесь встречаются {', '.join(npcs_clean[:3])}")
    if crea_hostile:
        hostile_str = ", ".join(lc_phrase(c) for c in crea_hostile[:3])
        detail_bits.append(f"основную угрозу представляют {hostile_str}")
    if quests:
        qnames = ", ".join(format_quest_name(q) for q in quests[:2])
        detail_bits.append(f"место задействовано в миссиях {qnames}")
    elif notable_loot:
        loot_str = ", ".join(lc_phrase(x) for x in notable_loot[:2])
        detail_bits.append(f"среди примечательных находок выделяются {loot_str}")

    if detail_bits and len(sentences) < 4:
        joined = "; ".join(detail_bits)
        sentences.append(joined[0].upper() + joined[1:] + ".")
    elif len(sentences) < 2:
        t_cnt = esm.get("terminalsCount", 0)
        c_cnt = esm.get("containersCount", 0)
        if t_cnt or c_cnt:
            sentences.append(
                f"При осмотре помещения обнаруживаются {t_cnt} терминал(ов) и {c_cnt} контейнер(ов) с припасами."
            )
        else:
            sentences.append(
                "Объект дополняет географию региона и служит точкой перехода или исследования на Пустоши."
            )

    summary = clean_spaces(" ".join(sentences[:4]))
    if len(summary) < 120:
        summary = clean_spaces(
            summary
            + f" В игровой системе локация относится к разделу «{DLC_SHORT_RU[dlc]}» и служит частью взаимосвязанной сети маршрутов Пустоши."
        )
    return summary, reused_desc_first


def build_section_1(
    node: dict[str, Any],
    esm: dict[str, Any],
    wiki_buckets: dict[str, str],
    reused_desc_first: bool,
    parent_place: str,
    nearest_markers: list[str],
    conn_locs: list[dict[str, Any]],
) -> str:
    """Section 1: 'Особенности и устройство'."""
    nid = node["id"]
    lbl = node["label"]
    sub = node.get("subtype", "")
    dlc = node.get("dlc", "base")
    ws = translate_worldspace(esm.get("worldspace", ""))
    parts: list[str] = []

    if nid in WORLD_CURATED and WORLD_CURATED[nid]["sec1_extra"]:
        parts.append(WORLD_CURATED[nid]["sec1_extra"])

    desc_txt = wiki_buckets.get("desc", "")
    if desc_txt and reused_desc_first:
        first = desc_txt.split(". ")[0].strip()
        rest = desc_txt[len(first) :].lstrip(". ").strip()
        if rest:
            desc_txt = rest
    if desc_txt:
        parts.append(desc_txt)
    if wiki_buckets.get("layout"):
        parts.append(wiki_buckets["layout"])
    if wiki_buckets.get("lore"):
        parts.append(wiki_buckets["lore"])

    geo_bits: list[str] = []
    if sub == "world":
        geo_bits.append(f"Тип области: внешний игровой мир ({DLC_LABELS_RU[dlc]}).")
    elif sub == "marker":
        mt = esm.get("markerType") or "Локация"
        coords = esm.get("coords")
        coord_str = (
            f" Координаты на карте мира: X {round(coords[0])}, Y {round(coords[1])}, Z {round(coords[2])}."
            if coords and len(coords) >= 3
            else ""
        )
        if re.match(r"^DC\d+", lbl, re.I):
            near_str = (
                f" Ближайшие именованные ориентиры — {', '.join(nearest_markers)}."
                if nearest_markers
                else ""
            )
            geo_bits.append(
                f"Маркер «{lbl}» (тип: {mt}, мир: «{ws}») обозначает точку перехода в одном из разрушенных секторов "
                f"Вашингтона.{near_str}{coord_str}"
            )
        else:
            geo_bits.append(f"Мир расположения: «{ws}»; категория маркера карты: {mt}.{coord_str}")
    else:
        if parent_place:
            if any(k in parent_place for k in ("служебная", "ресурсы симуляции", "прибрежные воды", "воздушная операция", "столичная система")):
                geo_bits.append(f"Пространственная привязка: {parent_place} ({DLC_LABELS_RU[dlc]}).")
            else:
                geo_bits.append(f"Пространственная привязка: «{parent_place}» ({DLC_LABELS_RU[dlc]}).")
        else:
            ctx = ws if ws not in ("внутреннее помещение", "Пустоши") else "Столичная Пустошь"
            geo_bits.append(f"Пространственная привязка: «{ctx}» ({DLC_LABELS_RU[dlc]}).")

    owner = translate_owner(esm.get("owner", ""))
    if owner:
        geo_bits.append(f"Принадлежность и контроль: {owner}.")

    doors = [clean_door_name(d) for d in esm.get("doorsTo", [])]
    conn_names = [clean_door_name(c["label"]) for c in conn_locs]
    merged_doors: list[str] = []
    for d in doors + conn_names:
        if d and d not in merged_doors and d != lbl:
            merged_doors.append(d)
    if merged_doors:
        geo_bits.append(f"Выходы и связующие переходы ведут к локациям: {', '.join(merged_doors[:10])}.")

    t_cnt = esm.get("terminalsCount", 0)
    c_cnt = esm.get("containersCount", 0)
    if t_cnt > 0 or c_cnt > 0:
        infra: list[str] = []
        if t_cnt > 0:
            infra.append(f"терминалов — {t_cnt}")
        if c_cnt > 0:
            infra.append(f"контейнеров — {c_cnt}")
        geo_bits.append(f"Внутри зафиксированы интерактивные объекты: {', '.join(infra)}.")

    parts.append(" ".join(geo_bits))
    return clean_spaces(" ".join(p for p in parts if p))


def build_section_2(
    node: dict[str, Any],
    esm: dict[str, Any],
    wiki_buckets: dict[str, str],
    parent_place: str,
    conn_locs: list[dict[str, Any]],
) -> str:
    """Section 2: 'Обитатели и опасности'."""
    parts: list[str] = []
    inhab_wiki = wiki_buckets.get("inhab", "")
    if inhab_wiki:
        parts.append(inhab_wiki)

    npcs_clean: list[str] = []
    seen_npc: set[str] = set()
    for raw in esm.get("npcsInCell", []):
        n = translate_entity(raw)
        if n not in seen_npc:
            seen_npc.add(n)
            npcs_clean.append(n)

    hostile, friendly, ambient = split_creatures(esm.get("creaturesInCell", []))

    if npcs_clean:
        # Avoid trivial duplicate if Wiki section already lists the exact single NPC
        if not (inhab_wiki and len(npcs_clean) == 1 and npcs_clean[0] in inhab_wiki):
            parts.append(f"Персонажи и фракции в зоне: {', '.join(npcs_clean)}.")
    if friendly:
        parts.append(f"Дружелюбные или именные спутники и роботы: {', '.join(friendly)}.")
    if hostile:
        parts.append(f"Враждебные существа и боевые единицы: {', '.join(hostile)}.")
    if ambient:
        parts.append(f"Мирная фауна и окружение: {', '.join(ambient)}.")

    joined_so_far = " ".join(parts)
    if len(joined_so_far) < 110:
        parts.append(
            build_danger_tail(node, esm, parent_place, conn_locs, npcs_clean, hostile, friendly)
        )

    return clean_spaces(" ".join(parts))


def build_section_3(
    node: dict[str, Any],
    esm: dict[str, Any],
    wiki_buckets: dict[str, str],
    graph_items: list[dict[str, Any]],
    graph_objects: list[dict[str, Any]],
    quests: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> str:
    """Section 3: 'Находки, объекты и связанные миссии'."""
    parts: list[str] = []

    if wiki_buckets.get("loot"):
        parts.append(wiki_buckets["loot"])

    priority_items: list[str] = []
    seen_it: set[str] = set()
    subtype_rank = {"book": 0, "key": 1, "note": 2, "weapon": 3, "armor": 4, "aid": 5, "misc": 6, "ammo": 7}
    sorted_g_items = sorted(graph_items, key=lambda it: (subtype_rank.get(it["subtype"], 9), it["label"]))
    for it in sorted_g_items:
        lbl = it["label"]
        if it["subtype"] == "misc" and is_junk_item(lbl):
            continue
        if lbl not in seen_it:
            seen_it.add(lbl)
            priority_items.append(lbl)

    for raw in esm.get("notableItems", []):
        base = raw.split(" ×")[0].strip()
        if is_junk_item(raw):
            continue
        if base not in seen_it and raw not in seen_it:
            seen_it.add(base)
            priority_items.append(raw)

    if priority_items:
        parts.append(f"Ключевые предметы и экипировка: {', '.join(priority_items[:14])}.")
    elif esm.get("notableItems"):
        parts.append(f"Из бытовых предметов в интерьере присутствуют: {', '.join(esm['notableItems'][:8])}.")

    notable_objs: list[str] = []
    seen_obj: set[str] = set()
    for ob in graph_objects:
        olbl = ob["label"]
        if olbl in GENERIC_OBJECTS or olbl in seen_obj:
            continue
        if ob["subtype"] in ("terminal", "activator", "container"):
            seen_obj.add(olbl)
            notable_objs.append(olbl)
    if notable_objs:
        parts.append(f"Примечательные объекты и терминалы: {', '.join(notable_objs[:10])}.")

    wq = wiki_buckets.get("quests", "")
    if wq and (not quests or len(wq) > 95 or " — " in wq):
        parts.append(f"Роль в заданиях по хроникам: {wq}")
    if quests:
        qlist = ", ".join(format_quest_name(q) for q in quests[:8])
        parts.append(f"Игровые квесты, затрагивающие локацию: {qlist}.")
    if events:
        elist = ", ".join(f"«{ev['label']}»" for ev in events[:5])
        parts.append(f"Сюжетные события: {elist}.")

    if wiki_buckets.get("notes"):
        parts.append(wiki_buckets["notes"])

    c_cnt = esm.get("containersCount", 0)
    t_cnt = esm.get("terminalsCount", 0)
    joined_so_far = " ".join(parts)
    if not parts:
        if c_cnt or t_cnt:
            parts.append(
                f"Уникальных сюжетных квестов к этой зоне не привязано; при исследовании доступно "
                f"{c_cnt} контейнер(ов) и {t_cnt} терминал(ов) для поиска стандартных припасов и записей."
            )
        else:
            parts.append(
                "Отдельных уникальных артефактов и прямых квестовых целей внутри этой точки не размещено; "
                "локация выполняет прежде всего транзитную, связующую или вспомогательную функцию."
            )
    elif len(joined_so_far) < 100:
        if c_cnt or t_cnt:
            parts.append(
                f"Также в зоне размещено {c_cnt} контейнер(ов) и {t_cnt} терминал(ов), доступных при тщательном осмотре."
            )
        else:
            parts.append(
                "Дополнительных сюжетных квестов или разветвлённых тайников в этой точке не отмечено."
            )

    return clean_spaces(" ".join(parts))


def resolve_parent_place(
    node: dict[str, Any],
    esm: dict[str, Any],
    nodes_by_id: dict[str, dict[str, Any]],
    esm_map: dict[str, dict[str, Any]],
    loc_adj: dict[str, set[str]],
    named_markers: list[tuple[str, str, list[float]]],
) -> str:
    """Determine the real parent complex / district for interiors or DC markers."""
    nid = node["id"]
    edid = node.get("edid", "")
    ws = esm.get("worldspace", "")

    if nid in SPECIAL_INTERIORS:
        return SPECIAL_INTERIORS[nid]["parent"]

    if node["subtype"] == "marker" and re.match(r"^DC\d+", node["label"], re.I):
        nearest = summarize_nearest_landmarks(node, esm.get("coords"), named_markers)
        return nearest[0] if nearest else ""

    if ws and ws not in ("Внутренняя локация", "Пустоши"):
        return translate_worldspace(ws)

    q: deque[tuple[str, int]] = deque([(nid, 0)])
    visited = {nid}
    while q:
        cur, dist = q.popleft()
        if cur != nid:
            cn = nodes_by_id[cur]
            ce = esm_map.get(cur, {})
            if cn["subtype"] == "marker" and not re.match(r"^DC\d+", cn["label"], re.I):
                return cn["label"]
            cws = ce.get("worldspace", "")
            if cws and cws not in ("Внутренняя локация", "Пустоши"):
                return translate_worldspace(cws)
        if dist < 4:
            for nxt in sorted(loc_adj.get(cur, ())):
                if nxt not in visited:
                    visited.add(nxt)
                    q.append((nxt, dist + 1))

    prefix_map = {
        "TL": "Трэнквилити-лейн",
        "PFalls": "Парадиз-Фоллз",
        "Oasis": "Оазис",
        "Citadel": "Цитадель",
        "DLC03zCitadel": "Цитадель",
        "LL": "Литл-Лэмплайт",
        "Vault101": "Убежище 101",
        "Vault106": "Убежище 106",
        "Vault92": "Убежище 92",
        "Vault87": "Убежище 87",
        "Tenpenny": "Тенпенни-Тауэр",
        "DLC03PPurity": "Мемориал Джефферсона",
        "PPurity": "Мемориал Джефферсона",
        "RedRacer": "Завод «Ред Рейсер»",
        "zDCint17to21": "Силовые станции Потомака",
    }
    for pref, pname in prefix_map.items():
        if edid.startswith(pref):
            return pname

    return ""


def verify_output(records: dict[str, dict[str, Any]], expected_ids: set[str]) -> None:
    """Assert strict completeness and quality invariants on generated location records."""
    assert len(records) == 576, f"Expected 576 records, got {len(records)}"
    assert set(records.keys()) == expected_ids, "Mismatch between output keys and graph location IDs"

    bad_tokens = ("{{", "}}", "[[", "]]", "<ref", "{|", "|}", "Игровой мир / крупная внешняя область")
    bad_factions = ("ParadiseFallsResidentFaction", "TenpennyTowerResidentFaction", "RivetCityResidentFaction")

    for nid, rec in records.items():
        assert rec["id"] == nid
        assert rec.get("role") and len(rec["role"]) >= 8, f"Weak role for {nid}"
        summary = rec.get("summary", "")
        assert len(summary) > 110, f"Summary too short ({len(summary)} chars) for {nid}: {summary}"
        secs = rec.get("sections", [])
        assert len(secs) == 3, f"Expected 3 sections for {nid}, got {len(secs)}"
        for idx, expected_title in enumerate(SECTION_TITLES):
            assert secs[idx]["title"] == expected_title, f"Bad section title for {nid}: {secs[idx]['title']}"
            assert len(secs[idx]["text"]) >= 80, (
                f"Short section {expected_title} ({len(secs[idx]['text'])}) for {nid}: {secs[idx]['text']}"
            )
        blob = " ".join([rec["role"], summary] + [s["text"] for s in secs])
        for tok in bad_tokens:
            assert tok not in blob, f"Forbidden token {tok!r} in {nid}"
        for fac in bad_factions:
            assert fac not in blob, f"Raw faction ID {fac!r} leaked in {nid}"
        assert ";;" not in blob, f"Double semicolon in {nid}"
        assert "•" not in blob, f"Raw bullet character in {nid}"
        assert "Fallout 76" not in blob and "Expeditions: The Pitt" not in blob, f"Non-F3 leakage in {nid}"


def main() -> None:
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    with open(DETAILS_PATH, "r", encoding="utf-8") as f:
        details = json.load(f)
    with open(WALKTHROUGHS_PATH, "r", encoding="utf-8") as f:
        walkthroughs = json.load(f)
    with open(ESM_RICH_PATH, "r", encoding="utf-8") as f:
        esm_rich = json.load(f)
    with open(WIKI_RU_PATH, "r", encoding="utf-8") as f:
        wiki_ru = json.load(f)

    nodes_by_id: dict[str, dict[str, Any]] = {n["id"]: n for n in graph["nodes"]}
    loc_nodes = [n for n in graph["nodes"] if n.get("type") == "location"]
    loc_ids = {n["id"] for n in loc_nodes}

    loc_adj: dict[str, set[str]] = defaultdict(set)
    loc_quests: dict[str, list[dict[str, Any]]] = defaultdict(list)
    loc_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    loc_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
    loc_objects: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for edge in graph["edges"]:
        s, t, et = edge["source"], edge["target"], edge["type"]
        if et == "location_connection" and s in loc_ids and t in loc_ids:
            loc_adj[s].add(t)
            loc_adj[t].add(s)
        elif s in loc_ids or t in loc_ids:
            lid = s if s in loc_ids else t
            oid = t if s in loc_ids else s
            other = nodes_by_id.get(oid)
            if not other:
                continue
            if et == "quest_location" and other["type"] == "quest":
                loc_quests[lid].append(other)
            elif et == "event_entity" and other["type"] == "event":
                loc_events[lid].append(other)
            elif et == "location_item" and other["type"] == "item":
                loc_items[lid].append(other)
            elif et == "location_object" and other["type"] == "object":
                loc_objects[lid].append(other)

    named_markers: list[tuple[str, str, list[float]]] = []
    for n in loc_nodes:
        if n["subtype"] == "marker" and not re.match(r"^DC\d+", n["label"], re.I):
            c = details.get(n["id"], {}).get("coords") or esm_rich.get(n["id"], {}).get("coords")
            if c and len(c) >= 2:
                named_markers.append((n["id"], n["label"], c))

    wt_order = {w["id"]: w.get("order", 999) for w in walkthroughs}

    def dedup_nodes(items: list[dict[str, Any]], sort_quest: bool = False) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for it in items:
            if it["id"] not in seen:
                seen.add(it["id"])
                out.append(it)
        if sort_quest:
            out.sort(key=lambda x: (wt_order.get(x["id"], 999), x["label"]))
        return out

    output: dict[str, dict[str, Any]] = {}
    wiki_used_cnt = 0

    for node in loc_nodes:
        nid = node["id"]
        esm = esm_rich.get(nid, {})
        det = details.get(nid, {})
        raw_wiki = wiki_ru.get(nid)
        valid_wiki = raw_wiki if is_valid_wiki(node, raw_wiki) else None

        wiki_lead = strip_epigraph_and_notices(valid_wiki.get("lead", "")) if valid_wiki else ""
        wiki_buckets = extract_wiki_sections(valid_wiki, edid=node.get("edid", ""))

        quests = dedup_nodes(loc_quests.get(nid, []), sort_quest=True)
        events = dedup_nodes(loc_events.get(nid, []))
        items = dedup_nodes(loc_items.get(nid, []))
        objects = dedup_nodes(loc_objects.get(nid, []))
        conn_locs = [nodes_by_id[cid] for cid in sorted(loc_adj.get(nid, ()))]

        coords = det.get("coords") or esm.get("coords")
        nearest_markers = summarize_nearest_landmarks(node, coords, named_markers)
        parent_place = resolve_parent_place(node, esm, nodes_by_id, esm_rich, loc_adj, named_markers)

        npcs_clean: list[str] = []
        seen_n: set[str] = set()
        for raw in esm.get("npcsInCell", []):
            tr = translate_entity(raw)
            if tr not in seen_n:
                seen_n.add(tr)
                npcs_clean.append(tr)
        crea_hostile, _, _ = split_creatures(esm.get("creaturesInCell", []))

        notable_loot: list[str] = []
        for it in items:
            if it["subtype"] != "misc" or not is_junk_item(it["label"]):
                notable_loot.append(it["label"])
        for raw in esm.get("notableItems", []):
            if not is_junk_item(raw):
                notable_loot.append(raw)

        role = infer_role(node, esm, parent_place, quests)
        summary, reused_desc_first = build_summary(
            node,
            esm,
            wiki_lead,
            wiki_buckets,
            parent_place,
            nearest_markers,
            quests,
            npcs_clean,
            crea_hostile,
            notable_loot,
        )
        sec1 = build_section_1(
            node, esm, wiki_buckets, reused_desc_first, parent_place, nearest_markers, conn_locs
        )
        sec2 = build_section_2(node, esm, wiki_buckets, parent_place, conn_locs)
        sec3 = build_section_3(node, esm, wiki_buckets, items, objects, quests, events)

        worldspace_val = esm.get("worldspace") or det.get("worldspace") or "Пустоши"
        marker_type_val = det.get("markerType") or esm.get("markerType")

        entry: dict[str, Any] = {
            "id": nid,
            "role": role,
            "summary": summary,
            "sections": [
                {"title": SECTION_TITLES[0], "text": sec1},
                {"title": SECTION_TITLES[1], "text": sec2},
                {"title": SECTION_TITLES[2], "text": sec3},
            ],
            "worldspace": worldspace_val,
        }
        if marker_type_val:
            entry["markerType"] = marker_type_val
        if coords:
            entry["coords"] = coords
        if valid_wiki and valid_wiki.get("wikiUrl"):
            entry["wikiUrl"] = valid_wiki["wikiUrl"]
            entry["sourceTag"] = "Fallout3.esm + Fallout Wiki (RU)"
            wiki_used_cnt += 1
        else:
            entry["sourceTag"] = "Fallout3.esm"

        output[nid] = entry

    verify_output(output, loc_ids)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(
        f"[OK] Generated {len(output)} location encyclopedia entries "
        f"(wiki+ESM: {wiki_used_cnt}, ESM-only: {len(output) - wiki_used_cnt}) -> {OUT_PATH}"
    )


if __name__ == "__main__":
    main()
