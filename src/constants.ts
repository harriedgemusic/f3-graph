import { DlcId, EdgeType, EntityType } from "./types";
import type { Lang } from "./i18n";

export const ENTITY_META: Record<
  EntityType,
  {
    label: string;
    labelEn: string;
    singular: string;
    singularEn: string;
    color: string;
    bgClass: string;
    borderClass: string;
    textClass: string;
    dotClass: string;
  }
> = {
  quest: {
    label: "Миссии",
    labelEn: "Quests",
    singular: "Миссия",
    singularEn: "Quest",
    color: "#f59e0b",
    bgClass: "bg-amber-500/15",
    borderClass: "border-amber-500/40",
    textClass: "text-amber-300",
    dotClass: "bg-amber-400",
  },
  character: {
    label: "Персонажи",
    labelEn: "Characters",
    singular: "Персонаж",
    singularEn: "Character",
    color: "#22c55e",
    bgClass: "bg-emerald-500/15",
    borderClass: "border-emerald-500/40",
    textClass: "text-emerald-300",
    dotClass: "bg-emerald-400",
  },
  location: {
    label: "Локации",
    labelEn: "Locations",
    singular: "Локация",
    singularEn: "Location",
    color: "#38bdf8",
    bgClass: "bg-sky-500/15",
    borderClass: "border-sky-500/40",
    textClass: "text-sky-300",
    dotClass: "bg-sky-400",
  },
  event: {
    label: "События",
    labelEn: "Events",
    singular: "Событие",
    singularEn: "Event",
    color: "#f43f5e",
    bgClass: "bg-rose-500/15",
    borderClass: "border-rose-500/40",
    textClass: "text-rose-300",
    dotClass: "bg-rose-400",
  },
  item: {
    label: "Предметы",
    labelEn: "Items",
    singular: "Предмет",
    singularEn: "Item",
    color: "#a78bfa",
    bgClass: "bg-violet-500/15",
    borderClass: "border-violet-500/40",
    textClass: "text-violet-300",
    dotClass: "bg-violet-400",
  },
  object: {
    label: "Объекты",
    labelEn: "Objects",
    singular: "Объект",
    singularEn: "Object",
    color: "#fb923c",
    bgClass: "bg-orange-500/15",
    borderClass: "border-orange-500/40",
    textClass: "text-orange-300",
    dotClass: "bg-orange-400",
  },
};

export const DLC_META: Record<
  DlcId,
  { label: string; labelEn: string; short: string; shortEn: string; color: string }
> = {
  base: {
    label: "Fallout 3 (Базовая игра)",
    labelEn: "Fallout 3 (Base Game)",
    short: "Fallout 3",
    shortEn: "Fallout 3",
    color: "#34d399",
  },
  anchorage: {
    label: "Операция «Анкоридж»",
    labelEn: "Operation: Anchorage",
    short: "Анкоридж",
    shortEn: "Anchorage",
    color: "#60a5fa",
  },
  pitt: {
    label: "Питт (The Pitt)",
    labelEn: "The Pitt",
    short: "Питт",
    shortEn: "The Pitt",
    color: "#f97316",
  },
  brokensteel: {
    label: "Сломанная сталь (Broken Steel)",
    labelEn: "Broken Steel",
    short: "Сломанная сталь",
    shortEn: "Broken Steel",
    color: "#facc15",
  },
  pointlookout: {
    label: "Пойнт-Лукаут (Point Lookout)",
    labelEn: "Point Lookout",
    short: "Пойнт-Лукаут",
    shortEn: "Point Lookout",
    color: "#a3e635",
  },
  zeta: {
    label: "Корабль Чужих «Зета»",
    labelEn: "Mothership Zeta",
    short: "«Зета»",
    shortEn: "Zeta",
    color: "#c084fc",
  },
};

export const EDGE_META: Record<EdgeType, { label: string; labelEn: string; color: string }> = {
  quest_npc: { label: "Участник миссии", labelEn: "Quest Participant", color: "#34d399" },
  quest_location: { label: "Место действия миссии", labelEn: "Quest Location", color: "#38bdf8" },
  quest_item: { label: "Предмет миссии", labelEn: "Quest Item", color: "#a78bfa" },
  quest_object: { label: "Объект миссии", labelEn: "Quest Object", color: "#fb923c" },
  quest_chain: { label: "Цепочка миссий", labelEn: "Quest Chain", color: "#f59e0b" },
  quest_event: { label: "Ключевое событие", labelEn: "Key Story Event", color: "#f43f5e" },
  npc_location: { label: "Обитает в локации", labelEn: "Located In", color: "#2dd4bf" },
  npc_item: { label: "Инвентарь / экипировка", labelEn: "Inventory / Gear", color: "#818cf8" },
  location_connection: { label: "Переход / дверь", labelEn: "Door / Passage", color: "#0ea5e9" },
  location_item: { label: "Найдено в локации", labelEn: "Found In Location", color: "#c084fc" },
  location_object: { label: "Объект в локации", labelEn: "Object In Location", color: "#fb923c" },
  object_key: { label: "Открывается ключом", labelEn: "Unlocked By Key", color: "#f472b6" },
  event_entity: { label: "Связано с событием", labelEn: "Linked To Event", color: "#fb7185" },
};

export const SUBTYPE_LABELS: Record<string, string> = {
  npc: "Персонаж (NPC)",
  creature: "Существо / Робот",
  world: "Мир / Пространство",
  marker: "Маркер на карте",
  interior: "Внутренняя локация",
  main: "Основной сюжет",
  side: "Побочная миссия",
  freeform: "Неотмечаемая миссия",
  anchorage: "Операция «Анкоридж»",
  pitt: "Питт (The Pitt)",
  brokensteel: "Сломанная сталь (Broken Steel)",
  pointlookout: "Пойнт-Лукаут (Point Lookout)",
  zeta: "Корабль Чужих «Зета»",
  story_event: "Сюжетное событие",
  random_encounter: "Случайная встреча",
  weapon: "Оружие",
  armor: "Броня / Одежда",
  aid: "Медикаменты / Еда",
  ammo: "Боеприпасы",
  book: "Книга навыков",
  key: "Ключ",
  note: "Заметка / Голодиск",
  misc: "Разное / Квестовый предмет",
  terminal: "Терминал",
  activator: "Активатор / Устройство",
  container: "Контейнер / Сейф",
  door: "Дверь / Переход",
  perk: "Способность (Перк)",
};

export const SUBTYPE_LABELS_EN: Record<string, string> = {
  npc: "Character (NPC)",
  creature: "Creature / Robot",
  world: "Worldspace",
  marker: "Map Marker",
  interior: "Interior Location",
  main: "Main Quest",
  side: "Side Quest",
  freeform: "Freeform Quest",
  anchorage: "Operation: Anchorage",
  pitt: "The Pitt",
  brokensteel: "Broken Steel",
  pointlookout: "Point Lookout",
  zeta: "Mothership Zeta",
  story_event: "Story Event",
  random_encounter: "Random Encounter",
  weapon: "Weapon",
  armor: "Armor / Apparel",
  aid: "Aid / Chems & Food",
  ammo: "Ammunition",
  book: "Skill Book",
  key: "Key",
  note: "Note / Holotape",
  misc: "Misc / Quest Item",
  terminal: "Terminal",
  activator: "Activator / Device",
  container: "Container / Safe",
  door: "Door / Passage",
  perk: "Perk",
};

export const WALKTHROUGH_GROUP_ORDER: {
  id:
    | "main"
    | "side"
    | "freeform"
    | "anchorage"
    | "pitt"
    | "brokensteel"
    | "pointlookout"
    | "zeta";
  label: string;
  labelEn: string;
}[] = [
  { id: "main", label: "Основной сюжет", labelEn: "Main Storyline" },
  { id: "side", label: "Побочные миссии", labelEn: "Side Quests" },
  { id: "brokensteel", label: "Сломанная сталь (Broken Steel)", labelEn: "Broken Steel" },
  { id: "anchorage", label: "Операция «Анкоридж»", labelEn: "Operation: Anchorage" },
  { id: "pitt", label: "Питт (The Pitt)", labelEn: "The Pitt" },
  { id: "pointlookout", label: "Пойнт-Лукаут (Point Lookout)", labelEn: "Point Lookout" },
  { id: "zeta", label: "Корабль Чужих «Зета»", labelEn: "Mothership Zeta" },
  { id: "freeform", label: "Свободные и неотмечаемые миссии", labelEn: "Freeform & Unmarked Quests" },
];

export function getEntityLabel(type: EntityType, lang: Lang): string {
  return lang === "en" ? ENTITY_META[type].labelEn : ENTITY_META[type].label;
}

export function getEntitySingular(type: EntityType, lang: Lang): string {
  return lang === "en" ? ENTITY_META[type].singularEn : ENTITY_META[type].singular;
}

export function getDlcLabel(dlc: DlcId, lang: Lang): string {
  return lang === "en" ? DLC_META[dlc].labelEn : DLC_META[dlc].label;
}

export function getDlcShort(dlc: DlcId, lang: Lang): string {
  return lang === "en" ? DLC_META[dlc].shortEn : DLC_META[dlc].short;
}

export function getEdgeLabel(edgeType: EdgeType, lang: Lang): string {
  const meta = EDGE_META[edgeType];
  if (!meta) return edgeType;
  return lang === "en" ? meta.labelEn : meta.label;
}

export function getSubtypeLabel(subtype: string, lang: Lang): string | undefined {
  return lang === "en" ? SUBTYPE_LABELS_EN[subtype] : SUBTYPE_LABELS[subtype];
}
