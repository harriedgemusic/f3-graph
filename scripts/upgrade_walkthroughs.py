#!/usr/bin/env python3
"""
Upgrade and complete public/data/walkthroughs.json across all 81 quests:
1. Normalize all 81 quest titles to literary Russian title case (including translating
   the 14 English quest titles using the exact canonical dictionary) and export
   {questNodeId: russianTitle} to /tmp/f3_quest_titles_ru.json.
2. Curate all 15 previously curated=False quests and expand all 34 1-step/2-step
   quests so 100% of all 81 quests have curated=True and 3..5 rich, actionable steps.
3. Clean and translate all English stageLogs and objectives so 0 developer dummy notes
   and 0 English strings remain.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path("/Users/harriedgemusic/Documents/repos/f3-graph")
WALKTHROUGHS_PATH = REPO_ROOT / "public/data/walkthroughs.json"
QUEST_TITLES_TMP_PATH = Path("/tmp/f3_quest_titles_ru.json")

# ---------------------------------------------------------------------------
# 1. Exact Canonical Russian Titles for all 81 Quests (keyed by quest nodeId)
# ---------------------------------------------------------------------------

QUEST_TITLES_RU: dict[str, str] = {
    # Prologue & Main Quest (17)
    "qst_00014e83": "Первые шаги",
    "qst_00014e84": "Быстрое взросление",
    "qst_00014e85": "Будущее в тумане",
    "qst_00014e86": "Побег!",
    "qst_00014e87": "След в след",
    "qst_00014e88": "Радио «Новости Галактики»",
    "qst_00014e89": "Гонка преследования",
    "qst_00014e8a": "Трэнквилити-Лейн",
    "qst_00014e8b": "Живая вода",
    "qst_00014e8c": "По следам",
    "qst_00014e8d": "Спасение из Рая",
    "qst_00014e8e": "Поиски Эдемских кущ",
    "qst_00014e8f": "Американская мечта",
    "qst_00014e90": "Проникновение",
    "qst_00014e91": "Забери его!",
    "qst_00014e93": "Проект «Нечистоты»",
    "qst_000872e6": "Поиски продолжаются",
    # Side Quests & Unmarked Collector Quests (21)
    "qst_00014e94": "Большие проблемы в Большом Городе",
    "qst_00014e95": "Нечеловеческий гамбит",
    "qst_00014e96": "Руководство по выживанию на Пустошах",
    "qst_00014e97": "Они!",
    "qst_00014e98": "Погоня за Ядер-Колой",
    "qst_00014e99": "Глава государства",
    "qst_0005ecfd": "Наследие Линкольна",
    "qst_00014e9b": "Искусственный человек",
    "qst_00014e9c": "Узы крови",
    "qst_0002a274": "Оазис",
    "qst_00014e9e": "Сила Атома",
    "qst_00014e9f": "Тенпенни-Тауэр",
    "qst_00014ea0": "Просто бизнес",
    "qst_00014ea1": "Контрольный выстрел",
    "qst_00014ea2": "Украденная независимость",
    "qst_0009b5bb": "Авраам Вашингтон — покупатель",
    "qst_00014ea3": "Проблемы на домашнем фронте",
    "qst_00014ea4": "Песнь Агаты",
    "qst_00014ea5": "Рейнджеры Рейли",
    "qst_0006f1e8": "Законник",
    "qst_0006f1e7": "Наёмный убийца",
    # Freeform & Companion Recruitment Quests (12)
    "qst_000173d8": "Поручения и заботы Мегатонны",
    "qst_000173d1": "Исследование руин Вашингтона",
    "qst_000173d9": "Поручения в Цитадели Братства Стали",
    "qst_0006136d": "Обучение ношению силовой брони",
    "qst_0009426d": "Наём напарника: Буч Делория",
    "qst_000371d2": "Наём напарника: Харон",
    "qst_000943ec": "Наём напарника: Кловер",
    "qst_000943ed": "Наём напарника: Псина",
    "qst_000943ee": "Наём напарника: Фокс",
    "qst_0002fa33": "Наём напарника: Джерико",
    "qst_000943eb": "Наём напарника: Сержант РЛ-3",
    "qst_00062736": "Наём напарника: Паладин-звезда Кросс",
    # DLC02: Operation: Anchorage (5)
    "qst_010009be": "Помощь Изгоям",
    "qst_010009bf": "Орудия Анкориджа",
    "qst_010009c0": "Подготовка наступления",
    "qst_010014f6": "Операция «Анкоридж»",
    "qst_010034da": "Разведданные симуляции «Анкоридж»",
    # DLC01: The Pitt (4)
    "qst_0200108c": "Проникнуть в Питт",
    "qst_0200108b": "Вредные условия труда",
    "qst_0200108d": "Свободный труд",
    "qst_0200a358": "Найти Билла-Дикаря",
    # DLC03: Broken Steel (6)
    "qst_03000802": "Смерть с небес",
    "qst_03000afd": "Плата за электричество",
    "qst_030011ad": "Кто смел, тот побеждает",
    "qst_03003b42": "Защита караванов",
    "qst_03003b67": "Великолепная лечебная вода!",
    "qst_03004c75": "Святая вода",
    # DLC04: Point Lookout (12)
    "qst_04005846": "Местные нравы",
    "qst_04005847": "Прогулка с духами",
    "qst_04005848": "Шепчущие голоса",
    "qst_04005849": "Мысли под контролем",
    "qst_0400584a": "Схватка интеллектов",
    "qst_0400584b": "Схватка интеллектов",
    "qst_04002f18": "Страны далёкие",
    "qst_04002f47": "Тёмная душа Блэкхолла",
    "qst_04003f70": "Бальзам на душу",
    "qst_0400815c": "Беспризорник Кенни",
    "qst_0400436e": "Бархатный занавес",
    "qst_04009b5e": "Сафари Плика",
    # DLC05: Mothership Zeta (4)
    "qst_05000802": "Не из этого мира",
    "qst_05000803": "Среди звёзд",
    "qst_05000804": "Эта галактика не столь велика...",
    "qst_05005c70": "Крысы в трюме корабля «Зета»",
}


# ---------------------------------------------------------------------------
# 2. Complete Stage Log Filter & Russian Translation Table
# ---------------------------------------------------------------------------

DUMMY_STAGE_LOGS: set[str] = {
    "not used",
    "empty",
    "test",
    ";Test Stage for jump-starting quest",
    ";stage not displayed -- used for dialogue should the player exit the sim",
    ";INITIAL STAGING",
    ";Water Quest Start Stuff",
    ";Disabling MQ11 Enclave and prime elevator",
    "remove old targets",
    "place new targets",
    "reset variables",
    "Clean up loose ends",
    "QUEST FAILS in 244 ONLY if not 150",
    "MSGBOX: Lepelletier dead.",
    "If quest is done, and not being blackmailed, pop a message when Griffon dies",
    "setup pipe duel",
    "setup board duel",
    "set up duel with Split Jack",
    "- and Citadel not exploded (See Bigsley)",
    "- and Citadel is exploded (Complete Quest)",
    "Conversation stage - part 2, brain response",
    "Conversation stage - part 3, tribal response",
    "Conversation stage - part 4 brain response",
    "Conversation stage - part 5, tribal response",
    "Conversation stage - part 6 brain response",
    "Conversation stage - part 7, tribal response",
}

STAGE_LOG_RU: dict[str, str] = {
    # CG01
    "Walk to Dad.": "Подойти к папе в родильном отделении.",
    "Open the crib's gate.": "Открыть дверцу детского манежа.",
    "Exit the crib.": "Выбраться из манежа в детскую комнату.",
    "Look at the S.P.E.C.I.A.L. book.": "Пролистать детскую книжку «К.Р.О.Х.А.» и распределить основные характеристики.",
    "Grab a toy and drag it to the play mat.": "Взять игрушку и перетащить её на игровой коврик.",
    "Trigger Dad's return": "Дождаться возвращения папы в детскую комнату.",
    "Follow Dad.": "Пойти вслед за папой к выходу из комнаты.",
    # CG02
    "Enjoy the party and speak with the guests.": "Отпраздновать десятый день рождения и пообщаться с гостями в кафетерии.",
    "Dad finished talking to player": "Папа завершил поздравительную речь и пригласил спуститься на реакторный уровень.",
    "Follow Dad to my surprise present.": "Проследовать за папой на нижний уровень за подарком-сюрпризом.",
    "Shoot all 3 targets with the BB gun.": "Поразить все 3 мишени из подаренного пневматического ружья.",
    "Use the BB gun to kill the radroach.": "Убить радтаракана из пневматического ружья.",
    "Stand next to Dad so Jonas can take the picture.": "Встать рядом с папой, чтобы Джонас сделал памятный снимок.",
    # CG04
    "Enter the Overseer's office.": "Проникнуть в кабинет Смотрителя Убежища 101.",
    "Use the Overseer's computer to access the secret tunnel.": "Воспользоваться терминалом Смотрителя, чтобы открыть потайной туннель к выходу.",
    "Enter the reactor room.": "Пройти в зал управления реактором.",
    "Turn the power back on.": "Включить подачу электроэнергии.",
    "Player flips first reactor switch -- guards react": "Переключён первый рубильник в реакторном зале — охрана Убежища поднимает тревогу.",
    "Open the vault door.": "Активировать механизм открытия главной двери Убежища 101.",
    "Escape from Vault 101.": "Покинуть Убежище 101 и выйти на Столичную Пустошь.",
    # MQ02
    "Find the Museum of Technology": "Найти Технический музей в руинах Вашингтона.",
    "Retrieve the Virgo II Communications Dish": "Снять антенну связи с макета лунного посадочного модуля «Дева-II».",
    "Find the Washington Monument": "Добраться до Монумента Вашингтона на Молле.",
    "Repair the damaged radio relay": "Установить антенну и починить повреждённый радиоретранслятор на вершине Монумента.",
    "Return to the Galaxy News Radio station and speak with Three Dog.": "Вернуться в студию радиостанции «Новости Галактики» и поговорить с Тридогнайтом.",
    # MQ05
    "Escort Doctor Li inside the Citadel.": "Сопроводить доктора Мэдисон Ли и выживших учёных внутрь Цитадели Братства Стали.",
    # MQ08
    "Locate the underground entrance to Vault 87": "Найти подземный вход в Убежище 87 через пещеры Литл-Лэмплайта.",
    "Retrieve the G.E.C.K.": "Отыскать и забрать Генератор Эдемских Кущ Компактный (ГЭКК).",
    "Rescue Fawkes from the Observation Cells (Optional)": "Освободить супермутанта Фокса из изоляционного блока (дополнительно).",
    "Escape from Vault 87": "Выбраться из лабораторий Убежища 87 с добытым ГЭКК.",
    # MQ09
    "If the player has rescued Fawkes, he is moved outside Raven Rock, and set to wait for the player.": "Если Фокс был освобождён в Убежище 87, он приходит к выходу с базы Рэйвен-Рок на помощь Одинокому Путнику.",
    # MQ10
    "Enter Rivet City through the underwater diving hatch.": "Проникнуть в затопленный отсек Ривет-Сити через подводный водолазный шлюз.",
    "Obtain the prototype power source.": "Отыскать и забрать экспериментальный прототип источника питания.",
    "Return the prototype power source to Scribe Rothchild at the Citadel.": "Доставить прототип источника питания писцу Ротшильду в Цитадель Братства Стали.",
    "Meet with Elder Lyons in his solar.": "Доложить старейшине Оуэну Лайонсу в его зале совещаний.",
    # MS11
    "Activate the detonator at Tenpenny Tower.": "Активировать детонатор атомной бомбы Мегатонны с балкона пентхауса Тенпенни-Тауэр.",
    # MS03
    "Ask Moira about her book.": "Расспросить Мойру Браун в «Магазине на кратере» о её книге.",
    "Help Moira with Chapter 1.": "Помочь Мойре Браун собрать материалы для первой главы «Руководства по выживанию на Пустошах».",
    "MS03a1 basic completion": "Глава 1 (добыча продовольствия в «Супермаге»): основное задание выполнено.",
    "MS03a1 bonus completion": "Глава 1 (добыча продовольствия в «Супермаге»): выполнено с дополнительным условием (найдены медикаменты).",
    "MS03a2 set up for fade and basic completion": "Глава 1 (исследование лучевой болезни): подготовка к базовому осмотру у Мойры.",
    "MS03a2 basic completion after fade up": "Глава 1 (исследование лучевой болезни): получена доза радиации 200 рад и пройдено лечение.",
    "MS03a2 fade out for bonus completion": "Глава 1 (исследование лучевой болезни): подготовка к лечению критического облучения (600+ рад).",
    "MS03a2 bonus completion after fade-out": "Глава 1 (исследование лучевой болезни): выполнено с дополнительным условием и получена способность «Рад-регенерация».",
    "MS03a3 basic completion": "Глава 1 (поход на Минное поле): основное задание по разведке игровой площадки выполнено.",
    "MS03a3 bonus completion": "Глава 1 (поход на Минное поле): выполнено с дополнительным условием (принесена противопехотная мина).",
    "Help Moira with Chapter 2.": "Помочь Мойре Браун с полевыми испытаниями для второй главы «Руководства».",
    "MS03b1 basic completion": "Глава 2 (испытание кротокрысоотпугивателя): основное задание выполнено.",
    "MS03b1 bonus completion": "Глава 2 (испытание кротокрысоотпугивателя): выполнено с дополнительным условием (испытано на 10+ кротокрысах).",
    "MS03b2 basic completion": "Глава 2 (наблюдение за болотниками в Мемориале Анкориджа): устройство наблюдения установлено.",
    "MS03b2 bonus completion": "Глава 2 (наблюдение за болотниками в Мемориале Анкориджа): выполнено без убийства ни одного болотника.",
    "MS03b3 basic fade-out": "Глава 2 (изучение тяжёлых травм): подготовка к медицинской процедуре у Мойры.",
    "MS03b3 basic completion after fade-out": "Глава 2 (изучение тяжёлых травм): основное задание выполнено (здоровье снижено ниже 50%).",
    "MS03b3 bonus fade-out": "Глава 2 (изучение тяжёлых травм): подготовка к лечению увечий.",
    "MS03b3 bonus completion after fade-out": "Глава 2 (изучение тяжёлых травм): выполнено с дополнительным условием (получено увечье конечности).",
    "Help Moira with the last chapter.": "Помочь Мойре Браун завершить третью, заключительную главу «Руководства».",
    "MS03c1 basic completion": "Глава 3 (история Ривет-Сити): основные сведения о создании города собраны.",
    "MS03c1 bonus completion": "Глава 3 (история Ривет-Сити): выяснена подлинная история корабля у Хорэса Пинкертона.",
    "MS03c2 basic completion": "Глава 3 (завод «РобКо»): установлен процессор в главный компьютер комплекса.",
    "MS03c2 bonus completion": "Глава 3 (завод «РобКо»): главный терминал перепрограммирован для оптимизации роботов.",
    "MS03c3 basic completion": "Глава 3 (Арлингтонская библиотека): получен каталог из терминала регистрации.",
    "MS03c3 bonus completion": "Глава 3 (Арлингтонская библиотека): скопирован полный архив данных главного компьютера библиотеки.",
    "Print the manuscript at Hubris Comics Publishing.": "Отпечатать тираж рукописи в типографии издательства «Хьюбрис Комикс».",
    "Bring the printed books back to Lea.": "Вернуть отпечатанные экземпляры книги заказчице.",
    "Moira Brown is dead. Her book will never be written. NO ACHIEVEMENT - QUEST FAILED!": "Мойра Браун погибла. Её книга никогда не будет дописана — задание провалено.",
    "Moira Brown has been convinced to give up on her book.": "Одинокий Путник убедил Мойру Браун отказаться от написания книги (способность «Критик»).",
    "The Wasteland Survival Guide has been distributed throughout the Capitol Wastes, where it may help survivors.": "«Руководство по выживанию на Пустошах» издано и распространено среди обитателей Столичной Пустоши.",
    "The Wasteland Survival Guide has been researched and spread throughout the Capitol Wasteland, where it will help countless survivors.": "Образцовое издание «Руководства по выживанию на Пустошах» распространено по всей Столичной Пустоши и спасёт множество жизней.",
    # MS01
    "start big town quest": "Начато задание по спасению пленников и обороне Большого Города от супермутантов.",
    # MS02
    'Called when the player begins the quest and agrees to stop the "heroes".': "Одинокий Путник согласился помочь дядюшке Роу остановить вражду Механиста и НеМирмики в Общине Кентербери.",
    "Uncle Roe has been killed, somehow... I'm looking at you, player.": "Дядюшка Роу погиб — получить у него денежное вознаграждение больше невозможно.",
    "The Mechanist raids the AntAgonizer's base! Just when the player said he'd join up with the AntAgonizer! What are the odds?!?! Time for a fight!": "Механист врывается в логово НеМирмики сразу после того, как герой предложил ей союз — начинается схватка!",
    "The AntAgonizer raids the Mechanist's base! Just when the player said he'd join up with the Mechanist! What are the odds?!?! Time for a fight!": "НеМирмика атакует мастерскую Механиста сразу после того, как герой встал на его сторону — начинается схватка!",
    "Player has convinced the AntAgonizer to retire": "Одинокий Путник убедил Таню Кристофф отказаться от образа НеМирмики и оставить костюм.",
    "Player has let the AntAgonizer continue on into the Wasteland": "НеМирмика покинула Общину Кентербери и отправилась странствовать по Пустоши.",
    "Player has convinced the Mechanist to retire": "Одинокий Путник убедил Скотта Воллиса оставить роль Механиста и вернуться к мирной жизни.",
    "Player has let the Mechanist continue on, into the wasteland.": "Механист покинул Общину Кентербери и ушёл странствовать по Пустоши.",
    "Player has killed the AntAgonizer.": "НеМирмика повержена в бою.",
    "The player has killed the Mechanist": "Механист повержен в бою.",
    "One of the supers has been dealt with - the player can collect the basic reward and end the quest.": "Один из противников нейтрализован — можно забрать базовую награду у дядюшки Роу.",
    "Both of the supers have been dealt with - the player can collect the bonus reward and end the quest.": "Оба «супергероя» нейтрализованы — можно получить удвоенную награду у дядюшки Роу.",
    "The player has killed the Mechanist and/or AntAgonizer before the quest began, and is immediately rewarded by Roe. CHANGED! If the player does this, now they don't even get the quest, the rewardxp, or the achievement. CHOICE & CONSEQUENCES, PUNK!": "Механист или НеМирмика были устранены ещё до начала задания у дядюшки Роу.",
    # MS04
    "Remove the source of Fire Ants": "Ликвидировать источник появления огненных муравьёв в гнезде под Грейдичем.",
    # MS08
    'NOTE: The quest is actually marked completed in dialog options where you tell Zimmer or Harkness that Harkness is an Android. This quest stays running until the end confrontation scene is resolved, after which this quest is also stopped. This is because you can tell Harkness "your secret is safe with me" which should seem like the quest is complete, but no confrontation occurs, allowing the player to also tell Zimmer about Harkness, in which a confrontation does occur. The confrontation is handled in MS08Fin.': "Задание завершается после раскрытия тайны андроида Харкнессу или доктору Зиммеру (допускается получение обеих наград до финальной развязки).",
    # MS09
    "Deliver Lucy's message to Arefu.": "Доставить письмо Люси Вест её родным в поселение Арефу на разрушенной эстакаде.",
    "Search the West Residence in Arefu.": "Обыскать дом семьи Вест в Арефу и выяснить судьбу родителей Люси.",
    "Report the status of Arefu's residents to Evan King.": "Сообщить Эвану Кингу о результатах проверки жителей Арефу.",
    "Find The Family.": "Отыскать логово «Семьи» в подземных туннелях к северу от Арефу.",
    "Find Ian West.": "Найти Иэна Веста в укрытии «Семьи» на станции метро Мерешти.",
    "Speak to Vance": "Поговорить с лидером «Семьи» Вэнсом о судьбе Иэна Веста и защите Арефу.",
    "Return to Evan King": "Вернуться к Эвану Кингу в Арефу и сообщить об исходе переговоров.",
    # MS15
    "Defend the Rotunda": "Защитить ротонду Национального архива вместе с Сидни от волн супермутантов.",
    # MS16
    "This is called to prepare the quest, once the player has completed MQ05.": "После завершения миссии «Живая вода» в районе Мегатонны начинает транслироваться аварийный радиосигнал Аматы.",
    "Vault 101 door can be opened": "Получен пароль Аматы — входную дверь Убежища 101 теперь можно открыть.",
    "Vault 101 door has been opened. Player will be greeted by Officer Gomez.": "Дверь Убежища 101 открыта; у входа Одинокого Путника встречает офицер Гомес.",
    "Through talking with one of Vault 101's residents, the lockdown's reasons have been explained, as well as one or two possible solutions.": "Жители Убежища 101 рассказали о противостоянии между сторонниками изоляции Смотрителя и повстанцами Аматы.",
    "The player has pledged to stop the Overseer.": "Одинокий Путник пообещал Амате убедить или сместить Смотрителя.",
    "The player has pledged to stop the rebels.": "Одинокий Путник согласился помочь Смотрителю подавить мятеж Аматы.",
    "The player has learned that he could sabotage Vault 101's water chip and force people to leave.": "Одинокий Путник узнал о возможности вывести из строя водный чип Убежища 101, чтобы вынудить жителей выйти на поверхность.",
    "The player has voluntarily chosen to leave the Vault forever. He can still change his mind by talking to a rebel or Gomez and saying he won't actually leave.": "Герой согласился добровольно покинуть Убежище 101, но ещё может изменить решение до выхода за главную дверь.",
    "The player has stopped or killed the Overseer. Now he must report back to the head of the rebels, Amata.": "Смотритель нейтрализован или отстранён от власти — необходимо сообщить об этом Амате.",
    "The player has stopped or killed Amata. Now he must report back to the head of the vault, the Overseer.": "Повстанцы остановлены — необходимо доложить Смотрителю Убежища 101.",
    "The player has sabotaged the vault's water chip. Everyone evacuates the Vault, and the Overseer comes to attack the player. Amata will meet the player at the Vault entrance.": "Система очистки воды саботирована: Убежище 101 готовится к экстренной эвакуации, а Амата встречает героя у выхода.",
    "For one reason or another, the player must leave Vault 101 forever.": "Кризис разрешён, однако Одинокому Путнику приходится навсегда покинуть Убежище 101.",
    "Both faction leaders are dead - Amata and Overseer/Allen Mack": "Оба лидера фракций Убежища 101 (Амата и Смотритель) погибли.",
    "The player has been barred from Vault 101, either by killing the Overseer and being banished by Amata, stopping the rebels and allowing the Overseer to close the vault, or by simply refusing to be involved and leaving.": "Двери Убежища 101 навсегда закрываются за спиной Одинокого Путника.",
    "The player has voluntarily left Vault 101, and the passwords have been changed behind him. QUEST FAILED - NO ACHIEVEMENT OR REWARD!": "Одинокий Путник добровольно покинул Убежище 101, не вмешавшись в конфликт, и коды доступа были сменены — задание провалено.",
    "The events inside have been resolved peacefully, but the player is still exiled from Vault 101.": "Кризис в Убежище 101 разрешён мирным путём, но ради безопасности общины Одинокий Путник отправляется в изгнание.",
    "The Overseer has been told to evacuate Vault 101, and it is now empty and poisoned, and its citizens are all either dead or wandering the wastes.": "Из-за разрушения системы водоснабжения жители вынуждены эвакуироваться из Убежища 101 на Столичную Пустошь.",
    # MS17
    "Recover the Soil Stradivarius from Vault 92": "Найти скрипку Страдивари в звукозаписывающих студиях Убежища 92.",
    "Return to Agatha": "Вернуть скрипку Страдивари старой Агате в её дом.",
    # MS18
    "Find the Statesman Hotel": "Добраться до гостиницы «Стейтсмен» через площадь Вернон и больницу «Надежда».",
    "Locate Reilly's Rangers": "Подняться на крышу гостиницы «Стейтсмен» к осаждённому отряду «Рейнджеров Рейли».",
    "Lead Reilly's Rangers to safety": "Прикрыть отход «Рейнджеров Рейли» через этажи гостиницы и ресторан.",
    "Get to the Metro Entrance": "Вывести выживших рейнджеров из гостиницы к выходу на поверхность.",
    "Return to Reilly at Ranger Compound": "Вернуться на базу «Рейнджеров Рейли» за наградой.",
    # DLC02
    "Investigate the Outcast Radio Signal.": "Исследовать радиосигнал Братства Изгоев в районе Бейлис-Кроссроудс.",
    "Assist the Outcast soldiers.": "Помочь бойцам Изгоев прорваться через позиции супермутантов к аванпосту.",
    "Speak with the Outcast Leader.": "Переговорить с Защитником Мак-Гроу в подземном бункере Изгоев.",
    "Explore the VSS facility.": "Осмотреть комплекс виртуального стратегического симулятора и получить нейрокостюм у специалистке Олин.",
    "Enter the simulation pod.": "Сесть в капсулу виртуальной реальности и запустить симуляцию «Анкоридж».",
    "Guns of Anchorage Completed": "Китайские артиллерийские орудия на утёсах уничтожены — операция «Орудия Анкориджа» завершена.",
    "Quest Completed": "Станция прослушки и топливное депо танков «Химера» зачищены — путь для главного наступления открыт.",
    'Handles award player with "Intel"': "Получен чемоданчик с разведданными внутри симуляции «Анкоридж» (сбор всех 10 даёт способность «Секретная операция»).",
    "start doctor healing": "Полевой врач доктор Адами проводит лечение в передовом лагере армии США.",
    # DLC01
    "Player has started the quest, must travel through Uptown to get to Haven": "Путь через Аптаун к башне Хэйвен на аудиенцию к лорду Исмаилу Ашуру.",
    "Player has entered Haven, must talk to Ashur at the top floor": "Вход в Хэйвен — необходимо подняться на верхний этаж к Исмаилу Ашуру.",
    "Player has finished talking with Ashur, Ashur is talking with intercom before leaving": "Беседа с Ашуром завершена; правитель Питта отдаёт распоряжения по интеркому.",
    "Ashur has talked to the intercom, made his pitch to the player, and is leaving": "Ашур изложил своё видение будущего Питта и предоставил доступ к лаборатории Сандры.",
    "Player has found out that the baby is the cure, must decide to kidnap or leave without it": "В лаборатории обнаружено, что источником иммунитета является младенец Мари — предстоит решить, похищать ли ребёнка.",
    "Player has left without the baby, stuck on Path A - Slaves are now hostile to player. Player must talk to Midea to find Wernher.": "Одинокий Путник покинул Хэйвен без ребёнка (путь Ашура) — восставшие рабы становятся враждебны.",
    "Player has left with the baby, stuck on Path B (for now), and Raiders are now hostile. Player is instructed to bring the baby to Midea": "Одинокий Путник забрал младенца Мари из колыбели — охрана и рейдеры Питта поднимают тревогу.",
    "Player has talked to Midea, and now knows where Wernher is - either to stop him, or to bring him the baby.": "Разговор с Мидеей: получены координаты тайного убежища Вернера на Сталелитейном дворе.",
    "Player has talked to Wernher, and must now make a choice to help him or oppose him": "Встреча с Вернером в его укрытии и окончательный выбор стороны в конфликте.",
    "Player has killed Wernher or convinced him to leave, now stuck on Path A": "Вернер убит или изгнан из Питта — восстание остановлено в пользу Ашура.",
    "Player has given the baby to Wernher, now stuck on Path B - told about light controller": "Младенец Мари передан Вернеру — получено задание отключить прожекторы на Сталелитейном дворе, чтобы впустить трогов в Аптаун.",
    "Player has returned the baby to Ashur's crib": "Младенец Мари возвращён родителям в башню Хэйвен.",
    "Player has deactivated the lights, and must exit Haven": "Защитные прожекторы отключены, троги прорываются в Аптаун — время для финальной схватки с Ашуром.",
    "(quest completed stage - PATH A)": "Задание завершено на стороне лорда Исмаила Ашура.",
    "(quest completed - PATH B)": "Задание завершено на стороне восставших рабов и Вернера.",
    "(No paths can be completed, quest failed, end DLC main quest)": "Задание провалено.",
    # DLC03
    "Start DLC03 Encounters": "Начато расследование нападений на водные караваны вокруг Ривет-Сити.",
    "setup knife duel": "Вызов главаря банды Одноглазого Джека на поединок в холодном оружии (нож, свинцовая труба или доска с гвоздями).",
    "player broke the rules of the duel (see DLC03SplitJackScript)": "Одинокий Путник нарушил правила честной дуэли — вся банда Одноглазого Джека вступает в бой.",
    "player won duel": "Одноглазый Джек повержен в честном поединке один на один.",
    "Convince gang to leave": "Банда убеждена прекратить налёты на водные караваны и покинуть товарную станцию Вильхельма.",
    "Player has option to extort Officer Lepelletier": "Появилась возможность потребовать с офицера Лепеллетье плату за «защиту» караванов.",
    "player extorted protection deal from Lepelleiter": "Офицер Лепеллетье вынуждена заключить сделку о регулярной выплате дани за безопасность караванов.",
    "player extorted one time 500 caps and no contract from Lepelletier": "С офицера Лепеллетье получена единовременная выплата в 500 крышек.",
    "FAIL QUEST happens here (because 255 is set when Lepelletier dies, and shouldn't end the quest in the case that you have the objective to get reward from Bigsley, killing her at that point isn't a fail.)": "Задание провалено из-за гибели офицера Лепеллетье до завершения расследования.",
    "player finds out from one of few ways, that Griffon has a bottle facility somewhere (whether there is a quest target or not depends on if he knows it's location, see quest objectives for condition)": "Выяснено, что Гриффон разливает поддельную воду «Аква Кура» в подземном цехе на станции «Управление музеями».",
    "Fail Quest": "Задание провалено.",
    "Player has found water pamphlet or seen water scene (or talks to Brother Gerard) - knows to go to Monastery": "Найдена брошюра секты или состоялся разговор с братом Джерардом — получена наводка на монастырь Вечного Света в Спрингвейле.",
    "Player needs to drink the Holy Water": "Для проверки лояльности необходимо выпить «святой воды».",
    "player has drunk the holy water": "Одинокий Путник выпил радиоактивную «святую воду».",
    'Player has spoken with Gerard - knows they\'re making "holy water," and how to get in': "Брат Джерард рассказал об обряде облучения и производстве «святой воды» в монастыре.",
    "Player has entered the Monastery nonviolently": "Одинокий Путник мирно допущен в подземелье монастыря Вечного Света.",
    "Player has gained entrance to Monastery through violence": "Одинокий Путник силой пробился в монастырь Вечного Света.",
    "Player has stopped Apostles nonviolently - report back to Bigsley": "Мать Кюри III убеждена прекратить отравление караванов без кровопролития — пора доложить писцу Бигсли.",
    "Player has stopped Apostles through violence - report back to Bigsley": "Апостолы Вечного Света ликвидированы в бою — пора доложить писцу Бигсли.",
    "Player blew up Megaton": "Мегатонна уничтожена взрывом атомной бомбы — необходимо сообщить писцу Бигсли о прекращении поставок в кратер.",
    "Player has reported back to Bigsley about the events in Megaton": "Писец Бигсли принял отчёт о разрешении кризиса с водой в Мегатонне и Спрингвейле.",
    # DLC04
    "Player is told about Punga and Riverboat": "Получены сведения о плодах панги и речном пароме «Бродячая герцогиня» на причале Потомака.",
    "Player has agreed to search for Nadine": "Одинокий Путник согласился помочь Кэтрин разыскать её пропавшую дочь Надин в Пойнт-Лукауте.",
    "Player talks with Tobar about going to Point Lookout": "Разговор с паромщиком Тобаром о покупке билета до Пойнт-Лукаута.",
    "Player agrees to go to Point Lookout with Tobar": "Приобретён билет на паром «Бродячая герцогиня» до Пойнт-Лукаута.",
    "Player uses the bed in the boat - move boat to new world": "Отдых в пассажирской каюте парома во время плавания к побережью Мэриленда.",
    "Tobar welcomes you to Point Lookout": "Прибытие на пирс Пилигримов в Пойнт-Лукауте.",
    "Player arrives at the Mansion, gates close": "Одинокий Путник подходит к особняку Кальвертов, где дикари начинают штурм.",
    "Player has come to the Mansion, and heard he has to go inside": "Десмонд Локхарт через интерком требует немедленно войти внутрь особняка.",
    "Begin Mansion Onslaught": "Начало обороны особняка Кальвертов вместе с Десмондом Локхартом и его псами.",
    "siege pt 1": "Отражение первой волны дикарей на первом этаже и у баррикад.",
    "siege pt 2": "Отражение прорыва дикарей через крышу и верхние комнаты особняка.",
    "siege pt 3": "Взрыв газа в крыле особняка и ликвидация последней группы нападающих.",
    "Post Onslaught, Desmond goes to talk to player": "Осада отбита; Десмонд Локхарт предлагает сделку по внедрению в культ дикарей.",
    "(Quest Ends, start DLC04MQ02)": "Оборона особняка завершена — переход к заданию «Прогулка с духами».",
    "Quest start": "Начато задание по проникновению в Собор Ковчега и Голубя.",
    "Player agrees to the plan and receives info from Desmond": "Десмонд Локхарт объяснил условия испытания дикарей на Священном болоте.",
    "Player reports to the Cathedral, is told about ritual": "Разговор с привратником у ворот Собора: для вступления в общину необходимо пройти ритуал у Матери-Панги.",
    "Player has acquired seeds from the Mother Pod": "Собраны семена с гигантской Матери-Панги в глубине Священного болота; начинаются галлюцинации от спор.",
    "Player passes out and wakes up outside the bog, post-hallucinations": "Одинокий Путник переживает видения на болоте, теряет сознание и приходит в себя у выхода из топи.",
    "Player returns to Cathedral, is welcomed as member": "Семена доставлены в Собор — культисты принимают героя в свои ряды, где его встречает Надин.",
    "quest completed, start MQ03": "Обряд посвящения пройден — переход к заданию «Шепчущие голоса».",
    "Player is welcomed into the tribals": "Одинокий Путник получил свободный доступ на территорию Собора Ковчега и Голубя.",
    "Player learns Jackson is not there, and where to find him": "От Надин и культистов получены сведения о том, что лидер секты Джексон ушёл в морской грот.",
    "Player has reported back to Desmond, and is told to track down Jackson": "Десмонд Локхарт поручил проследить за Джексоном в прибрежных пещерах.",
    "Player triggers Jackson/Brain scene in the sea cave": "В морском гроте обнаружен Джексон, беседующий с голографической проекцией мозга.",
    "Conversation over, Jackson leaves": "Тайная беседа Джексона с голограммой профессора Кальверта завершена.",
    "Jackson leaves the scene uninterrupted, or player has talked with him and dismissed him - the brain notices the player and talks to him (or waits to talk to him, until the player approaches close enough).": "Профессор Кальверт замечает Одинокого Путника через проектор и обращается к нему напрямую.",
    "Player kills Jackson": "Лидер культистов Джексон убит в морском гроте.",
    "Player addressed by Brain": "Мозг профессора Кальверта предлагает Одинокому Путнику работать против Десмонда.",
    "Quest ends.": "Тайна «голоса» дикарей раскрыта — переход к заданию «Мысли под контролем».",
    "Marguerite has asked me to collect ingredients for her tonic whiskey.": "Маргарита попросила собрать ингредиенты (дрожжи, плоды панги и ядерные батареи) для её фирменного самогона.",
    "Marguerite is brewing some whiskey. I should check back when it's done.": "Маргарита запустила перегонный аппарат — через сутки можно забрать готовую партию самогона.",
    "TAG -- Game over": "Игра в салки с Кенни в пещере Херцога завершена.",
    "TAG -- Kenny's it": "Игра в салки: Кенни водит и догоняет Одинокого Путника.",
    "TAG -- Player's It": "Игра в салки: Одинокий Путник водит и должен осалить Кенни.",
    "HIDE & SEEK -- Game over": "Игра в прятки с Кенни завершена.",
    "HIDE & SEEK -- Kenny hiding, player seeking": "Игра в прятки: Кенни прячется в штольнях шахты, а Одинокий Путник ищет его.",
    "HIDE & SEEK -- player hiding, Kenny seeking": "Игра в прятки: Одинокий Путник прячется, а Кенни отправляется на поиски.",
    # DLC05
    "This is for the Maint Level Teleporter": "Активирован телепорт технического уровня корабля «Зета».",
    "; This stage just denotes that player has started the sewage bit": "Одинокий Путник попадает в систему сброса отходов и технический трюм корабля «Зета».",
    "; Player has spoken to sally in the cart": "Состоялся разговор с Салли у транспортной тележки в техническом отсеке.",
    "; stage for after player crashes into sewer area": "Падение в нижний коллектор мусоропровода корабля «Зета».",
    "; player and Sally are splitting up.": "Салли уходит по вентиляционному лазу к пульту управления, чтобы открывать шлюзы.",
    "; player has entered sewer02 (the main/regular level)": "Переход на основной уровень технического трюма, кишащий инопланетными червями и дронами.",
    "; Player is almost to Sally's control room spot.": "Прорыв к диспетчерской рубке, где ждёт Салли.",
    "; player and Sally had control room conversation and now must leave.": "Встреча с Салли в рубке управления — путь к телепорту открыт.",
    "; player has finished the sewers sub-level": "Зачистка технического трюма корабля «Зета» успешно завершена.",
}


# ---------------------------------------------------------------------------
# 3. Upgraded Walkthrough Content for all 49 Quests (15 uncurated + 34 <3 steps)
# ---------------------------------------------------------------------------

UPGRADED_GUIDES: dict[str, dict[str, Any]] = {
    # =========================================================================
    # ОСНОВНОЙ СЮЖЕТ (ДОПОЛНИТЕЛЬНЫЕ И СВЯЗУЮЩИЕ ВЕТКИ)
    # =========================================================================
    "MQSearch": {
        "order": 5,
        "summary": "Сквозная сюжетная веха первой половины основной кампании Fallout 3: розыск сбежавшего из Убежища 101 отца Джеймса через зацепки в Мегатонне, эфир радиостанции «Новости Галактики», лабораторию Ривет-Сити и гараж Смита Кейси.",
        "startCondition": "Начинается автоматически при выходе из Убежища 101 на Столичную Пустошь в конце пролога «Побег!».",
        "prerequisites": ["CG04"],
        "rewards": [
            "Сюжетные переходы к заданиям «След в след», «Радио „Новости Галактики“» и «Гонка преследования»",
            "Открытие ключевых поселений Столичной Пустоши (Мегатонна, Ривет-Сити, Убежище 112)",
        ],
        "missableWarnings": [
            "Если сразу прийти в Ривет-Сити или гараж Смита Кейси, промежуточные этапы «След в след» и «Радио „Новости Галактики“» завершатся досрочно — чтобы не потерять опыт и ключ от тайника Тридогнайта, проходите цепочку последовательно.",
        ],
        "steps": [
            {
                "title": "Наведите справки о Джеймсе в Мегатонне",
                "description": "Спуститесь от деревянной обзорной площадки Убежища 101 через руины Спрингвейла к воротам Мегатонны. Расспросите шерифа Лукаса Симмса и владельца салуна Колина Мориарти о недавнем визите вашего отца.",
                "skillChecks": ["Красноречие", "Взлом 25", "Наука 25"],
                "tip": "Записи о маршруте Джеймса можно прочитать бесплатно, взломав терминал Мориарти в заднем кабинете салуна.",
            },
            {
                "title": "Проследите маршрут от студии Тридогнайта до Ривет-Сити",
                "description": "По наводке Мориарти доберитесь через линии метро до здания «Новостей Галактики» и поговорите с диджеем Тридогнайтом, который направит вас к доктору Мэдисон Ли в научную лабораторию авианосца Ривет-Сити.",
                "skillChecks": ["Красноречие"],
            },
            {
                "title": "Изучите дневники в Мемориале Джефферсона и найдите Убежище 112",
                "description": "В ротонде проекта «Чистота» прослушайте голодиски Джеймса (особенно запись № 10), из которых выяснится, что отец отправился к доктору Станисласу Брауну в Убежище 112 под гаражом Смита Кейси.",
            },
        ],
    },
    "MQ10": {
        "order": 14,
        "summary": "Вырезанная миссия основного сюжета «Проникновение» (Infiltration), сохранившаяся в ресурсах базового файла Fallout3.esm между побегом с базы Рэйвен-Рок и финальным штурмом «Забери его!»: тайная вылазка в затопленный трюм Ривет-Сити за прототипом источника питания для Либерти Прайма.",
        "startCondition": "В финальной версии игры квест отключён в сюжетном скрипте после «Американской мечты» и доступен только через архив ресурсов или консольную команду.",
        "prerequisites": ["MQ09"],
        "rewards": [
            "Прототип источника питания для запуска гигантского робота Либерти Прайма",
            "Доступ к финальному совещанию у старейшины Оуэна Лайонса перед операцией «Забери его!»",
        ],
        "missableWarnings": [
            "Миссия является архивной вехой разработки: в релизной версии Fallout 3 писец Ротшильд запускает Либерти Прайма сразу по возвращении героя из Рэйвен-Рок.",
        ],
        "steps": [
            {
                "title": "Проникните в Ривет-Сити через подводный шлюз",
                "description": "Согласно первому этапу задания (Stage 10), Одинокому Путнику предстояло нырнуть к подводному водолазному люку отломанного носа авианосца Ривет-Сити, чтобы попасть в изолированные технические отсеки.",
                "tip": "Этот же подводный маршрут используется в побочных квестах «Руководство по выживанию на Пустошах» и «Искусственный человек» для визита к Хорэсу Пинкертону.",
            },
            {
                "title": "Добудьте экспериментальный источник питания",
                "description": "На втором этапе (Stage 20) требовалось преодолеть затопленные коридоры и ловушки внутри корабельного трюма, чтобы извлечь довоенный прототип энергоблока.",
            },
            {
                "title": "Доставьте прототип писцу Ротшильду в Цитадель",
                "description": "На третьем этапе (Stage 30) добытый энергоисточник необходимо было принести главному технологу Братства Стали писцу Ротшильду в лабораторное крыло Цитадели для завершения сборки Либерти Прайма.",
            },
            {
                "title": "Доложите старейшине Лайонсу в зале совещаний",
                "description": "На заключительном этапе (Stage 40) герой поднимался в зал совещаний старейшины Оуэна Лайонса и стража Сары Лайонс, откуда начинался марш к Мемориалу Джефферсона.",
            },
        ],
    },
    "MQA": {
        "order": 16,
        "summary": "Этическая кульминация основного сюжета в ротонде Мемориала Джефферсона: решить, что сделать с ампулой модифицированного вируса ВРЭ, полученной от суперкомпьютера президента Эдема на базе Рэйвен-Рок.",
        "startCondition": "Активируется автоматически после получения ампулы с модифицированным ВРЭ от президента Джона Генри Эдема в задании «Американская мечта».",
        "prerequisites": ["MQ09"],
        "rewards": [
            "+250 очков доброй кармы при передаче ампулы ВРЭ старейшине Лайонсу",
            "Альтернативные финальные слайды концовки и особые последствия для питьевой воды в дополнении Broken Steel",
        ],
        "missableWarnings": [
            "ВНИМАНИЕ: Если ввести ампулу модифицированного ВРЭ в консоль очистителя, вся вода «Аква Пура» в Broken Steel станет смертельно ядовитой для жителей Пустоши и для самого Одинокого Путника (употребление нескольких бутылок приведёт к мгновенной смерти)!",
        ],
        "steps": [
            {
                "title": "Получите ампулу модифицированного ВРЭ в Рэйвен-Рок",
                "description": "На верхнем уровне базы Анклава Рэйвен-Рок выслушайте предложение президента Джона Генри Эдема и заберите со стойки контейнера ампулу с модифицированным штаммом вируса рукотворной эволюции (ВРЭ), созданным для уничтожения всех мутировавших существ через питьевую воду.",
            },
            {
                "title": "Обсудите находку со старейшиной Лайонсом в Цитадели",
                "description": "Во время военного совета в лаборатории Цитадели перед началом штурма «Забери его!» вы можете сразу рассказать старейшине Оуэну Лайонсу о замысле Эдема и передать ему опасный контейнер либо сохранить ампулу при себе до входа в Мемориал Джефферсона.",
                "branches": [
                    {
                        "label": "Отдать вирус ВРЭ старейшине Лайонсу",
                        "tone": "good",
                        "summary": "Добровольно передайте ампулу ВРЭ руководству Братства Стали в Цитадели.",
                        "outcome": "Вы получаете высокую положительную карму, а угроза заражения проекта «Чистота» устраняется заранее.",
                    },
                    {
                        "label": "Оставить ампулу при себе до финала",
                        "tone": "neutral",
                        "summary": "Утаите наличие вируса до проникновения в зал управления очистителем.",
                        "outcome": "Окончательное решение остаётся за вами непосредственно у пульта ротонды.",
                    },
                ],
            },
            {
                "title": "Сделайте выбор у панели фильтрации проекта «Чистота»",
                "description": "Победив полковника Августа Огастуса Отэмна в ротонде Мемориала Джефферсона, подойдите к боковому приемнику реагентов перед вводом кода «2-1-6».",
                "branches": [
                    {
                        "label": "Запустить очиститель без вируса ВРЭ",
                        "tone": "good",
                        "summary": "Не вставляйте капсулу ВРЭ в систему фильтрации и введите код активации 2-1-6.",
                        "outcome": "Столичная Пустошь получает чистую целебную воду без скрытого геноцида.",
                    },
                    {
                        "label": "Ввести модифицированный ВРЭ в систему",
                        "tone": "evil",
                        "summary": "Поместите ампулу Эдема в приёмник консоли перед запуском очистителя.",
                        "outcome": "Крупная потеря кармы; в концовке и в Broken Steel заражённая вода «Аква Пура» вызывает массовую гибель людей и мутантов.",
                    },
                ],
            },
        ],
    },

    # =========================================================================
    # ПОБОЧНЫЕ КВЕСТЫ (РАСШИРЕНИЕ ДО 3–4 ДЕТАЛЬНЫХ ШАГОВ)
    # =========================================================================
    "MS11": {
        "order": 17,
        "summary": "Судьба города Мегатонны: обезвредить неразорвавшуюся атомную бомбу в центре кратера по просьбе шерифа Лукаса Симмса или установить на неё импульсный детонатор по заказу агента Тенпенни мистера Берка.",
        "startCondition": "Поговорите с шерифом Лукасом Симмсом у ворот Мегатонны или с мистером Берком в дальнем углу салуна Мориарти.",
        "prerequisites": [],
        "rewards": [
            "Собственный дом в Мегатонне + робот-дворецкий Уодсворт + 100–500 крышек (Добрый путь)",
            "Люкс в пентхаусе Тенпенни-Тауэр + 500–1000 крышек (Злой путь)",
            "Китайский автомат, фуражка и плащ шерифа (если дать Берку застрелить Симмса)",
        ],
        "missableWarnings": [
            "Взрыв Мегатонны навсегда уничтожает город и почти всех его жителей (кроме Мойры Браун, которая превратится в гуля).",
            "ОБЯЗАТЕЛЬНО заберите Пупс «Сила» со стола в спальне дома Лукаса Симмса до возможного уничтожения Мегатонны!",
        ],
        "steps": [
            {
                "title": "Выслушайте шерифа Симмса и мистера Берка",
                "description": "При входе в Мегатонну поговорите с шерифом Лукасом Симмсом о бомбе в центре кратера (проверка Красноречия повысит награду со 100 до 500 крышек). Затем зайдите в салун Мориарти, где мистер Берк предложит импульсный взрыватель и до 1000 крышек за подрыв города.",
                "skillChecks": ["Красноречие", "Бартер"],
            },
            {
                "title": "Решите, выдавать ли мистера Берка шерифу",
                "description": "Если вы сообщите Лукасу Симмсу о заговоре Берка и пойдёте вместе с ним в салун для ареста, Берк выхватит пистолет с глушителем, как только шериф повернётся спиной. Успейте застрелить Берка первым, чтобы спасти жизнь Симмсу!",
                "tip": "Если Симмс всё же погибнет, квест по разминированию примет его сын Харден Симмс, а с тела шерифа можно забрать уникальный плащ, шляпу, ключ от дома и китайский автомат.",
            },
            {
                "title": "Разминируйте бомбу или установите импульсный взрыватель",
                "description": "Спуститесь в радиоактивную лужу у подножия бомбы в центре Мегатонны. Для обезвреживания или установки детонатора требуется навык «Взрывчатка» не ниже 25.",
                "skillChecks": ["Взрывчатка 25"],
                "tip": "Если навыка «Взрывчатка» не хватает, примите таблетку «Ментатов» (+5 к Восприятию и +10 к Взрывчатке) — их можно взять у Лео Стала или купить у Мойры.",
                "branches": [
                    {
                        "label": "Обезвредить атомную бомбу (Добрый путь)",
                        "tone": "good",
                        "summary": "Отключите взрыватель бомбы и доложите шерифу Лукасу (или Хардену) Симмсу.",
                        "outcome": "+200 доброй кармы, 100–500 крышек и ключи от собственного дома в Мегатонне.",
                    },
                    {
                        "label": "Установить детонатор и взорвать город (Злой путь)",
                        "tone": "evil",
                        "summary": "Закрепите импульсный заряд Берка, отправляйтесь на балкон Тенпенни-Тауэр и нажмите кнопку детонатора.",
                        "outcome": "-1000 кармы, 500–1000 крышек и ключи от роскошного номера в Тенпенни-Тауэр.",
                    },
                ],
            },
        ],
    },
    "MS01": {
        "order": 19,
        "summary": "Спасение жителей Большого Города: повзрослевшие изгнанники из Литл-Лэмплайта страдают от постоянных налётов супермутантов, похитивших врача Рыжую и охотника Коротышку в полицейский участок Джермантауна.",
        "startCondition": "Поговорите с часовым Дасти у моста в Большой Город (к северу от Спрингвейла) или с любым из поселенцев.",
        "prerequisites": [],
        "rewards": [
            "300–500 крышек от Рыжей (или лечение в клинике)",
            "Счастливый бильярдный шар № 8 (+1 к Удаче, пока лежит в инвентаре — подарок от Лютика после лечения в клинике!)",
            "Схема «Крышко-мины» и обучение у Горькой Купчихи",
        ],
        "missableWarnings": [
            "Перед выходом из Большого Города зайдите в клинику и вылечите Лютика (Медицина 40): после завершения квеста он подарит уникальный «Счастливый бильярдный шар» (+1 к Удаче)!",
            "После возвращения Рыжей обязательно останьтесь и обучите поселенцев обороне — иначе супермутанты перебьют весь город в ваше отсутствие.",
        ],
        "steps": [
            {
                "title": "Осмотрите Большой Город и помогите Лютику",
                "description": "Перейдите мост в Большой Город, выслушайте Дасти и загляните в лазарет Рыжей, где на койке лежит раненый Лютик. Окажите ему первую помощь (проверка навыка «Медицина» 40 или «Удача» 7), чтобы спасти ему жизнь.",
                "skillChecks": ["Медицина 40", "Удача 7"],
            },
            {
                "title": "Проникните в полицейский участок Джермантауна",
                "description": "Отправляйтесь на северо-восток к штаб-квартире полиции Джермантауна. Обойдите мины и снайпера на вышке, войдите через верхний этаж или чёрный ход и спуститесь в камеры предварительного заключения на среднем уровне, где держат Рыжую.",
                "skillChecks": ["Взлом 50", "Скрытность"],
                "tip": "Ключ от камер можно снять с пояса супермутанта-тюремщика, если навык «Взлом» ниже 50.",
            },
            {
                "title": "Освободите Рыжую и Коротышку на нижнем ярусе",
                "description": "Откройте камеру Рыжей, вооружите её трофейным оружием, затем спуститесь в подвальную кухню, перебейте супермутантов у котла и освободите второго пленника — Коротышку. Выведите обоих наружу и сопроводите в Большой Город.",
            },
            {
                "title": "Обучите жителей обороне и отразите штурм супермутантов",
                "description": "В Большом Городе Рыжая попросит научить поселенцев защищаться. Выберите один из четырёх способов подготовки и вместе с жителями отбейте атакующий отряд супермутантов у моста.",
                "skillChecks": ["Лёгкое оружие 50", "Взрывчатка 50", "Наука 50", "Скрытность 50"],
                "branches": [
                    {
                        "label": "Починить роботов на свалке (Наука 50)",
                        "tone": "good",
                        "summary": "Перепрограммируйте протектрона и робота-охранника на городской свалке.",
                        "outcome": "Два боевых робота навсегда усиливают гарнизон Большого Города.",
                    },
                    {
                        "label": "Обучить стрельбе или заминировать мост",
                        "tone": "alt",
                        "summary": "Проведите тренировку по стрельбе (Лёгкое оружие 50) или заложите мины у моста (Взрывчатка 50).",
                        "outcome": "Жители успешно отбивают штурм супермутантов без потерь.",
                    },
                ],
            },
        ],
    },
    "MS02": {
        "order": 20,
        "summary": "Битва двух эксцентричных «супергероев» в Общине Кентербери: изобретатель Скотт Воллис в броне Механиста со своими роботами сражается против сироты Тани Кристофф в костюме НеМирмики, повелевающей гигантскими муравьями.",
        "startCondition": "Станьте свидетелем уличной схватки в Общине Кентербери (северо-восток карты) и поговорите с главой торгового узла дядюшкой Роу.",
        "prerequisites": [],
        "rewards": [
            "Уникальный лазерный пистолет «Взгляд протектрона» (за костюм НеМирмики) или уникальный боевой нож «Жало муравья» (за броню Механиста)",
            "Костюм и шлем Механиста и/или броня и шлем НеМирмики",
            "200–400 крышек от дядюшки Роу (удвоенная сумма при проверке Красноречия)",
        ],
        "missableWarnings": [
            "Высокое Красноречие, способность «Вечный ребёнок» / «Чёрная вдова» / «Женоубийца» позволяют убедить ОБОИХ противников мирно сложить костюмы — так вы получите и уникальное оружие одного из них, и оба комплекта брони, и максимальную карму!",
        ],
        "steps": [
            {
                "title": "Расспросите дядюшку Роу, Эрнеста и Дерека Пейсиона",
                "description": "После короткой перестрелки между Механистом и НеМирмикой на площади Общины Кентербери поговорите с дядюшкой Роу. Расспросите племянника Роу Дерека Пейсиона и механика Эрнеста, чтобы узнать предысторию обоих «героев» и расположение их тайных баз.",
                "skillChecks": ["Красноречие"],
            },
            {
                "title": "Проникните в мастерскую Механиста в Центре ремонта роботов",
                "description": "Войдите в здание Центра ремонта роботов на южной окраине города. Преодолейте ловушки, турели и патрульных роботов, спуститесь в литейный цех и вызовите Скотта Воллиса через кофейный аппарат-потайную дверь.",
                "skillChecks": ["Красноречие", "Наука 50", "Вечный ребёнок"],
                "tip": "Если убедить Механиста в том, что его война пугает жителей города, он добровольно отдаст вам свой костюм и шлем без боя.",
            },
            {
                "title": "Спуститесь в муравьиное логово НеМирмики",
                "description": "Через люк за складом на севере Общины Кентербери войдите в извилистые муравьиные туннели. Старайтесь не убивать муравьёв по пути, если рассчитываете на мирные переговоры с Таней Кристофф у её трона.",
                "skillChecks": ["Красноречие", "Женоубийца", "Вечный ребёнок"],
            },
            {
                "title": "Завершите конфликт и получите награду у дядюшки Роу",
                "description": "Вы можете отдать костюм одного противника другому ради уникального оружия («Взгляд протектрона» или «Жало муравья»), а затем убедить второго также уйти на покой, после чего вернуться к дядюшке Роу за крышками.",
                "branches": [
                    {
                        "label": "Убедить обоих сложить костюмы мирно",
                        "tone": "good",
                        "summary": "Примените Красноречие на Механисте и НеМирмике (предварительно обменяв один из костюмов на уникальное оружие).",
                        "outcome": "Оба живы, максимальная карма и удвоенная награда в 400 крышек от дядюшки Роу.",
                    },
                    {
                        "label": "Устранить одного или обоих в бою",
                        "tone": "evil",
                        "summary": "Перебейте охрану и заберите костюмы силой.",
                        "outcome": "Вы получаете трофейную броню и награду Роу, но теряете возможность мирной развязки.",
                    },
                ],
            },
        ],
    },
    "MS12": {
        "order": 27,
        "summary": "Острый конфликт вокруг элитного небоскрёба Тенпенни-Тауэр: разумные гули во главе с бывшим полицейским Роем Филлипсом требуют права поселиться в башне, тогда как владелец Алистер Тенпенни и начальник охраны Густаво стремятся их уничтожить.",
        "startCondition": "Подойдите к главным воротам Тенпенни-Тауэр на юго-западе карты и прослушайте спор Роя Филлипса по интеркому, затем поговорите с шефом Густаво.",
        "prerequisites": [],
        "rewards": [
            "Уникальная «Маска гуля» (делает ВСЕХ диких гулей в игре полностью дружелюбными — награда Роя Филлипса!)",
            "500–700 крышек от шефа Густаво (за ликвидацию гулей на станции Уоррингтон)",
        ],
        "missableWarnings": [
            "ВАЖНО: Даже при «мирном» дипломатическом заселении гулей через несколько игровых дней Рой Филлипс всё равно сбросит всех жителей-людей (включая Алистера Тенпенни и Герберта «Смельчака» Дэшвуда) в подвал! Перед завершением квеста в пользу гулей обязательно получите схему «Дротикомёта» у Лидии Монтенегро и завершите мини-квест Герберта Дэшвуда!",
        ],
        "steps": [
            {
                "title": "Выслушайте условия Густаво и Алистера Тенпенни",
                "description": "Поговорите с начальником охраны Густаво у стойки вестибюля Тенпенни-Тауэр (он предложит 500–700 крышек за зачистку логова Роя), а затем поднимитесь на лифте в пентхаус к Алистеру Тенпенни, который согласится пустить гулей только при условии, что пятеро главных арендаторов-снобов покинут башню или изменят мнение.",
                "skillChecks": ["Красноречие", "Бартер"],
            },
            {
                "title": "Встретьтесь с Роем Филлипсом на станции Уоррингтон",
                "description": "Идите на запад к депо и станции метро Уоррингтон, где укрываются Рой Филлипс, Майкл Мастерс и Бесси Линн. Рой предложит либо тайно открыть герметичную дверь подвала Тенпенни-Тауэр для стаи диких гулей, либо добиться законного заселения.",
            },
            {
                "title": "Убедите или выселите пятерых несогласных жителей (Дипломатический путь)",
                "description": "Если вы выбрали мирный путь, поговорите с миссис Ланкастер, мистером Лингом, мисс Монтенегро, Эдгаром Веллингтоном II и Миллисент Веллингтон. Вы можете переубедить их проверками Красноречия либо найти в сейфе/кабинете любовные письма Эдгара и Сьюзен Ланкастер, что приведёт к скандалу и бегству всех пятерых.",
                "skillChecks": ["Красноречие", "Взлом 50"],
            },
            {
                "title": "Выберите окончательный исход для Тенпенни-Тауэр",
                "description": "Завершите задание одним из трёх способов и заберите заслуженную награду.",
                "branches": [
                    {
                        "label": "Дипломатическое заселение гулей",
                        "tone": "good",
                        "summary": "Получите согласие Алистера Тенпенни после ухода пятерых арендаторов и сообщите Рою Филлипсу.",
                        "outcome": "Рой вручает уникальную «Маску гуля» и +300 кармы (но спустя несколько дней тайно расправляется с оставшимися людьми).",
                    },
                    {
                        "label": "Впустить диких гулей через генераторную",
                        "tone": "evil",
                        "summary": "Взломайте терминал (Наука 50) или откройте ключом Густаво дверь в подвале башни.",
                        "outcome": "Вы получаете «Маску гуля» и трофеи со всех магазинов башни, но теряете 600 очков кармы.",
                    },
                    {
                        "label": "Уничтожить Роя Филлипса и его группу",
                        "tone": "evil",
                        "summary": "Ликвидируйте Роя, Майкла и Бесси на станции Уоррингтон и доложите Густаво.",
                        "outcome": "Вы получаете 500–700 крышек и сохраняете всех жителей Тенпенни-Тауэр живыми, но упускаете «Маску гуля».",
                    },
                ],
            },
        ],
    },
    "MS13": {
        "order": 28,
        "summary": "Контракт работорговцев Парадиз-Фоллз: привратник Ворчун выдаёт экспериментальный гипнотизирующий излучатель «Месмерон» и рабские ошейники для захвата четырёх жителей Столичной Пустоши.",
        "startCondition": "Поговорите с привратником Ворчуном у шлагбаума Парадиз-Фоллз (к северу от Арефу) и согласитесь выполнить тестовый заказ, чтобы получить пропуск в лагерь.",
        "prerequisites": [],
        "rewards": [
            "Уникальное гипнотическое оружие «Месмерон» и боеприпасы к нему",
            "По 250 крышек за каждого доставленного пленника (итого 1000 крышек) + свободный проход в Парадиз-Фоллз",
        ],
        "missableWarnings": [
            "Порабощение Флэка лишает вас торговца оружием в Ривет-Сити, а порабощение Рыжей до завершения «Больших проблем в Большом Городе» осложнит защиту поселения.",
            "Даже добрый персонаж может взять этот квест просто ради бесплатного получения уникального «Месмерона», после чего перебить работорговцев и освободить детей в квесте «Спасение из Рая»!",
        ],
        "steps": [
            {
                "title": "Получите «Месмерон» и список целей у Ворчуна",
                "description": "У входа в Парадиз-Фоллз откажитесь платить взятку и возьмите у Ворчуна гипнотизатор «Месмерон» и рабский ошейник. В список входят четыре цели: снайпер Арканзас (Минное поле), торговец оружием Флэк (Ривет-Сити), аристократка Сьюзен Ланкастер (Тенпенни-Тауэр) и врач Рыжая (Большой Город).",
            },
            {
                "title": "Освойте механику гипноза и надевания ошейника",
                "description": "Подойдите к выбранной цели вне поля зрения охраны, сохраните игру и выстрелите в голову из «Месмерона». Пока жертва находится в трансе (держится за голову), немедленно заговорите с ней, выберите реплику надевания рабского ошейника и прикажите бежать в Парадиз-Фоллз.",
                "tip": "У «Месмерона» есть шанс вызвать приступ бешенства или взрыв головы вместо гипноза — всегда делайте быстрое сохранение перед выстрелом!",
            },
            {
                "title": "Захватите Арканзаса и остальных пленников из списка",
                "description": "Проще всего начать с Арканзаса на крыше разрушенного дома в центре Минного поля (он изначально враждебен, поэтому подкрадитесь к нему сзади в режиме скрытности). При желании продолжите охоту на Сьюзен Ланкастер, Флэка и Рыжую, возвращаясь к Ворчуну за новым ошейником после каждого пленника.",
                "skillChecks": ["Скрытность"],
            },
            {
                "title": "Получите выплату и доступ в Парадиз-Фоллз",
                "description": "Доставив хотя бы одного пленника из списка, вы получите от Ворчуна 250 крышек и постоянный пропуск во внутренний двор Парадиз-Фоллз к Гробовщику Джонсу. За поимку всех четырёх целей Ворчун выплатит в сумме 1000 крышек.",
            },
        ],
    },
    "MS16": {
        "order": 31,
        "summary": "Возвращение в родное Убежище 101: спустя время после гибели Джеймса ваш Пип-Бой ловит аварийный радиосигнал Аматы, умоляющей помочь остановить тиранию Смотрителя и гражданский раскол.",
        "startCondition": "После завершения сюжетного квеста «Живая вода» (MQ05) подойдите к окрестностям Мегатонны или Убежища 101, прослушайте радиостанцию «Аварийная частота Убежища 101» и откройте входную дверь паролем Аматы.",
        "prerequisites": ["MQ05"],
        "rewards": [
            "Модифицированный рабочий комбинезон Убежища 101 (+5 к Ремонту, +5 к Взлому) или броня охраны",
            "Последний шанс забрать пропущенный в прологе Пупс «Медицина» из кабинета Джеймса и схемы в терминале Смотрителя",
        ],
        "missableWarnings": [
            "ВНИМАНИЕ: После завершения этого задания и вашего выхода в пещеру дверь Убежища 101 закроется НАВСЕГДА! Обязательно проверьте кабинет отца (Пупс «Медицина») и поговорите с Бучем Делорией, чтобы он отправился в бар «У руля» в Ривет-Сити как доступный напарник!",
        ],
        "steps": [
            {
                "title": "Примите сигнал бедствия и войдите в Убежище 101",
                "description": "Поймав радиосигнал в районе Мегатонны, вернитесь в пещеру Убежища 101 и активируйте пульт двери новым паролем. На входе вас встретит дружелюбный офицер Гомес и расскажет, что жители разделились на сторонников жёсткой изоляции Смотрителя (Альфонса Альмодовара или Аллена Мака) и повстанцев Аматы, выступающих за открытие Убежища.",
            },
            {
                "title": "Выслушайте Амату, Смотрителя и Буча Делорию",
                "description": "Проберитесь в клинику и комнаты отдыха к Амате и Бучу. Амата попросит убедить Смотрителя уйти в отставку без кровопролития, Буч предложит саботировать систему очистки воды в реакторном зале, а Смотритель в своём кабинете потребует подавить мятеж молодежи.",
                "skillChecks": ["Красноречие"],
            },
            {
                "title": "Разрешите политический кризис внутри Убежища",
                "description": "Выберите способ урегулирования конфликта между двумя лагерями жителей.",
                "skillChecks": ["Красноречие", "Наука 50", "Взлом 50"],
                "branches": [
                    {
                        "label": "Убедить Смотрителя добровольно уступить власть Амате",
                        "tone": "good",
                        "summary": "Пройдите проверку Красноречия в разговоре с Альфонсом Альмодоваром (или предъявите ему записи разведки Пустоши из его терминала).",
                        "outcome": "Амата становится новым Смотрителем, Убежище 101 сохранено в мире и постепенно начинает торговлю с поверхностью.",
                    },
                    {
                        "label": "Устранить Смотрителя силой или саботировать водный чип",
                        "tone": "evil",
                        "summary": "Убейте Смотрителя (Амата будет потрясена гибелью отца) либо сломайте систему водоочистки на реакторном уровне по совету Буча.",
                        "outcome": "При поломке реактора все жители вынуждены эвакуироваться на опасную Пустошь.",
                    },
                ],
            },
            {
                "title": "Заберите памятные вещи и навсегда покиньте Убежище 101",
                "description": "Какой бы путь вы ни выбрали, Амата (или Смотритель) попросит вас навсегда уйти из Убежища 101, чтобы предотвратить новый раскол. Заберите все ценные предметы, выйдите за гермозатвор и получите прощальную награду.",
            },
        ],
    },

    # =========================================================================
    # НЕОТМЕЧАЕМЫЕ КОЛЛЕКЦИОННЫЕ И ПЕРКОВЫЕ ЗАДАНИЯ СТОЛИЧНОЙ ПУСТОШИ
    # =========================================================================
    "MS15Museum": {
        "order": 30,
        "summary": "Скупка довоенных исторических реликвий в Ривет-Сити: хранитель музея «Общество сохранения столицы» Авраам Вашингтон готов щедро заплатить за подлинники Билля о правах, Великой хартии вольностей и артефакты эпохи Авраама Линкольна.",
        "startCondition": "Поговорите с Авраамом Вашингтоном в его музее на средней палубе Ривет-Сити (до, во время или после квеста «Украденная независимость»).",
        "prerequisites": [],
        "rewards": [
            "75–100 крышек за «Билль о правах» и 75–100 крышек за «Великую хартию вольностей»",
            "От 40 до 200 крышек за каждый проданный артефакт Авраама Линкольна (при высоком Бартере/Красноречии)",
            "Пополнение стеклянных витрин музея Ривет-Сити переданными экспонатами",
        ],
        "missableWarnings": [
            "Артефакты Линкольна выгоднее и благороднее отдать Ганнибалу Хэмлину и Калебу Смиту у Мемориала Линкольна (квест «Глава государства» / «Наследие Линкольна»), а уникальную «Винтовку Линкольна» (калибр .44 «Магнум») ни в коем случае не продавайте — это один из мощнейших карабинов в игре!",
        ],
        "steps": [
            {
                "title": "Расспросите Авраама Вашингтона о редких документах",
                "description": "Посетите каюту музея «Общество сохранения столицы» на средней палубе Ривет-Сити. Помимо главного заказа на Декларацию независимости, расспросите Авраама Вашингтона о других исторических реликвиях, которые он готов приобрести для своей экспозиции.",
                "skillChecks": ["Бартер", "Красноречие"],
            },
            {
                "title": "Найдите Билль о правах и Великую хартию вольностей в Национальном архиве",
                "description": "Во время вылазки в бронированное хранилище Национального архива (квест «Украденная независимость») тщательно обыщите боковые сейфы в восточном и западном крыльях подвала. В них лежат уцелевшие оригиналы «Билля о правах» и «Великой хартии вольностей».",
                "skillChecks": ["Взлом 50", "Наука 50"],
                "tip": "Оба документа можно забрать попутно перед разговором с роботом-протектроном Баттоном Гвиннетом в главном зале хранилища.",
            },
            {
                "title": "Продайте найденные документы с проверкой Бартера",
                "description": "Вернитесь в Ривет-Сити и предложите Вашингтону найденные пергаменты. Успешная проверка торговли поднимает закупочную цену каждого документа с 75 до 100 крышек, а сами реликвии сразу появляются под стеклом музейных витрин.",
                "skillChecks": ["Бартер"],
            },
        ],
    },
    "MS06LincolnArtifacts": {
        "order": 23,
        "summary": "Масштабная охота за десятью подлинными реликвиями 16-го президента США Авраама Линкольна в залах Исторического музея: каждый найденный артефакт можно передать освобождённым рабам Ганнибала Хэмлина, продать коллекционеру Аврааму Вашингтону или сдать работорговцу Лерою Уокеру для уничтожения.",
        "startCondition": "Начните поиск в офисах Исторического музея на Молле или поговорите с Ганнибалом Хэмлином (Храм Единения), Лероем Уокером (Мемориал Линкольна) либо Авраамом Вашингтоном (Ривет-Сити).",
        "prerequisites": [],
        "rewards": [
            "Уникальная «Винтовку Линкольна» (.44 «Магнум», 50 ед. урона, нулевой разброс — лучше оставить себе!)",
            "До 1500+ крышек и положительная карма при продаже/передаче остальных 9 реликвий",
            "Цилиндр Линкольна (+1 к Интеллекту, +5 к Красноречию)",
        ],
        "missableWarnings": [
            "Прежде чем продавать плакат Мемориала Линкольна кому-либо, обязательно покажите его Калебу Смиту в Храме Единения по квесту «Глава государства», иначе восстановление статуи затянется!",
            "Работорговец Лерой Уокер скупает реликвии только для того, чтобы сжечь их — если вы планируете ликвидировать работорговцев в квесте «Глава государства», продавайте вещи Хэмлину или Вашингтону.",
        ],
        "steps": [
            {
                "title": "Обследуйте нижние залы и офисы Исторического музея",
                "description": "Войдите в Исторический музей (мимо входа в гулий город Подземелье — сверните налево через двустворчатые двери в залы, занятые дикими гулями). На двух ярусах экспозиции и офисов спрятаны 10 артефактов: Винтовка Линкольна, Дневник Линкольна, Фигурка Эйба, Цилиндр Линкольна, Запись голоса Линкольна, Геттисбергская речь, Прокламация об освобождении, Плакат о розыске Джона Уилкса Бута, Плакат о призыве времён Гражданской войны и Монета с профилем Линкольна.",
                "skillChecks": ["Взлом 50", "Наука 50"],
                "tip": "Уникальная «Винтовка Линкольна» лежит в угловой стеклянной витрине на верхнем ярусе офисов музея — заберите её в первую очередь!",
            },
            {
                "title": "Покажите чертёж/плакат Калебу Смиту по квесту «Глава государства»",
                "description": "Если вы выполняете задание «Глава государства», сначала отнесите найденный плакат с изображением Мемориала каменщику Калебу Смиту в Храм Единения, чтобы бывшие рабы смогли реконструировать разбитую голову статуи.",
            },
            {
                "title": "Выберите покупателя для каждого из артефактов",
                "description": "Все три заинтересованные стороны готовы выкупить реликвии по отдельности, причём проверки Красноречия или Бартера удваивают выплату за каждый предмет.",
                "skillChecks": ["Красноречие", "Бартер"],
                "branches": [
                    {
                        "label": "Передать реликвии Ганнибалу Хэмлину (Добрый путь)",
                        "tone": "good",
                        "summary": "После переселения общины Храма Единения к Мемориалу Линкольна продайте или подарите артефакты Ганнибалу.",
                        "outcome": "Высокий прирост доброй кармы, крышки и возрождение исторического мемориала свободных людей.",
                    },
                    {
                        "label": "Продать коллекцию Аврааму Вашингтону (Нейтральный путь)",
                        "tone": "neutral",
                        "summary": "Отнесите предметы в музей Ривет-Сити и пройдите проверки Бартера.",
                        "outcome": "Вы получаете максимальную коммерческую выручку, а вещи выставляются в витринах авианосца.",
                    },
                    {
                        "label": "Сдать артефакты работорговцу Лерою Уокеру (Злой путь)",
                        "tone": "evil",
                        "summary": "Отдайте находки главе работорговцев у Мемориала Линкольна для уничтожения.",
                        "outcome": "Быстрые крышки, но потеря кармы и уничтожение исторического наследия.",
                    },
                ],
            },
        ],
    },
    "PerkLawbringer": {
        "order": 37,
        "summary": "Охота за головами от лица законников Столичной Пустоши: взяв способность «Законник» на 14-м уровне, Одинокий Путник вступает в организацию «Регуляторы» и сдаёт пальцы убитых злодеев Соноре Круз.",
        "startCondition": "Выберите способность «Законник» (Lawbringer) при получении 14-го или более высокого уровня.",
        "prerequisites": [],
        "rewards": [
            "Уникальный «Плащ Регулятора» (+1 к Харизме, +5 к Лёгкому оружию)",
            "По 10 крышек и +5 доброй кармы за каждый палец злого персонажа (и 1000 крышек за особый контракт на Джей Ди Крокетта!)",
        ],
        "missableWarnings": [
            "Наемники компании «Коготь», рейдеры, работорговцы Парадиз-Фоллз и солдаты Анклава всегда оставляют после смерти «Палец» — это бесконечный источник крышек и положительной кармы!",
        ],
        "steps": [
            {
                "title": "Возьмите способность «Законник» и найдите штаб-квартиру Регуляторов",
                "description": "При взятии перка «Законник» на вашей карте появится маркер «Штаб-квартира Регуляторов» — деревянный фермерский дом к востоку от Свалки братьев Джалбертов и к северу от завода «Корвега». Войдите внутрь и поговорите с командиром Сонорой Круз, чтобы получить фирменный плащ.",
            },
            {
                "title": "Изучите особые ордера на розыск на столе Соноры",
                "description": "Осмотрите письменный стол рядом с Сонорой Круз и прочитайте ориентировки на особо опасных преступников Пустоши (таких как неуловимый убийца Джей Ди Крокетт), за ликвидацию которых полагается повышенная премия.",
                "tip": "Особый палец именного преступника приносит до 1000 крышек при сдаче Соноре Круз.",
            },
            {
                "title": "Собирайте пальцы злодеев и сдавайте их за крышки и карму",
                "description": "Во время зачистки лагерей рейдеров, засад компании «Коготь», патрулей Анклава и баз работорговцев забирайте с тел трофейные «Пальцы» (вес 0) и периодически приносите их Соноре Круз в обмен на крышки и укрепление статуса праведника Пустоши.",
            },
        ],
    },
    "PerkContractKiller": {
        "order": 38,
        "summary": "Тайные заказы синдиката «Партнёры Литтлхорна»: взяв способность «Наёмный убийца» на 14-м уровне, герой начинает снимать уши с убитых праведников и сдавать их загадочному Дэниэлу Литтлхорну на Свалке.",
        "startCondition": "Выберите способность «Наёмный убийца» (Contract Killer) при достижении 14-го или более высокого уровня.",
        "prerequisites": [],
        "rewards": [
            "По 10 крышек и -10 кармы за каждое ухо положительного персонажа",
            "До 1000 крышек за выполнение именных контрактов из досье на столе Литтлхорна",
        ],
        "missableWarnings": [
            "Сдача ушей Дэниэлу Литтлхорну стремительно снижает карму и вызывает засады карательных отрядов «Регуляторов» при переходах по карте!",
        ],
        "steps": [
            {
                "title": "Примите предложение «Партнёров Литтлхорна» и найдите офис на Свалке",
                "description": "Сразу после выбора способности «Наёмный убийца» вы получите записку с координатами офиса «Партнёров Литтлхорна» в полуразрушенном здании на южной окраине Свалки (к югу от Минного поля). Войдите внутрь и познакомьтесь с Дэниэлом Литтлхорном.",
            },
            {
                "title": "Ознакомьтесь с досье приоритетных целей на столе",
                "description": "Прочитайте контрактные записки на столе Литтлхорна, где перечислены особо ненавистные его нанимателям защитники порядка Столичной Пустоши, за чьи уши выплачивается крупный бонус.",
            },
            {
                "title": "Собирайте уши добрых персонажей и получайте вознаграждение",
                "description": "При убийстве бойцов «Регуляторов», паладинов Братства Стали, охранников караванов и мирных жителей с положительной кармой забирайте с их тел трофейные «Уши» и приносите их Дэниэлу Литтлхорну за звонкие крышки.",
                "tip": "Если вы поддерживаете злую или нейтральную карму для напарников вроде Джерико, Кловер или Буча, сдача нескольких ушей Литтлхорну — самый быстрый способ скорректировать карму вниз.",
            },
        ],
    },

    # =========================================================================
    # СВОБОДНЫЕ ПОРУЧЕНИЯ И ОБУЧЕНИЕ (FREEFORM)
    # =========================================================================
    "FreeformMegaton": {
        "order": 80,
        "summary": "Свод скрытых (неотмечаемых в Пип-Бое) поручений жителей Мегатонны: починка протекающего водопровода для инженера Уолтера, бесконечная сдача металлолома, тайник с химикатами Лео Стала и примирение Билли Крила с Мэгги.",
        "startCondition": "Поговорите с Уолтером на водоочистной станции Мегатонны, Лео Сталом в «Медном котелке» или жителями города в любое время до возможного взрыва бомбы.",
        "prerequisites": [],
        "rewards": [
            "200 крышек за починку 3 труб + бесконечная скупка металлолома у Уолтера (по 10 крышек и 5 ОО за каждый кусок!)",
            "Ключ от тайника с наркотиками Лео Стала на водоочистной станции и положительная карма",
            "Постоянные скидки у Мойры Браун и доктора Черча при хороших отношениях с городом",
        ],
        "missableWarnings": [
            "Починка трёх труб для Уолтера — один из лучших источников бесконечного опыта и крышек на протяжении всей игры; обязательно выполните её в первый же визит в Мегатонну!",
        ],
        "steps": [
            {
                "title": "Почините три протекающие трубы водопровода Мегатонны",
                "description": "Поговорите с пожилым инженером Уолтером в здании водоочистителя на верхнем ярусе города. Затем найдите по характерному шипению и струям воды 3 повреждения: первое — на пандусе у ворот напротив дома Кромвеля, второе — на нижней дорожке позади клиники и дома Симмса, третье — на крыше у входа в салун Мориарти. Для ремонта каждой трубы требуется навык «Ремонт» не ниже 30.",
                "skillChecks": ["Ремонт 30"],
                "tip": "Комбинезон рабочего Убежища 101 или книга «Починка тостера» помогут легко добрать «Ремонт» до 30 уже на 2-м уровне.",
            },
            {
                "title": "Сдавайте металлолом Уолтеру за крышки и опыт",
                "description": "Доложите Уолтеру о починке труб и получите 200 крышек. После этого он предложит неограниченно принимать любой найденный на Пустоши металлолом: либо за 10 крышек и 5 ОО за штуку, либо безвозмездно ради быстрого повышения доброй кармы.",
            },
            {
                "title": "Раскройте ночную зависимость Лео Стала",
                "description": "Проследите за поваром Лео Сталом поздно ночью (когда он крадётся в здание водоочистителя) или взломайте его ящик с винтами и психо, после чего поговорите с ним. При успешной проверке Красноречия вы можете либо убедить Лео навсегда бросить химию (+карма), либо шантажировать его и забрать ключ от тайника.",
                "skillChecks": ["Красноречие", "Взлом 25"],
            },
            {
                "title": "Помогите жителям и жертвуйте церкви Детей Атома",
                "description": "Пообщайтесь с Билли Крилом и приёмной девочкой Харден, выслушайте проповедь исповедника Кромвеля у бомбы (пожертвование крышек Церкви Детей Атома позволяет мгновенно поднять карму в любой момент игры) и проверьте снайпера Стокгольма на внешних мостках.",
            },
        ],
    },
    "FreeformDC": {
        "order": 81,
        "summary": "Полевые поручения и боевые стычки в разрушенных кварталах Вашингтона: спасение послушника Братства Стали Пибоди на площади Фолс-Чёрч, зачистка укреплённого опорного пункта супермутантов и помощь патрулям Львиного Прайда на Молле.",
        "startCondition": "Выйдите из станции метро к руинам Фолс-Чёрч (по пути к зданию «Новостей Галактики») или исследуйте центральные площади Вашингтона.",
        "prerequisites": [],
        "rewards": [
            "Боеприпасы (5.56-мм патроны, микроядерные батареи и стимуляторы) от спасённых бойцов Братства Стали",
            "Трофейная силовая броня и тяжёлое вооружение с павших участников городских боёв",
        ],
        "missableWarnings": [
            "В перестрелках у Фолс-Чёрч и на площади перед «Новостями Галактики» старайтесь как можно быстрее уничтожать супермутантов с гранатомётами и миниганами, чтобы спасти послушника Пибоди и паладинов.",
        ],
        "steps": [
            {
                "title": "Прикройте отряд Братства Стали и послушника Пибоди в Фолс-Чёрч",
                "description": "Выйдя из метро на восточную сторону Фолс-Чёрч, вы попадёте в разгар уличного боя между патрулём Братства Стали и супермутантами. Помогите бойцам прикрыть молодого послушника Пибоди, зажатого огнём среди разрушенных офисных зданий.",
            },
            {
                "title": "Ликвидируйте пулемётное гнездо супермутантов в угловом здании",
                "description": "Поговорите с командиром выжившего патруля Братства: он попросит уничтожить засевших в соседнем двухэтажном здании супермутантов, блокирующих продвижение к Чеви-Чейз. Зачистите оба этажа руин и вернитесь к отряду за боеприпасами и благодарностью.",
            },
            {
                "title": "Поддержите гарнизоны Братства на Молле и площади Вернон",
                "description": "При дальнейшем исследовании центрального Вашингтона (окопы у Монумента Вашингтона, Капитолий, площадь Вернон и станция Дюпон-сёркл) помогайте патрулям Братства отражать атаки супермутантов и кентавров, собирая жетоны павших воинов для сдачи писцу Джеймсон.",
            },
        ],
    },
    "FreeformCitadel": {
        "order": 82,
        "summary": "Внутренняя жизнь и свободные поручения в Цитадели Братства Стали (руины Пентагона): сдача жетонов погибших паладинов писцу Элизабет Джеймсон, снабжение у рыцаря-капитана Сумрак, медотсек Скальпеля и архивные терминалы.",
        "startCondition": "Получите доступ в Цитадель по ходу сюжетного задания «Живая вода» (MQ05).",
        "prerequisites": ["MQ05"],
        "rewards": [
            "По 100 крышек и +5 доброй кармы за каждый жетон Братства Стали, сданный писцу Джеймсон",
            "Доступ к арсеналу рыцаря-капитана Сумрак, хирургу Скальпелю и уникальному терминалу сводок Братства",
        ],
        "missableWarnings": [
            "Никогда не выбрасывайте и не продавайте торговцам «Жетоны Братства Стали», найденные на телах павших паладинов по всей Пустоши — писец Джеймсон в кольце A платит за каждый жетон по 100 крышек и начисляет карму!",
        ],
        "steps": [
            {
                "title": "Сдавайте жетоны павших воинов писцу Элизабет Джеймсон",
                "description": "В архивном зале кольца A Цитадели разыщите писца Элизабет Джеймсон. Она ведёт реестр потерь Братства Стали на Столичной Пустоши и выплачивает по 100 крышек (а также даёт положительную карму) за каждый принесённый вами «Жетон Братства Стали».",
                "tip": "Жетоны можно снимать со всех погибших в боях с супермутантами рыцарей и паладинов (у «Новостей Галактики», в Фолс-Чёрч, на Молле и у разрушенных аванпостов).",
            },
            {
                "title": "Получите допуск к арсеналу у рыцаря-капитана Сумрак",
                "description": "Убедите старейшину Оуэна Лайонса разрешить вам пользоваться интендантским складом и обратитесь к рыцарю-капитана Сумрак в казармах кольца B. У неё продаются лазерное и плазменное оружие, силовая броня и крупные партии энергоячеек, а её навык ремонта позволяет чинить экипировку.",
            },
            {
                "title": "Посетите лазарет Скальпеля и изучите терминалы кольца A",
                "description": "В кольце B познакомьтесь с медицинским роботом Мистером Помощником по прозвищу Скальпель (он лечит ранения и радиацию и продаёт стимуляторы), а в лаборатории и кольце A изучите компьютерные терминалы с досье на супермутантов, Изгоев и проект «Либерти Прайм».",
            },
        ],
    },
    "FreeformPowerArmor": {
        "order": 83,
        "summary": "Обучение ношению силовой брони в Цитадели Братства Стали: получение личного разрешения старейшины Оуэна Лайонса и прохождение строевого инструктажа у паладина Ганни на учебном плацу.",
        "startCondition": "Завершите эвакуацию учёных в Цитадель в сюжетном задании «Живая вода» (MQ05).",
        "prerequisites": ["MQ05"],
        "rewards": [
            "Постоянная способность «Умение носить силовую броню» (Power Armor Training)",
            "Возможность экипировать любую силовую броню Братства, Изгоев, Анклава и уникальный комплект Т-51b",
        ],
        "missableWarnings": [
            "Если вы уже прошли дополнение «Operation: Anchorage», способность «Умение носить силовую броню» выдаётся автоматически по завершении симуляции — в этом случае тренировка у Ганни не требуется.",
        ],
        "steps": [
            {
                "title": "Испросите разрешение у старейшины Оуэна Лайонса",
                "description": "В лабораторном крыле Цитадели (сразу после завершения «Живой воды» и получения задания «По следам») обратитесь к старейшине Оуэну Лайонсу и попросите обучить вас обращению с силовой бронёй Братства Стали.",
            },
            {
                "title": "Найдите паладина Ганни на учебном плацу Цитадели",
                "description": "Выйдите из лаборатории во внутренний двор (плац) Цитадели, где тренируются послушники Львиного Прайда, и заговорите с инструктором — паладином Ганни.",
            },
            {
                "title": "Завершите инструктаж и экипируйте силовую броню",
                "description": "Выслушайте наставления Ганни о балансировке сервоприводов и гидравлики. После короткого затемнения экрана ваш персонаж получит способность «Умение носить силовую броню», позволяющую надевать любые комплекты силовой брони и шлемов в игре.",
                "tip": "Бесплатный комплект силовой брони Братства можно сразу взять в казармах или снять с тел павших воинов у здания «Новостей Галактики».",
            },
        ],
    },

    # =========================================================================
    # НАЁМ НАПАРНИКОВ (8 СПУТНИКОВ СТОЛИЧНОЙ ПУСТОШИ)
    # =========================================================================
    "FollowersHireDogmeat": {
        "order": 84,
        "summary": "Присоединение верного пса по кличке Псина на Свалке: самый преданный четвероногий спутник Столичной Пустоши следует за героем при любой карме и умеет искать припасы параллельно с гуманоидным напарником.",
        "startCondition": "Отправляйтесь на локацию «Свалка» (Scrapyard) к югу от Минного поля и к северо-востоку от дилерского центра «Дотационная машина».",
        "prerequisites": [],
        "rewards": [
            "Постоянный спутник Псина (занимает отдельный слот животного и путешествует вместе с любым вторым напарником!)",
            "Поиск оружия, боеприпасов, медикаментов и еды по голосовой команде",
        ],
        "missableWarnings": [
            "С установленным дополнением Broken Steel здоровье Псины масштабируется с вашим уровнем до 15 000 ОЗ, а на 22-м уровне можно взять способность «Щенята!», чтобы в случае гибели пса у входа в Убежище 101 всегда появлялся его щенок.",
        ],
        "steps": [
            {
                "title": "Доберитесь до Свалки к югу от Минного поля",
                "description": "Отправляйтесь на северо-восток от Мегатонны через мост к локации «Свалка» (южнее Минного поля). Пройдите вглубь лабиринта из ржавых автобусов и автомобильных кузовов, ориентируясь на звуки стрельбы и собачий лай.",
            },
            {
                "title": "Уничтожьте мародёров-рейдеров, убивших прежнего хозяина Псины",
                "description": "В центре Свалки возле тела погибшего скитальца Псина в одиночку сражается с тремя рейдерами. Помогите псу перебить бандитов, стараясь не задеть саму собаку шальной очередью или взрывом.",
            },
            {
                "title": "Пригласите Псину в отряд и используйте команды поиска",
                "description": "Подойдите к успокоившейся собаке, заговорите с ней и предложите пойти вместе с вами. В диалоге с Псиной вы в любой момент можете отдать приказ обшарить окрестности в поисках патронов, оружия, стимуляторов или пищи (пёс даже умеет доставать предметы из запертых шкафов!).",
                "tip": "Если вы отпустите Псину или прикажете ей ждать слишком долго, она вернётся к входной двери Убежища 101.",
            },
        ],
    },
    "FollowersHireJericho": {
        "order": 85,
        "summary": "Наём бывшего рейдера Джерико в Мегатонне: закалённый ветеран Пустошей соглашается тряхнуть стариной и пойти в поход только с персонажем со злой кармой за подъёмные в 1000 крышек.",
        "startCondition": "Поговорите с Джерико на улицах Мегатонны, в его доме или в салуне Мориарти, имея злую карму и 1000 крышек.",
        "prerequisites": [],
        "rewards": [
            "Спутник Джерико (вооружён китайским автоматом с бесконечным боезапасом 5.56-мм, мастер лёгкого оружия)",
            "Помощь в бою на ранних этапах игры для персонажей с отрицательной кармой",
        ],
        "missableWarnings": [
            "Если вы взорвёте Мегатонну по квесту «Сила Атома» ДО того, как наймёте Джерико, он погибнет при ядерном взрыве!",
        ],
        "steps": [
            {
                "title": "Разыщите Джерико в Мегатонне",
                "description": "Джерико живёт в собственной хижине на среднем ярусе Мегатонны (недалеко от салуна Мориарти) и днём прогуливается по городу в кожаной броне. Заговорите с ним о его рейдерском прошлом и предложите отправиться в странствия.",
            },
            {
                "title": "Обеспечьте злую карму и соберите 1000 крышек",
                "description": "Джерико откажется иметь дело с «паиньками»: для его найма ваша карма должна быть отрицательной (статус «Злой» или ниже), а также потребуется 1000 крышек «на сигареты и дорожные расходы».",
                "tip": "Быстро понизить карму в начале игры можно взломом чужих терминалов и кражей мелких предметов в Мегатонне или Тенпенни-Тауэр.",
            },
            {
                "title": "Выплатите подъёмные и экипируйте напарника",
                "description": "Передайте Джерико 1000 крышек, чтобы он немедленно присоединился к вашему отряду. Он отлично стреляет из своего штатного китайского автомата (не тратя ваши патроны) и охотно наденет любую переданную ему боевую или силовую броню.",
            },
        ],
    },
    "FollowersHireCharon": {
        "order": 86,
        "summary": "Выкуп контракта гуля-телохранителя Харона в баре «Девятый круг» в Подземелье: неустрашимый боец с уникальным дробовиком беспрекословно служит тому, кто владеет его трудовым договором, независимо от кармы.",
        "startCondition": "Посетите бар «Девятый круг» в городе гулей Подземелье (внутри Исторического музея на Молле) и поговорите с барменом Азрухалом.",
        "prerequisites": [],
        "rewards": [
            "Постоянный спутник Харон (не зависит от вашей кармы!)",
            "Уникальный дальнобойный «Дробовик Харона» и нож, а также возможность забрать вещи с тела Азрухала",
        ],
        "missableWarnings": [
            "Сразу после получения контракта Харон сам хладнокровно застрелит своего бывшего хозяина Азрухала — если вы хотите купить у Азрухала редкие препараты или схему, сделайте это ДО выкупа контракта!",
        ],
        "steps": [
            {
                "title": "Найдите Азрухала и Харона в баре «Девятый круг»",
                "description": "Войдите в Исторический музей на Молле, пройдите через череп мамонта в поселение гулей Подземелье и поднимитесь в бар «Девятый круг». У входа неподвижно стоит высокий гуль-вышибала Харон, а за стойкой торгует его хозяин Азрухал.",
            },
            {
                "title": "Выкупите контракт за крышки или устраните Грету",
                "description": "Расспросите Азрухала о передаче контракта Харона. Он предложит два варианта сделки: заплатить наличными либо тайно убить его конкурентку — повариху Грету из закусочной Кэрол.",
                "skillChecks": ["Бартер 50"],
                "branches": [
                    {
                        "label": "Выкупить контракт за крышки (Добрый/Нейтральный путь)",
                        "tone": "good",
                        "summary": "Заплатите Азрухалу 2000 крышек (или 1000 крышек при навыке «Бартер» не ниже 50).",
                        "outcome": "Контракт переходит к вам без убийства невинной жительницы Подземелья.",
                    },
                    {
                        "label": "Устранить Грету по заказу Азрухала (Злой путь)",
                        "tone": "evil",
                        "summary": "Подкараульте Грету на выходе из закусочной Кэрол и ликвидируйте её.",
                        "outcome": "Вы получаете контракт Харона бесплатно, но теряете карму и повара в Подземелье.",
                    },
                ],
            },
            {
                "title": "Передайте контракт Харону и примите его в отряд",
                "description": "Подойдите к Харону и покажите ему выкупленный документ. Освободившись от обязательств перед ненавистным барменом, Харон тут же расправится с Азрухалом из своего снайперского боевого дробовика и перейдёт под ваше командование.",
                "tip": "Харон отлично носит силовую броню (включая Т-51b и броню Анклава) и одинаково верен как святому, так и злодею.",
            },
        ],
    },
    "FollowersHireRL3": {
        "order": 87,
        "summary": "Покупка довоенного армейского робота «Мистер Храбрец» модели Сержант РЛ-3 у бродячего торговца Жестянщика Джо: грозный летающий спутник с плазменным орудием и огнемётом для персонажей с нейтральной кармой.",
        "startCondition": "Встретьте торговца роботами Жестянщика Джо возле завода «РобКо» (к северу от Тенпенни-Тауэр), имея нейтральную карму и 1000 крышек.",
        "prerequisites": [],
        "rewards": [
            "Боевой робот-напарник Сержант РЛ-3 (вооружён встроенным плазменным излучателем и огнемётом)",
            "Высокий запас прочности (масштабируется до 9500 ОЗ с дополнением Broken Steel)",
        ],
        "missableWarnings": [
            "Жестянщик Джо продаст Сержанта РЛ-3 ТОЛЬКО в том случае, если ваша текущая карма строго нейтральная — перед разговором с ним при необходимости выровняйте карму кражей или пожертвованием крышек!",
        ],
        "steps": [
            {
                "title": "Перехватите Жестянщика Джо у комплекса «РобКо»",
                "description": "Отправляйтесь на юго-запад карты к заводу «РобКо» (между Тенпенни-Тауэр и Мегатонной). Торговец Жестянщик Джо в сопровождении Сержанта РЛ-3 и двух роботов-охранников патрулирует дорогу от входа в завод «РобКо» на север.",
            },
            {
                "title": "Выровняйте карму до нейтрального уровня",
                "description": "Перед началом диалога убедитесь, что в разделе статистики Пип-Боя ваша карма имеет статус «Нейтральный». Если карма слишком добрая — украдите несколько пустых бутылок в чужом доме; если слишком злая — пожертвуйте крышки Церкви Детей Атома в Мегатонне.",
            },
            {
                "title": "Выкупите Сержанта РЛ-3 за 1000 крышек",
                "description": "Поговорите с Жестянщиком Джо и заплатите 1000 крышек за перепрограммирование Сержанта РЛ-3 под ваше командование. Бравый армейский робот немедленно поступит в ваш отряд и останется в нём даже в том случае, если позже ваша карма сместится к добру или злу.",
                "tip": "Если вы временно отпустите Сержанта РЛ-3, он будет ждать вас в центре Общины Кентербери.",
            },
        ],
    },
    "FollowersHireClover": {
        "order": 88,
        "summary": "Выкуп телохранительницы Кловер у главаря работорговцев Гробовщика Джонса в Парадиз-Фоллз: фанатично преданная рабыня следует только за персонажем со злой кармой.",
        "startCondition": "Пройдите в Парадиз-Фоллз и поговорите с Гробовщиком Джонсом в его особняке-берлоге, имея злую карму.",
        "prerequisites": [],
        "rewards": [
            "Постоянный спутник Кловер (специализируется на холодном и лёгком стрелковом оружии)",
        ],
        "missableWarnings": [
            "Если вы убьёте Гробовщика Джонса во время штурма Парадиз-Фоллз (квест «Спасение из Рая») до покупки Кловер, нанять её станет невозможно!",
        ],
        "steps": [
            {
                "title": "Получите доступ в Парадиз-Фоллз и найдите Гробовщика Джонса",
                "description": "Попадите внутрь базы работорговцев Парадиз-Фоллз (выполнив поручение Ворчуна «Просто бизнес» или заплатив 500 крышек на входе) и зайдите в дальнее здание «Берлога Гробовщика», где обитает лидер лагеря Гробовщик Джонс вместе со своими рабынями Кловер и Алой.",
            },
            {
                "title": "Договоритесь о покупке Кловер при злой карме",
                "description": "Убедитесь, что ваша карма отрицательная, и расспросите Гробовщика Джонса о Кловер. Он согласится уступить свою любимую телохранительницу за 1000 крышек.",
                "skillChecks": ["Красноречие", "Бартер"],
                "tip": "Успешная проверка Красноречия или Бартера снижает цену выкупа Кловер вдвое — с 1000 до 500 крышек.",
            },
            {
                "title": "Вооружите Кловер для ближнего и среднего боя",
                "description": "Сразу после оплаты Кловер переходит под ваше начало. По умолчанию она вооружена китайским мечом и обрезанным ружьём, поэтому обязательно выдайте ей качественную броню и мощный карабин или потрошитель.",
            },
        ],
    },
    "FollowersHireButch": {
        "order": 89,
        "summary": "Воссоединение с другом детства и лидером «Туннельных змей» Бучем Делорией в баре Ривет-Сити: после разрешения кризиса в Убежище 101 Буч выходит на поверхность и готов путешествовать с героем при нейтральной карме.",
        "startCondition": "Завершите побочный квест «Проблемы на домашнем фронте» (MS16), сохранив жизнь Бучу, и найдите его в баре «У руля» в Ривет-Сити при нейтральной карме.",
        "prerequisites": ["MS16"],
        "rewards": [
            "Бесплатный напарник Буч Делория",
            "Бесплатная смена причёски вашего персонажа в полевых условиях в любой момент",
        ],
        "missableWarnings": [
            "Буч появляется в Ривет-Сити ТОЛЬКО после того, как вы побываете в Убежище 101 по квесту «Проблемы на домашнем фронте» и не допустите его гибели!",
        ],
        "steps": [
            {
                "title": "Встретьтесь с Бучем во время «Проблем на домашнем фронте»",
                "description": "Вернувшись в Убежище 101 по сигналу Аматы (квест MS16), поговорите с Бучем Делорией в жилом секторе. Он мечтает вырваться на Столичную Пустошь и основать собственную банду «Туннельных змей» на поверхности.",
            },
            {
                "title": "Разыщите Буча в баре «У руля» в Ривет-Сити",
                "description": "После завершения квеста в Убежище 101 отправляйтесь на нижнюю палубу авианосца Ривет-Сити в салун «У руля» (Muddy Rudder). Буч сидит за столиком в своей фирменной кожаной куртке «Туннельных змей».",
            },
            {
                "title": "Примите Буча в команду при нейтральной карме",
                "description": "Если ваша карма нейтральна, Буч с радостью и совершенно бесплатно присоединится к вам. Помимо помощи в перестрелках, он в любое время может бесплатно подстричь вас или уложить волосы в фирменном стиле «Туннельных змей».",
                "tip": "Поскольку изначально Буч вооружён лишь зубочисткой (выкидным ножом) и 10-мм пистолетом, передайте ему хорошую броню и стрелковое оружие.",
            },
        ],
    },
    "FollowersHireCross": {
        "order": 90,
        "summary": "Наём ветерана Братства Стали Паладина-звезды Кросс в Цитадели: киборг-телохранительница, некогда сопровождавшая вашего отца Джеймса и младенца в Убежище 101, бесплатно вступает в отряд к герою с доброй кармой.",
        "startCondition": "Доберитесь до Цитадели в сюжетном квесте «Живая вода» (MQ05) и поговорите с Паладином-звездой Кросс в лаборатории или кольце A при доброй карме.",
        "prerequisites": ["MQ05"],
        "rewards": [
            "Бесплатный элитный напарник Паладин-звезда Кросс в полной силовой броне Братства Стали",
            "Мастер энергетического и холодного оружия (вооружена суперкувалдой и лазерным пистолетом)",
        ],
        "missableWarnings": [
            "Кросс требует положительной кармы не только при первом найме, но и при повторном приглашении после ожидания — поддерживайте статус праведника!",
        ],
        "steps": [
            {
                "title": "Разыщите Паладина-звезду Кросс в лаборатории Цитадели",
                "description": "После прибытия в Цитадель Братства Стали и беседы со старейшиной Оуэном Лайонсом (квест «Живая вода») найдите Паладина-звезду Кросс в лабораторном зале или в коридорах кольца A.",
            },
            {
                "title": "Расспросите Кросс о прошлом вашего отца Джеймса",
                "description": "Поговорите с Кросс о том, как двадцать лет назад она защищала вашего отца Джеймса и вас на пути от Мемориала Джефферсона к дверям Убежища 101. Узнав о героической гибели Джеймса, она посчитает своим долгом оберегать вас.",
            },
            {
                "title": "Примите Паладина-звезду Кросс в отряд при доброй карме",
                "description": "Если ваша карма положительная, Кросс бесплатно присоединится к вам. Она уже одета в силовую броню Братства Стали и сокрушает врагов в ближнем бою суперкувалдой, а при передаче ей гатлинг-лазера или плазменной винтовки становится грозным стрелком.",
            },
        ],
    },
    "FollowersHireFawkes": {
        "order": 91,
        "summary": "Присоединение разумного супермутанта Фокса после побега с базы Анклава Рэйвен-Рок: самый могучий и живучий напарник в Fallout 3, вооружённый неиссякаемым гатлинг-лазером и абсолютно невосприимчивый к радиации.",
        "startCondition": "Освободите Фокса из камеры № 5 в Убежище 87 во время квеста «Поиски Эдемских кущ» (MQ08), а затем встретьте его у выхода из Рэйвен-Рок в конце «Американской мечты» (MQ09) при доброй карме.",
        "prerequisites": ["MQ08", "MQ09"],
        "rewards": [
            "Могучий спутник Фокс с бесконечным гатлинг-лазером и суперкувалдой",
            "Возможность отправить Фокса внутрь радиоактивной камеры проекта «Чистота» в финале «Забери его!» (с дополнением Broken Steel)",
        ],
        "missableWarnings": [
            "Чтобы Фокс пришёл к вам на помощь у базы Рэйвен-Рок, вы ОБЯЗАНЫ освободить его из изоляционной камеры № 5 в Убежище 87 во время поисков ГЭКК!",
        ],
        "steps": [
            {
                "title": "Освободите Фокса в изоляторе Убежища 87",
                "description": "Во время прохождения сюжетного задания «Поиски Эдемских кущ» в экспериментальных отсеках Убежища 87 выпустите дружелюбного супермутанта Фокса из камеры № 5 (отключив пожарную тревогу на терминале или найдя ключ). В благодарность он достанет для вас ГЭКК из смертельно радиоактивного зала.",
            },
            {
                "title": "Встретьтесь с Фоксом у выхода с базы Рэйвен-Рок",
                "description": "Выбравшись на поверхность из горящего бункера Анклава Рэйвен-Рок в конце миссии «Американская мечта», вы увидите Фокса, расправляющегося с солдатами Анклава из трофейного гатлинг-лазера прямо у горной тропы.",
            },
            {
                "title": "Пригласите Фокса в отряд при доброй карме",
                "description": "Поговорите с Фоксом после боя: при наличии положительной кармы он бесплатно станет вашим постоянным спутник. Благодаря огромному запасу здоровья (до 15 000 ОЗ в Broken Steel) и скорострельному гатлинг-лазеру он в одиночку справляется с Бегемотами и патрулями Анклава.",
                "tip": "Если вы временно отпустите Фокса, он всегда будет ждать вас у входа в Исторический музей (Подземелье).",
            },
        ],
    },

    # =========================================================================
    # DLC 1: OPERATION: ANCHORAGE (РАСШИРЕНИЕ ДО 3–4 ШАГОВ + РАЗВЕДДАННЫЕ)
    # =========================================================================
    "DLC02OA1": {
        "order": 40,
        "summary": "Экспедиция на аванпост Братства Изгоев в районе Бейлис-Кроссроудс: помощь отряду защитника Моррисона в бою с супермутантами и погружение в довоенный военный симулятор освобождения Анкориджа ради открытия запертого арсенала.",
        "startCondition": "Поймайте в Пип-Бое радиопередачу «Сигнал бедствия Изгоев» и отправляйтесь к станции метро Бейлис-Кроссроудс на юге карты.",
        "prerequisites": [],
        "rewards": [
            "Нейроинтерфейсный костюм Изгоев",
            "Доступ в подземный бункер и капсулу симуляции «Операция „Анкоридж“»",
        ],
        "missableWarnings": [
            "После входа в капсулу симуляции вы не сможете вернуться на Столичную Пустошь или воспользоваться своим прежним снаряжением до полного завершения виртуальной кампании на Аляске!",
        ],
        "steps": [
            {
                "title": "Прорвитесь через позиции супермутантов у Бейлис-Кроссроудс",
                "description": "Выйдите со станции метро Бейлис-Кроссроудс и помогите бойцам Братства Изгоев отбить многоярусные руины и траншеи у отрядов супермутантов на пути к входу в бункер.",
            },
            {
                "title": "Спуститесь на аванпост Изгоев и поговорите с защитником Мак-Гроу",
                "description": "Воспользуйтесь грузовым лифтом в конце улицы, чтобы спуститься на секретный подземный объект. В командном зале защитник Мак-Гроу объяснит, что хранилище с довоенной бронёй Т-51b заблокировано протоколом симуляции, а открыть его может только человек с внешним интерфейсом Пип-Боя 3000.",
            },
            {
                "title": "Наденьте нейрокостюм у специалистке Олин и войдите в капсулу",
                "description": "Пройдите в техническую лабораторию к специалистке Олин, получите нейроинтерфейсный костюм, экипируйте его и зайдите в открывшуюся капсулу виртуальной реальности, чтобы перенестись на заснеженные утёсы Аляски.",
            },
        ],
    },
    "DLC02OA2": {
        "order": 41,
        "summary": "Первая боевая операция виртуальной кампании на Аляске: скрытное восхождение по скалам в паре с сержантом Бенджамином Монтгомери, проникновение в китайский артиллерийский бункер и подрыв трёх дальнобойных орудий.",
        "startCondition": "Начинается автоматически сразу после запуска капсулы виртуальной симуляции «Анкоридж».",
        "prerequisites": ["DLC02OA1"],
        "rewards": [
            "Переход в полевой штаб генерала Чейза и доступ к тактическим наборам вооружения",
            "4 из 10 чемоданчиков с разведданными (на пути к артиллерийской батарее и внутри бункера)",
        ],
        "missableWarnings": [
            "Внимание: локация «Утёсы Анкориджа» и артиллерийский бункер станут НАВСЕГДА недоступны после взрыва трёх орудий! Обязательно соберите все 4 чемоданчика с разведданными в этой миссии до установки последнего заряда!",
        ],
        "steps": [
            {
                "title": "Пройдите по горному карнизу и встретьтесь с сержантом Монтгомери",
                "description": "Высадившись на снежном уступе с 10-мм пистолетом с глушителем и траншейным ножом, нейтрализуйте первых китайских часовых, используйте настенные диспенсеры здоровья и боеприпасов и соединитесь с сержантом Бенджамином Монтгомери у подвесного моста.",
                "tip": "Первый чемоданчик с разведданными лежит в комнате за запертой дверью на средней станции перед выходом на верхний снежный мост.",
            },
            {
                "title": "Прорвитесь через китайский артиллерийский бункер",
                "description": "Вместе с Монтгомери войдите в скальный комплекс китайской армии. Зачищайте коридоры, склады и казармы (остерегайтесь солдат с огнемётами и снайперов), не забывая пополнять боезапас у красных терминалов раздачи патронов и забирать ещё 3 чемоданчика с разведданными.",
                "skillChecks": ["Взлом", "Лёгкое оружие"],
            },
            {
                "title": "Заложите заряды на все три береговых орудия",
                "description": "Выйдите на верхнюю артиллерийскую площадку, перебейте охрану у трёх гигантских пушек и поочерёдно установите взрывчатку на казённую часть каждого орудия. Отойдите на безопасное расстояние: после подрыва батареи вы автоматически перенесётесь в командный шатёр генерала Чейза.",
            },
        ],
    },
    "DLC02OA3": {
        "order": 42,
        "summary": "Диверсионный этап освобождения Аляски из полевого лагеря США: выбор класса вооружения, комплектование собственной ударной группы у лейтенанта Моргана и зачистка Станции прослушки и топливного депо танков «Химера».",
        "startCondition": "Начинается в командной палатке генерала Константина Чейза сразу после уничтожения береговых орудий.",
        "prerequisites": ["DLC02OA2"],
        "rewards": [
            "Возможность получить Гаусс-винтовку у квартирмейстера при успешной проверке Красноречия",
            "4 чемоданчика с разведданными (2 на Станции прослушки и 2 в Депо «Химера»)",
        ],
        "missableWarnings": [
            "Обязательно попросите у квартирмейстера в палатке снабжения прототип Гаусс-винтовки (проверка Красноречия) и соберите все 4 чемоданчика с разведданными внутри Станции прослушки и Депо «Химера» до завершения обеих задач!",
        ],
        "steps": [
            {
                "title": "Выберите пакет вооружения и сформируйте ударный отряд",
                "description": "Выслушайте брифинг генерала Чейза, возьмите маркеры реквизиции и обратитесь к лейтенанту Моргану для набора ударной группы (пехота, гранатомётчик, снайпер, робот-охранник или «Мистер Храбрец»). Затем подойдите к квартирмейстеру, выберите боевой комплект и убедите его выдать экспериментальную Гаусс-винтовку.",
                "skillChecks": ["Красноречие"],
            },
            {
                "title": "Зачистите китайскую Станцию прослушки в ледяных шахтах",
                "description": "Отправляйтесь по восточной тропе через разрушенный город и горную штольню к Станции прослушки. Внутри впервые появятся элитные китайские диверсанты «Алые драгуны» в оптической стелс-броне. Перебейте охрану, соберите 2 чемоданчика с разведданными и скачайте данные с главного терминала связи.",
            },
            {
                "title": "Взорвите топливные резервуары в Депо танков «Химера»",
                "description": "Вернитесь в лагерь (при необходимости пополните ударный отряд у Моргана) и выдвигайтесь по западному ущелью к базе бронетехники. Пробейтесь мимо артиллерийских танков «Химера», найдите ещё 2 чемоданчика разведданных в палатках и установите заряды на оба огромных топливных хранилища.",
            },
            {
                "title": "Доложите генералу Чейзу о готовности к генеральному штурму",
                "description": "После подрыва обоих резервуаров в Депо «Химера» и зачистки Станции прослушки вернитесь в штабную палатку США и примите командование финальным наступлением на завод импульсного поля.",
            },
        ],
    },
    "DLC02FF": {
        "order": 44,
        "summary": "Сбор всех 10 секретных чемоданчиков с разведданными на протяжении четырёх этапов симуляции «Анкоридж» ради получения постоянной способности «Секретная операция», а также полевые диалоги с военным корреспондентом и доктором Адами.",
        "startCondition": "Активируется автоматически при подборе любого чемоданчика с разведданными или разговоре с персоналом американской базы внутри симуляции «Анкоридж».",
        "prerequisites": ["DLC02OA1"],
        "rewards": [
            "Уникальная способность «Секретная операция» (+3 к Науке, +3 к Взлому, +3 к Скрытности навсегда!)",
            "Дополнительное лечение у полевого врача доктора Адами и исторические сводки военного корреспондента",
        ],
        "missableWarnings": [
            "Все 10 чемоданчиков с разведданными можно собрать ТОЛЬКО во время прохождения симуляции — если пропустить хотя бы один в «Орудиях Анкориджа» или на Станции прослушки, получить перк «Секретная операция» будет невозможно!",
        ],
        "steps": [
            {
                "title": "Соберите 4 чемоданчика в миссии «Орудия Анкориджа»",
                "description": "На скальном подъёме найдите 1-й чемоданчик в запертой каморке перекачивающей станции перед мостом к Монтгомери. Внутри артиллерийского бункера заберите 2-й чемоданчик со стола в казарме с двухъярусными койками, 3-й — на ящиках в зале с обрушенным потолком и 4-й — в угловом кабинете офицера перед выходом к трём орудиям.",
            },
            {
                "title": "Пообщайтесь с доктором Адами и корреспондентом в лагере США",
                "description": "В американском базовом лагере загляните в медицинскую палатку к доктору Адами (она мгновенно исцеляет любые ранения и увечья) и дайте интервью военному корреспонденту у входа, который делает пропагандистский фотоснимок (прообраз памятника освободителям Анкориджа!).",
            },
            {
                "title": "Соберите 4 чемоданчика в миссии «Подготовка наступления»",
                "description": "По дороге к Станции прослушки заберите 5-й чемоданчик на верхнем мостике ледяной шахты, а 6-й — на столе в главной комнате самой Станции прослушки. На пути к Депо «Химера» возьмите 7-й чемоданчик в заброшенном домике у крана, а 8-й — в угловой палатке внутри самого танкового депо.",
            },
            {
                "title": "Найдите последние 2 чемоданчика в «Операции „Анкоридж“» и получите перк",
                "description": "Во время финального штурма в миссии «Операция „Анкоридж“» подберите 9-й чемоданчик в блиндаже с пленными американцами по левому флангу траншей, а 10-й — в трансформаторной будке сразу за пультом отключения импульсного поля. Сразу после взятия десятого кейса вам навсегда присваивается способность «Секретная операция»!",
            },
        ],
    },

    # =========================================================================
    # DLC 2: THE PITT (РАСШИРЕНИЕ ВСЕХ 4 КВЕСТОВ ДО 3–4 ШАГОВ)
    # =========================================================================
    "DLC01Quest01": {
        "order": 45,
        "summary": "Путь на север к радиовышке беглого жителя Питта Вернера: добыча одежды раба для маскировки, поездка на дрезине через железнодорожный туннель и проход через конфискационный пост на мосту в Питт.",
        "startCondition": "Прослушайте в Пип-Бое радиосигнал бедствия Вернера и встретьтесь с ним у радиовышки на крайнем севере Столичной Пустоши.",
        "prerequisites": [],
        "rewards": [
            "Проникновение в индустриальные руины Питта (бывший Питтсбург)",
            "Возможность получить лохмотья раба мирным путём и освободить невольников в депо",
        ],
        "missableWarnings": [
            "На КПП за мостом в Питт рейдеры временно конфискуют всё ваше снаряжение (оно в полной сохранности вернётся после победы на арене «Яма» в следующем квесте).",
        ],
        "steps": [
            {
                "title": "Помогите Вернеру отбить атаку рейдеров у радиовышки",
                "description": "Доберитесь до северной радиовышки (северо-восточнее форта Константин), уничтожьте группу рейдеров Питта и выслушайте Вернера. Он просит проникнуть в заражённый промышленный город Питт под видом раба, чтобы выкрасть лекарство от мутагенной болезни трогов.",
            },
            {
                "title": "Добудьте одежду раба на Поезде-призраке",
                "description": "Идите на северо-запад к палаточному лагерю работорговцев у входа в железнодорожный туннель. Перебейте конвоиров и снимите одежду с тела погибшего невольника (либо убедите пленника Рамзи отдать вам комплект лохмотьев раба), а также отоприте клетки с выжившими рабами.",
                "skillChecks": ["Красноречие", "Взлом"],
            },
            {
                "title": "Пересеките мост в Питт и пройдите досмотр у Мекса",
                "description": "Воспользуйтесь ручной дрезиной в туннеле, чтобы переправиться в Питт. Наденьте одежду раба, пройдите по заминированному подвесному мосту, сдайте снаряжение привратнику Мексу на КПП (спрятанный в куртке Вернера пистолет можно утаить при проверке Скрытности) и войдите в рабочий квартал Даунтаун.",
                "skillChecks": ["Скрытность"],
            },
        ],
    },
    "DLC01Quest02": {
        "order": 46,
        "summary": "Испытания невольника в Даунтауне Питта: встреча со связной Вернера Мидеей, охота за стальными слитками среди диких трогов на Сталелитейном дворе и три смертельных поединка на радиоактивной арене «Яма» за свободу и возврат снаряжения.",
        "startCondition": "Начинается автоматически после прохода в Даунтаун Питта и стычки с надсмотрщиками.",
        "prerequisites": ["DLC01Quest01"],
        "rewards": [
            "Полный возврат всего вашего снаряжения из сундука у арены «Яма»",
            "Уникальная экипировка от кузнеца Эверетта за сбор стальных слитков (вплоть до винтовки «Перфоратор» за 90 слитков и «Племенной силовой брони» за 100 слитков!)",
            "Способность «Боец Ямы» (+3% к сопротивлению урону и радиации) и пропуск в Аптаун к лорду Ашуру",
        ],
        "missableWarnings": [
            "На Сталелитейном дворе и заброшенном заводе спрятано ровно 100 стальных слитков! Собрав все 100 и сдав их Эверетту, вы получите весь комплект уникальных наград дополнения The Pitt!",
        ],
        "steps": [
            {
                "title": "Найдите Мидею в бараках Даунтауна",
                "description": "Вступитесь за раба, которого избивают надсмотрщики у входа в Даунтаун, и проследуйте за девушкой Мидеей в её жилище. Там вас тайно навестит Вернер и расскажет, что единственный путь в укреплённый Аптаун к лорду Ашуру — отличиться на сборе стали и победить на гладиаторской арене.",
            },
            {
                "title": "Выйдите на Сталелитейный двор и соберите стальные слитки",
                "description": "Пройдите через ворота к кузнецу Эверетту, возьмите у Марко двуручную дисковую пилу «Автопила» (или револьвер Билла-Дикаря) и отправляйтесь на кишащий трогами Сталелитейный двор. Для сюжета достаточно принести Эверетту 10 стальных слитков, но за каждые новые 10 слитков (до 100 штук) он выдаёт редкую броню и уникальное оружие.",
                "tip": " «Автопила» буквально за секунды распиливает трогов в режиме прицеливания и не требует дефицитных патронов.",
            },
            {
                "title": "Запишитесь на гладиаторские бои у Фейдры и выиграйте 3 раунда в «Яме»",
                "description": "Вернувшись в Даунтаун после речи Ашура по громкоговорителю, поговорите с распорядительницей арены Фейдрой. Выберите оружие у спонсора Креншоу и одержите победу в трёх раундах среди бочек с радиоактивными отходами: против троих рабов, против братьев Медведя и наконец против чемпиона арены Груббера в силовой броне.",
            },
            {
                "title": "Заберите своё снаряжение у Креншоу и поднимайтесь в Аптаун",
                "description": "Победив Груббера, вы завоюете титул свободного гражданина Питта и способность «Боец Ямы». Откройте сундук рядом с Креншоу, чтобы забрать все свои вещи, конфискованные на мосту, и направляйтесь через ворота Аптауна к башне Хэйвен.",
            },
        ],
    },
    "DLC01Quest03": {
        "order": 47,
        "summary": "Драматический финал дополнения The Pitt: аудиенция у бывшего паладина Братства Стали Исмаила Ашура в башне Хэйвен, открытие того, что «лекарством» является его новорождённая дочь Мари, и тяжёлый моральный выбор между порядком Ашура и кровавым бунтом Вернера.",
        "startCondition": "Начинается сразу после победы в третьем бою на арене «Яма» и возврата вашего снаряжения.",
        "prerequisites": ["DLC01Quest02"],
        "rewards": [
            "Способность «Иммунитет к мутациям» (Booster Shot, +10% сопротивления радиации) и доступ к прессу для переделки патронов",
            "Уникальная силовая броня Ашура (при свержении Ашура) или постоянные поставки боеприпасов и детские игрушки для Мари (при поддержке Ашура)",
        ],
        "missableWarnings": [
            "В конфликте Питта нет однозначно «доброй» стороны: Ашур и его жена-учёный Сандра действительно близки к синтезу вакцины в чистой лаборатории, тогда как Вернер жаждет личной мести и власти.",
        ],
        "steps": [
            {
                "title": "Поднимитесь в башню Хэйвен на аудиенцию к лорду Ашуру",
                "description": "Пройдите через верхние мостки Аптауна во дворец Хэйвен и поднимитесь на лифте в тронный зал Исмаила Ашура. Бывший воин Братства Стали Лайонса расскажет, как он очистил город от дикарей и почему вынужден использовать подневольный труд, пока его жена Сандра не завершит создание вакцины.",
            },
            {
                "title": "Войдите в лабораторию Сандры и узнайте правду о младенце Мари",
                "description": "Когда во время разговора в Даунтауне вспыхнет бунт и Ашур покинет зал, пройдите в научную лабораторию к его супруге Сандре. Выяснится, что «лекарство», за которым охотится Вернер, — это их грудная дочь Мари, родившаяся с врождённым иммунитетом к троглодитному вырождению.",
            },
            {
                "title": "Примите решение у колыбели Мари и найдите укрытие Вернера",
                "description": "Решите, похищать ли младенца Мари из колыбели (что сделает всех рейдеров Питта и супругов Ашур враждебными) или оставить ребёнка в Хэйвене (тогда против вас восстанут вооружённые рабы). В обоих случаях проберитесь к Мидее и далее в тайный штаб Вернера на Сталелитейном дворе.",
                "branches": [
                    {
                        "label": "Поддержать Ашура и сохранить ребёнка в семье",
                        "tone": "good",
                        "summary": "Оставьте Мари родителям (или верните её в колыбель после разговора с Вернером) и остановите мятеж Вернера.",
                        "outcome": "Вы устраняете или изгоняете Вернера (проверка Красноречия или перк «Чёрная вдова»), Сандра продолжает безопасную разработку лекарства и дарит вам перк и доступ к прессу патронов.",
                    },
                    {
                        "label": "Поддержать восстание рабов и передать Мари Вернеру",
                        "tone": "alt",
                        "summary": "Принесите младенца Вернеру, отключите прожекторы на Сталелитейном дворе, чтобы впустить орду трогов в Аптаун, и сразитесь с Исмаилом Ашуром.",
                        "outcome": "Рейдеры Питта разгромлены, вы забираете уникальную силовую броню Ашура, а власть в городе переходит к Вернеру и Мидее.",
                    },
                ],
            },
        ],
    },
    "DLC01FFLD": {
        "order": 48,
        "summary": "Побочное расследование в Питте: поиск пропавшего на заброшенном заводе Сталелитейного двора раба Билла-Дикаря и обретение его уникального бесшумного револьвера калибра .32.",
        "startCondition": "Расспросите Мидею в Даунтауне о пропавшем Билле-Дикаре или самостоятельно найдите его тело на Сталелитейном дворе.",
        "prerequisites": ["DLC01Quest01"],
        "rewards": [
            "Уникальный револьвер «Огнестрел Билла-Дикаря» (Wild Bill's Sidearm, калибр .32, высокий критический урон)",
            "Попутный сбор стальных слитков возле места гибели Билла",
        ],
        "missableWarnings": [
            "Обязательно обыщите площадку вокруг тела Билла-Дикаря — рядом с ним и на верхних мостках за цехом лежит сразу более десятка стальных слитков для коллекции Эверетта!",
        ],
        "steps": [
            {
                "title": "Расспросите Мидею о судьбе Билла-Дикаря",
                "description": "После первого разговора с Мидеей в бараках Даунтауна спросите её о пропавшем товарище по имени Билл-Дикарь, который отправился на Сталелитейный двор за стальными слитками и не вернулся.",
            },
            {
                "title": "Найдите тело Билла-Дикаря у лестницы заброшенного цеха",
                "description": "Выйдите на Сталелитейный двор, пройдите через большой разрушенный заводской ангар во внутренний тупик с ржавыми трубами и поднимитесь по металлической лестнице слева. У подножия пролёта среди убитых трогов лежит тело Билла-Дикаря — заберите его прощальную записку и уникальный револьвер «Огнестрел Билла-Дикаря».",
            },
            {
                "title": "Сообщите Мидее о гибели Билла",
                "description": "Вернитесь в Даунтаун Питта и передайте Мидее печальную весть о том, что Билл-Дикарь пал в бою с трогами, чтобы завершить поручение и получить опыт.",
            },
        ],
    },

    # =========================================================================
    # DLC 3: BROKEN STEEL — ВОДНЫЕ ПОРУЧЕНИЯ ПИСАРЯ БИГСЛИ (3 КВЕСТА)
    # =========================================================================
    "DLC03WQ01": {
        "order": 53,
        "summary": "Расследование грабежей водных караванов Ривет-Сити по поручению писца Бигсли и офицера Лепеллетье: выслеживание банды Одноглазого Джека на товарной станции Вильхельма, честная дуэль на холодном оружии или рэкет.",
        "startCondition": "Поговорите с управляющим поставками воды писцом Бигсли в ротонде Мемориала Джефферсона после начала дополнения Broken Steel.",
        "prerequisites": ["DLC03BS1"],
        "rewards": [
            "200–400 крышек от писца Бигсли за обеспечение безопасности маршрута",
            "Либо еженедельная дань крышками от банды Одноглазого Джека и/или шантаж офицера Лепеллетье на 500 крышек",
        ],
        "missableWarnings": [
            "Если во время дуэли с Одноглазым Джеком вы достанете огнестрельное оружие вместо выбранного холодного оружия, вся банда немедленно откроет огонь!",
        ],
        "steps": [
            {
                "title": "Переговорите с писцом Бигсли и офицером Лепеллетье в Ривет-Сити",
                "description": "Выслушайте жалобы писца Бигсли в Мемориале Джефферсона на пропажу партий «Аква Пура» и отправляйтесь на мост Ривет-Сити к офицеру службы безопасности Лепеллетье. Она направит вас к патрульным Дэвису и Лорин на северном берегу Потомака.",
            },
            {
                "title": "Проследите путь налётчиков до товарной станции Вильхельма",
                "description": "Доберитесь до места засады у реки к северу от проекта «Чистота», осмотрите разбитый караван и идите по следам вверх к базе бандитов возле товарной станции Вильхельма, где заправляет Одноглазый Джек.",
            },
            {
                "title": "Разберитесь с Одноглазым Джеком и доложите в Ривет-Сити",
                "description": "Встретьтесь с Одноглазым Джеком и выберите способ решения проблемы: убедите банду уйти проверкой Красноречия, вызовите Джека на дуэль один на один (на ножах, свинцовых трубах или досках с гвоздями), перебейте всех налётчиков или вступите с ними в преступный сговор, после чего вернитесь к Лепеллетье и Бигсли.",
                "skillChecks": ["Красноречие", "Холодное оружие"],
                "branches": [
                    {
                        "label": "Победить Джека на дуэли или убедить банду уйти (Добрый путь)",
                        "tone": "good",
                        "summary": "Одолейте Одноглазого Джека в честном бою холодным оружием или прогоните банду Красноречием и доложите Лепеллетье.",
                        "outcome": "Караваны Ривет-Сити в безопасности, вы получаете награду у писца Бигсли.",
                    },
                    {
                        "label": "Взять долю с бандитов или шантажировать Лепеллетье (Злой путь)",
                        "tone": "evil",
                        "summary": "Договоритесь с Джеком о еженедельной доле с грабежей или вымогайте 500 крышек у офицера Лепеллетье за «защиту».",
                        "outcome": "Постоянный нелегальный доход крышками ценой репутации.",
                    },
                ],
            },
        ],
    },
    "DLC03WQ02": {
        "order": 54,
        "summary": "Разоблачение мошенничества гуля Гриффона у входа в Исторический музей: выяснение того, как перекупщик превращает чистую воду Братства в радиоактивную подделку «Аква Кура», якобы возвращающую гулям волосы и гладкую кожу.",
        "startCondition": "Купите бутылку «Аква Кура» у зазывалы Гриффона в вестибюле Исторического музея (Подземелье) или поговорите с его поставщиком воды после старта Broken Steel.",
        "prerequisites": ["DLC03BS1"],
        "rewards": [
            "Награда крышками и доброй кармой при прекращении обмана и возврате поставок Подземелью",
            "Либо регулярная доля с продаж «Аква Кура» (по 150+ крышек) и бесплатные бутылки при шантаже Гриффона",
        ],
        "missableWarnings": [
            "На станции метро «Управление музеями» цех розлива Гриффона охраняют вооружённые наёмники и турели — прихватите боеприпасы или взломайте охранный терминал!",
        ],
        "steps": [
            {
                "title": "Изучите лавку Гриффона в Подземелье и расспросите писца Бигсли",
                "description": "Послушайте рекламную речь гуля Гриффона у входа в Подземелье, расспросите его об источнике чудодейственной воды «Аква Кура», а затем наведайтесь в Мемориал Джефферсона к писцу Бигсли, чтобы узнать, кто выкупает квоту чистой воды для гулей.",
                "skillChecks": ["Красноречие", "Наука"],
            },
            {
                "title": "Обследуйте подпольный цех розлива на станции «Управление музеями»",
                "description": "Спуститесь на станцию метро «Управление музеями» (Museum Authority) на Молле. Пробейтесь через охрану Гриффона к линии розлива и скачайте с рабочего терминала бухгалтерские записи, доказывающие, что Гриффон разбавляет краденую «Аква Пура» грязной радиоактивной водой.",
                "skillChecks": ["Наука", "Взлом"],
            },
            {
                "title": "Предъявите улики Гриффону и определите судьбу его бизнеса",
                "description": "Вернитесь в Исторический музей и уличите Гриффона во лжи.",
                "skillChecks": ["Красноречие", "Бартер"],
                "branches": [
                    {
                        "label": "Заставить Гриффона бесплатно раздавать чистую воду",
                        "tone": "good",
                        "summary": "Пригрозите разоблачением перед жителями Подземелья и потребуйте прекратить продажу фальшивки.",
                        "outcome": "Жители Подземелья получают настоящую чистую воду «Аква Пура», а вы — положительную карму.",
                    },
                    {
                        "label": "Шантажировать Гриффона и войти в долю",
                        "tone": "evil",
                        "summary": "Потребуйте процент с прибыли в обмен на молчание о подпольном цехе на станции метро.",
                        "outcome": "Гриффон регулярно выплачивает вам долю крышками с продаж «Аква Кура».",
                    },
                ],
            },
        ],
    },
    "DLC03WQ03": {
        "order": 55,
        "summary": "Расследование пропажи водных караванов Мегатонны: проникновение в монастырь секты «Апостолы Вечного Света» в Спрингвейле, где фанатики Матери Кюри III облучают воду для «обращения» путников в гулей.",
        "startCondition": "Поговорите с писцом Бигсли в Мемориале Джефферсона или найдите проповедника брата Джерарда и листовку секты у ворот Мегатонны.",
        "prerequisites": ["DLC03BS1"],
        "rewards": [
            "Награда от писца Бигсли и возобновление поставок чистой воды в Мегатонну",
            "Партия «Святой воды» и редкие препараты из подземелья монастыря",
        ],
        "missableWarnings": [
            "Если Мегатонна была взорвана вами в квесте «Сила Атома», достаточно просто сообщить об этом изумлённому писцу Бигсли — задание сразу завершится!",
        ],
        "steps": [
            {
                "title": "Найдите брата Джерарда у дороги между Мегатонной и Спрингвейлом",
                "description": "Обследуйте окрестности Мегатонны: подберите миссионерскую брошюру с тела погибшего караванщика и поговорите с проповедником братом Джерардом у руин Спрингвейла. Чтобы заслужить доверие секты, выпейте предложенную им радиоактивную «святую воду» (или наберите дозу радиации свыше 200 рад).",
            },
            {
                "title": "Войдите в монастырь Вечного Света в подвале дома Спрингвейла",
                "description": "Получив благословение Джерарда (или взломав вход силой), спуститесь в подземелье разрушенного здания в Спрингвейле, где обустроен монастырь «Апостолов Вечного Света» во главе со светящейся гулихой Матерью Кюри III (бывшей послушницей Церкви Детей Атома).",
                "skillChecks": ["Взлом", "Красноречие"],
            },
            {
                "title": "Остановите отравление воды и доложите писцу Бигсли",
                "description": "Поговорите с Матерью Кюри III о перехвате водных караванов Братства Стали.",
                "skillChecks": ["Красноречие", "Наука"],
                "branches": [
                    {
                        "label": "Переубедить Мать Кюри III без кровопролития",
                        "tone": "good",
                        "summary": "Докажите проверкой Красноречия или Науки, что насильственное облучение убивает людей, а не дарует им «просветление».",
                        "outcome": "Секта прекращает нападения на караваны Мегатонны без боя; Бигсли выдаёт полную награду.",
                    },
                    {
                        "label": "Ликвидировать фанатиков силой",
                        "tone": "alt",
                        "summary": "Уничтожьте Мать Кюри III и её последователей в подземелье монастыря.",
                        "outcome": "Угроза караванам устранена, вы забираете запасы секты и отчитываетесь перед Бигсли.",
                    },
                ],
            },
        ],
    },

    # =========================================================================
    # DLC 4: POINT LOOKOUT (РАСШИРЕНИЕ 8 СЮЖЕТНЫХ И ПОБОЧНЫХ КВЕСТОВ ДО 3–4 ШАГОВ)
    # =========================================================================
    "DLC04MQ03": {
        "order": 62,
        "summary": "Раскрытие тайны культа дикарей Пойнт-Лукаута: по поручению Десмонда Локхарта и подсказке Надин вы выслеживаете верховного жреца Джексона в прибрежном морском гроте и обнаруживаете, что «духом» секты является голограмма живого мозга профессора Кальверта.",
        "startCondition": "Начинается автоматически сразу после возвращения в Собор Ковчега и Голубя и завершения обряда «Прогулка с духами».",
        "prerequisites": ["DLC04MQ02"],
        "rewards": [
            "Раскрытие заговора профессора Кальверта и переход к квесту «Мысли под контролем»",
            "Трофеи из морского грота и арсенала культистов",
        ],
        "missableWarnings": [
            "В морском гроте можно не спешить атаковать Джексона сразу — дождитесь окончания его диалога с голограммой Мозга, чтобы услышать всю историю манипуляций Кальверта!",
        ],
        "steps": [
            {
                "title": "Расспросите Надин и культистов Собора о местонахождении Джексона",
                "description": "Став полноправным членом братства Собора Ковчега и Голубя, поговорите с Надин и смотрителями храма. Вы узнаете, что лидер общины Джексон регулярно уходит за указаниями «духов» в изолированный морской грот на восточном побережье. Доложите об этом Десмонду Локхарту в особняке.",
            },
            {
                "title": "Проберитесь через морской грот к тайному святилищу",
                "description": "Отправляйтесь к пещере «Морской грот» на берегу океана. Спускайтесь по извилистым каменным галереям мимо болотников и фанатиков-дикарей, пока не выйдете к подземному залу с довоенным голографическим проектором.",
                "skillChecks": ["Скрытность"],
            },
            {
                "title": "Подслушайте беседу Джексона с голограммой Мозга и поговорите с Кальвертом",
                "description": "Проследите за разговором Джексона с парящим изображением мозга. Когда Джексон уйдёт (или будет убит вами в бою), подойдите к проектору: с вами заговорит сам профессор Кальверт, чей живой мозг управляет культом из подземной лаборатории, и предложит предать Десмонда.",
            },
        ],
    },
    "DLC04MQ04": {
        "order": 63,
        "summary": "Психотропная война между Кальвертом и Десмондом: установка или уничтожение глушителя телепатии на колесе обозрения, месть паромщику Тобару за похищенный кусок вашего мозга и взрыв особняка Кальвертов.",
        "startCondition": "Начинается сразу после разговора с голограммой мозга профессора Кальверта в морском гроте.",
        "prerequisites": ["DLC04MQ03"],
        "rewards": [
            "Возвращение (или уничтожение) похищенного фрагмента вашего мозга и капитанская фуражка Тобара",
            "Полный контроль над паромом «Бродячая герцогиня» для бесплатных поездок между Пустошью и Пойнт-Лукаутом",
        ],
        "missableWarnings": [
            "В каюте Тобара на пароме обязательно осмотрите коллекцию вырезанных фрагментов мозга на полках и заберите свой собственный образец вместе с ключом от капитанской рубки!",
        ],
        "steps": [
            {
                "title": "Разберитесь с психотропным излучателем на колесе обозрения",
                "description": "Профессор Кальверт требует уничтожить генератор помех Десмонда на вершине колеса обозрения на набережной Пилигримов, тогда как Десмонд просит защитить устройство. При приближении к аттракциону Кальверт начнёт транслировать телепатические импульсы прямо в ваш череп через послеоперационный шрам!",
                "branches": [
                    {
                        "label": "Выбросить излучатель в мусоропровод (в пользу Десмонда)",
                        "tone": "alt",
                        "summary": "Спрячьте или защитите устройство помех от дикарей.",
                        "outcome": "Телепатический сигнал Кальверта ослаблен перед финальной схваткой.",
                    },
                    {
                        "label": "Разбить излучатель на колесе обозрения (по приказу Кальверта)",
                        "tone": "alt",
                        "summary": "Взорвите генератор помех Десмонда на вершине аттракциона.",
                        "outcome": "Кальверт получает полную мощь пси-передатчика.",
                    },
                ],
            },
            {
                "title": "Наведайтесь в машинное отделение парома и убейте паромщика Тобара",
                "description": "Поняв, что во время вашего беспамятства на пароме Тобар провёл вам трепанацию черепа, отправляйтесь на борт «Бродячей герцогини». Спуститесь в запертый коридор за спальной каютой, ликвидируйте вооружённого тесаком Тобара и заберите со стола банку с фрагментом собственного мозга.",
            },
            {
                "title": "Поспешите к особняку Кальвертов после подрыва",
                "description": "Выйдя с парома на пирс, вы станете свидетелем того, как Кальверт дистанционно взрывает фамильный особняк вместе с Десмондом. Доберитесь до дымящихся руин, где чудом уцелевший Десмонд открывает секретный люк в подземный комплекс маяка.",
            },
        ],
    },
    "DLC04MQ05a": {
        "order": 64,
        "summary": "Развязка вековой дуэли в подземелье маяка Пойнт-Лукаута (путь союза с Десмондом Локхартом): спуск в секретную биолабораторию под маяком, прорыв через роботов-охранников и уничтожение резервуара с мозгом профессора Кальверта.",
        "startCondition": "Спуститесь вслед за Десмондом Локхартом в подземный бункер под руинами особняка и маяком Пойнт-Лукаута.",
        "prerequisites": ["DLC04MQ04"],
        "rewards": [
            "Способность «Превосходство гуля» (Ghoul Ecology, +5 ед. урона любому оружию) или доступ к хранилищу артефактов лаборатории",
            "Уникальный «СВЧ-излучатель» (Microwave Emitter, игнорирующий броню энергооружием!), очки Десмонда и боеприпасы из сейфа",
        ],
        "missableWarnings": [
            "Не забудьте забрать уникальный «СВЧ-излучатель» из оружейного хранилища в боковом крыле подземной лаборатории перед выходом на поверхность!",
        ],
        "steps": [
            {
                "title": "Прорвитесь с Десмондом через подземный комплекс к маяку",
                "description": "Пройдите через технические туннели под разрушенным особняком в секретный научный бункер под маяком Пойнт-Лукаута. Помогайте Десмонду уничтожать турели, роботов-охранников и боевых робомозгов профессора Кальверта.",
                "skillChecks": ["Наука 75", "Энергооружие"],
            },
            {
                "title": "Войдите в центральный зал с капсулой мозга Кальверта",
                "description": "Когда вы достигнете главного лабораторного купола, профессор Кальверт в последний раз попытается переманить вас на свою сторону, а Десмонд потребует немедленно разбить бронированную колбу своего заклятого врага.",
            },
            {
                "title": "Разбейте капсулу Кальверта и откройте оружейное хранилище",
                "description": "Откройте огонь по стеклянной сфере жизнеобеспечения мозга профессора Кальверта, пока она не разрушится. После победы поговорите с торжествующим Десмондом Локхартом (он откроет кодовую дверь в хранилище с уникальным «СВЧ-излучателем» и боеприпасами), а также решите, поминать ли Надин как нового капитана парома.",
                "tip": "При желании после открытия хранилища можно устранить и самого Десмонда, чтобы забрать его уникальные очки (+5 к Лёгкому оружию, +5 к Взрывчатке).",
            },
        ],
    },
    "DLC04MQ05b": {
        "order": 65,
        "summary": "Альтернативный финал в подземном бункере маяка (путь профессора Кальверта): ликвидация Десмонда Локхарта по приказу Мозга, неизбежное предательство Кальверта и бой с его защитными роботами.",
        "startCondition": "В центральном зале подземной лаборатории маяка примите сторону мозга профессора Кальверта и атакуйте Десмонда Локхарта.",
        "prerequisites": ["DLC04MQ04"],
        "rewards": [
            "Очки Десмонда (+5 к Лёгкому оружию, +5 к Взрывчатке) и его оружие с тела",
            "Доступ в сокровищницу лаборатории с уникальным «СВЧ-излучателем» (Microwave Emitter)",
        ],
        "missableWarnings": [
            "Профессор Кальверт предаст вас сразу же после смерти Десмонда, активировав боевых роботов и турели зала — приготовьте импульсные гранаты или мощное оружие заранее!",
        ],
        "steps": [
            {
                "title": "Поверните оружие против Десмонда Локхарта в главном зале",
                "description": "Выслушав ультиматум обоих довоенных соперников перед капсулой мозга, откройте огонь по Десмонду Локхарту. Учитывайте, что Десмонд отлично вооружён и использует укрытия лабораторного зала.",
            },
            {
                "title": "Отразите внезапную атаку роботов после предательства Кальверта",
                "description": "Как только Десмонд падет, высокомерный профессор Кальверт объявит, что больше не нуждается в услугах «дикаря с Пустоши», заблокирует выходы и спустит на вас своих роботов-охранников и потолочные турели.",
            },
            {
                "title": "Уничтожьте капсулу Кальверта и заберите сокровища бункера",
                "description": "Увернитесь от огня роботов, расстреляйте бронированный стеклянный резервуар с мозгом самого Кальверта, заберите очки и ключ с тела Десмонда и откройте хранилище с уникальным «СВЧ-излучателем», после чего поднимитесь на лифте к вершине маяка.",
            },
        ],
    },
    "DLC04FF01": {
        "order": 66,
        "summary": "Экспедиция на раскопки довоенного исследовательского судна «Озимандия» (An Antique Land): сбор геологоразведочных данных с трёх болотных буровых участков вокруг нефтяной вышки для открытия медицинского сейфа с биогелем.",
        "startCondition": "Активируйте рабочий терминал на борту наполовину вкопанного в землю корабля на локации «Раскопки судна „Озимандия“» в центральной части Пойнт-Лукаута.",
        "prerequisites": [],
        "rewards": [
            "Доступ в запертое хранилище судна «Озимандия» с партией адаптированного и чистого биогеля, стимуляторов, Рад-Х и Мед-Х",
            "Очки опыта и раскрытие довоенной истории бурения на болотах Мэриленда",
        ],
        "missableWarnings": [
            "Извлечение кассет с данными на каждом из трёх участков почвенной съёмки вызывает из-под воды стаю разъярённых болотных крабов (болотников) — держите дробовик или мины наготове!",
        ],
        "steps": [
            {
                "title": "Активируйте терминал на раскопках судна «Озимандия»",
                "description": "Найдите в глубине болот Пойнт-Лукаута огороженный котлован с остовом исследовательского корабля «Озимандия». Спуститесь во внутренний отсек судна, прочитайте дневники экспедиции Сильвии на главном терминале и запустите протокол сбора геологических проб, чтобы отметить на карте 3 участка съёмки.",
            },
            {
                "title": "Соберите данные с трёх участков почвенной съёмки",
                "description": "Обойдите по очереди участок почвенной съёмки № 1, № 2 и № 3 на затопленных торфяниках вокруг буровой вышки. На каждой точке активируйте полевой прибор регистрации данных и отбейтесь от вылезающих из трясины болотников.",
            },
            {
                "title": "Загрузите результаты в судовой компьютер и откройте сейф",
                "description": "Вернитесь в трюм судна «Озимандия» и введите все три пакета данных в лабораторный терминал. Автоматика разблокирует бронированную дверь корабельного хранилища, где хранятся контейнеры с редким инопланетным/довоенным биогелем и медикаментами.",
            },
        ],
    },
    "DLC04FF02": {
        "order": 67,
        "summary": "Мистическая лавкрафтовская драма «Тёмная душа Блэкхолла»: аристократ Авдий Блэкхолл просит вернуть из рук болотных культистов старинную семейную реликвию — зловещий оккультный гримуар «Кривбекни», за которым охотится проповедница Марселла.",
        "startCondition": "Поговорите с хозяином поместья Блэкхоллов Авдием Блэкхоллом (на юго-западе Пойнт-Лукаута).",
        "prerequisites": [],
        "rewards": [
            "1000 крышек (2000 крышек при проверке Красноречия) и уникальное «Ритуальное холодное оружие» при передаче книги Авдию Блэкхоллу",
            "Либо +300 очков доброй кармы и очищение проклятия при уничтожении «Кривбекни» у обелиска в Данвич-билдинг на Столичной Пустоши",
        ],
        "missableWarnings": [
            "Если вы отдадите «Кривбекни» Авдию Блэкхоллу, а затем прокрадётесь в потайной подвал его особняка, вы сможете подглядеть оккультный ритуал жертвоприношения и забрать уникальный «Ритуальный нож» (а при желании и саму книгу для уничтожения в Данвич-билдинг)!",
        ],
        "steps": [
            {
                "title": "Примите заказ Авдия Блэкхолла и поговорите с Марселлой",
                "description": "В поместье Блэкхоллов выслушайте просьбу Авдия вернуть похищенную дикарями «семейную книгу». По пути к болотам загляните в палаточный лагерь «Пункт помощи беженцам» у берега, где миссионерка Марселла раскроет, что книга на самом деле является проклятым фолиантом «Кривбекни», и попросит принести её ей для уничтожения.",
                "skillChecks": ["Красноречие"],
            },
            {
                "title": "Заберите гримуар «Кривбекни» с алтаря на Ритуальной стоянке",
                "description": "Проберитесь на северо-восток в туманную локацию «Ритуальная стоянка» (Капище), охраняемую самыми опасными болотными дикарями и брутами. Зачистите круг хижин, спуститесь в подземное капище под главным тотемом и снимите с костяного пьедестала переплетённый человеческой кожей фолиант «Кривбекни».",
                "tip": "Как только вы возьмёте книгу с алтаря, сверху спустится новая волна фанатиков — заминируйте лестницу заранее!",
            },
            {
                "title": "Осмотрите место гибели Марселлы в её лагере",
                "description": "Если вы решите отнести книгу Марселле, то по возвращении в «Пункт помощи беженцам» обнаружите, что проповедница убита контрабандистами. Прослушайте её предсмертную голозапись «Записка Марселлы»: она умоляет отвезти «Кривбекни» на Столичную Пустошь и сжечь её у тёмного обелиска в подземельях Данвич-билдинг.",
            },
            {
                "title": "Выберите судьбу проклятой книги: особняк Блэкхолла или Данвич-билдинг",
                "description": "Завершите историю одним из двух путей.",
                "skillChecks": ["Красноречие", "Скрытность"],
                "branches": [
                    {
                        "label": "Уничтожить «Кривбекни» у обелиска в Данвич-билдинг (Добрый путь)",
                        "tone": "good",
                        "summary": "Вернитесь на пароме на Столичную Пустошь, спуститесь в Зловещие руины под Данвич-билдинг (юго-запад карты) и приложите книгу к чёрному монолиту.",
                        "outcome": "Обелиск вспыхивает пламенем и сжигает «Кривбекни», принося вам высокую положительную карму.",
                    },
                    {
                        "label": "Продать книгу Авдию Блэкхоллу (Злой/Хитрый путь)",
                        "tone": "evil",
                        "summary": "Отдайте фолиант Авдию в поместье Блэкхоллов за 1000–2000 крышек.",
                        "outcome": "Авдий открывает потайной ход за бюстом в спальне и проводит жертвоприношение в склепе (там можно убить его, забрать «Ритуальный нож» и всё равно увезти книгу в Данвич-билдинг!).",
                    },
                ],
            },
        ],
    },
    "DLC04FF03": {
        "order": 68,
        "summary": "Самогонный промысел на болотах Пойнт-Лукаута («Бальзам на душу» / A Spoonful of Whiskey): хитрая отшельница Маргарита притворяется тяжелобольной в своей хижине, чтобы заставить путника собрать дрожжи, ядерные батареи и плоды панги для запуска перегонного куба.",
        "startCondition": "Зайдите в «Хижину Маргариты» на южном краю болот Пойнт-Лукаута и поговорите с лежащей в постели хозяйкой.",
        "prerequisites": [],
        "rewards": [
            "Партия уникального «Самогона» Маргариты (+2 к Силе, +2 к Харизме, +10 ОЗ!) и возможность регулярно забирать новые бутылки",
            "Очки опыта и сниженный список ингредиентов при разоблачении её симуляции",
        ],
        "missableWarnings": [
            "Примените в диалоге с Маргаритой навыки «Медицина» 40, «Наука» 40, «Бартер» 40 или «Восприятие» 7 — если разоблачить её притворство, вам НЕ придётся искать 24 бутылки очищенной воды, а плодов панги понадобится вдвое меньше!",
        ],
        "steps": [
            {
                "title": "Поговорите с Маргаритой и разоблачите её мнимую болезнь",
                "description": "В деревянной хижине к северо-востоку от особняка Кальвертов вы найдёте стонущую в кровати Маргариту, которая просит принести компоненты для «целебной микстуры». Пройдите проверки Медицины, Науки, Бартера или Восприятия, чтобы понять, что она совершенно здорова и просто варит болотный самогон на продажу.",
                "skillChecks": ["Медицина 40", "Наука 40", "Бартер 40", "Восприятие 7"],
                "tip": "При успешном разоблачении Маргарита вычеркнет из списка 24 бутылки очищенной воды и согласится на 10 плодов культивированной панги (или 20 дикой) вместо удвоенной нормы.",
            },
            {
                "title": "Соберите дрожжи, ядерные батареи и плоды панги",
                "description": "Отыщите на болотах и в заброшенных лавках Пойнт-Лукаута (например, в магазине «Дары моря» и лагерях контрабандистов) 3 пачки дрожжей, 6 ядерных батарей и 10 плодов культивированной панги (растут в Соборе Ковчега и Голубя; либо соберите 20 плодов дикой панги на трясине).",
            },
            {
                "title": "Передайте ингредиенты и заберите готовый самогон через сутки",
                "description": "Отдайте все припасы Маргарите: она тут же встанет с постели и запустит самогонный аппарат во дворе. Подождите 24 игровых часа и вернитесь к ней за своей первой бесплатной партией крепкого «Самогона» (в дальнейшем у неё можно регулярно получать новые бутылки).",
            },
        ],
    },
    "DLC04FF04": {
        "order": 69,
        "summary": "Знакомство с осиротевшим мальчиком Кенни в заброшенной шахте «Пещера Херцога»: игры в салки и прятки под сводами штольни, подарок плюшевого медведя и получение постоянного убежища для отдыха в Пойнт-Лукауте.",
        "startCondition": "Спуститесь в локацию «Пещера Херцога» (Herzog Mine) в центральной части Пойнт-Лукаута и пройдите в жилой грот в глубине шахты.",
        "prerequisites": [],
        "rewards": [
            "Уникальный «Медведь Кенни» и доступ к тайнику с боеприпасами",
            "Безопасная кровать и дружелюбный дом-убежище в центре Пойнт-Лукаута",
        ],
        "missableWarnings": [
            "По дороге через верхние ярусы пещеры Херцога будьте осторожны с растяжками, капканами и обвалами, которые Кенни расставил для защиты от болотных дикарей!",
        ],
        "steps": [
            {
                "title": "Преодолейте ловушки в пещере Херцога и найдите жилой грот Кенни",
                "description": "Войдите в старую шахту «Пещера Херцога» к северу от Собора. Обезвреживайте самодельные ловушки в верхних штреках, пока не выйдете к освещённому подземному дому, где в полном одиночестве живёт мальчик-сирота Кенни.",
                "skillChecks": ["Взрывчатка", "Ремонт", "Вечный ребёнок"],
            },
            {
                "title": "Сыграйте с Кенни в салки и в прятки",
                "description": "Расспросите Кенни о судьбе его родителей и согласитесь поиграть с ним. Вы можете сыграть с мальчиком в салки (догоняя его по мостикам грота и убегая, когда водит он) или в прятки в боковых ответвлениях шахты.",
            },
            {
                "title": "Подарите плюшевого мишку и получите доступ к дому Кенни",
                "description": "Принесите скучающему мальчику плюшевого мишку (или пройдите добрые реплики диалога). Растроганный Кенни объявит вас своим лучшим другом, разрешит бесплатно спать на кровати и хранить вещи в его пещере, а также позволит забрать его любимого «Медведя Кенни».",
            },
        ],
    },
    "DLC04FF05": {
        "order": 70,
        "summary": "Довоенный шпионский триллер «Бархатный занавес»: расследование провалившейся операции китайских разведчиков Ян и Чэня в Пойнт-Лукауте, проникновение в карантинный лагерь «Тертлдав», подрыв застрявшей субмарины SSN-37-1A и побег из секретного бункера с уникальной винтовкой «Бэквотер».",
        "startCondition": "Войдите в номер 1D гостиницы «Домашняя» (Homestead Motel) на набережной Пойнт-Лукаута и активируйте терминал рядом со скелетом китайского агента.",
        "prerequisites": [],
        "rewards": [
            "Уникальная рычажная винтовка «Бэквотер» (Backwater Rifle, калибр 10-мм, 5-кратный шанс критического удара!)",
            "Китайские разведкомбинезоны, крышки, стелс-бои и способность взлома/науки из терминалов бункера",
        ],
        "missableWarnings": [
            "Не забудьте забрать уникальную винтовку «Бэквотер» со стойки на стене в финальном секретном бункере ДО того, как начнётся обратный отсчёт газовой ловушки!",
        ],
        "steps": [
            {
                "title": "Осмотрите номер 1D мотеля, тайник на пирсе и ячейку № 1207 в банке",
                "description": "В номере 1D гостиницы «Домашняя» прочитайте сообщения на терминале, заберите из комода возле скелета ключ от шкафчика и откройте ящик хранения на пирсе Пилигримов. С полученной голозаписью голосового пароля отправляйтесь в здание банка Пойнт-Лукаута, откройте депозитарную ячейку № 1207 и прослушайте приказ о ликвидации улик.",
            },
            {
                "title": "Найдите останки агента Ян в карантинном лагере «Тертлдав»",
                "description": "Отправляйтесь в заброшенный довоенный лагерь для интернированных «Тертлдав» (Turtledove Detention Camp), охраняемый роботами и гулями. Изучите журнал допросов в бараке охраны и откопайте на заднем дворе у забора безымянную могилу, чтобы забрать с тела агента Ян коды доступа к китайской подлодке.",
            },
            {
                "title": "Активируйте самоуничтожение подводной лодки SSN-37-1A",
                "description": "Доберитесь до секретного прибрежного грота на юго-западе карты, где стоит на мели китайская диверсионная субмарина SSN-37-1A. Войдите внутрь с кодом агента Ян, запустите протокол самоуничтожения на рубке, поверните дублирующий рычаг в торпедном отсеке и успейте выбежать наружу до взрыва.",
            },
            {
                "title": "Откройте секретный бункер хроматическими очками и спаситесь из ловушки",
                "description": "Вернитесь к терминалу в номере 1D мотеля, достаньте из сливного бачка унитаза специальные хроматические очки и наденьте их перед статуей напротив парка развлечений, чтобы увидеть цветовую комбинацию люка секретного бункера (красный, синий, жёлтый, зелёный). Внизу заберите со стены уникальную винтовку «Бэквотер», активируйте главный компьютер и, когда включится угарный газ, взломайте боковую вентиляционную решётку для побега!",
                "skillChecks": ["Взлом", "Наука", "Ремонт"],
            },
        ],
    },
    "DLC04FF06": {
        "order": 71,
        "summary": "Кровавый аттракцион «Сафари Плика» в прибрежной пещере Пойнт-Лукаута: эксцентричный гуль-охотник Плик за 1000 крышек предлагает проверить свои силы на подземной арене против волн разъярённых диких гулей и светящихся.",
        "startCondition": "Найдите локацию «Пляж у берегового грота» на северо-восточном побережье Пойнт-Лукаута, спуститесь в пещеру и поговорите с гулем Пликом.",
        "prerequisites": [],
        "rewards": [
            "Уникальный двуручный топор «Расчленитель» (The Dismemberer) со стола трофеев после победы",
            "Журнал Плика и уникальный гатлинг-лазер/снаряжение при желании",
        ],
        "missableWarnings": [
            "На арене одновременно атакуют до десятка быстрых диких гулей-потрошителей и светящихся — если вы играете с дополнением Broken Steel на высоком уровне, обязательно наденьте «Маску гуля» или запаситесь минами и боевым дробовиком!",
        ],
        "steps": [
            {
                "title": "Заплатите Плику 1000 крышек за участие в сафари",
                "description": "Спуститесь в прибрежный грот на северо-востоке Пойнт-Лукаута, где гуль Плик устроил частный охотничий клуб. Оплатите вступительный взнос в 1000 крышек, чтобы он открыл решётку на подземную арену.",
            },
            {
                "title": "Выйдите на арену, нажмите кнопку сирены и переживите волны гулей",
                "description": "Зайдите в огороженный сеткой зал (предварительно разложив противопехотные и крышко-мины перед боковыми шлюзами) и нажмите красную кнопку сигнала на центральном столбе. Из клеток хлынут несколько волн диких гулей, бродяг и светящихся — уничтожьте всех до единого.",
                "tip": "Если надеть «Маску гуля» из квеста «Тенпенни-Тауэр», даже гули на арене Плика не станут нападать первыми!",
            },
            {
                "title": "Вернитесь к Плику и заберите уникальный топор «Расчленитель»",
                "description": "Когда последний гуль падёт и ворота арены откроются, доложите изумлённому Плику о своей победе. В качестве главного приза со стены трофеев снимается блокировка с уникального пожарного топора «Расчленитель».",
            },
        ],
    },

    # =========================================================================
    # DLC 5: MOTHERSHIP ZETA (РАСШИРЕНИЕ 3 КВЕСТОВ ДО 3–4 ШАГОВ)
    # =========================================================================
    "DLC05MZ1": {
        "order": 72,
        "summary": "Похищение притягивающим лучом с места крушения НЛО на борт гигантского флагмана пришельцев «Зета»: побег из тюремного изолятора вместе с рейдершей Сомой и девочкой Салли, возврат снаряжения и подрыв реактора в Инженерном ядре.",
        "startCondition": "Поймайте радиосигнал «Разбившийся корабль пришельцев» к северу от свалки Гринер Пасчерс и электростанции MDPL-13 и подойдите к летающей тарелке.",
        "prerequisites": [],
        "rewards": [
            "Энергетическое оружие Чужих (Атомайзер, Дезинтегратор, Силовая дубинка) и инопланетный биогель",
            "Освобождение союзников из криогенного стазиса: военврача Эллиота Теркориана, самурая Тосиро Каго и ковбоя Полсона",
        ],
        "missableWarnings": [
            "ВНИМАНИЕ: На корабле «Зета» спрятано 25 голозаписей пленных пришельцев (за сбор всех 25 даётся способность «Эксперт-ксенотехник» +20% к урону оружием Чужих). Записи № 19 (в Паровом туннеле перед Инженерным ядром) и в Криолаборатории можно забрать ТОЛЬКО по ходу сюжета — после финала эти отсеки блокируются навсегда!",
        ],
        "steps": [
            {
                "title": "Устройте потасовку с Сомой и выберитесь из камеры содержания",
                "description": "Очнувшись после экспериментов Чужих в энергетической камере рядом с девушкой Сомой, согласитесь инсценировать с ней кулачную драку. Когда двое пришельцев с дубинками откроют силовое поле, чтобы разнять вас, перебейте охрану и выпустите из соседнего бокса маленькую девочку Салли.",
            },
            {
                "title": "Верните своё снаряжение в отсеке хранения",
                "description": "Следуйте за Салли через вентиляционные шахты и коридоры тюремного блока к камере вещевых доказательств. Откройте контейнер перед обзорным окном, чтобы забрать всё своё оружие и броню, а также подберите первые инопланетные атомайзеры и дезинтеграторы.",
            },
            {
                "title": "Выведите из стазиса Эллиота, самурая Тосиро Каго и ковбоя Полсона",
                "description": "По пути через паровой туннель (не пропустите запись пленного № 19!) доберитесь до Инженерного ядра корабля. Активируйте пульты четырёх криогенных капсул, чтобы разморозить полевого медика армии США Эллиота Теркориана (из Анкориджа 2077 года), японского самурая XVI века Тосиро Каго и стрелка Дикого Запада Полсона.",
            },
            {
                "title": "Перегрузите генератор в двигательном отсеке",
                "description": "Спуститесь в двигательный зал Инженерного ядра, поочерёдно поднимите три охлаждающих контура генератора и расстреляйте их, укрываясь от огня пришельцев и дронов, чтобы обесточить внутренние переборки и открыть проход к другим секторам корабля.",
            },
        ],
    },
    "DLC05MZ2": {
        "order": 73,
        "summary": "Диверсия в трёх ключевых крыльях корабля «Зета»: уничтожение генераторов в Криолаборатории, Ангаре (где строится «Валькирия») и Сборочном цехе роботов, сборка стабилизатора из деталей дронов и выход в открытый космос по обшивке корабля.",
        "startCondition": "Поговорите с Салли и спасёнными союзниками в Инженерном ядре после перегрузки главного двигателя.",
        "prerequisites": ["DLC05MZ1"],
        "rewards": [
            "Уникальное оружие Чужих («Защитник капитана», криогранаты и криомины от Эллиота Теркориана)",
            "Скафандр пришельцев и выход в открытый космос на фоне планеты Земля",
        ],
        "missableWarnings": [
            "ОБЯЗАТЕЛЬНО соберите все голозаписи пленных в Криолаборатории, Грузовом трюме, Биолаборатории и Сборочном цехе ДО того, как наденете скафандр и выйдете в открытый космос — после этого двери в эти крылья из Инженерного ядра закроются навсегда!",
        ],
        "steps": [
            {
                "title": "Уничтожьте генераторы в Криолаборатории и Сборочном цехе роботов",
                "description": "Из Инженерного ядра поочерёдно пройдите в Криолабораторию (возьмите с собой медика Эллиота — он умеет изготавливать для вас криогранаты и криомины!) и в Сборочный цех роботов (вместе с Сомой). В конце каждого крыла поднимите защитные кожухи генератора и расстреляйте три силовых узла.",
                "tip": "Во время зачистки Сборочного цеха обязательно соберите 3 исправных блока управления с уничтоженных дронов-охранников — они понадобятся для ремонта телепорта!",
            },
            {
                "title": "Взорвите генератор в Ангаре и отразите контратаку в Инженерном ядре",
                "description": "Вместе с ковбоем Полсоном пробейтесь на смотровой балкон огромного Ангара, где стоит перехватчик пришельцев, запустите перегрузку ангарного реактора и уничтожьте третий генератор. Вернитесь в Инженерное ядро и помогите союзникам отбить штурмовой отряд Чужих.",
            },
            {
                "title": "Поднимитесь через декомпрессионный шлюз и наденьте скафандр",
                "description": "С помощью собранных с дронов деталей почините телепорт на технический уровень и войдите в декомпрессионную камеру. Обыщите тело погибшего офицера из Убежища 108, наденьте герметичный космический скафандр и активируйте шлюз.",
            },
            {
                "title": "Пройдите по внешней обшивке «Зеты» в открытом космосе",
                "description": "Выйдите на корпус корабля на орбите Земли! Передвигаясь под куполом защитного поля, активируйте по очереди три внешних распределительных щита, чтобы подать энергию на телепорт к орудийной палубе и капитанскому мостику.",
            },
        ],
    },
    "DLC05FF01": {
        "order": 75,
        "summary": "Приключение в техническом трюме и мусоропроводе корабля «Зета» («Крысы в трюме корабля „Зета“» / Steerage Rats): падение в отсек сброса отходов во время поездки с Салли, прорыв через лабиринт коллекторов с инопланетными червями и поиск всех 25 записей пленных.",
        "startCondition": "Запускается автоматически при посадке в транспортную тележку с Салли на техническом уровне или в отсеке сброса отходов корабля «Зета».",
        "prerequisites": ["DLC05MZ1"],
        "rewards": [
            "Способность «Эксперт-ксенотехник» (Xenotech Expert, +20% к урону всем оружием пришельцев за прослушивание всех 25 записей пленных!)",
            "Крупные запасы кристаллов Чужих, эпоксидной смолы (чинит текущее оружие прямо в инвентаре!) и редких образцов с Земли",
        ],
        "missableWarnings": [
            "В техническом отсеке и мусоропроводе находятся сразу несколько терминалов с голозаписями пленных — активируйте каждый зелёный пульт по пути к рубке Салли!",
        ],
        "steps": [
            {
                "title": "Спуститесь на транспортной тележке в отсек сброса отходов",
                "description": "Из Инженерного ядра войдите в технический сектор и поговорите с Салли у грузовой люльки. Когда тележка сорвётся с рельсов и рухнет в мусоропровод трюма, Салли уползёт по верхнему вентиляционному каналу к диспетчерской, чтобы открывать вам заблокированные переборки.",
            },
            {
                "title": "Прорвитесь через два уровня коллекторов к рубке управления Салли",
                "description": "Продвигайтесь через заваленные земным мусором (тракторами, дорожными знаками и контейнерами) залы технического трюма, отстреливая агрессивных инопланетных турельных червей, дронов и мерзостей, пока Салли поэтапно разблокирует шлюзы на вашем пути.",
                "tip": "Собирайте по ящикам трюма «Инопланетную эпоксидную смолу» — при использовании в Пип-Бое она мгновенно восстанавливает прочность оружия в ваших руках без верстака и запчастей!",
            },
            {
                "title": "Прослушайте все 25 голозаписей пленных ради способности «Эксперт-ксенотехник»",
                "description": "Встретьтесь с Салли в диспетчерской рубке трюма и активируйте телепорт обратно в Инженерное ядро. Параллельно обследуйте все зелёные консоли звукозаписи в отсеках корабля: прослушав все 25 дневников похищенных землян разных эпох, вы получите постоянную способность «Эксперт-ксенотехник» (+20% урона инопланетным оружием).",
            },
        ],
    },
}


def clean_and_translate_stage_logs(stage_logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out developer dummy comments and translate every English stage log to Russian."""
    cleaned_stages: list[dict[str, Any]] = []
    for st in stage_logs:
        new_logs: list[str] = []
        seen_in_stage: set[str] = set()
        for raw_log in st.get("logs", []):
            s = raw_log.strip()
            if not s or s in DUMMY_STAGE_LOGS:
                continue
            if s in STAGE_LOG_RU:
                ru = STAGE_LOG_RU[s]
            elif re.search(r"[а-яА-ЯёЁ]", s) and not re.search(r"[a-zA-Z]{4,}", s):
                ru = s
            else:
                raise KeyError(f"Untranslated stageLog string: {s!r}")
            if ru and ru not in seen_in_stage:
                seen_in_stage.add(ru)
                new_logs.append(ru)
        if new_logs:
            cleaned_stages.append(
                {
                    "stage": st["stage"],
                    "logs": new_logs,
                    "completes": bool(st.get("completes", False)),
                    "fails": bool(st.get("fails", False)),
                }
            )
    return cleaned_stages


def clean_objectives(objectives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize quotes and whitespace in Russian ESM objectives."""
    cleaned: list[dict[str, Any]] = []
    for obj in objectives:
        txt = obj.get("text", "").strip()
        if not txt:
            continue
        # Replace straight quotes around titles with Russian guillemets «»
        txt = re.sub(r'"([^"]+)"', r"«\1»", txt)
        txt = re.sub(r"\s+\.", ".", txt)
        if txt.endswith(","):
            txt = txt[:-1] + "."
        cleaned.append({"index": obj["index"], "text": txt})
    return cleaned


def main() -> None:
    assert WALKTHROUGHS_PATH.exists(), f"Missing {WALKTHROUGHS_PATH}"
    walkthroughs: list[dict[str, Any]] = json.loads(WALKTHROUGHS_PATH.read_text(encoding="utf-8"))
    assert len(walkthroughs) == 81, f"Expected 81 quests, found {len(walkthroughs)}"

    upgraded_count = 0
    for w in walkthroughs:
        nid = w["nodeId"]
        edid = w["edid"]

        # 1. Canonical Russian Title
        if nid not in QUEST_TITLES_RU:
            raise KeyError(f"Missing quest nodeId in QUEST_TITLES_RU: {nid} ({edid})")
        w["title"] = QUEST_TITLES_RU[nid]

        # 2. Upgrade curated walkthroughs for all 15 previously uncurated & 34 1-2 step quests
        if edid in UPGRADED_GUIDES:
            ug = UPGRADED_GUIDES[edid]
            w["curated"] = True
            w["order"] = ug["order"]
            w["summary"] = ug["summary"]
            w["startCondition"] = ug["startCondition"]
            w["prerequisites"] = ug.get("prerequisites", w.get("prerequisites", []))
            w["rewards"] = ug["rewards"]
            w["missableWarnings"] = ug.get("missableWarnings", [])
            w["steps"] = ug["steps"]
            upgraded_count += 1

        # 3. Clean & translate stageLogs and objectives
        w["stageLogs"] = clean_and_translate_stage_logs(w.get("stageLogs", []))
        w["objectives"] = clean_objectives(w.get("objectives", []))

    # Sort deterministically by (order, title)
    walkthroughs.sort(key=lambda x: (x["order"], x["title"]))

    # Write updated walkthroughs.json and /tmp/f3_quest_titles_ru.json
    WALKTHROUGHS_PATH.write_text(
        json.dumps(walkthroughs, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    QUEST_TITLES_TMP_PATH.write_text(
        json.dumps(QUEST_TITLES_RU, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # 4. Strict Verification Audit
    total_quests = len(walkthroughs)
    curated_true = sum(1 for w in walkthroughs if w.get("curated") is True)
    titles_without_cyrillic = [
        (w["edid"], w["title"])
        for w in walkthroughs
        if not re.search(r"[а-яА-ЯёЁ]", w.get("title", ""))
    ]
    all_caps_titles = [
        (w["edid"], w["title"])
        for w in walkthroughs
        if w.get("title", "").isupper()
    ]
    quests_lt_3_steps = [
        (w["edid"], len(w.get("steps", [])))
        for w in walkthroughs
        if len(w.get("steps", [])) < 3
    ]
    english_stage_logs = []
    for w in walkthroughs:
        for st in w.get("stageLogs", []):
            for lg in st.get("logs", []):
                if not re.search(r"[а-яА-ЯёЁ]", lg) or re.search(r"[a-zA-Z]{4,}", lg):
                    english_stage_logs.append((w["edid"], st["stage"], lg))
    english_objectives = []
    for w in walkthroughs:
        for o in w.get("objectives", []):
            txt = o.get("text", "")
            if not re.search(r"[а-яА-ЯёЁ]", txt):
                english_objectives.append((w["edid"], o["index"], txt))

    print(f"Upgraded walkthroughs: {upgraded_count} quests expanded/curated")
    print(f"Total quests: {total_quests}")
    print(f"curated=True: {curated_true}")
    print(f"Titles without Cyrillic: {len(titles_without_cyrillic)}")
    print(f"ALL-CAPS titles remaining: {len(all_caps_titles)}")
    print(f"Quests with < 3 steps: {len(quests_lt_3_steps)}")
    print(f"English stageLogs remaining: {len(english_stage_logs)}")
    print(f"English objectives remaining: {len(english_objectives)}")

    assert total_quests == 81
    assert curated_true == 81
    assert len(titles_without_cyrillic) == 0, f"Titles without Cyrillic: {titles_without_cyrillic}"
    assert len(all_caps_titles) == 0, f"ALL-CAPS titles: {all_caps_titles}"
    assert len(quests_lt_3_steps) == 0, f"Quests < 3 steps: {quests_lt_3_steps}"
    assert len(english_stage_logs) == 0, f"English stageLogs: {english_stage_logs}"
    assert len(english_objectives) == 0, f"English objectives: {english_objectives}"


if __name__ == "__main__":
    main()
