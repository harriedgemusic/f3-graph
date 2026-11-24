import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { GraphNode, Walkthrough } from "./types";

export type Lang = "ru" | "en";

const LANG_STORAGE_KEY = "f3_graph_lang_v1";

function detectInitialLang(): Lang {
  if (typeof window !== "undefined") {
    try {
      const params = new URLSearchParams(window.location.search);
      const urlLang = params.get("lang");
      if (urlLang === "en" || urlLang === "ru") return urlLang;
    } catch {
      // ignore URL parsing errors
    }
    try {
      const saved = localStorage.getItem(LANG_STORAGE_KEY);
      if (saved === "en" || saved === "ru") return saved;
    } catch {
      // ignore storage errors
    }
  }
  return "ru";
}

const UI_STRINGS = {
  ru: {
    docTitle: "Fallout 3 GOTY — Интерактивный граф мира и прохождение миссий",
    loadingSubtitle: "Загрузка графа сущностей и прохождений Fallout 3 GOTY...",
    errorTitle: "Ошибка инициализации данных",
    errorGraphMissing: "Файл graph.json не загружен",
    errorUnknown: "Неизвестная ошибка загрузки данных",
    headerSubtitle: "Граф персонажей, локаций, событий, предметов, миссий и объектов (RUS ESM)",
    langToggleTitle: "Переключить язык интерфейса и базы (RU / EN)",
    tabs: {
      graph: "Интерактивный граф",
      walkthroughs: "Прохождение миссий",
      catalog: "Энциклопедия сущностей",
      stats: "Аналитика мира",
    },
    graph: {
      linksPrefix: "Связей:",
      tooltipHint: "Клик — выбрать · 2× — фокус",
      searchPlaceholder: "Поиск (нажмите /)...",
      modeGalaxy: "3D Галактика",
      modeMap: "3D Карта",
      densityTitle: "Плотность отображения узлов графа",
      scopeAtlasShort: "Обзор",
      scopeCoreShort: "Сюжет",
      scopeExtendedShort: "Весь мир",
      scopeAtlasTitle: "Ключевые узлы и ориентиры",
      scopeCoreTitle: "Ядро сюжета и квестов",
      scopeExtendedTitle: "Все сущности Fallout 3 GOTY",
      filtersBtn: "Фильтры",
      graphDetailHeading: "Детализация графа",
      scopeAtlasLong: "Обзор (Атлас)",
      scopeCoreLong: "Ядро сюжета",
      scopeExtendedLong: "Полный мир",
      nodesUnit: "узлов",
      moduleHeading: "Модуль / Дополнение",
      allModulesOption: "Все модули Fallout 3 GOTY",
      bgLootEdgesLabel: "Фоновые связи лута и контейнеров",
      edgeTypesHeading: "Типы связей",
      enableAll: "Включить все",
      pathFinderBtn: "Путь A → B",
      isolationPrefix: "3D-фокус:",
      hopSingular: "шаг",
      hopPlural: "шага",
      exitIsolation: "Выйти",
      quickJumpLabel: "Быстрый переход к ключевым узлам:",
      flyToTitle: "Перейти к",
      pathHeading: "Поиск связи в графе:",
      pointAPlaceholder: "Точка А...",
      pointBPlaceholder: "Точка Б...",
      close: "Закрыть",
      chainLabel: "Цепочка",
      stepsWord: "шага",
      noPathFound: "Связь между выбранными узлами не найдена.",
      dockNodes: "Узлы:",
      dockEdges: "Связи:",
      zoomIn: "Приблизить",
      zoomOut: "Отдалить",
      centerCamera: "Центрировать камеру (R)",
      autoOrbitTitle: "Автовращение сцены",
      autoOrbitLabel: "Орбита",
      resetAllTitle: "Сбросить фильтры и камеру",
      resetAllLabel: "Сброс",
      controlsHint: "ЛКМ — вращать · ПКМ — сдвиг · Колесо — зум · WASD/QE — полёт · Двойной клик — 3D-фокус",
    },
    inspector: {
      expandTitle: "Развернуть статью для удобного чтения",
      collapseTitle: "Свернуть панель статьи",
      compactLabel: "Узкий вид",
      expandLabel: "Развернуть статью",
      closeTitle: "Закрыть инспектор",
      openWalkthrough: "Открыть прохождение",
      clearIsolation: "Сбросить изоляцию",
      isolate1Hop: "Изолировать 1 шаг",
      isolate2Hops: "2 шага",
      findPath: "Найти путь",
      connectedEntities: "Связанные сущности",
      filterLinksPlaceholder: "Фильтр связей...",
      noMatchingLinks: "Нет совпадающих связей.",
      moreCount: "ещё",
    },
    details: {
      noEntry: "Подробная энциклопедическая запись для этой сущности отсутствует.",
      sourceEsmWiki: "Файлы игры + Fallout Wiki",
      sourceEsm: "Файлы игры (.ESM)",
      sourceEnc: "Файлы игры + Энциклопедия",
      wikiDefaultLabel: "Статья Fallout Wiki",
      charParams: "Параметры персонажа",
      uniqueBadge: "Уникальный",
      essentialBadge: "Сюжетный (бессмертный)",
      raceLabel: "Раса:",
      levelLabel: "Уровень:",
      hpLabel: "ОЗ (HP):",
      sexLabel: "Пол:",
      female: "Женский",
      male: "Мужской",
      essentialLabel: "Бессмертный:",
      essentialYes: "Да (сюжетный)",
      no: "Нет",
      uniqueLabel: "Уникальный:",
      yes: "Да",
      behaviorLabel: "Поведение:",
      specialHeading: "Система характеристик S.P.E.C.I.A.L.",
      specialScale: "Шкала 1–10",
      servicesTitle: "Услуги и роль:",
      factionsTitle: "Фракции:",
      inventoryTitle: "Инвентарь (ключевые предметы):",
      collapse: "Свернуть",
      allBtn: "Все",
      showAllBtn: "Показать все",
      expandFull: "Развернуть полностью",
      locationGeo: "География локации",
      worldspaceLabel: "Мир:",
      markerTypeLabel: "Тип маркера:",
      itemSpecsHeading: "Характеристики предмета",
      weaponClass: "Класс оружия",
      damage: "Урон",
      dr: "СУ (DR)",
      ammo: "Боеприпасы",
      clipSize: "Магазин",
      fireRate: "Скорострельность",
      apCost: "Стоимость ОД",
      apUnit: "ОД (V.A.T.S.)",
      critDamage: "Крит. урон",
      spread: "Разброс",
      durability: "Прочность",
      value: "Цена",
      capsShort: "кр.",
      weight: "Вес",
      effectsTitle: "Эффекты и свойства:",
      unlocksItemTitle: "Открывает двери / сейфы:",
      noteTextTitle: "Текст заметки / документа:",
      perkDetailsHeading: "Сведения о способности",
      objectDetailsHeading: "Сведения об объекте",
      lockDiffLabel: "Сложность взлома:",
      perkEffectsTitle: "Требования и бонусы:",
      objectEffectsTitle: "Эффекты и требования:",
      objectUnlocksTitle: "Назначение / требуемый ключ:",
      terminalEntriesTitle: "Записи терминала",
      entryFallback: "Запись #",
      quotesHeading: "Реплики и цитаты",
    },
    catalog: {
      allCategories: "Все категории",
      searchPlaceholder: "Поиск по названию (RUS/ENG), роли, описанию, EditorID или FormID...",
      allDlcs: "Все дополнения (GOTY)",
      allSubtypes: "Все подтипы",
      sortByLinks: "По связям",
      sortByName: "По алфавиту",
      foundRecords: "Найдено записей:",
      page: "Страница",
      of: "из",
      dmgChip: "Урон:",
      drChip: "СУ:",
      ammoChip: "Боеприпасы:",
      apChip: "ОД",
      capsWord: "крышек",
      lvlChip: "Ур.",
      hpChip: "ОЗ:",
      essentialChip: "Сюжетный",
      lockChip: "Взлом:",
      terminalChip: "Терминал:",
      entriesShort: "зап.",
      linksLabel: "Связей:",
      articleBtn: "Статья",
      guideBtn: "Гайд",
      toGraphBtn: "На граф",
      prevPage: "Назад",
      nextPage: "Вперёд",
      backToPrevArticle: "Назад к предыдущей статье",
      closeArticleTitle: "Закрыть статью (Esc)",
      closeArticleAria: "Закрыть статью",
      to3dGraphBtn: "На 3D-граф",
      focus3dBtn: "3D-фокус",
      walkthroughBtn: "Прохождение",
    },
    walkthroughs: {
      archiveTitle: "Архив миссий",
      completedRatio: "пройдено",
      searchPlaceholder: "Найти миссию (название, EDID)...",
      filterAll: "Все",
      filterMain: "Сюжет",
      filterSide: "Побочные",
      filterDlc: "DLC",
      filterFreeform: "Свободные",
      allCampaigns: "Все кампании и DLC",
      notFound: "Миссии не найдены.",
      guideBadge: "ГАЙД",
      stepsShort: "шагов",
      emptyState: "Выберите миссию слева, чтобы увидеть пошаговое прохождение.",
      questCompleted: "Миссия пройдена",
      markCompleted: "Отметить пройденной",
      showOnGraph: "Показать миссию на графе",
      stepsProgressPrefix: "Выполнено шагов:",
      of: "из",
      howToStart: "Как начать задание",
      keyRewards: "Ключевые награды",
      missableWarnings: "Важно не пропустить",
      loreHeading: "Энциклопедическая справка и лор миссии",
      stepsHeading: "Шаги для успешного выполнения",
      markStepTitle: "Отметить шаг выполненным",
      outcomePrefix: "Итог:",
      linkedEntitiesHeading: "Участники, локации и объекты миссии в графе",
      showEntityTitle: "Показать сущность на графе",
      esmHeadingPrefix: "Официальные цели и журнал Пип-Боя (из файлов ESM:",
      esmObjectivesWord: "целей",
      esmStagesWord: "стадий",
      esmObjectivesSub: "Задачи в Пип-Бое (QOBJ):",
      esmStagesSub: "Записи стадий квеста (INDX / CNAM):",
      stageWord: "Стадия",
      completesBadge: "ЗАВЕРШЕНИЕ",
      failsBadge: "ПРОВАЛ",
      toneGood: "Добрый путь",
      toneEvil: "Злой путь",
      toneNeutral: "Нейтральный путь",
      toneAlt: "Альтернатива",
      groupCharacters: "Персонажи",
      groupLocations: "Локации",
      groupEvents: "События",
      groupItems: "Предметы",
      groupObjects: "Объекты и перки",
      groupQuests: "Связанные миссии",
    },
    stats: {
      totalNodes: "Всего узлов графа",
      storyCore: "Ядро сюжета:",
      totalEdges: "Связей между сущностями",
      edgeTypesSubtitle: "13 типов игровых отношений",
      questsWithWt: "Миссий с прохождением",
      curatedGuides: "Детальных гайдов:",
      dataSource: "Источник данных",
      sourceValue: "Fallout 3 GOTY (6 ESM)",
      sourceSub: "Fallout 3 GOTY (RUS + ENG ESM)",
      byCategory: "Распределение по категориям сущностей",
      byModule: "Распределение по модулям (Base + 5 DLC)",
      edgeTypesHeading: "Типы игровых связей в графе",
      topHubsHeading: "Ключевые хабы по числу связей (нажмите для перехода на граф)",
    },
  },
  en: {
    docTitle: "Fallout 3 GOTY — Interactive World Graph & Quest Walkthroughs",
    loadingSubtitle: "Loading Fallout 3 GOTY entity graph & walkthroughs...",
    errorTitle: "Data Initialization Error",
    errorGraphMissing: "Failed to load graph.json",
    errorUnknown: "Unknown data loading error",
    headerSubtitle: "Knowledge graph of characters, locations, events, items, quests & objects (ENG ESM)",
    langToggleTitle: "Switch interface & database language (RU / EN)",
    tabs: {
      graph: "Interactive Graph",
      walkthroughs: "Quest Walkthroughs",
      catalog: "Entity Encyclopedia",
      stats: "World Analytics",
    },
    graph: {
      linksPrefix: "Links:",
      tooltipHint: "Click — select · 2× — focus",
      searchPlaceholder: "Search (press /)...",
      modeGalaxy: "3D Galaxy",
      modeMap: "3D Map",
      densityTitle: "Graph node display density",
      scopeAtlasShort: "Overview",
      scopeCoreShort: "Story",
      scopeExtendedShort: "Full World",
      scopeAtlasTitle: "Key hubs & landmarks",
      scopeCoreTitle: "Main story & quest core",
      scopeExtendedTitle: "All Fallout 3 GOTY entities",
      filtersBtn: "Filters",
      graphDetailHeading: "Graph Detail",
      scopeAtlasLong: "Overview (Atlas)",
      scopeCoreLong: "Story Core",
      scopeExtendedLong: "Full World",
      nodesUnit: "nodes",
      moduleHeading: "Module / Expansion",
      allModulesOption: "All Fallout 3 GOTY modules",
      bgLootEdgesLabel: "Background loot & container links",
      edgeTypesHeading: "Link Types",
      enableAll: "Enable all",
      pathFinderBtn: "Path A → B",
      isolationPrefix: "3D Focus:",
      hopSingular: "hop",
      hopPlural: "hops",
      exitIsolation: "Exit",
      quickJumpLabel: "Quick jump to landmarks:",
      flyToTitle: "Fly to",
      pathHeading: "Find Graph Path:",
      pointAPlaceholder: "Start node A...",
      pointBPlaceholder: "Target node B...",
      close: "Close",
      chainLabel: "Path",
      stepsWord: "steps",
      noPathFound: "No connection found between selected nodes.",
      dockNodes: "Nodes:",
      dockEdges: "Edges:",
      zoomIn: "Zoom in",
      zoomOut: "Zoom out",
      centerCamera: "Center camera (R)",
      autoOrbitTitle: "Auto-orbit scene",
      autoOrbitLabel: "Orbit",
      resetAllTitle: "Reset filters & camera",
      resetAllLabel: "Reset",
      controlsHint: "LMB — orbit · RMB — pan · Wheel — zoom · WASD/QE — fly · Double-click — 3D focus",
    },
    inspector: {
      expandTitle: "Expand article for comfortable reading",
      collapseTitle: "Collapse article panel",
      compactLabel: "Compact",
      expandLabel: "Expand",
      closeTitle: "Close inspector",
      openWalkthrough: "Open Walkthrough",
      clearIsolation: "Clear Isolation",
      isolate1Hop: "Isolate 1 hop",
      isolate2Hops: "2 hops",
      findPath: "Find Path",
      connectedEntities: "Connected Entities",
      filterLinksPlaceholder: "Filter connections...",
      noMatchingLinks: "No matching connections.",
      moreCount: "more",
    },
    details: {
      noEntry: "No detailed encyclopedia entry is available for this entity.",
      sourceEsmWiki: "Game Files + Fallout Wiki",
      sourceEsm: "Game Files (.ESM)",
      sourceEnc: "Game Files + Encyclopedia",
      wikiDefaultLabel: "Fallout Wiki Article",
      charParams: "Character Attributes",
      uniqueBadge: "Unique",
      essentialBadge: "Essential (Immortal)",
      raceLabel: "Race:",
      levelLabel: "Level:",
      hpLabel: "HP:",
      sexLabel: "Sex:",
      female: "Female",
      male: "Male",
      essentialLabel: "Essential:",
      essentialYes: "Yes (Essential)",
      no: "No",
      uniqueLabel: "Unique:",
      yes: "Yes",
      behaviorLabel: "Behavior:",
      specialHeading: "S.P.E.C.I.A.L. Attributes",
      specialScale: "Scale 1–10",
      servicesTitle: "Services & Role:",
      factionsTitle: "Factions:",
      inventoryTitle: "Inventory (Key Items):",
      collapse: "Collapse",
      allBtn: "All",
      showAllBtn: "Show all",
      expandFull: "Show full text",
      locationGeo: "Location Geography",
      worldspaceLabel: "Worldspace:",
      markerTypeLabel: "Marker Type:",
      itemSpecsHeading: "Item Specifications",
      weaponClass: "Weapon Class",
      damage: "Damage",
      dr: "DR",
      ammo: "Ammo",
      clipSize: "Clip Size",
      fireRate: "Fire Rate",
      apCost: "AP Cost",
      apUnit: "AP (V.A.T.S.)",
      critDamage: "Crit Damage",
      spread: "Spread",
      durability: "Item HP",
      value: "Value",
      capsShort: "caps",
      weight: "Weight",
      effectsTitle: "Effects & Properties:",
      unlocksItemTitle: "Unlocks Doors / Safes:",
      noteTextTitle: "Note / Document Text:",
      perkDetailsHeading: "Perk Details",
      objectDetailsHeading: "Object Details",
      lockDiffLabel: "Lock Difficulty:",
      perkEffectsTitle: "Requirements & Bonuses:",
      objectEffectsTitle: "Effects & Requirements:",
      objectUnlocksTitle: "Purpose / Required Key:",
      terminalEntriesTitle: "Terminal Entries",
      entryFallback: "Entry #",
      quotesHeading: "Quotes & Dialogue",
    },
    catalog: {
      allCategories: "All Categories",
      searchPlaceholder: "Search by name, role, description, EditorID, or FormID...",
      allDlcs: "All Expansions (GOTY)",
      allSubtypes: "All Subtypes",
      sortByLinks: "By Links",
      sortByName: "A–Z",
      foundRecords: "Entries found:",
      page: "Page",
      of: "of",
      dmgChip: "DMG:",
      drChip: "DR:",
      ammoChip: "Ammo:",
      apChip: "AP",
      capsWord: "caps",
      lvlChip: "Lv.",
      hpChip: "HP:",
      essentialChip: "Essential",
      lockChip: "Lock:",
      terminalChip: "Terminal:",
      entriesShort: "entries",
      linksLabel: "Links:",
      articleBtn: "Article",
      guideBtn: "Guide",
      toGraphBtn: "Graph",
      prevPage: "Previous",
      nextPage: "Next",
      backToPrevArticle: "Back to previous article",
      closeArticleTitle: "Close article (Esc)",
      closeArticleAria: "Close article",
      to3dGraphBtn: "3D Graph",
      focus3dBtn: "3D Focus",
      walkthroughBtn: "Walkthrough",
    },
    walkthroughs: {
      archiveTitle: "Quest Archive",
      completedRatio: "done",
      searchPlaceholder: "Find quest (title, EDID)...",
      filterAll: "All",
      filterMain: "Main",
      filterSide: "Side",
      filterDlc: "DLC",
      filterFreeform: "Freeform",
      allCampaigns: "All Campaigns & DLCs",
      notFound: "No quests found.",
      guideBadge: "GUIDE",
      stepsShort: "steps",
      emptyState: "Select a quest on the left to view its step-by-step walkthrough.",
      questCompleted: "Quest Completed",
      markCompleted: "Mark Completed",
      showOnGraph: "Show Quest on Graph",
      stepsProgressPrefix: "Steps completed:",
      of: "of",
      howToStart: "How to Start",
      keyRewards: "Key Rewards",
      missableWarnings: "Missable Warnings",
      loreHeading: "Encyclopedia Lore & Background",
      stepsHeading: "Step-by-Step Walkthrough",
      markStepTitle: "Mark step completed",
      outcomePrefix: "Outcome:",
      linkedEntitiesHeading: "Linked Characters, Locations & Objects on Graph",
      showEntityTitle: "Show entity on graph",
      esmHeadingPrefix: "Official Pip-Boy Objectives & Journal (from ESM:",
      esmObjectivesWord: "objectives",
      esmStagesWord: "stages",
      esmObjectivesSub: "Pip-Boy Objectives (QOBJ):",
      esmStagesSub: "Quest Stage Logs (INDX / CNAM):",
      stageWord: "Stage",
      completesBadge: "COMPLETES",
      failsBadge: "FAILS",
      toneGood: "Good Path",
      toneEvil: "Evil Path",
      toneNeutral: "Neutral Path",
      toneAlt: "Alternative",
      groupCharacters: "Characters",
      groupLocations: "Locations",
      groupEvents: "Events",
      groupItems: "Items",
      groupObjects: "Objects & Perks",
      groupQuests: "Related Quests",
    },
    stats: {
      totalNodes: "Total Graph Nodes",
      storyCore: "Story Core:",
      totalEdges: "Entity Connections",
      edgeTypesSubtitle: "13 game relationship types",
      questsWithWt: "Quests with Walkthroughs",
      curatedGuides: "Curated guides:",
      dataSource: "Data Source",
      sourceValue: "Fallout 3 GOTY (6 ESM)",
      sourceSub: "Fallout 3 GOTY (ENG + RUS ESM)",
      byCategory: "Distribution by Entity Category",
      byModule: "Distribution by Module (Base + 5 DLCs)",
      edgeTypesHeading: "Graph Relationship Types",
      topHubsHeading: "Top Hubs by Connections (click to jump to graph)",
    },
  },
} as const;

export type UiStrings = (typeof UI_STRINGS)[Lang];

export function getNodeLabel(node: Pick<GraphNode, "label" | "labelEn">, lang: Lang): string {
  return lang === "en" ? node.labelEn || node.label : node.label;
}

export function getNodeAltLabel(node: Pick<GraphNode, "label" | "labelEn">, lang: Lang): string | null {
  if (lang === "en") return null;
  if (node.labelEn && node.labelEn !== node.label) return node.labelEn;
  return null;
}

export function getWalkthroughTitle(wt: Pick<Walkthrough, "title" | "titleEn">, lang: Lang): string {
  return lang === "en" ? wt.titleEn || wt.title : wt.title;
}

export function formatNumber(n: number, lang: Lang): string {
  return n.toLocaleString(lang === "en" ? "en-US" : "ru-RU");
}

interface I18nContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  toggleLang: () => void;
  t: UiStrings;
  formatNumber: (n: number) => string;
  getNodeLabel: (node: Pick<GraphNode, "label" | "labelEn">) => string;
  getNodeAltLabel: (node: Pick<GraphNode, "label" | "labelEn">) => string | null;
  getWalkthroughTitle: (wt: Pick<Walkthrough, "title" | "titleEn">) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLangState] = useState<Lang>(detectInitialLang);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
  }, []);

  const toggleLang = useCallback(() => {
    setLangState((prev) => (prev === "ru" ? "en" : "ru"));
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(LANG_STORAGE_KEY, lang);
    } catch {
      // ignore storage errors
    }
    if (typeof document !== "undefined") {
      document.documentElement.lang = lang;
      document.title = UI_STRINGS[lang].docTitle;
    }
  }, [lang]);

  const value = useMemo<I18nContextValue>(
    () => ({
      lang,
      setLang,
      toggleLang,
      t: UI_STRINGS[lang],
      formatNumber: (n: number) => formatNumber(n, lang),
      getNodeLabel: (node) => getNodeLabel(node, lang),
      getNodeAltLabel: (node) => getNodeAltLabel(node, lang),
      getWalkthroughTitle: (wt) => getWalkthroughTitle(wt, lang),
    }),
    [lang, setLang, toggleLang]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return ctx;
}
