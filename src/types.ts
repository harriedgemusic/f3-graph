export type EntityType =
  | "quest"
  | "character"
  | "location"
  | "event"
  | "item"
  | "object";

export type DlcId =
  | "base"
  | "anchorage"
  | "pitt"
  | "brokensteel"
  | "pointlookout"
  | "zeta";

export type EdgeType =
  | "quest_npc"
  | "quest_location"
  | "quest_item"
  | "quest_object"
  | "quest_chain"
  | "quest_event"
  | "npc_location"
  | "npc_item"
  | "location_connection"
  | "location_item"
  | "location_object"
  | "object_key"
  | "event_entity";

export type GraphScope = "atlas" | "core" | "extended";
export type GraphLayoutMode = "galaxy" | "map3d";
export type AppTab = "graph" | "walkthroughs" | "catalog" | "stats";

export interface GraphNode {
  id: string;
  fid: string;
  edid: string;
  label: string;
  labelEn: string;
  type: EntityType;
  subtype: string;
  dlc: DlcId;
  tier: "atlas" | "core" | "extended";
  degree: number;
  x: number;
  y: number;
  x3d: number;
  y3d: number;
  z3d: number;
  mapX: number;
  mapY: number;
  mapZ: number;
  icon?: string;
  walkthroughId?: string;
}

export interface IconAtlasEntry {
  col: number;
  row: number;
  u: number;
  v: number;
  uw: number;
  vh: number;
  url: string;
  isColor: boolean;
}

export interface IconAtlasData {
  cols: number;
  rows: number;
  cellSize: number;
  atlasWidth: number;
  atlasHeight: number;
  icons: Record<string, IconAtlasEntry>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  weight?: number;
}

export interface GraphMeta {
  generatedAt: string;
  source: string;
  countsByType: Record<EntityType, number>;
  countsByDlc: Record<DlcId, number>;
  countsByEdgeType: Record<string, number>;
  atlasNodes?: number;
  coreNodes: number;
  totalNodes: number;
  totalEdges: number;
}

export interface GraphData {
  meta: GraphMeta;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface EncyclopediaSection {
  title: string;
  text: string;
}

export interface NodeDetail {
  id: string;
  role?: string;
  summary?: string;
  sections?: EncyclopediaSection[];
  race?: string;
  level?: number;
  hp?: number;
  female?: boolean;
  essential?: boolean;
  unique?: boolean;
  factions?: string[];
  services?: string[];
  behavior?: string;
  special?: number[];
  quotes?: string[];
  worldspace?: string;
  markerType?: string;
  coords?: [number, number, number];
  value?: number;
  weight?: number;
  damage?: number;
  dr?: number;
  ammo?: string;
  clipSize?: number;
  fireRate?: number;
  apCost?: number;
  critDamage?: number;
  critMult?: number;
  spread?: string;
  health?: number;
  weaponClass?: string;
  effects?: string[];
  unlocks?: string[];
  lockDiff?: string;
  text?: string;
  menuItems?: { title: string; text: string }[];
  inventory?: { id: string; label: string; count: number }[];
  questCategory?: string;
  wikiUrl?: string;
  sourceTag?: string;
}

export type DetailsMap = Record<string, NodeDetail>;

export interface WalkthroughBranch {
  label: string;
  tone: "good" | "evil" | "neutral" | "alt";
  summary: string;
  outcome: string;
}

export interface WalkthroughStep {
  title: string;
  description: string;
  skillChecks?: string[];
  tip?: string;
  branches?: WalkthroughBranch[];
}

export interface EsmObjective {
  index: number;
  text: string;
}

export interface EsmStageLog {
  stage: number;
  logs: string[];
  completes?: boolean;
  fails?: boolean;
}

export interface Walkthrough {
  id: string;
  nodeId: string;
  fid: string;
  edid: string;
  title: string;
  titleEn: string;
  dlc: DlcId;
  category:
    | "main"
    | "side"
    | "freeform"
    | "anchorage"
    | "pitt"
    | "brokensteel"
    | "pointlookout"
    | "zeta";
  order: number;
  curated: boolean;
  summary: string;
  startCondition: string;
  prerequisites?: string[];
  rewards: string[];
  missableWarnings?: string[];
  steps: WalkthroughStep[];
  objectives: EsmObjective[];
  stageLogs: EsmStageLog[];
  linkedEntities: {
    characters: string[];
    locations: string[];
    events: string[];
    items: string[];
    objects: string[];
    quests: string[];
  };
}
