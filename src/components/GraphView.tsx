import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  ArrowLeft,
  ArrowRight,
  Compass,
  Eye,
  Focus,
  GitFork,
  Layers,
  Maximize2,
  Navigation,
  Orbit,
  Pause,
  Play,
  RotateCcw,
  Search,
  SlidersHorizontal,
  Sparkles,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import {
  DLC_META,
  EDGE_META,
  ENTITY_META,
  getDlcLabel,
  getDlcShort,
  getEdgeLabel,
  getEntityLabel,
  getEntitySingular,
  getSubtypeLabel,
} from "../constants";
import { NeighborEntry } from "../data/useFalloutData";
import { getNodeLabel as getLocalizedNodeLabel, Lang, useI18n } from "../i18n";
import {
  DetailsMap,
  DlcId,
  EdgeType,
  EntityType,
  GraphData,
  GraphLayoutMode,
  GraphNode,
  GraphScope,
  IconAtlasData,
  Walkthrough,
} from "../types";
import { EntityIcon } from "./EntityIcon";
import { InspectorPanel } from "./InspectorPanel";

interface GraphViewProps {
  graphData: GraphData;
  details: DetailsMap | null;
  iconAtlas: IconAtlasData | null;
  nodeMap: Map<string, GraphNode>;
  walkthroughByNodeId: Map<string, Walkthrough>;
  adjacency: Map<string, NeighborEntry[]>;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string | null) => void;
  isolation: { rootId: string; hops: 1 | 2 } | null;
  onSetIsolation: (iso: { rootId: string; hops: 1 | 2 } | null) => void;
  onOpenWalkthrough: (walkthroughId: string) => void;
}

const ALL_TYPES: EntityType[] = [
  "quest",
  "character",
  "location",
  "event",
  "item",
  "object",
];

const ALL_EDGE_TYPES = Object.keys(EDGE_META) as EdgeType[];
const LABEL_POOL_SIZE = 54;
const MAX_ACTIVE_RIBBONS = 2400;

type DepthShadeMode = "strong" | "soft" | "off";

interface HoveredEdgeInfo {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  fromId: string;
  toId: string;
}

interface PreparedNodeInstance {
  nd: GraphNode;
  pos: THREE.Vector3;
  size: number;
  u: number;
  v: number;
  uw: number;
  vh: number;
  isColor: number;
  r: number;
  g: number;
  b: number;
  alpha: number;
  highlight: number;
  tierOrder: number;
}

function evalCubicBezier(
  out: THREE.Vector3,
  p0: THREE.Vector3,
  p1: THREE.Vector3,
  p2: THREE.Vector3,
  p3: THREE.Vector3,
  t: number
): THREE.Vector3 {
  const u = 1 - t;
  const b0 = u * u * u;
  const b1 = 3 * u * u * t;
  const b2 = 3 * u * t * t;
  const b3 = t * t * t;
  out.set(
    p0.x * b0 + p1.x * b1 + p2.x * b2 + p3.x * b3,
    p0.y * b0 + p1.y * b1 + p2.y * b2 + p3.y * b3,
    p0.z * b0 + p1.z * b1 + p2.z * b2 + p3.z * b3
  );
  return out;
}

function computeDepthRange(targetDist: number): { near: number; far: number } {
  const d = THREE.MathUtils.clamp(targetDist, 70, 900);
  const blend = THREE.MathUtils.smoothstep(d, 175, 410);
  const nearClose = d * 1.08;
  const farClose = d + 225;
  const nearOverview = d * 0.54;
  const farOverview = d * 1.32;
  return {
    near: THREE.MathUtils.lerp(nearClose, nearOverview, blend),
    far: THREE.MathUtils.lerp(farClose, farOverview, blend),
  };
}

function createGlowTexture(): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 128;
  const ctx = canvas.getContext("2d")!;
  const grad = ctx.createRadialGradient(64, 64, 4, 64, 64, 62);
  grad.addColorStop(0, "rgba(255, 255, 255, 1)");
  grad.addColorStop(0.28, "rgba(255, 255, 255, 0.55)");
  grad.addColorStop(0.65, "rgba(255, 255, 255, 0.14)");
  grad.addColorStop(1, "rgba(255, 255, 255, 0)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 128, 128);
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
}

function getNodeCardSize(nd: GraphNode): number {
  const boost =
    nd.type === "quest"
      ? 3.4
      : nd.type === "event"
        ? 2.5
        : nd.subtype === "marker" || nd.subtype === "world"
          ? 1.5
          : 0;
  return Math.min(17.5, 8.0 + boost + Math.sqrt(Math.max(1, nd.degree)) * 1.02);
}

/**
 * Fast 3D spatial-hash de-clumping pass so adjacent plaques never sit right on top of one another.
 */
function declumpPositions3D(
  nodes: GraphNode[],
  posMap: Map<string, THREE.Vector3>,
  pinnedId: string | null,
  clearanceMult = 1.42,
  iterations = 4
): void {
  const n = nodes.length;
  if (n < 2) return;

  const xs = new Float32Array(n);
  const ys = new Float32Array(n);
  const zs = new Float32Array(n);
  const radii = new Float32Array(n);
  const pinned = new Uint8Array(n);

  for (let i = 0; i < n; i++) {
    const nd = nodes[i];
    const p = posMap.get(nd.id)!;
    xs[i] = p.x;
    ys[i] = p.y;
    zs[i] = p.z;
    radii[i] = getNodeCardSize(nd) * 0.5 * clearanceMult;
    pinned[i] = pinnedId === nd.id ? 1 : 0;
  }

  const cellSize = 34;
  const invCell = 1 / cellSize;

  for (let iter = 0; iter < iterations; iter++) {
    const grid = new Map<number, number[]>();
    for (let i = 0; i < n; i++) {
      const gx = Math.floor(xs[i] * invCell) + 4096;
      const gy = Math.floor(ys[i] * invCell) + 4096;
      const gz = Math.floor(zs[i] * invCell) + 4096;
      const key = gx + gy * 8192 + gz * 67108864;
      let bucket = grid.get(key);
      if (!bucket) {
        bucket = [];
        grid.set(key, bucket);
      }
      bucket.push(i);
    }

    for (let i = 0; i < n; i++) {
      const gx = Math.floor(xs[i] * invCell) + 4096;
      const gy = Math.floor(ys[i] * invCell) + 4096;
      const gz = Math.floor(zs[i] * invCell) + 4096;

      for (let dz = -1; dz <= 1; dz++) {
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            const key = (gx + dx) + (gy + dy) * 8192 + (gz + dz) * 67108864;
            const bucket = grid.get(key);
            if (!bucket) continue;
            for (let k = 0; k < bucket.length; k++) {
              const j = bucket[k];
              if (j <= i) continue;
              let vx = xs[j] - xs[i];
              let vy = ys[j] - ys[i];
              let vz = zs[j] - zs[i];
              let dSq = vx * vx + vy * vy + vz * vz;
              const minDist = radii[i] + radii[j];
              if (dSq >= minDist * minDist) continue;

              if (dSq < 1e-4) {
                const ang = (i * 2.399963 + j * 0.7) % (Math.PI * 2);
                vx = Math.cos(ang);
                vy = ((i + j) % 3 - 1) * 0.45;
                vz = Math.sin(ang);
                dSq = vx * vx + vy * vy + vz * vz;
              }
              const d = Math.sqrt(dSq);
              const push = (minDist - d) * 0.48;
              const nx = (vx / d) * push;
              const ny = (vy / d) * push;
              const nz = (vz / d) * push;

              if (pinned[i]) {
                xs[j] += nx * 2;
                ys[j] += ny * 2;
                zs[j] += nz * 2;
              } else if (pinned[j]) {
                xs[i] -= nx * 2;
                ys[i] -= ny * 2;
                zs[i] -= nz * 2;
              } else {
                xs[i] -= nx;
                ys[i] -= ny;
                zs[i] -= nz;
                xs[j] += nx;
                ys[j] += ny;
                zs[j] += nz;
              }
            }
          }
        }
      }
    }
  }

  for (let i = 0; i < n; i++) {
    const p = posMap.get(nodes[i].id)!;
    p.set(xs[i], ys[i], zs[i]);
  }
}

/**
 * Compute spacious 3D radial constellation positions for isolated ego-subgraph.
 */
function computeIsolationPositions3D(
  rootId: string,
  nodes: GraphNode[],
  adjacency: Map<string, NeighborEntry[]>,
  lang: Lang
): Map<string, THREE.Vector3> {
  const posMap = new Map<string, THREE.Vector3>();
  posMap.set(rootId, new THREE.Vector3(0, 0, 0));

  const hop1Set = new Set<string>();
  for (const nb of adjacency.get(rootId) ?? []) {
    hop1Set.add(nb.node.id);
  }

  const groups: Record<EntityType, { hop1: GraphNode[]; hop2: GraphNode[] }> = {
    quest: { hop1: [], hop2: [] },
    event: { hop1: [], hop2: [] },
    character: { hop1: [], hop2: [] },
    location: { hop1: [], hop2: [] },
    item: { hop1: [], hop2: [] },
    object: { hop1: [], hop2: [] },
  };

  for (const nd of nodes) {
    if (nd.id === rootId) continue;
    if (hop1Set.has(nd.id)) groups[nd.type].hop1.push(nd);
    else groups[nd.type].hop2.push(nd);
  }

  const placeRing = (
    list: GraphNode[],
    yCenter: number,
    radiusBase: number,
    angleStart: number,
    angleSpan: number,
    yWave: number
  ) => {
    const n = list.length;
    if (n === 0) return;
    const locale = lang === "en" ? "en" : "ru";
    list.sort(
      (a, b) =>
        b.degree - a.degree ||
        getLocalizedNodeLabel(a, lang).localeCompare(getLocalizedNodeLabel(b, lang), locale)
    );
    const perRing = Math.max(12, Math.min(26, Math.ceil(Math.sqrt(n) * 4.5)));
    for (let i = 0; i < n; i++) {
      const ringIdx = Math.floor(i / perRing);
      const posInRing = i % perRing;
      const countInThisRing = Math.min(perRing, n - ringIdx * perRing);
      const t =
        countInThisRing === 1
          ? 0.5
          : posInRing / (countInThisRing - 1 + (angleSpan >= Math.PI * 1.99 ? 1 : 0));
      const ang = angleStart + t * angleSpan + ringIdx * 0.32;
      const r = radiusBase + ringIdx * 62;
      const y = yCenter + Math.sin(i * 1.9) * yWave + ringIdx * 18;
      posMap.set(list[i].id, new THREE.Vector3(Math.cos(ang) * r, y, Math.sin(ang) * r));
    }
  };

  // Spacious Hop 1 concentric 3D bands
  placeRing(groups.quest.hop1, 140, 170, 0, Math.PI * 2, 18);
  placeRing(groups.event.hop1, 95, 185, 0.3, Math.PI * 2, 16);
  placeRing(groups.character.hop1, 28, 195, -Math.PI * 0.45, Math.PI * 0.95, 22);
  placeRing(groups.location.hop1, -28, 200, Math.PI * 0.55, Math.PI * 0.95, 22);
  placeRing(groups.item.hop1, -105, 185, 0.15, Math.PI * 2, 18);
  placeRing(groups.object.hop1, -150, 175, 0.45, Math.PI * 2, 18);

  // Spacious Hop 2 outer bands
  placeRing(groups.quest.hop2, 205, 330, 0.2, Math.PI * 2, 24);
  placeRing(groups.event.hop2, 155, 345, 0.5, Math.PI * 2, 22);
  placeRing(groups.character.hop2, 48, 365, -Math.PI * 0.5, Math.PI, 28);
  placeRing(groups.location.hop2, -48, 375, Math.PI * 0.5, Math.PI, 28);
  placeRing(groups.item.hop2, -175, 350, 0.1, Math.PI * 2, 24);
  placeRing(groups.object.hop2, -220, 335, 0.4, Math.PI * 2, 24);

  declumpPositions3D(nodes, posMap, rootId, 1.55, 5);
  return posMap;
}

export const GraphView: React.FC<GraphViewProps> = ({
  graphData,
  details,
  iconAtlas,
  nodeMap,
  walkthroughByNodeId,
  adjacency,
  selectedNodeId,
  onSelectNode,
  isolation,
  onSetIsolation,
  onOpenWalkthrough,
}) => {
  const { lang, t, formatNumber, getNodeLabel, getNodeAltLabel } = useI18n();
  const langRef = useRef<Lang>(lang);
  langRef.current = lang;
  const mountRef = useRef<HTMLDivElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const iconAtlasRef = useRef<IconAtlasData | null>(iconAtlas);
  iconAtlasRef.current = iconAtlas;

  // View & filter states (start clean in "atlas" 3D galaxy!)
  const [scope, setScope] = useState<GraphScope>("atlas");
  const [layoutMode, setLayoutMode] = useState<GraphLayoutMode>("galaxy");
  const [dlcFilter, setDlcFilter] = useState<DlcId | "all">("all");
  const [visibleTypes, setVisibleTypes] = useState<Set<EntityType>>(
    () => new Set(ALL_TYPES)
  );
  const [visibleEdgeTypes, setVisibleEdgeTypes] = useState<Set<EdgeType>>(
    () => new Set(ALL_EDGE_TYPES)
  );
  const [showBgLootEdges, setShowBgLootEdges] = useState(false);

  // Popover drawers & navigation modes
  const [showFilters, setShowFilters] = useState(false);
  const [showPathFinder, setShowPathFinder] = useState(false);
  const [autoRotate, setAutoRotate] = useState(false);
  const [depthMode, setDepthMode] = useState<DepthShadeMode>("strong");
  const [flightHistory, setFlightHistory] = useState<string[]>([]);
  const [isTouringPath, setIsTouringPath] = useState(false);
  const tourTimerRef = useRef<number | null>(null);

  // Search autocomplete
  const [searchQuery, setSearchQuery] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);

  // Path finder
  const [pathStartId, setPathStartId] = useState<string | null>(null);
  const [pathEndId, setPathEndId] = useState<string | null>(null);
  const [pathStartQuery, setPathStartQuery] = useState("");
  const [pathEndQuery, setPathEndQuery] = useState("");

  // Hover + Tooltip (node or connection beam)
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<HoveredEdgeInfo | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);

  // Visible node/edge counts
  const [visibleStats, setVisibleStats] = useState({ nodes: 0, edges: 0 });

  // Pool of projected 3D DOM label refs
  const labelDivRefs = useRef<(HTMLDivElement | null)[]>([]);
  const labelDotRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const labelTextRefs = useRef<(HTMLSpanElement | null)[]>([]);

  // Three.js mutable refs
  const threeRef = useRef<{
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    renderer: THREE.WebGLRenderer;
    controls: OrbitControls;
    gridHelper: THREE.GridHelper;
    radarRings: THREE.Group;
    stratumRings: THREE.Group;
    iconMesh: THREE.InstancedMesh;
    iconGeo: THREE.PlaneGeometry;
    iconMat: THREE.ShaderMaterial;
    atlasTexture: THREE.Texture | null;
    attrCenter: THREE.InstancedBufferAttribute;
    attrSize: THREE.InstancedBufferAttribute;
    attrUvRect: THREE.InstancedBufferAttribute;
    attrColor: THREE.InstancedBufferAttribute;
    attrAlpha: THREE.InstancedBufferAttribute;
    attrHighlight: THREE.InstancedBufferAttribute;
    attrIsColor: THREE.InstancedBufferAttribute;
    bgLines: THREE.LineSegments;
    bgLineMat: THREE.ShaderMaterial;
    activeEdgeMesh: THREE.InstancedMesh;
    activeEdgeGeo: THREE.PlaneGeometry;
    activeEdgeMat: THREE.ShaderMaterial;
    attrEdgeStart: THREE.InstancedBufferAttribute;
    attrEdgeEnd: THREE.InstancedBufferAttribute;
    attrEdgeColor: THREE.InstancedBufferAttribute;
    attrEdgeWidth: THREE.InstancedBufferAttribute;
    attrEdgeIntensity: THREE.InstancedBufferAttribute;
    selectedHalo: THREE.Sprite;
    hoveredHalo: THREE.Sprite;
    flightOrb: THREE.Sprite;
    pathHaloGroup: THREE.Group;
    glowTex: THREE.CanvasTexture;
    nodePositions: Map<string, THREE.Vector3>;
    nodeSizes: Map<string, number>;
    preparedInstances: PreparedNodeInstance[];
    lastSortCamPos: THREE.Vector3;
    labelBoxes: { x1: number; y1: number; x2: number; y2: number; node: GraphNode }[];
    pickableEdges: {
      id: string;
      source: string;
      target: string;
      type: EdgeType;
      priority: number;
    }[];
    visibleNodes: GraphNode[];
    visibleEdges: {
      id: string;
      source: string;
      target: string;
      type: EdgeType;
    }[];
    showBgLootEdges: boolean;
    flight: {
      active: boolean;
      isCorridor: boolean;
      startTime: number;
      duration: number;
      fromPos: THREE.Vector3;
      toPos: THREE.Vector3;
      fromTarget: THREE.Vector3;
      toTarget: THREE.Vector3;
      p0: THREE.Vector3;
      p1: THREE.Vector3;
      p2: THREE.Vector3;
      p3: THREE.Vector3;
      t0: THREE.Vector3;
      t1: THREE.Vector3;
      t2: THREE.Vector3;
      t3: THREE.Vector3;
      linkStart: THREE.Vector3;
      linkEnd: THREE.Vector3;
      edgeId: string | null;
    };
    pressedKeys: Set<string>;
  } | null>(null);

  // Isolation neighborhood (1 or 2 hops)
  const isolatedSet = useMemo(() => {
    if (!isolation) return null;
    if (!nodeMap.has(isolation.rootId)) return null;
    const set = new Set<string>([isolation.rootId]);
    const hop1: string[] = [];
    for (const nb of adjacency.get(isolation.rootId) ?? []) {
      set.add(nb.node.id);
      hop1.push(nb.node.id);
    }
    if (isolation.hops === 2) {
      for (const nid of hop1) {
        for (const nb of adjacency.get(nid) ?? []) {
          set.add(nb.node.id);
        }
      }
    }
    return set;
  }, [isolation, adjacency, nodeMap]);

  // Shortest Path BFS
  const shortestPath = useMemo(() => {
    if (!pathStartId || !pathEndId || pathStartId === pathEndId) {
      return {
        nodeIds: [] as string[],
        nodeSet: new Set<string>(),
        edgeSet: new Set<string>(),
      };
    }
    const visited = new Set<string>([pathStartId]);
    const parent = new Map<string, { prev: string; edgeId: string }>();
    const queue: string[] = [pathStartId];
    let found = false;

    while (queue.length > 0 && !found) {
      const cur = queue.shift()!;
      for (const nb of adjacency.get(cur) ?? []) {
        if (!visited.has(nb.node.id)) {
          visited.add(nb.node.id);
          parent.set(nb.node.id, { prev: cur, edgeId: nb.edge.id });
          if (nb.node.id === pathEndId) {
            found = true;
            break;
          }
          queue.push(nb.node.id);
        }
      }
    }

    if (!found) {
      return {
        nodeIds: [] as string[],
        nodeSet: new Set<string>(),
        edgeSet: new Set<string>(),
      };
    }

    const nodeIds: string[] = [];
    const edgeSet = new Set<string>();
    let curr: string | undefined = pathEndId;
    while (curr) {
      nodeIds.push(curr);
      const p = parent.get(curr);
      if (!p) break;
      edgeSet.add(p.edgeId);
      curr = p.prev;
    }
    nodeIds.reverse();
    return { nodeIds, nodeSet: new Set(nodeIds), edgeSet };
  }, [pathStartId, pathEndId, adjacency]);

  // Focus & neighbor sets synced to ref for frame loop & visual updater
  const focusNodeId = selectedNodeId;
  const neighborsOfFocus = useMemo(() => {
    const set = new Set<string>();
    if (!focusNodeId) return set;
    for (const nb of adjacency.get(focusNodeId) ?? []) {
      set.add(nb.node.id);
    }
    return set;
  }, [focusNodeId, adjacency]);

  const neighborsOfHovered = useMemo(() => {
    const set = new Set<string>();
    if (!hoveredNodeId) return set;
    for (const nb of adjacency.get(hoveredNodeId) ?? []) {
      set.add(nb.node.id);
    }
    return set;
  }, [hoveredNodeId, adjacency]);

  const depthStrength = depthMode === "strong" ? 1.0 : depthMode === "soft" ? 0.62 : 0.0;

  const visualStateRef = useRef({
    selectedNodeId: null as string | null,
    hoveredNodeId: null as string | null,
    hoveredEdge: null as HoveredEdgeInfo | null,
    focusNodeId: null as string | null,
    neighborsOfFocus: new Set<string>(),
    neighborsOfHovered: new Set<string>(),
    pathNodeIds: [] as string[],
    pathNodeSet: new Set<string>(),
    pathEdgeSet: new Set<string>(),
    isolationActive: false,
    isolationRootId: null as string | null,
    autoRotate: false,
    depthStrength: 1.0,
  });

  visualStateRef.current = {
    selectedNodeId,
    hoveredNodeId,
    hoveredEdge,
    focusNodeId,
    neighborsOfFocus,
    neighborsOfHovered,
    pathNodeIds: shortestPath.nodeIds,
    pathNodeSet: shortestPath.nodeSet,
    pathEdgeSet: shortestPath.edgeSet,
    isolationActive: Boolean(isolatedSet),
    isolationRootId: isolation?.rootId ?? null,
    autoRotate,
    depthStrength,
  };

  const stopPathTour = useCallback(() => {
    if (tourTimerRef.current !== null) {
      window.clearTimeout(tourTimerRef.current);
      tourTimerRef.current = null;
    }
    setIsTouringPath(false);
  }, []);

  // Start smooth 3D camera flight (standard ease)
  const flyCameraTo = useCallback((toPos: THREE.Vector3, toTarget: THREE.Vector3, duration = 520) => {
    const st = threeRef.current;
    if (!st) return;
    st.flight.active = true;
    st.flight.isCorridor = false;
    st.flight.edgeId = null;
    st.flight.startTime = performance.now();
    st.flight.duration = duration;
    st.flight.fromPos.copy(st.camera.position);
    st.flight.toPos.copy(toPos);
    st.flight.fromTarget.copy(st.controls.target);
    st.flight.toTarget.copy(toTarget);
    st.flightOrb.visible = false;
  }, []);

  const resetCamera = useCallback(() => {
    stopPathTour();
    const st = threeRef.current;
    if (!st) return;
    if (visualStateRef.current.isolationActive) {
      const is2Hops = isolation?.hops === 2;
      flyCameraTo(
        new THREE.Vector3(0, is2Hops ? 225 : 175, is2Hops ? 670 : 510),
        new THREE.Vector3(0, 0, 0),
        480
      );
    } else if (layoutMode === "map3d") {
      flyCameraTo(new THREE.Vector3(0, 460, 740), new THREE.Vector3(0, 0, 0), 500);
    } else {
      const zDist = scope === "extended" ? 690 : scope === "core" ? 620 : 565;
      flyCameraTo(new THREE.Vector3(0, 200, zDist), new THREE.Vector3(0, 0, 0), 500);
    }
  }, [flyCameraTo, layoutMode, scope, isolation?.hops, stopPathTour]);

  // Sort prepared instances back-to-front by camera distance within each priority tier
  // so foreground bright plaques always render cleanly on top of distant shaded silhouettes
  const uploadSortedInstances = useCallback(
    (st: NonNullable<typeof threeRef.current>, camPos: THREE.Vector3) => {
      const list = st.preparedInstances;
      const count = list.length;
      if (count === 0) {
        st.iconMesh.count = 0;
        return;
      }

      const indices = new Array<number>(count);
      const distSq = new Float32Array(count);
      const cx = camPos.x;
      const cy = camPos.y;
      const cz = camPos.z;
      for (let i = 0; i < count; i++) {
        indices[i] = i;
        const p = list[i].pos;
        const dx = p.x - cx;
        const dy = p.y - cy;
        const dz = p.z - cz;
        distSq[i] = dx * dx + dy * dy + dz * dz;
      }

      // Draw dimmed/far items first, closer items later, and top-tier highlighted items last
      indices.sort((ia, ib) => {
        const ta = list[ia].tierOrder;
        const tb = list[ib].tierOrder;
        if (ta !== tb) return ta - tb;
        return distSq[ib] - distSq[ia];
      });

      const cArr = st.attrCenter.array as Float32Array;
      const sArr = st.attrSize.array as Float32Array;
      const uArr = st.attrUvRect.array as Float32Array;
      const colArr = st.attrColor.array as Float32Array;
      const aArr = st.attrAlpha.array as Float32Array;
      const hArr = st.attrHighlight.array as Float32Array;
      const icArr = st.attrIsColor.array as Float32Array;

      for (let outIdx = 0; outIdx < count; outIdx++) {
        const item = list[indices[outIdx]];
        const i3 = outIdx * 3;
        const i4 = outIdx * 4;

        cArr[i3] = item.pos.x;
        cArr[i3 + 1] = item.pos.y;
        cArr[i3 + 2] = item.pos.z;
        sArr[outIdx] = item.size;

        uArr[i4] = item.u;
        uArr[i4 + 1] = item.v;
        uArr[i4 + 2] = item.uw;
        uArr[i4 + 3] = item.vh;
        icArr[outIdx] = item.isColor;

        colArr[i3] = item.r;
        colArr[i3 + 1] = item.g;
        colArr[i3 + 2] = item.b;
        aArr[outIdx] = item.alpha;
        hArr[outIdx] = item.highlight;
      }

      st.iconMesh.count = count;
      st.attrCenter.needsUpdate = true;
      st.attrSize.needsUpdate = true;
      st.attrUvRect.needsUpdate = true;
      st.attrColor.needsUpdate = true;
      st.attrAlpha.needsUpdate = true;
      st.attrHighlight.needsUpdate = true;
      st.attrIsColor.needsUpdate = true;
      st.lastSortCamPos.copy(camPos);
    },
    []
  );

  // Apply billboard icon buffers, halos, depth-shaded bg lines, and 3D glowing ribbon beams
  const refreshVisualHighlights = useCallback(() => {
    const st = threeRef.current;
    if (!st) return;
    const vs = visualStateRef.current;
    const hasPath = vs.pathNodeSet.size > 0;
    const activeId = vs.focusNodeId;
    const hovId = vs.hoveredNodeId;
    const hovEdge = vs.hoveredEdge;
    const atlas = iconAtlasRef.current;

    const tmpColor = new THREE.Color();
    const prepared: PreparedNodeInstance[] = [];
    const densityScale =
      st.visibleNodes.length > 2600 ? 0.72 : st.visibleNodes.length > 900 ? 0.84 : 1.0;

    // Cap primary highlighted ribbons on mega-hubs (e.g. 140-380 links) to top 28 priority neighbors
    // so hubs never turn into a dense wall of overlapping stripes
    const primaryFocusEdgeIds = new Set<string>();
    const primaryFocusNeighborIds = new Set<string>();
    if (activeId) {
      const orderedNbs = adjacency.get(activeId) ?? [];
      for (const nb of orderedNbs) {
        if (!st.nodePositions.has(nb.node.id)) continue;
        if (primaryFocusEdgeIds.size >= 28) break;
        primaryFocusEdgeIds.add(nb.edge.id);
        primaryFocusNeighborIds.add(nb.node.id);
      }
    }

    st.nodeSizes.clear();

    for (const nd of st.visibleNodes) {
      const pos = st.nodePositions.get(nd.id);
      if (!pos) continue;
      const baseSize = getNodeCardSize(nd) * densityScale;
      const baseHex = ENTITY_META[nd.type].color;

      let scaleMult = 1.0;
      let colorHex = baseHex;
      let alpha = 0.96;
      let highlight = 0.0;
      let tierOrder = 1;

      if (hasPath) {
        if (vs.pathNodeSet.has(nd.id)) {
          scaleMult = 1.42;
          colorHex = "#fbbf24";
          alpha = 1.0;
          highlight = 1.0;
          tierOrder = 3;
        } else {
          scaleMult = 0.68;
          colorHex = baseHex;
          alpha = 0.13;
          highlight = 0.0;
          tierOrder = 0;
        }
      } else if (activeId) {
        if (nd.id === activeId) {
          scaleMult = 1.48;
          alpha = 1.0;
          highlight = 1.0;
          tierOrder = 3;
        } else if (primaryFocusNeighborIds.has(nd.id)) {
          scaleMult = 1.22;
          alpha = 0.98;
          highlight = 0.62;
          tierOrder = 2;
        } else if (vs.neighborsOfFocus.has(nd.id)) {
          scaleMult = 1.04;
          alpha = 0.78;
          highlight = 0.34;
          tierOrder = 2;
        } else {
          scaleMult = 0.68;
          alpha = 0.13;
          highlight = 0.0;
          tierOrder = 0;
        }
      } else {
        if (nd.id === hovId) {
          scaleMult = 1.26;
          alpha = 1.0;
          highlight = 0.85;
          tierOrder = 3;
        } else if (hovId && vs.neighborsOfHovered.has(nd.id)) {
          scaleMult = 1.12;
          alpha = 0.96;
          highlight = 0.46;
          tierOrder = 2;
        } else if (vs.isolationActive && nd.id === vs.isolationRootId) {
          scaleMult = 1.42;
          alpha = 1.0;
          highlight = 0.9;
          tierOrder = 3;
        }
      }

      if (nd.id === hovId && tierOrder < 3) {
        scaleMult = Math.max(scaleMult, 1.24);
        alpha = 1.0;
        highlight = Math.max(highlight, 0.82);
        tierOrder = 3;
      }

      if (hovEdge && (nd.id === hovEdge.toId || nd.id === hovEdge.fromId) && tierOrder < 3) {
        scaleMult = Math.max(scaleMult, nd.id === hovEdge.toId ? 1.3 : 1.18);
        alpha = 1.0;
        highlight = Math.max(highlight, nd.id === hovEdge.toId ? 0.9 : 0.7);
        tierOrder = 3;
      }

      const finalSize = baseSize * scaleMult;
      st.nodeSizes.set(nd.id, finalSize);

      const entry = nd.icon && atlas ? atlas.icons[nd.icon] : undefined;
      tmpColor.set(colorHex);
      prepared.push({
        nd,
        pos,
        size: finalSize,
        u: entry ? entry.u : 0,
        v: entry ? entry.v : 0,
        uw: entry ? entry.uw : 0,
        vh: entry ? entry.vh : 0,
        isColor: entry?.isColor ? 1.0 : 0.0,
        r: tmpColor.r,
        g: tmpColor.g,
        b: tmpColor.b,
        alpha,
        highlight,
        tierOrder,
      });
    }

    st.preparedInstances = prepared;
    uploadSortedInstances(st, st.camera.position);

    // Subtle crisp halos (calibrated to never cause overexposure blowouts)
    if (vs.selectedNodeId && st.nodePositions.has(vs.selectedNodeId)) {
      const nd = nodeMap.get(vs.selectedNodeId);
      const pos = st.nodePositions.get(vs.selectedNodeId)!;
      const r = nd ? st.nodeSizes.get(nd.id) ?? getNodeCardSize(nd) : 12;
      st.selectedHalo.position.copy(pos);
      st.selectedHalo.scale.setScalar(r * 1.85);
      (st.selectedHalo.material as THREE.SpriteMaterial).color.set(
        nd ? ENTITY_META[nd.type].color : "#34d399"
      );
      st.selectedHalo.visible = true;
    } else {
      st.selectedHalo.visible = false;
    }

    const haloTargetId = hovId ?? hovEdge?.toId ?? null;
    if (haloTargetId && haloTargetId !== vs.selectedNodeId && st.nodePositions.has(haloTargetId)) {
      const nd = nodeMap.get(haloTargetId);
      const pos = st.nodePositions.get(haloTargetId)!;
      const r = nd ? st.nodeSizes.get(nd.id) ?? getNodeCardSize(nd) : 12;
      st.hoveredHalo.position.copy(pos);
      st.hoveredHalo.scale.setScalar(hovEdge ? r * 2.0 : r * 1.75);
      (st.hoveredHalo.material as THREE.SpriteMaterial).color.set(
        hovEdge ? "#fbbf24" : "#ffffff"
      );
      st.hoveredHalo.visible = true;
    } else {
      st.hoveredHalo.visible = false;
    }

    // Path halos (skip selectedNodeId so two halos never stack)
    st.pathHaloGroup.clear();
    if (hasPath) {
      for (const pid of vs.pathNodeIds) {
        if (pid === vs.selectedNodeId) continue;
        const pos = st.nodePositions.get(pid);
        if (!pos) continue;
        const spr = new THREE.Sprite(
          new THREE.SpriteMaterial({
            map: st.glowTex,
            color: 0xfbbf24,
            transparent: true,
            opacity: 0.36,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
          })
        );
        spr.position.copy(pos);
        spr.scale.setScalar(22);
        st.pathHaloGroup.add(spr);
      }
    }

    // Rebuild depth-shaded background LineSegments + clean non-additive 3D ribbon beams
    const bgCoords: number[] = [];
    const bgColors: number[] = [];
    const cTmp = new THREE.Color();

    const pathIndexMap = new Map<string, number>();
    if (hasPath) {
      vs.pathNodeIds.forEach((id, idx) => pathIndexMap.set(id, idx));
    }

    const eStartArr = st.attrEdgeStart.array as Float32Array;
    const eEndArr = st.attrEdgeEnd.array as Float32Array;
    const eColArr = st.attrEdgeColor.array as Float32Array;
    const eWidthArr = st.attrEdgeWidth.array as Float32Array;
    const eIntArr = st.attrEdgeIntensity.array as Float32Array;
    let ribbonCount = 0;

    const pushRibbon = (
      pStart: THREE.Vector3,
      pEnd: THREE.Vector3,
      hex: string,
      width: number,
      intensity: number
    ) => {
      if (ribbonCount >= MAX_ACTIVE_RIBBONS) return;
      const i3 = ribbonCount * 3;
      eStartArr[i3] = pStart.x;
      eStartArr[i3 + 1] = pStart.y;
      eStartArr[i3 + 2] = pStart.z;
      eEndArr[i3] = pEnd.x;
      eEndArr[i3 + 1] = pEnd.y;
      eEndArr[i3 + 2] = pEnd.z;
      cTmp.set(hex);
      eColArr[i3] = cTmp.r;
      eColArr[i3 + 1] = cTmp.g;
      eColArr[i3 + 2] = cTmp.b;
      eWidthArr[ribbonCount] = width;
      eIntArr[ribbonCount] = intensity;
      ribbonCount++;
    };

    const pickables: {
      id: string;
      source: string;
      target: string;
      type: EdgeType;
      priority: number;
    }[] = [];

    const activeFlightEdgeId = st.flight.active ? st.flight.edgeId : null;
    const hubRibbonScale =
      primaryFocusEdgeIds.size > 16
        ? THREE.MathUtils.clamp(16 / primaryFocusEdgeIds.size, 0.62, 1.0)
        : 1.0;

    let hoverPreviewCount = 0;
    let ambientArteryCount = 0;

    for (const e of st.visibleEdges) {
      const p1 = st.nodePositions.get(e.source);
      const p2 = st.nodePositions.get(e.target);
      if (!p1 || !p2) continue;

      const isHoveredThisEdge = hovEdge?.id === e.id;
      const isFlightThisEdge = activeFlightEdgeId === e.id;
      const isPathEdge = hasPath && vs.pathEdgeSet.has(e.id);
      const isFocusEdge =
        !hasPath && activeId && (e.source === activeId || e.target === activeId);
      const isHoverNodeEdge =
        !isPathEdge &&
        !isFocusEdge &&
        hovId &&
        (e.source === hovId || e.target === hovId);
      const isIsoRootEdge =
        vs.isolationActive &&
        !hasPath &&
        !activeId &&
        (e.source === vs.isolationRootId || e.target === vs.isolationRootId);

      if (isPathEdge) {
        const idxA = pathIndexMap.get(e.source) ?? 0;
        const idxB = pathIndexMap.get(e.target) ?? 1;
        const [ps, pe] = idxA <= idxB ? [p1, p2] : [p2, p1];
        pushRibbon(
          ps,
          pe,
          "#fbbf24",
          isHoveredThisEdge || isFlightThisEdge ? 3.6 : 2.6,
          isHoveredThisEdge || isFlightThisEdge ? 1.35 : 1.05
        );
        pickables.push({ ...e, priority: 3 });
      } else if (isHoveredThisEdge || isFlightThisEdge) {
        const [ps, pe] =
          (hovEdge && hovEdge.fromId === e.target) || e.target === activeId ? [p2, p1] : [p1, p2];
        pushRibbon(ps, pe, "#fbbf24", 3.5, 1.35);
        pickables.push({ ...e, priority: 3 });
      } else if (isFocusEdge) {
        const [ps, pe] = e.source === activeId ? [p1, p2] : [p2, p1];
        if (primaryFocusEdgeIds.has(e.id)) {
          pushRibbon(
            ps,
            pe,
            EDGE_META[e.type]?.color ?? "#34d399",
            2.2 * hubRibbonScale,
            0.92
          );
          pickables.push({ ...e, priority: 3 });
        } else {
          // Secondary links on massive >28-edge hubs stay clean thin lines until hovered
          bgCoords.push(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z);
          cTmp.set(EDGE_META[e.type]?.color ?? "#34d399").multiplyScalar(0.85);
          bgColors.push(cTmp.r, cTmp.g, cTmp.b, cTmp.r, cTmp.g, cTmp.b);
          pickables.push({ ...e, priority: 2 });
        }
      } else if (isHoverNodeEdge && hoverPreviewCount < 24) {
        hoverPreviewCount++;
        const [ps, pe] = e.source === hovId ? [p1, p2] : [p2, p1];
        pushRibbon(
          ps,
          pe,
          EDGE_META[e.type]?.color ?? "#34d399",
          1.7,
          activeId ? 0.52 : 0.78
        );
        if (!activeId) pickables.push({ ...e, priority: 2 });
      } else if (isIsoRootEdge && ribbonCount < 32) {
        const [ps, pe] = e.source === vs.isolationRootId ? [p1, p2] : [p2, p1];
        pushRibbon(ps, pe, EDGE_META[e.type]?.color ?? "#34d399", 1.7, 0.72);
        pickables.push({ ...e, priority: 2 });
      } else {
        // In 2-hop isolation on giant hubs, skip non-root loot/chordal clutter
        if (
          vs.isolationActive &&
          e.source !== vs.isolationRootId &&
          e.target !== vs.isolationRootId &&
          (e.type === "location_item" || e.type === "location_object" || st.visibleNodes.length > 350)
        ) {
          continue;
        }
        if (
          !vs.isolationActive &&
          !st.showBgLootEdges &&
          (e.type === "location_item" || e.type === "location_object")
        ) {
          continue;
        }

        // In general overview, subtly accent key story arteries so connections read clearly at a glance
        const isStoryArtery =
          !activeId &&
          !hasPath &&
          !vs.isolationActive &&
          st.visibleNodes.length <= 600 &&
          ambientArteryCount < 420 &&
          (e.type === "quest_chain" ||
            e.type === "quest_event" ||
            e.type === "location_connection" ||
            e.type === "quest_location");

        if (isStoryArtery) {
          ambientArteryCount++;
          pushRibbon(p1, p2, EDGE_META[e.type]?.color ?? "#34d399", 1.05, 0.42);
        } else {
          bgCoords.push(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z);
          cTmp.set(EDGE_META[e.type]?.color ?? "#2a5c47");
          bgColors.push(cTmp.r, cTmp.g, cTmp.b, cTmp.r, cTmp.g, cTmp.b);
        }

        if (!activeId && !hasPath) {
          pickables.push({ ...e, priority: 1 });
        }
      }
    }

    st.pickableEdges = pickables;

    st.activeEdgeMesh.count = ribbonCount;
    st.attrEdgeStart.needsUpdate = true;
    st.attrEdgeEnd.needsUpdate = true;
    st.attrEdgeColor.needsUpdate = true;
    st.attrEdgeWidth.needsUpdate = true;
    st.attrEdgeIntensity.needsUpdate = true;

    const bgGeo = st.bgLines.geometry;
    bgGeo.setAttribute("position", new THREE.Float32BufferAttribute(bgCoords, 3));
    bgGeo.setAttribute("aLineColor", new THREE.Float32BufferAttribute(bgColors, 3));
    bgGeo.computeBoundingSphere();
    st.bgLineMat.uniforms.uBaseOpacity.value =
      hasPath ? 0.06 : activeId ? (primaryFocusEdgeIds.size >= 28 ? 0.22 : 0.07) : 0.44;
  }, [nodeMap, adjacency, uploadSortedInstances]);

  const navHandlersRef = useRef<{
    onClickNode: (nodeId: string) => void;
    onClickEdge: (edge: HoveredEdgeInfo) => void;
    onBack: () => void;
    onCancelTour: () => void;
  }>({
    onClickNode: () => { },
    onClickEdge: () => { },
    onBack: () => { },
    onCancelTour: () => { },
  });

  // Initialize Three.js WebGL scene once
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 1200;
    const height = container.clientHeight || 800;

    const scene = new THREE.Scene();
    const fogHex = 0x050a08;
    scene.background = new THREE.Color(fogHex);
    scene.fog = new THREE.FogExp2(fogHex, 0.00075);

    const camera = new THREE.PerspectiveCamera(52, width / height, 1, 6000);
    camera.position.set(0, 175, 495);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.075;
    controls.rotateSpeed = 0.7;
    controls.zoomSpeed = 0.95;
    controls.panSpeed = 0.85;
    controls.minDistance = 22;
    controls.maxDistance = 2400;

    // Lights
    scene.add(new THREE.AmbientLight(0xd9f9ea, 0.7));
    scene.add(new THREE.HemisphereLight(0x6ee7b7, 0x24190c, 0.85));
    const keyLight = new THREE.PointLight(0xfffbeb, 1.4, 3000, 0.4);
    keyLight.position.set(420, 560, 480);
    scene.add(keyLight);
    const rimLight = new THREE.PointLight(0x38bdf8, 0.95, 3000, 0.4);
    rimLight.position.set(-460, -280, -420);
    scene.add(rimLight);

    // Subtle 3D Starfield
    const starCount = 850;
    const starPos = new Float32Array(starCount * 3);
    const starCol = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      starPos[i * 3] = (Math.random() - 0.5) * 2600;
      starPos[i * 3 + 1] = (Math.random() - 0.5) * 1400;
      starPos[i * 3 + 2] = (Math.random() - 0.5) * 2600;
      const c = new THREE.Color(i % 7 === 0 ? "#f59e0b" : "#34d399");
      starCol[i * 3] = c.r;
      starCol[i * 3 + 1] = c.g;
      starCol[i * 3 + 2] = c.b;
    }
    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute("position", new THREE.BufferAttribute(starPos, 3));
    starGeo.setAttribute("color", new THREE.BufferAttribute(starCol, 3));
    const starMat = new THREE.PointsMaterial({
      size: 2.2,
      vertexColors: true,
      transparent: true,
      opacity: 0.38,
      sizeAttenuation: true,
    });
    scene.add(new THREE.Points(starGeo, starMat));

    // Holographic Coordinate Grid at Y = 0
    const gridHelper = new THREE.GridHelper(1200, 24, 0x1e5c44, 0x0e291e);
    const gridMats = Array.isArray(gridHelper.material)
      ? gridHelper.material
      : [gridHelper.material];
    for (const gm of gridMats) {
      gm.transparent = true;
      gm.opacity = 0.18;
    }
    scene.add(gridHelper);

    // Radar concentric rings at Y = 0
    const radarRings = new THREE.Group();
    for (const r of [180, 360, 540]) {
      const rg = new THREE.RingGeometry(r - 0.8, r + 0.8, 96);
      rg.rotateX(-Math.PI / 2);
      const rm = new THREE.MeshBasicMaterial({
        color: 0x2dd4bf,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.12,
      });
      radarRings.add(new THREE.Mesh(rg, rm));
    }
    scene.add(radarRings);

    // Vertical Stratum reference rings (upper quests & lower objects)
    const stratumRings = new THREE.Group();
    for (const [ry, col] of [
      [190, 0xf59e0b],
      [-185, 0xfb923c],
    ] as [number, number][]) {
      const rg = new THREE.RingGeometry(460, 461.5, 96);
      rg.rotateX(-Math.PI / 2);
      rg.translate(0, ry, 0);
      stratumRings.add(
        new THREE.Mesh(
          rg,
          new THREE.MeshBasicMaterial({
            color: col,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.1,
          })
        )
      );
    }
    scene.add(stratumRings);

    const fogColorVec = new THREE.Color("#050a08");

    // Instanced 3D Billboard Icon Plaques with GPU Depth Shading
    const maxNodes = Math.max(4500, graphData.nodes.length);
    const iconGeo = new THREE.PlaneGeometry(1, 1);

    const attrCenter = new THREE.InstancedBufferAttribute(new Float32Array(maxNodes * 3), 3);
    const attrSize = new THREE.InstancedBufferAttribute(new Float32Array(maxNodes), 1);
    const attrUvRect = new THREE.InstancedBufferAttribute(new Float32Array(maxNodes * 4), 4);
    const attrColor = new THREE.InstancedBufferAttribute(new Float32Array(maxNodes * 3), 3);
    const attrAlpha = new THREE.InstancedBufferAttribute(new Float32Array(maxNodes), 1);
    const attrHighlight = new THREE.InstancedBufferAttribute(new Float32Array(maxNodes), 1);
    const attrIsColor = new THREE.InstancedBufferAttribute(new Float32Array(maxNodes), 1);

    iconGeo.setAttribute("aCenter", attrCenter);
    iconGeo.setAttribute("aSize", attrSize);
    iconGeo.setAttribute("aUvRect", attrUvRect);
    iconGeo.setAttribute("aColor", attrColor);
    iconGeo.setAttribute("aAlpha", attrAlpha);
    iconGeo.setAttribute("aHighlight", attrHighlight);
    iconGeo.setAttribute("aIsColor", attrIsColor);

    const initRange = computeDepthRange(525);

    const iconMat = new THREE.ShaderMaterial({
      uniforms: {
        uAtlas: { value: null },
        uHasAtlas: { value: 0.0 },
        uDepthNear: { value: initRange.near },
        uDepthFar: { value: initRange.far },
        uDepthStrength: { value: 1.0 },
        uFogColor: { value: fogColorVec.clone() },
      },
      vertexShader: `
        attribute vec3 aCenter;
        attribute float aSize;
        attribute vec4 aUvRect;
        attribute vec3 aColor;
        attribute float aAlpha;
        attribute float aHighlight;
        attribute float aIsColor;

        uniform float uDepthNear;
        uniform float uDepthFar;
        uniform float uDepthStrength;

        varying vec2 vUv;
        varying vec4 vUvRect;
        varying vec3 vColor;
        varying float vAlpha;
        varying float vHighlight;
        varying float vIsColor;
        varying float vCamDist;

        void main() {
          vUv = uv;
          vUvRect = aUvRect;
          vColor = aColor;
          vAlpha = aAlpha;
          vHighlight = aHighlight;
          vIsColor = aIsColor;

          vec4 mvCenter = viewMatrix * modelMatrix * vec4(aCenter, 1.0);
          float camDist = length(mvCenter.xyz);
          vCamDist = camDist;

          float farFactor = smoothstep(uDepthNear, uDepthFar, camDist) * uDepthStrength * (1.0 - clamp(aHighlight, 0.0, 1.0));
          float maxAngular = mix(0.068, 0.092, step(0.72, aHighlight));
          float effSize = min(aSize, max(3.2, abs(mvCenter.z) * maxAngular)) * mix(1.0, 0.68, farFactor);
          mvCenter.xy += position.xy * effSize;
          gl_Position = projectionMatrix * mvCenter;
        }
      `,
      fragmentShader: `
        uniform sampler2D uAtlas;
        uniform float uHasAtlas;
        uniform float uDepthNear;
        uniform float uDepthFar;
        uniform float uDepthStrength;
        uniform vec3 uFogColor;

        varying vec2 vUv;
        varying vec4 vUvRect;
        varying vec3 vColor;
        varying float vAlpha;
        varying float vHighlight;
        varying float vIsColor;
        varying float vCamDist;

        float sdRoundedBox(vec2 p, vec2 b, float r) {
          vec2 q = abs(p) - b + vec2(r);
          return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
        }

        void main() {
          vec2 p = vUv - vec2(0.5);
          float dist = sdRoundedBox(p, vec2(0.47, 0.47), 0.14);
          if (dist > 0.02) discard;

          float outerMask = 1.0 - smoothstep(-0.015, 0.02, dist);
          float borderMask = smoothstep(-0.068, -0.024, dist) * outerMask;

          float radialGlow = clamp(1.0 - length(p) * 1.45, 0.0, 1.0);
          vec3 bgCol = vec3(0.005, 0.014, 0.010) + vColor * (0.09 * radialGlow + 0.08 * vHighlight);
          vec3 borderCol = mix(vColor, vec3(0.95, 1.0, 0.98), 0.15 + 0.48 * vHighlight);

          vec3 col = mix(bgCol, borderCol, borderMask * (0.80 + 0.20 * vHighlight));
          float outAlpha = outerMask * mix(0.92, 1.0, max(borderMask, vHighlight));

          if (uHasAtlas > 0.5 && vUvRect.z > 0.0001) {
            vec2 innerUv = (vUv - vec2(0.11)) / 0.78;
            if (innerUv.x >= 0.0 && innerUv.x <= 1.0 && innerUv.y >= 0.0 && innerUv.y <= 1.0) {
              vec2 safeUv = clamp(innerUv, 0.015, 0.985);
              vec2 atlasUv = vUvRect.xy + safeUv * vUvRect.zw;
              vec4 tex = texture2D(uAtlas, atlasUv);
              vec3 monoTint = mix(vColor, vec3(0.96, 1.0, 0.98), 0.45 + 0.30 * vHighlight);
              vec3 iconRgb = vIsColor > 0.5 ? tex.rgb : tex.rgb * monoTint;
              float iconMix = tex.a * 0.98;
              col = mix(col, iconRgb, iconMix);
              outAlpha = max(outAlpha, outerMask * iconMix);
            }
          } else {
            float dotMask = 1.0 - smoothstep(0.12, 0.16, length(p));
            col = mix(col, vColor, dotMask);
          }

          // Atmospheric 3D depth shading: darken distant unselected objects into deep Pip-Boy space
          float rawDepth = smoothstep(uDepthNear, uDepthFar, vCamDist) * uDepthStrength;
          float highlightKeep = smoothstep(0.05, 0.75, vHighlight) * mix(0.76, 0.95, step(0.72, vHighlight));
          float effDepth = rawDepth * (1.0 - highlightKeep);
          float shade = 1.0 - effDepth;

          vec3 shadedCol = mix(uFogColor, col, mix(0.06, 1.0, pow(shade, 1.3)));
          float shadedAlpha = outAlpha * vAlpha * mix(0.12, 1.0, pow(shade, 1.15));

          gl_FragColor = vec4(shadedCol, shadedAlpha);
          #include <colorspace_fragment>
        }
      `,
      transparent: true,
      depthWrite: false,
      depthTest: true,
    });

    const iconMesh = new THREE.InstancedMesh(iconGeo, iconMat, maxNodes);
    iconMesh.count = 0;
    iconMesh.frustumCulled = false;
    iconMesh.renderOrder = 2;
    scene.add(iconMesh);

    // Load texture atlas asynchronously for WebGL billboard cards
    let disposed = false;
    let atlasTexture: THREE.Texture | null = null;
    new THREE.TextureLoader().load("/icons/atlas.png", (tex) => {
      if (disposed) {
        tex.dispose();
        return;
      }
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.flipY = true;
      tex.minFilter = THREE.LinearMipmapLinearFilter;
      tex.magFilter = THREE.LinearFilter;
      tex.generateMipmaps = true;
      tex.needsUpdate = true;
      atlasTexture = tex;
      iconMat.uniforms.uAtlas.value = tex;
      iconMat.uniforms.uHasAtlas.value = 1.0;
      if (threeRef.current) {
        threeRef.current.atlasTexture = tex;
      }
      refreshVisualHighlights();
    });

    // Depth-shaded Background LineSegments (nearby links crisp, distant links fade into darkness)
    const bgLineMat = new THREE.ShaderMaterial({
      uniforms: {
        uBaseOpacity: { value: 0.46 },
        uDepthNear: { value: initRange.near },
        uDepthFar: { value: initRange.far },
        uDepthStrength: { value: 1.0 },
        uFogColor: { value: fogColorVec.clone() },
      },
      vertexShader: `
        attribute vec3 aLineColor;
        varying vec3 vLineColor;
        varying float vCamDist;

        void main() {
          vLineColor = aLineColor;
          vec4 mvPos = viewMatrix * modelMatrix * vec4(position, 1.0);
          vCamDist = length(mvPos.xyz);
          gl_Position = projectionMatrix * mvPos;
        }
      `,
      fragmentShader: `
        uniform float uBaseOpacity;
        uniform float uDepthNear;
        uniform float uDepthFar;
        uniform float uDepthStrength;
        uniform vec3 uFogColor;

        varying vec3 vLineColor;
        varying float vCamDist;

        void main() {
          float depthT = smoothstep(uDepthNear * 0.85, uDepthFar, vCamDist) * uDepthStrength;
          float shade = 1.0 - depthT;
          vec3 col = mix(uFogColor, vLineColor * 1.15, mix(0.08, 1.0, shade));
          float alpha = uBaseOpacity * mix(0.04, 1.0, pow(shade, 1.35));
          if (alpha < 0.008) discard;
          gl_FragColor = vec4(col, alpha);
          #include <colorspace_fragment>
        }
      `,
      transparent: true,
      depthWrite: false,
      depthTest: true,
    });

    const bgLines = new THREE.LineSegments(new THREE.BufferGeometry(), bgLineMat);
    bgLines.frustumCulled = false;
    bgLines.renderOrder = 0;
    scene.add(bgLines);

    // Instanced 3D Glowing Directional Ribbon Beams for active/hovered/path connections
    const activeEdgeGeo = new THREE.PlaneGeometry(1, 1, 16, 1);
    const attrEdgeStart = new THREE.InstancedBufferAttribute(
      new Float32Array(MAX_ACTIVE_RIBBONS * 3),
      3
    );
    const attrEdgeEnd = new THREE.InstancedBufferAttribute(
      new Float32Array(MAX_ACTIVE_RIBBONS * 3),
      3
    );
    const attrEdgeColor = new THREE.InstancedBufferAttribute(
      new Float32Array(MAX_ACTIVE_RIBBONS * 3),
      3
    );
    const attrEdgeWidth = new THREE.InstancedBufferAttribute(
      new Float32Array(MAX_ACTIVE_RIBBONS),
      1
    );
    const attrEdgeIntensity = new THREE.InstancedBufferAttribute(
      new Float32Array(MAX_ACTIVE_RIBBONS),
      1
    );

    activeEdgeGeo.setAttribute("aStart", attrEdgeStart);
    activeEdgeGeo.setAttribute("aEnd", attrEdgeEnd);
    activeEdgeGeo.setAttribute("aEdgeColor", attrEdgeColor);
    activeEdgeGeo.setAttribute("aEdgeWidth", attrEdgeWidth);
    activeEdgeGeo.setAttribute("aEdgeIntensity", attrEdgeIntensity);

    const activeEdgeMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uAspect: { value: width / height },
        uDepthNear: { value: initRange.near },
        uDepthFar: { value: initRange.far },
        uDepthStrength: { value: 1.0 },
        uFogColor: { value: fogColorVec.clone() },
      },
      vertexShader: `
        attribute vec3 aStart;
        attribute vec3 aEnd;
        attribute vec3 aEdgeColor;
        attribute float aEdgeWidth;
        attribute float aEdgeIntensity;

        uniform float uAspect;

        varying float vSegT;
        varying float vSide;
        varying vec3 vEdgeColor;
        varying float vIntensity;
        varying float vCamDist;
        varying float vScreenLen;

        void main() {
          vec4 mvA = viewMatrix * modelMatrix * vec4(aStart, 1.0);
          vec4 mvB = viewMatrix * modelMatrix * vec4(aEnd, 1.0);

          float zNear = -1.5;
          if (mvA.z > zNear && mvB.z > zNear) {
            gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
            return;
          }

          float tA = 0.0;
          float tB = 1.0;
          if (mvA.z > zNear) {
            tA = clamp((zNear - mvA.z) / (mvB.z - mvA.z), 0.0, 1.0);
            mvA = mix(mvA, mvB, tA);
          } else if (mvB.z > zNear) {
            tB = clamp((zNear - mvA.z) / (mvB.z - mvA.z), 0.0, 1.0);
            mvB = mix(mvA, mvB, tB);
          }

          float localU = position.x + 0.5;
          vSegT = mix(tA, tB, localU);
          vSide = position.y * 2.0;
          vEdgeColor = aEdgeColor;
          vIntensity = aEdgeIntensity;

          vec4 mvP = mix(mvA, mvB, localU);
          vCamDist = length(mvP.xyz);

          vec4 clipA = projectionMatrix * mvA;
          vec4 clipB = projectionMatrix * mvB;
          vec2 ndcA = clipA.xy / max(0.0001, clipA.w);
          vec2 ndcB = clipB.xy / max(0.0001, clipB.w);

          vec2 screenDelta = vec2((ndcB.x - ndcA.x) * uAspect, ndcB.y - ndcA.y);
          float sLen = length(screenDelta);
          vScreenLen = sLen;
          vec2 screenDir = sLen > 1e-5 ? screenDelta / sLen : vec2(1.0, 0.0);
          vec2 screenPerp = vec2(-screenDir.y, screenDir.x);

          vec4 clipP = projectionMatrix * mvP;
          float worldNdcH = (aEdgeWidth * 0.65 * projectionMatrix[1][1]) / max(18.0, -mvP.z);
          float minNdcH = aEdgeWidth * 0.0014;
          float halfNdc = max(minNdcH, min(0.0085, worldNdcH));

          clipP.x += (screenPerp.x / max(0.1, uAspect)) * vSide * halfNdc * clipP.w;
          clipP.y += screenPerp.y * vSide * halfNdc * clipP.w;

          gl_Position = clipP;
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform float uDepthNear;
        uniform float uDepthFar;
        uniform float uDepthStrength;
        uniform vec3 uFogColor;

        varying float vSegT;
        varying float vSide;
        varying vec3 vEdgeColor;
        varying float vIntensity;
        varying float vCamDist;
        varying float vScreenLen;

        void main() {
          float d = abs(vSide);
          float core = exp(-d * d * 9.0);
          float halo = (1.0 - smoothstep(0.08, 1.0, d)) * 0.32;

          float speed = vIntensity > 1.2 ? 1.35 : 0.68;
          float wave = fract(vSegT * 2.5 - uTime * speed);
          float pulse = vIntensity > 0.55
            ? smoothstep(0.60, 0.94, wave) * (1.0 - smoothstep(0.94, 1.0, wave))
            : 0.0;

          // Gracefully fade beam right at the outer border of both endpoint plaques so hubs never pile up
          float clearT = clamp(0.055 / max(0.09, vScreenLen), 0.035, 0.26);
          float tipFade = smoothstep(clearT * 0.4, clearT * 1.3, vSegT) *
                          (1.0 - smoothstep(1.0 - clearT * 1.15, 1.0 - clearT * 0.35, vSegT));

          float depthScale = vIntensity > 0.55 ? 1.28 : 1.0;
          float depthRaw = smoothstep(uDepthNear, uDepthFar * depthScale, vCamDist) * uDepthStrength;
          float depthKeep = vIntensity > 0.55 ? mix(1.0, 0.48, depthRaw) : mix(1.0, 0.06, depthRaw);

          vec3 baseCol = mix(vEdgeColor, vec3(0.98, 1.0, 0.96), core * (0.22 + 0.48 * pulse));
          vec3 finalCol = mix(uFogColor, baseCol, depthKeep);

          float alpha = (core * 0.78 + halo + pulse * core * 0.45) * tipFade * clamp(vIntensity, 0.0, 1.25) * depthKeep;
          if (alpha < 0.01) discard;

          gl_FragColor = vec4(finalCol, clamp(alpha, 0.0, 0.92));
          #include <colorspace_fragment>
        }
      `,
      transparent: true,
      blending: THREE.NormalBlending,
      depthWrite: false,
      depthTest: true,
    });

    const activeEdgeMesh = new THREE.InstancedMesh(
      activeEdgeGeo,
      activeEdgeMat,
      MAX_ACTIVE_RIBBONS
    );
    activeEdgeMesh.count = 0;
    activeEdgeMesh.frustumCulled = false;
    activeEdgeMesh.renderOrder = 1;
    scene.add(activeEdgeMesh);

    // Halos & Corridor Flight Light Orb (subtle non-washing-out opacities)
    const glowTex = createGlowTexture();
    const selectedHalo = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: glowTex,
        color: 0x34d399,
        transparent: true,
        opacity: 0.38,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      })
    );
    selectedHalo.visible = false;
    selectedHalo.renderOrder = 3;
    scene.add(selectedHalo);

    const hoveredHalo = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: glowTex,
        color: 0xffffff,
        transparent: true,
        opacity: 0.34,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      })
    );
    hoveredHalo.visible = false;
    hoveredHalo.renderOrder = 3;
    scene.add(hoveredHalo);

    const flightOrb = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: glowTex,
        color: 0xfbbf24,
        transparent: true,
        opacity: 0.82,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      })
    );
    flightOrb.visible = false;
    flightOrb.scale.setScalar(20);
    flightOrb.renderOrder = 4;
    scene.add(flightOrb);

    const pathHaloGroup = new THREE.Group();
    scene.add(pathHaloGroup);

    const pressedKeys = new Set<string>();

    threeRef.current = {
      scene,
      camera,
      renderer,
      controls,
      gridHelper,
      radarRings,
      stratumRings,
      iconMesh,
      iconGeo,
      iconMat,
      atlasTexture,
      attrCenter,
      attrSize,
      attrUvRect,
      attrColor,
      attrAlpha,
      attrHighlight,
      attrIsColor,
      bgLines,
      bgLineMat,
      activeEdgeMesh,
      activeEdgeGeo,
      activeEdgeMat,
      attrEdgeStart,
      attrEdgeEnd,
      attrEdgeColor,
      attrEdgeWidth,
      attrEdgeIntensity,
      selectedHalo,
      hoveredHalo,
      flightOrb,
      pathHaloGroup,
      glowTex,
      nodePositions: new Map(),
      nodeSizes: new Map(),
      preparedInstances: [],
      lastSortCamPos: camera.position.clone(),
      labelBoxes: [],
      pickableEdges: [],
      visibleNodes: [],
      visibleEdges: [],
      showBgLootEdges: false,
      flight: {
        active: false,
        isCorridor: false,
        startTime: 0,
        duration: 500,
        fromPos: new THREE.Vector3(),
        toPos: new THREE.Vector3(),
        fromTarget: new THREE.Vector3(),
        toTarget: new THREE.Vector3(),
        p0: new THREE.Vector3(),
        p1: new THREE.Vector3(),
        p2: new THREE.Vector3(),
        p3: new THREE.Vector3(),
        t0: new THREE.Vector3(),
        t1: new THREE.Vector3(),
        t2: new THREE.Vector3(),
        t3: new THREE.Vector3(),
        linkStart: new THREE.Vector3(),
        linkEnd: new THREE.Vector3(),
        edgeId: null,
      },
      pressedKeys,
    };

    // Cancel camera flight when user takes manual control
    const cancelFlight = () => {
      if (threeRef.current) {
        threeRef.current.flight.active = false;
        threeRef.current.flight.edgeId = null;
        threeRef.current.flightOrb.visible = false;
      }
      navHandlersRef.current.onCancelTour();
    };
    controls.addEventListener("start", cancelFlight);

    // Exact 3D ray-to-billboard + label + screen-space connection ribbon picking
    const raycaster = new THREE.Raycaster();
    const pointerNdc = new THREE.Vector2();
    const tmpRayDiff = new THREE.Vector3();
    const mvTmp1 = new THREE.Vector4();
    const mvTmp2 = new THREE.Vector4();
    const clipTmp1 = new THREE.Vector4();
    const clipTmp2 = new THREE.Vector4();
    let downPos = { x: 0, y: 0 };
    let isPointerDown = false;
    let hoverTimer: number | null = null;
    let pendingHoverKey: string | null = null;
    let committedHoverKey: string | null = null;

    const clearHoverTimer = () => {
      if (hoverTimer !== null) {
        window.clearTimeout(hoverTimer);
        hoverTimer = null;
      }
    };

    const pickNodeAtEvent = (ev: MouseEvent): GraphNode | null => {
      const st = threeRef.current;
      if (!st) return null;
      const rect = renderer.domElement.getBoundingClientRect();
      const localX = ev.clientX - rect.left;
      const localY = ev.clientY - rect.top;
      pointerNdc.x = (localX / rect.width) * 2 - 1;
      pointerNdc.y = -(localY / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointerNdc, camera);
      const ray = raycaster.ray;

      const vs = visualStateRef.current;
      const dNear = iconMat.uniforms.uDepthNear.value as number;
      const dFar = iconMat.uniforms.uDepthFar.value as number;
      const dStr = vs.depthStrength;

      let bestNode: GraphNode | null = null;
      let bestT = Infinity;

      for (const nd of st.visibleNodes) {
        const pos = st.nodePositions.get(nd.id);
        if (!pos) continue;
        tmpRayDiff.subVectors(pos, ray.origin);
        const t = tmpRayDiff.dot(ray.direction);
        if (t <= 1) continue;

        const isHighlighted =
          nd.id === vs.selectedNodeId ||
          nd.id === vs.hoveredNodeId ||
          vs.neighborsOfFocus.has(nd.id) ||
          vs.pathNodeSet.has(nd.id);

        const rawDepth = THREE.MathUtils.smoothstep(t, dNear, dFar) * dStr;
        const shade = isHighlighted ? 1.0 : 1.0 - rawDepth;
        // Heavily shaded distant background nodes have tighter hit radii so foreground links stay easy to click
        const shadeRadiusScale = 0.48 + 0.52 * shade;

        const size = st.nodeSizes.get(nd.id) ?? getNodeCardSize(nd);
        const pickR = size * 0.56 * shadeRadiusScale;
        if (ray.distanceSqToPoint(pos) <= pickR * pickR) {
          if (t < bestT) {
            bestT = t;
            bestNode = nd;
          }
        }
      }

      if (bestNode) return bestNode;

      // Also check projected visible HTML label boxes so clicking a node's text badge hits the node
      for (const box of st.labelBoxes) {
        if (localX >= box.x1 && localX <= box.x2 && localY >= box.y1 && localY <= box.y2) {
          return box.node;
        }
      }

      return null;
    };

    const pickEdgeAtEvent = (ev: MouseEvent): HoveredEdgeInfo | null => {
      const st = threeRef.current;
      if (!st || st.pickableEdges.length === 0) return null;
      const rect = renderer.domElement.getBoundingClientRect();
      const mx = ev.clientX - rect.left;
      const my = ev.clientY - rect.top;
      const cw = rect.width;
      const ch = rect.height;
      if (cw <= 0 || ch <= 0) return null;

      camera.updateMatrixWorld();
      const viewMat = camera.matrixWorldInverse;
      const projMat = camera.projectionMatrix;
      const vs = visualStateRef.current;
      const dNear = iconMat.uniforms.uDepthNear.value as number;
      const dFar = iconMat.uniforms.uDepthFar.value as number;
      const zNear = -1.5;

      let bestEdge: HoveredEdgeInfo | null = null;
      let bestScore = Infinity;

      for (const e of st.pickableEdges) {
        const p1 = st.nodePositions.get(e.source);
        const p2 = st.nodePositions.get(e.target);
        if (!p1 || !p2) continue;

        mvTmp1.set(p1.x, p1.y, p1.z, 1.0).applyMatrix4(viewMat);
        mvTmp2.set(p2.x, p2.y, p2.z, 1.0).applyMatrix4(viewMat);
        if (mvTmp1.z > zNear && mvTmp2.z > zNear) continue;

        if (mvTmp1.z > zNear) {
          const tClip = (zNear - mvTmp1.z) / (mvTmp2.z - mvTmp1.z);
          mvTmp1.lerp(mvTmp2, tClip);
        } else if (mvTmp2.z > zNear) {
          const tClip = (zNear - mvTmp2.z) / (mvTmp1.z - mvTmp2.z);
          mvTmp2.lerp(mvTmp1, tClip);
        }

        // For ambient edges (priority === 1), only pick foreground unshaded connections
        const midDist = 0.5 * (-mvTmp1.z - mvTmp2.z);
        if (e.priority === 1) {
          const rawDepth = THREE.MathUtils.smoothstep(midDist, dNear, dFar) * vs.depthStrength;
          if (1.0 - rawDepth < 0.52) continue;
        }

        clipTmp1.copy(mvTmp1).applyMatrix4(projMat);
        clipTmp2.copy(mvTmp2).applyMatrix4(projMat);
        if (clipTmp1.w <= 0.0001 || clipTmp2.w <= 0.0001) continue;

        const sx1 = (clipTmp1.x / clipTmp1.w * 0.5 + 0.5) * cw;
        const sy1 = (-clipTmp1.y / clipTmp1.w * 0.5 + 0.5) * ch;
        const sx2 = (clipTmp2.x / clipTmp2.w * 0.5 + 0.5) * cw;
        const sy2 = (-clipTmp2.y / clipTmp2.w * 0.5 + 0.5) * ch;

        const dx = sx2 - sx1;
        const dy = sy2 - sy1;
        const segLenSq = dx * dx + dy * dy;
        if (segLenSq < 324) continue; // ignore tiny <18px projected links

        const segParam = THREE.MathUtils.clamp(
          ((mx - sx1) * dx + (my - sy1) * dy) / segLenSq,
          0,
          1
        );
        const segLen = Math.sqrt(segLenSq);
        const distFromEndPx = Math.min(segParam * segLen, (1 - segParam) * segLen);
        if (distFromEndPx < 13) continue; // leave endpoints to node plaques

        const px = sx1 + dx * segParam;
        const py = sy1 + dy * segParam;
        const distPx = Math.hypot(mx - px, my - py);
        const maxPx = e.priority >= 2 ? 11.5 : 7.0;
        if (distPx > maxPx) continue;

        const score = (4 - e.priority) * 100 + distPx + midDist * 0.004;
        if (score < bestScore) {
          bestScore = score;
          let fromId = e.source;
          let toId = e.target;
          if (vs.selectedNodeId === e.target) {
            fromId = e.target;
            toId = e.source;
          } else if (vs.selectedNodeId === e.source) {
            fromId = e.source;
            toId = e.target;
          } else if (vs.hoveredNodeId === e.target) {
            fromId = e.target;
            toId = e.source;
          } else if (vs.hoveredNodeId === e.source) {
            fromId = e.source;
            toId = e.target;
          } else {
            // Orient from closer node toward farther/clicked destination
            const d1 = camera.position.distanceToSquared(p1);
            const d2 = camera.position.distanceToSquared(p2);
            if (d2 < d1 && segParam < 0.65) {
              fromId = e.target;
              toId = e.source;
            }
          }
          bestEdge = {
            id: e.id,
            source: e.source,
            target: e.target,
            type: e.type,
            fromId,
            toId,
          };
        }
      }

      return bestEdge;
    };

    const onPointerDown = (ev: PointerEvent) => {
      isPointerDown = true;
      downPos = { x: ev.clientX, y: ev.clientY };
      clearHoverTimer();
      pendingHoverKey = null;
      if (committedHoverKey !== null) {
        committedHoverKey = null;
        setHoveredNodeId(null);
        setHoveredEdge(null);
      }
      if (tooltipRef.current) {
        tooltipRef.current.style.opacity = "0";
      }
    };

    const onPointerMove = (ev: PointerEvent) => {
      if (isPointerDown) return;
      const hitNode = pickNodeAtEvent(ev);
      const hitEdge = hitNode ? null : pickEdgeAtEvent(ev);
      const nextKey = hitNode
        ? `node:${hitNode.id}`
        : hitEdge
          ? `edge:${hitEdge.id}:${hitEdge.toId}`
          : null;

      renderer.domElement.style.cursor = nextKey ? "pointer" : "grab";

      if (nextKey) {
        if (tooltipRef.current) {
          tooltipRef.current.style.transform = `translate3d(${ev.clientX + 16}px, ${ev.clientY + 16}px, 0)`;
          if (committedHoverKey === nextKey) {
            tooltipRef.current.style.opacity = "1";
          }
        }
        if (pendingHoverKey !== nextKey) {
          pendingHoverKey = nextKey;
          clearHoverTimer();
          const delay = hitEdge ? 65 : 130;
          hoverTimer = window.setTimeout(() => {
            committedHoverKey = nextKey;
            setHoveredNodeId(hitNode ? hitNode.id : null);
            setHoveredEdge(hitEdge);
            if (tooltipRef.current) {
              tooltipRef.current.style.opacity = "1";
            }
          }, delay);
        }
      } else {
        if (tooltipRef.current) {
          tooltipRef.current.style.opacity = "0";
        }
        if (pendingHoverKey !== null || committedHoverKey !== null) {
          pendingHoverKey = null;
          clearHoverTimer();
          hoverTimer = window.setTimeout(() => {
            committedHoverKey = null;
            setHoveredNodeId(null);
            setHoveredEdge(null);
          }, 75);
        }
      }
    };

    const onPointerLeave = () => {
      pendingHoverKey = null;
      committedHoverKey = null;
      clearHoverTimer();
      setHoveredNodeId(null);
      setHoveredEdge(null);
      if (tooltipRef.current) {
        tooltipRef.current.style.opacity = "0";
      }
    };

    const onGlobalPointerUp = () => {
      isPointerDown = false;
    };

    const onPointerUp = (ev: PointerEvent) => {
      isPointerDown = false;
      const dist = Math.hypot(ev.clientX - downPos.x, ev.clientY - downPos.y);
      if (dist > 5 || ev.button !== 0) return;

      const hitNode = pickNodeAtEvent(ev);
      if (hitNode) {
        navHandlersRef.current.onClickNode(hitNode.id);
        return;
      }

      const hitEdge = pickEdgeAtEvent(ev);
      if (hitEdge) {
        navHandlersRef.current.onClickEdge(hitEdge);
        return;
      }

      navHandlersRef.current.onCancelTour();
      onSelectNode(null);
    };

    const onDblClick = (ev: MouseEvent) => {
      const hit = pickNodeAtEvent(ev);
      if (hit) {
        navHandlersRef.current.onCancelTour();
        onSelectNode(hit.id);
        onSetIsolation({ rootId: hit.id, hops: 1 });
      }
    };

    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    renderer.domElement.addEventListener("pointermove", onPointerMove);
    renderer.domElement.addEventListener("pointerup", onPointerUp);
    renderer.domElement.addEventListener("pointerleave", onPointerLeave);
    renderer.domElement.addEventListener("dblclick", onDblClick);
    window.addEventListener("pointerup", onGlobalPointerUp);
    window.addEventListener("pointercancel", onGlobalPointerUp);

    // Keyboard WASD / QE / Backspace / R / Esc / /
    const onKeyDown = (ev: KeyboardEvent) => {
      const tag = (ev.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
        if (ev.key === "Escape") (ev.target as HTMLElement).blur();
        return;
      }
      if (ev.key === "/") {
        ev.preventDefault();
        searchInputRef.current?.focus();
        return;
      }
      if (ev.key === "Backspace") {
        ev.preventDefault();
        navHandlersRef.current.onBack();
        return;
      }
      if (ev.key === "Escape") {
        navHandlersRef.current.onCancelTour();
        setShowFilters(false);
        setShowPathFinder(false);
        onSelectNode(null);
        return;
      }
      if (ev.key.toLowerCase() === "r" || ev.key.toLowerCase() === "к") {
        navHandlersRef.current.onCancelTour();
        if (threeRef.current) {
          threeRef.current.flight.active = true;
          threeRef.current.flight.isCorridor = false;
          threeRef.current.flight.edgeId = null;
          threeRef.current.flight.startTime = performance.now();
          threeRef.current.flight.duration = 450;
          threeRef.current.flight.fromPos.copy(camera.position);
          threeRef.current.flight.toPos.set(0, 175, 495);
          threeRef.current.flight.fromTarget.copy(controls.target);
          threeRef.current.flight.toTarget.set(0, 0, 0);
          threeRef.current.flightOrb.visible = false;
        }
        return;
      }
      pressedKeys.add(ev.code);
    };
    const onKeyUp = (ev: KeyboardEvent) => {
      pressedKeys.delete(ev.code);
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);

    // ResizeObserver so canvas adapts smoothly when Inspector opens/closes
    const ro = new ResizeObserver(() => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w > 0 && h > 0) {
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
        activeEdgeMat.uniforms.uAspect.value = w / h;
      }
    });
    ro.observe(container);

    // Animation loop + GPU depth uniforms + corridor flight + projected DOM 3D labels
    let rafId = 0;
    const projVec = new THREE.Vector3();
    const forwardVec = new THREE.Vector3();
    const rightVec = new THREE.Vector3();
    const upVec = new THREE.Vector3(0, 1, 0);
    const tmpDelta = new THREE.Vector3();
    let lastTime = performance.now();

    const animate = (now: number) => {
      rafId = requestAnimationFrame(animate);
      const dt = Math.min(0.05, (now - lastTime) / 1000);
      lastTime = now;

      const st = threeRef.current;
      if (!st) return;

      st.activeEdgeMat.uniforms.uTime.value = now * 0.001;

      // Full-3D Keyboard flight (WASD flies in true 3D gaze direction so you can glide along links!)
      if (st.pressedKeys.size > 0) {
        if (st.flight.active) {
          st.flight.active = false;
          st.flight.edgeId = null;
          st.flightOrb.visible = false;
        }
        camera.getWorldDirection(forwardVec);
        if (forwardVec.lengthSq() > 1e-6) forwardVec.normalize();
        rightVec.crossVectors(forwardVec, upVec);
        if (rightVec.lengthSq() > 1e-6) rightVec.normalize();
        else rightVec.set(1, 0, 0);

        const pivotDist = camera.position.distanceTo(controls.target);
        const speed = Math.max(125, Math.min(340, pivotDist * 0.72)) * dt;
        tmpDelta.set(0, 0, 0);
        if (st.pressedKeys.has("KeyW") || st.pressedKeys.has("ArrowUp"))
          tmpDelta.addScaledVector(forwardVec, speed);
        if (st.pressedKeys.has("KeyS") || st.pressedKeys.has("ArrowDown"))
          tmpDelta.addScaledVector(forwardVec, -speed);
        if (st.pressedKeys.has("KeyD") || st.pressedKeys.has("ArrowRight"))
          tmpDelta.addScaledVector(rightVec, speed);
        if (st.pressedKeys.has("KeyA") || st.pressedKeys.has("ArrowLeft"))
          tmpDelta.addScaledVector(rightVec, -speed);
        if (st.pressedKeys.has("KeyE") || st.pressedKeys.has("Space"))
          tmpDelta.y += speed;
        if (st.pressedKeys.has("KeyQ"))
          tmpDelta.y -= speed;

        camera.position.add(tmpDelta);
        controls.target.add(tmpDelta);

        // Keep orbit pivot at a comfortable local look-ahead distance when flying inside the graph
        const newPivotDist = camera.position.distanceTo(controls.target);
        if (newPivotDist > 210) {
          const desiredDist = THREE.MathUtils.lerp(newPivotDist, 165, Math.min(1, dt * 4));
          controls.target.copy(camera.position).addScaledVector(forwardVec, desiredDist);
        }
      }

      // Smooth camera flight (cubic Bézier corridor along connection OR standard ease)
      if (st.flight.active) {
        const rawT = Math.min(1, (now - st.flight.startTime) / st.flight.duration);
        if (st.flight.isCorridor) {
          // Smooth ease-in-out along the connection corridor
          const ease =
            rawT < 0.5
              ? 4 * rawT * rawT * rawT
              : 1 - Math.pow(-2 * rawT + 2, 3) / 2;
          evalCubicBezier(
            camera.position,
            st.flight.p0,
            st.flight.p1,
            st.flight.p2,
            st.flight.p3,
            ease
          );
          const targetEase = Math.min(1, Math.pow(rawT, 0.78));
          evalCubicBezier(
            controls.target,
            st.flight.t0,
            st.flight.t1,
            st.flight.t2,
            st.flight.t3,
            targetEase
          );
          // Animate traveler light orb leading along the connection A -> B
          const orbT = Math.min(1, ease * 1.08);
          st.flightOrb.position.lerpVectors(st.flight.linkStart, st.flight.linkEnd, orbT);
          st.flightOrb.scale.setScalar(22 + Math.sin(rawT * Math.PI) * 18);
          st.flightOrb.visible = rawT < 0.98;
        } else {
          const ease = 1 - Math.pow(1 - rawT, 3);
          camera.position.lerpVectors(st.flight.fromPos, st.flight.toPos, ease);
          controls.target.lerpVectors(st.flight.fromTarget, st.flight.toTarget, ease);
        }

        if (rawT >= 1) {
          st.flight.active = false;
          st.flightOrb.visible = false;
          if (st.flight.edgeId) {
            st.flight.edgeId = null;
            refreshVisualHighlights();
          }
        }
      }

      controls.autoRotate = visualStateRef.current.autoRotate && !st.flight.active;
      controls.autoRotateSpeed = 0.55;
      controls.update();

      // Update adaptive 3D depth-shading uniforms across icons, bg lines, and active ribbons
      const vs = visualStateRef.current;
      const targetDist = camera.position.distanceTo(controls.target);
      const { near: dNear, far: dFar } = computeDepthRange(targetDist);
      st.iconMat.uniforms.uDepthNear.value = dNear;
      st.iconMat.uniforms.uDepthFar.value = dFar;
      st.iconMat.uniforms.uDepthStrength.value = vs.depthStrength;

      st.bgLineMat.uniforms.uDepthNear.value = dNear;
      st.bgLineMat.uniforms.uDepthFar.value = dFar;
      st.bgLineMat.uniforms.uDepthStrength.value = vs.depthStrength;

      st.activeEdgeMat.uniforms.uDepthNear.value = dNear;
      st.activeEdgeMat.uniforms.uDepthFar.value = dFar;
      st.activeEdgeMat.uniforms.uDepthStrength.value = vs.depthStrength;

      // Re-sort instances back-to-front whenever camera moves noticeably
      if (camera.position.distanceToSquared(st.lastSortCamPos) > 25) {
        uploadSortedInstances(st, camera.position);
      }

      renderer.render(scene, camera);

      // Project crisp, depth-aware 2D HTML labels for foreground & connected 3D nodes
      const cw = container.clientWidth;
      const ch = container.clientHeight;
      const hasFocus = Boolean(vs.focusNodeId);
      const hasPath = vs.pathNodeSet.size > 0;
      const hovEdge = vs.hoveredEdge;

      const vFovTan = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
      const candidates: {
        node: GraphNode;
        pos: THREE.Vector3;
        dist: number;
        priority: number;
        shade: number;
      }[] = [];

      for (const nd of st.visibleNodes) {
        const p = st.nodePositions.get(nd.id);
        if (!p) continue;
        const dist = camera.position.distanceTo(p);
        const rawDepth = THREE.MathUtils.smoothstep(dist, dNear, dFar) * vs.depthStrength;
        const shade = 1.0 - rawDepth;

        let prio = 0;
        const isTechLabel =
          /^(DC\d|test|dummy|temp|000)/i.test(nd.label) || /^[A-Z0-9_]{6,}$/.test(nd.label);

        if (nd.id === vs.selectedNodeId) prio = 1050;
        else if (nd.id === vs.hoveredNodeId) prio = 1000;
        else if (hovEdge && (nd.id === hovEdge.toId || nd.id === hovEdge.fromId)) prio = 980;
        else if (hasPath && vs.pathNodeSet.has(nd.id)) prio = 900;
        else if (hasFocus && vs.neighborsOfFocus.has(nd.id)) prio = 720 + nd.degree;
        else if (vs.hoveredNodeId && vs.neighborsOfHovered.has(nd.id) && !hasFocus)
          prio = 640 + nd.degree;
        else if (vs.isolationActive) {
          if (nd.id !== vs.isolationRootId && shade < 0.32) continue;
          prio = (nd.id === vs.isolationRootId ? 920 : 480) + nd.degree;
        } else if (!hasFocus && !hasPath && !isTechLabel && nd.degree > 1) {
          // Hide labels on shaded distant objects so only the foreground layer is labeled!
          if (shade < 0.42) continue;
          if (nd.type === "quest" && nd.subtype === "main") prio = 360 + nd.degree;
          else if (nd.type === "quest" || nd.type === "event") prio = 260 + nd.degree;
          else if (nd.subtype === "marker" && nd.degree >= 10) prio = 190 + nd.degree;
          else if (nd.degree >= 14 || dist < 210) prio = 145 + nd.degree + (dist < 210 ? 95 : 0);
        }
        if (prio <= 0) continue;

        candidates.push({
          node: nd,
          pos: p,
          dist,
          priority: prio - dist * 0.12 + shade * 65,
          shade,
        });
      }
      candidates.sort((a, b) => b.priority - a.priority);

      const occupied: { x1: number; y1: number; x2: number; y2: number; node: GraphNode }[] = [];
      // Reserve screen rectangle of the selected node's icon plaque so neighbor labels never cross its face
      let selectedPlaqueBox: { x1: number; y1: number; x2: number; y2: number } | null = null;
      if (vs.selectedNodeId) {
        const selPos = st.nodePositions.get(vs.selectedNodeId);
        const selNd = nodeMap.get(vs.selectedNodeId);
        if (selPos && selNd) {
          projVec.copy(selPos).project(camera);
          if (projVec.z >= -1 && projVec.z <= 1) {
            const selDist = camera.position.distanceTo(selPos);
            const sx = (projVec.x * 0.5 + 0.5) * cw;
            const sy = (-projVec.y * 0.5 + 0.5) * ch;
            const rawS = st.nodeSizes.get(selNd.id) ?? getNodeCardSize(selNd);
            const effS = Math.min(rawS, Math.max(3.2, selDist * 0.092));
            const halfPx = Math.max(14, (effS * ch) / (4 * Math.max(20, selDist) * vFovTan));
            selectedPlaqueBox = {
              x1: sx - halfPx - 6,
              y1: sy - halfPx - 6,
              x2: sx + halfPx + 6,
              y2: sy + halfPx + 4,
            };
          }
        }
      }

      let poolIdx = 0;
      const maxLabelsNow = hasFocus || hasPath ? 32 : 22;
      const topSafeY = hasFocus || hasPath ? 150 : 128;

      for (let i = 0; i < candidates.length && poolIdx < maxLabelsNow; i++) {
        const cand = candidates[i];
        projVec.copy(cand.pos).project(camera);
        if (projVec.z < -1 || projVec.z > 1) continue;

        const sx = (projVec.x * 0.5 + 0.5) * cw;
        const sy = (-projVec.y * 0.5 + 0.5) * ch;
        if (sx < 48 || sx > cw - 60 || sy < topSafeY || sy > ch - 46) continue;
        // Clear bottom-left stats/controls dock and bottom-right legend pills
        if (sx < 650 && sy > ch - 96) continue;
        if (!hasFocus && sx > cw - 610 && sy > ch - 66) continue;

        const isSelectedSelf = cand.node.id === vs.selectedNodeId;
        const maxAng = isSelectedSelf ? 0.092 : 0.068;
        const rawCardSize = st.nodeSizes.get(cand.node.id) ?? getNodeCardSize(cand.node);
        const cardSize = Math.min(rawCardSize, Math.max(3.2, cand.dist * maxAng));
        const halfPx = (cardSize * ch) / (4 * Math.max(20, cand.dist) * vFovTan);
        const labelTopY = sy + Math.max(6, halfPx) + 4;

        const candLabel = getLocalizedNodeLabel(cand.node, langRef.current);
        const approxW = Math.min(250, candLabel.length * 7.6 + 28);
        const approxH = 24;
        const bx1 = sx - approxW / 2 - 4;
        const by1 = labelTopY - 2;
        const bx2 = sx + approxW / 2 + 4;
        const by2 = labelTopY + approxH + 2;

        if (!isSelectedSelf && selectedPlaqueBox) {
          if (
            !(
              bx2 < selectedPlaqueBox.x1 ||
              bx1 > selectedPlaqueBox.x2 ||
              by2 < selectedPlaqueBox.y1 ||
              by1 > selectedPlaqueBox.y2
            )
          ) {
            continue;
          }
        }

        let overlaps = false;
        if (cand.priority < 990) {
          for (const box of occupied) {
            if (!(bx2 < box.x1 || bx1 > box.x2 || by2 < box.y1 || by1 > box.y2)) {
              overlaps = true;
              break;
            }
          }
        }
        if (overlaps) continue;
        occupied.push({ x1: bx1, y1: by1, x2: bx2, y2: by2, node: cand.node });

        const isPinned = cand.priority >= 620;
        const labelOpacity = isPinned
          ? THREE.MathUtils.clamp(0.75 + 0.25 * cand.shade, 0.72, 1.0)
          : THREE.MathUtils.clamp((cand.shade - 0.35) / 0.55, 0.28, 0.98);
        const labelScale = isPinned ? 1.0 : THREE.MathUtils.lerp(0.88, 1.0, cand.shade);

        const div = labelDivRefs.current[poolIdx];
        const dot = labelDotRefs.current[poolIdx];
        const txt = labelTextRefs.current[poolIdx];
        if (div && dot && txt) {
          div.style.transform = `translate3d(${Math.round(sx)}px, ${Math.round(labelTopY)}px, 0) translate(-50%, 0) scale(${labelScale.toFixed(3)})`;
          div.style.opacity = labelOpacity.toFixed(2);
          dot.style.backgroundColor = ENTITY_META[cand.node.type].color;
          if (txt.textContent !== candLabel) txt.textContent = candLabel;
        }
        poolIdx++;
      }

      st.labelBoxes = occupied;

      for (let j = poolIdx; j < LABEL_POOL_SIZE; j++) {
        const div = labelDivRefs.current[j];
        if (div && div.style.opacity !== "0") div.style.opacity = "0";
      }
    };

    rafId = requestAnimationFrame(animate);

    return () => {
      disposed = true;
      clearHoverTimer();
      cancelAnimationFrame(rafId);
      ro.disconnect();
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("pointerup", onGlobalPointerUp);
      window.removeEventListener("pointercancel", onGlobalPointerUp);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      renderer.domElement.removeEventListener("pointerleave", onPointerLeave);
      renderer.domElement.removeEventListener("dblclick", onDblClick);
      controls.removeEventListener("start", cancelFlight);
      controls.dispose();
      glowTex.dispose();
      if (atlasTexture) atlasTexture.dispose();
      iconGeo.dispose();
      iconMat.dispose();
      bgLines.geometry.dispose();
      bgLineMat.dispose();
      activeEdgeGeo.dispose();
      activeEdgeMat.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
      threeRef.current = null;
    };
  }, [graphData, onSelectNode, onSetIsolation, refreshVisualHighlights, uploadSortedInstances]);

  const suppressNextResetRef = useRef(false);

  // Rebuild visible 3D nodes & edges when structural filters / scope / layoutMode / isolation change
  useEffect(() => {
    const st = threeRef.current;
    if (!st) return;

    const visNodes: GraphNode[] = [];
    const addedSet = new Set<string>();

    for (const nd of graphData.nodes) {
      if (isolatedSet) {
        if (!isolatedSet.has(nd.id)) continue;
        if (nd.id !== isolation?.rootId) {
          if (!visibleTypes.has(nd.type)) continue;
          if (dlcFilter !== "all" && nd.dlc !== dlcFilter) continue;
        }
      } else {
        if (scope === "atlas" && nd.tier !== "atlas") continue;
        if (scope === "core" && nd.tier === "extended") continue;
        if (!visibleTypes.has(nd.type)) continue;
        if (dlcFilter !== "all" && nd.dlc !== dlcFilter) continue;
      }
      visNodes.push(nd);
      addedSet.add(nd.id);
    }

    // Positions: 3D radial constellation if isolated, else spacious expanded x3d/y3d/z3d or map3d + de-clumping
    const isoPositions =
      isolatedSet && isolation
        ? computeIsolationPositions3D(isolation.rootId, visNodes, adjacency, langRef.current)
        : null;

    st.nodePositions.clear();

    const galaxyBaseScale = scope === "extended" ? 1.82 : scope === "core" ? 1.54 : 1.3;

    for (const nd of visNodes) {
      let p: THREE.Vector3;
      if (isoPositions) {
        p = isoPositions.get(nd.id) ?? new THREE.Vector3(0, 0, 0);
      } else if (layoutMode === "map3d") {
        p = new THREE.Vector3(nd.mapX * 1.28, nd.mapY * 1.35, nd.mapZ * 1.28);
      } else {
        const r = Math.hypot(nd.x3d, nd.y3d, nd.z3d);
        // Open up the congested inner downtown cluster while keeping outer landmarks bounded
        const coreRelief = 1.0 + 0.34 * Math.exp(-r / 155);
        const s = galaxyBaseScale * coreRelief;
        p = new THREE.Vector3(nd.x3d * s, nd.y3d * s, nd.z3d * s);
      }
      st.nodePositions.set(nd.id, p);
    }

    if (!isoPositions) {
      const clearance = scope === "extended" ? 1.18 : scope === "core" ? 1.32 : 1.48;
      declumpPositions3D(visNodes, st.nodePositions, selectedNodeId, clearance, 4);
    }

    // Collect all edges between added nodes; background loot edges are filtered dynamically in refreshVisualHighlights
    const visEdges: { id: string; source: string; target: string; type: EdgeType }[] = [];
    let activeEdgeDisplayCount = 0;
    for (const e of graphData.edges) {
      if (!visibleEdgeTypes.has(e.type)) continue;
      if (!addedSet.has(e.source) || !addedSet.has(e.target)) continue;
      visEdges.push(e);
      if (
        isolatedSet ||
        showBgLootEdges ||
        (e.type !== "location_item" && e.type !== "location_object")
      ) {
        activeEdgeDisplayCount++;
      }
    }

    st.visibleNodes = visNodes;
    st.visibleEdges = visEdges;
    st.showBgLootEdges = showBgLootEdges;
    setVisibleStats({ nodes: visNodes.length, edges: activeEdgeDisplayCount });

    // Environment grid visibility by mode
    const gridMats = Array.isArray(st.gridHelper.material)
      ? st.gridHelper.material
      : [st.gridHelper.material];
    for (const gm of gridMats) {
      gm.opacity = isolatedSet ? 0.14 : layoutMode === "map3d" ? 0.4 : 0.18;
    }
    st.stratumRings.visible = !isolatedSet && layoutMode === "galaxy";
    st.radarRings.visible = layoutMode === "map3d" || Boolean(isolatedSet);

    refreshVisualHighlights();
    if (suppressNextResetRef.current) {
      suppressNextResetRef.current = false;
    } else {
      resetCamera();
    }
  }, [
    graphData,
    scope,
    layoutMode,
    dlcFilter,
    visibleTypes,
    visibleEdgeTypes,
    showBgLootEdges,
    isolatedSet,
    isolation,
    adjacency,
    refreshVisualHighlights,
    resetCamera,
  ]);

  // Refresh highlights when selection / hover / path / atlas / depth changes
  useEffect(() => {
    refreshVisualHighlights();
  }, [hoveredNodeId, hoveredEdge, selectedNodeId, shortestPath, iconAtlas, depthMode, refreshVisualHighlights]);

  // Ensure node is included in current scope/type filters before flying to it
  const ensureNodeVisible = useCallback(
    (nd: GraphNode) => {
      if (!isolatedSet) {
        let changed = false;
        if (nd.tier === "extended" && scope !== "extended") {
          setScope("extended");
          changed = true;
        } else if (nd.tier === "core" && scope === "atlas") {
          setScope("core");
          changed = true;
        }
        if (!visibleTypes.has(nd.type)) {
          setVisibleTypes((prev) => new Set([...prev, nd.type]));
          changed = true;
        }
        if (dlcFilter !== "all" && nd.dlc !== dlcFilter) {
          setDlcFilter("all");
          changed = true;
        }
        if (changed) {
          suppressNextResetRef.current = true;
        }
      }
    },
    [isolatedSet, scope, visibleTypes, dlcFilter]
  );

  // Fly camera to a specific node smoothly (used for initial jump / search / landmarks)
  const flyToNode = useCallback(
    (nodeId: string, recordHistory = true) => {
      const nd = nodeMap.get(nodeId);
      if (!nd) return;

      ensureNodeVisible(nd);
      if (recordHistory && selectedNodeId && selectedNodeId !== nodeId) {
        setFlightHistory((prev) => [...prev.slice(-14), selectedNodeId]);
      }
      onSelectNode(nodeId);

      setTimeout(() => {
        const st = threeRef.current;
        if (!st) return;
        const target = st.nodePositions.get(nodeId);
        if (!target) return;
        const framingDist = THREE.MathUtils.clamp(
          132 + Math.sqrt(Math.max(1, nd.degree)) * 4.6,
          135,
          205
        );
        const offset = st.camera.position.clone().sub(st.controls.target);
        if (offset.length() < 1) offset.set(0, 56, 145);
        offset.setLength(framingDist);
        if (Math.hypot(offset.x, offset.z) < 52) {
          offset.x += 52;
          offset.setLength(framingDist);
        }
        flyCameraTo(target.clone().add(offset), target, 540);
      }, 45);
    },
    [nodeMap, ensureNodeVisible, selectedNodeId, onSelectNode, flyCameraTo]
  );

  // True 3D Corridor Flight along a connection from fromId -> toId!
  const flyAlongEdge = useCallback(
    (
      fromId: string,
      toId: string,
      opts?: { edgeId?: string | null; recordHistory?: boolean; durationOverride?: number }
    ) => {
      const fromNd = nodeMap.get(fromId);
      const toNd = nodeMap.get(toId);
      if (!toNd) return;
      if (!fromNd || fromId === toId) {
        flyToNode(toId, opts?.recordHistory ?? true);
        return;
      }

      ensureNodeVisible(fromNd);
      ensureNodeVisible(toNd);

      if ((opts?.recordHistory ?? true) && fromId !== toId) {
        setFlightHistory((prev) =>
          prev[prev.length - 1] === fromId ? prev : [...prev.slice(-14), fromId]
        );
      }

      onSelectNode(toId);

      // Find matching edge id if not explicitly provided so the beam lights up during flight
      let resolvedEdgeId = opts?.edgeId ?? null;
      if (!resolvedEdgeId) {
        const nb = (adjacency.get(fromId) ?? []).find((x) => x.node.id === toId);
        if (nb) resolvedEdgeId = nb.edge.id;
      }

      setTimeout(() => {
        const st = threeRef.current;
        if (!st) return;
        const pStart = st.nodePositions.get(fromId);
        const pEnd = st.nodePositions.get(toId);
        if (!pStart || !pEnd) return;

        const dir = pEnd.clone().sub(pStart);
        const linkLen = dir.length();
        if (linkLen < 4) {
          flyToNode(toId, false);
          return;
        }
        dir.divideScalar(linkLen);

        // Compute perpendicular "cockpit above-link" vector so the glowing connection beam
        // stretches visibly across the lower center of the viewport straight into pEnd
        const upPerp = new THREE.Vector3(0, 1, 0).addScaledVector(dir, -dir.y);
        if (upPerp.lengthSq() < 0.08) {
          upPerp.set(0, 0, 1).addScaledVector(dir, -dir.z);
        }
        upPerp.normalize();

        const hubSpreadDist = THREE.MathUtils.clamp(
          122 + Math.sqrt(Math.max(1, toNd.degree)) * 4.5,
          126,
          198
        );
        const stopDist = THREE.MathUtils.clamp(
          Math.max(linkLen * 0.52, hubSpreadDist),
          122,
          205
        );
        const endCamPos = pEnd
          .clone()
          .addScaledVector(dir, -stopDist)
          .addScaledVector(upPerp, 36);

        // Prevent OrbitControls vertical gimbal lock if link is nearly vertical
        const horiz = Math.hypot(endCamPos.x - pEnd.x, endCamPos.z - pEnd.z);
        if (horiz < 46) {
          const radialX = endCamPos.x - pEnd.x || 1;
          const radialZ = endCamPos.z - pEnd.z || 0.5;
          const rLen = Math.hypot(radialX, radialZ);
          endCamPos.x = pEnd.x + (radialX / rLen) * 46;
          endCamPos.z = pEnd.z + (radialZ / rLen) * 46;
        }

        const p0 = st.camera.position.clone();
        const p3 = endCamPos;
        const p1 = new THREE.Vector3();
        const p2 = new THREE.Vector3();

        if (linkLen <= stopDist) {
          p1.lerpVectors(p0, p3, 0.36).addScaledVector(upPerp, 14);
          p2.lerpVectors(p0, p3, 0.72).addScaledVector(upPerp, 8);
        } else {
          const corridorStart = pStart.clone().addScaledVector(upPerp, 28);
          if (p0.distanceTo(pStart) > 220) {
            p1.lerpVectors(p0, corridorStart, 0.65);
          } else {
            p1.copy(corridorStart);
          }
          p2.lerpVectors(corridorStart, p3, 0.64);
        }

        const t0 = st.controls.target.clone();
        const t1 = pStart.clone().lerp(pEnd, 0.38);
        const t2 = pStart.clone().lerp(pEnd, 0.86);
        const t3 = pEnd.clone();

        const duration =
          opts?.durationOverride ?? THREE.MathUtils.clamp(540 + linkLen * 1.35, 640, 1200);

        st.flight.active = true;
        st.flight.isCorridor = true;
        st.flight.edgeId = resolvedEdgeId;
        st.flight.startTime = performance.now();
        st.flight.duration = duration;
        st.flight.p0.copy(p0);
        st.flight.p1.copy(p1);
        st.flight.p2.copy(p2);
        st.flight.p3.copy(p3);
        st.flight.t0.copy(t0);
        st.flight.t1.copy(t1);
        st.flight.t2.copy(t2);
        st.flight.t3.copy(t3);
        st.flight.linkStart.copy(pStart);
        st.flight.linkEnd.copy(pEnd);
        st.flightOrb.position.copy(pStart);
        st.flightOrb.visible = true;

        refreshVisualHighlights();
      }, 45);
    },
    [nodeMap, adjacency, ensureNodeVisible, flyToNode, onSelectNode, refreshVisualHighlights]
  );

  // Retrace flight back along the previous connection
  const goBackAlongHistory = useCallback(() => {
    stopPathTour();
    if (flightHistory.length === 0) return;
    const prevId = flightHistory[flightHistory.length - 1];
    setFlightHistory((h) => h.slice(0, -1));
    if (selectedNodeId && selectedNodeId !== prevId) {
      flyAlongEdge(selectedNodeId, prevId, { recordHistory: false });
    } else {
      flyToNode(prevId, false);
    }
  }, [flightHistory, selectedNodeId, flyAlongEdge, flyToNode, stopPathTour]);

  // Automated multi-hop flight tour along shortestPath chain A -> ... -> B
  const startPathTour = useCallback(() => {
    const chain = shortestPath.nodeIds;
    if (chain.length < 2) return;
    stopPathTour();
    setIsTouringPath(true);

    // Ensure all chain nodes are visible
    for (const id of chain) {
      const nd = nodeMap.get(id);
      if (nd) ensureNodeVisible(nd);
    }

    flyToNode(chain[0], false);

    let stepIdx = 0;
    const runNextHop = () => {
      if (stepIdx >= chain.length - 1) {
        setIsTouringPath(false);
        tourTimerRef.current = null;
        return;
      }
      const a = chain[stepIdx];
      const b = chain[stepIdx + 1];
      stepIdx++;
      const hopDur = 920;
      flyAlongEdge(a, b, { recordHistory: true, durationOverride: hopDur });
      tourTimerRef.current = window.setTimeout(runNextHop, hopDur + 260);
    };

    tourTimerRef.current = window.setTimeout(runNextHop, 640);
  }, [shortestPath.nodeIds, stopPathTour, nodeMap, ensureNodeVisible, flyToNode, flyAlongEdge]);

  useEffect(() => {
    return () => {
      if (tourTimerRef.current !== null) window.clearTimeout(tourTimerRef.current);
    };
  }, []);

  // Keep imperative WebGL event handlers wired to latest navigation state
  navHandlersRef.current = {
    onClickNode: (clickedId: string) => {
      stopPathTour();
      if (!selectedNodeId) {
        flyToNode(clickedId, false);
        return;
      }
      if (clickedId === selectedNodeId) {
        flyToNode(clickedId, false);
        return;
      }
      if (neighborsOfFocus.has(clickedId)) {
        flyAlongEdge(selectedNodeId, clickedId, { recordHistory: true });
      } else {
        flyToNode(clickedId, true);
      }
    },
    onClickEdge: (edge: HoveredEdgeInfo) => {
      stopPathTour();
      flyAlongEdge(edge.fromId, edge.toId, { edgeId: edge.id, recordHistory: true });
    },
    onBack: goBackAlongHistory,
    onCancelTour: stopPathTour,
  };

  // Search autocomplete hits
  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return [];
    const hits: GraphNode[] = [];
    for (const n of graphData.nodes) {
      if (
        n.label.toLowerCase().includes(q) ||
        n.labelEn.toLowerCase().includes(q) ||
        n.edid.toLowerCase().includes(q) ||
        n.fid.toLowerCase().includes(q)
      ) {
        hits.push(n);
      }
    }
    const locale = lang === "en" ? "en" : "ru";
    hits.sort(
      (a, b) =>
        b.degree - a.degree ||
        getNodeLabel(a).localeCompare(getNodeLabel(b), locale)
    );
    return hits.slice(0, 14);
  }, [searchQuery, graphData.nodes, lang, getNodeLabel]);

  const pathStartCandidates = useMemo(() => {
    const q = pathStartQuery.trim().toLowerCase();
    if (!q) return [];
    return graphData.nodes
      .filter((n) => n.label.toLowerCase().includes(q) || n.labelEn.toLowerCase().includes(q))
      .slice(0, 8);
  }, [pathStartQuery, graphData.nodes]);

  const pathEndCandidates = useMemo(() => {
    const q = pathEndQuery.trim().toLowerCase();
    if (!q) return [];
    return graphData.nodes
      .filter((n) => n.label.toLowerCase().includes(q) || n.labelEn.toLowerCase().includes(q))
      .slice(0, 8);
  }, [pathEndQuery, graphData.nodes]);

  const toggleType = (t: EntityType) => {
    setVisibleTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) {
        if (next.size > 1) next.delete(t);
      } else {
        next.add(t);
      }
      return next;
    });
  };

  const toggleEdgeType = (et: EdgeType) => {
    setVisibleEdgeTypes((prev) => {
      const next = new Set(prev);
      if (next.has(et)) next.delete(et);
      else next.add(et);
      return next;
    });
  };

  const zoomStep = (factor: number) => {
    const st = threeRef.current;
    if (!st) return;
    const offset = st.camera.position.clone().sub(st.controls.target);
    const nextLen = THREE.MathUtils.clamp(offset.length() * factor, 30, 2200);
    offset.setLength(nextLen);
    flyCameraTo(st.controls.target.clone().add(offset), st.controls.target.clone(), 240);
  };

  const cycleDepthMode = () => {
    setDepthMode((prev) =>
      prev === "strong" ? "soft" : prev === "soft" ? "off" : "strong"
    );
  };

  const handleResetAll = () => {
    stopPathTour();
    onSetIsolation(null);
    onSelectNode(null);
    setFlightHistory([]);
    setScope("atlas");
    setDlcFilter("all");
    setDepthMode("strong");
    setVisibleTypes(new Set(ALL_TYPES));
    setVisibleEdgeTypes(new Set(ALL_EDGE_TYPES));
    setShowBgLootEdges(false);
    setPathStartId(null);
    setPathEndId(null);
    setPathStartQuery("");
    setPathEndQuery("");
    setShowFilters(false);
    setShowPathFinder(false);
    flyCameraTo(new THREE.Vector3(0, 175, 495), new THREE.Vector3(0, 0, 0), 480);
  };

  const hoveredNode = hoveredNodeId ? nodeMap.get(hoveredNodeId) ?? null : null;
  const selectedNode = selectedNodeId ? nodeMap.get(selectedNodeId) ?? null : null;
  const selectedNeighbors = selectedNodeId ? adjacency.get(selectedNodeId) ?? [] : [];
  const selectedWalkthrough = selectedNodeId
    ? walkthroughByNodeId.get(selectedNodeId)
    : undefined;

  const activeFiltersCount =
    (scope !== "atlas" ? 1 : 0) +
    (dlcFilter !== "all" ? 1 : 0) +
    (ALL_TYPES.length - visibleTypes.size) +
    (ALL_EDGE_TYPES.length - visibleEdgeTypes.size) +
    (showBgLootEdges ? 1 : 0);

  const quickJumpLandmarks = useMemo(() => {
    const targets: { match: (n: GraphNode) => boolean }[] = [
      { match: (n) => n.edid === "MS11" || n.label === "Сила Атома" },
      { match: (n) => n.edid === "MQ01" || n.edid === "CG04" || n.label === "Побег!" },
      { match: (n) => (n.edid.toLowerCase().includes("vault101") || n.label.includes("Убежище 101")) && n.type === "location" },
      {
        match: (n) =>
          n.label === "Мегатонна" || (n.labelEn === "Megaton" && n.subtype === "marker"),
      },
      {
        match: (n) =>
          n.edid.toLowerCase().includes("threedog") || n.label.includes("Тридогнайт"),
      },
      { match: (n) => n.edid === "Fawkes" || n.edid === "MQ08Fawkes" || n.label === "Фокс" },
      { match: (n) => n.edid === "Weap10mmPistol" || n.label === "10-мм пистолет" },
    ];
    const picked: GraphNode[] = [];
    const usedIds = new Set<string>();
    for (const t of targets) {
      const found = graphData.nodes.find((n) => !usedIds.has(n.id) && t.match(n));
      if (found) {
        picked.push(found);
        usedIds.add(found.id);
      }
    }
    if (picked.length < 6) {
      const sorted = [...graphData.nodes]
        .filter((n) => !usedIds.has(n.id) && !/^(DC\d|test|dummy)/i.test(n.label))
        .sort((a, b) => b.degree - a.degree);
      for (const n of sorted) {
        if (picked.length >= 6) break;
        picked.push(n);
        usedIds.add(n.id);
      }
    }
    return picked;
  }, [graphData.nodes]);

  return (
    <div className="relative flex h-full w-full overflow-hidden bg-[#050a08]">
      {/* Main 3D Viewport */}
      <div className="relative flex-1 overflow-hidden">
        <div ref={mountRef} className="h-full w-full" />

        {/* Projected 3D HTML Labels Pool */}
        <div className="pointer-events-none absolute inset-0 z-10 overflow-hidden">
          {Array.from({ length: LABEL_POOL_SIZE }).map((_, i) => (
            <div
              key={i}
              ref={(el) => {
                labelDivRefs.current[i] = el;
              }}
              style={{ opacity: 0 }}
              className="absolute left-0 top-0 inline-flex max-w-[245px] items-center gap-1.5 whitespace-nowrap rounded-md border border-emerald-900/60 bg-[#07100c]/88 px-2 py-0.5 text-[11px] font-medium text-emerald-50 shadow-lg backdrop-blur-sm transition-opacity duration-100"
            >
              <span
                ref={(el) => {
                  labelDotRefs.current[i] = el;
                }}
                className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400"
              />
              <span
                ref={(el) => {
                  labelTextRefs.current[i] = el;
                }}
                className="truncate"
              />
            </div>
          ))}
        </div>

        {/* Floating Hover Tooltip (Node or Connection Beam) */}
        <div
          ref={tooltipRef}
          style={{ opacity: 0 }}
          className="pointer-events-none fixed left-0 top-0 z-40 max-w-xs rounded-lg border border-emerald-700/60 bg-[#08110d]/95 px-3 py-2 text-xs shadow-2xl backdrop-blur-md transition-opacity duration-150"
        >
          {hoveredNode ? (
            (() => {
              const hoveredLabel = getNodeLabel(hoveredNode);
              const isConnectedToSelected =
                selectedNodeId &&
                selectedNodeId !== hoveredNode.id &&
                neighborsOfFocus.has(hoveredNode.id);
              return (
                <div className="flex items-start gap-2.5">
                  <EntityIcon
                    iconKey={hoveredNode.icon}
                    type={hoveredNode.type}
                    label={hoveredLabel}
                    iconAtlas={iconAtlas}
                    size="md"
                  />
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex items-center gap-1.5 font-semibold text-emerald-50">
                      <span
                        className={`h-2 w-2 shrink-0 rounded-full ${ENTITY_META[hoveredNode.type].dotClass}`}
                      />
                      <span className="truncate">{hoveredLabel}</span>
                    </div>
                    <div className="text-[11px] text-emerald-400/85">
                      {getSubtypeLabel(hoveredNode.subtype, lang) ??
                        getEntitySingular(hoveredNode.type, lang)}{" "}
                      • {getDlcShort(hoveredNode.dlc, lang)}
                    </div>
                    <div className="font-mono text-[10px] text-amber-300/95">
                      {isConnectedToSelected
                        ? `→ ${t.graph.flyAlongLinkTitle} «${hoveredLabel}»`
                        : `${t.graph.linksPrefix} ${hoveredNode.degree} · ${t.graph.tooltipHint}`}
                    </div>
                  </div>
                </div>
              );
            })()
          ) : hoveredEdge ? (
            (() => {
              const fromNd = nodeMap.get(hoveredEdge.fromId);
              const toNd = nodeMap.get(hoveredEdge.toId);
              if (!fromNd || !toNd) return null;
              const em = EDGE_META[hoveredEdge.type];
              return (
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5 text-[11px] font-semibold text-amber-300">
                    <span
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ backgroundColor: em?.color ?? "#fbbf24" }}
                    />
                    <span>{getEdgeLabel(hoveredEdge.type, lang)}</span>
                  </div>
                  <div className="flex items-center gap-1.5 font-medium text-emerald-50">
                    <span className="max-w-[110px] truncate opacity-80">
                      {getNodeLabel(fromNd)}
                    </span>
                    <ArrowRight className="h-3.5 w-3.5 shrink-0 text-amber-400" />
                    <span className="max-w-[135px] truncate font-semibold text-amber-200">
                      {getNodeLabel(toNd)}
                    </span>
                  </div>
                  <div className="font-mono text-[10px] text-emerald-400/90">
                    {t.graph.edgeTooltipFlyHint}
                  </div>
                </div>
              );
            })()
          ) : null}
        </div>

        {/* Unified Top Floating HUD Stack (never overlaps across rows!) */}
        <div className="pointer-events-none absolute left-3 right-3 top-3 z-30 flex flex-col items-start gap-2">
          <div className="flex w-full flex-wrap items-start justify-between gap-2">
            <div className="pointer-events-auto relative flex flex-wrap items-center gap-2 rounded-xl border border-emerald-900/60 bg-[#09120e]/88 p-1.5 shadow-2xl backdrop-blur-md">
              {/* Search */}
              <div className="relative w-56 sm:w-64">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-emerald-500" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onFocus={() => setSearchFocused(true)}
                  onBlur={() => setTimeout(() => setSearchFocused(false), 180)}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t.graph.searchPlaceholder}
                  className="w-full rounded-lg border border-emerald-900/70 bg-[#050a08] py-1.5 pl-8 pr-7 text-xs text-emerald-100 placeholder-emerald-600 focus:border-emerald-400 focus:outline-none"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-emerald-500 hover:text-emerald-200"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}

                {searchFocused && searchResults.length > 0 && (
                  <div className="absolute left-0 right-0 top-full z-50 mt-1.5 max-h-80 overflow-y-auto rounded-xl border border-emerald-800/70 bg-[#09120e]/98 p-1 shadow-2xl">
                    {searchResults.map((hit) => {
                      const hitLabel = getNodeLabel(hit);
                      const hitAlt = getNodeAltLabel(hit);
                      return (
                        <button
                          key={hit.id}
                          onMouseDown={(e) => {
                            e.preventDefault();
                            flyToNode(hit.id);
                            setSearchQuery(hitLabel);
                            setSearchFocused(false);
                          }}
                          className="flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs hover:bg-emerald-950/75"
                        >
                          <div className="flex min-w-0 items-center gap-2">
                            <EntityIcon
                              iconKey={hit.icon}
                              type={hit.type}
                              label={hitLabel}
                              iconAtlas={iconAtlas}
                              size="sm"
                            />
                            <div className="min-w-0">
                              <div className="truncate font-medium text-emerald-50">
                                {hitLabel}
                              </div>
                              <div className="truncate font-mono text-[10px] text-emerald-500/80">
                                {hitAlt ? `${hitAlt} • ` : ""}
                                {hit.edid}
                              </div>
                            </div>
                          </div>
                          <span className="shrink-0 font-mono text-[10px] text-emerald-400">
                            {hit.degree}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* 3D Mode Switch */}
              <div className="flex items-center rounded-lg border border-emerald-900/70 bg-[#050a08] p-0.5 text-xs">
                <button
                  onClick={() => setLayoutMode("galaxy")}
                  className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition ${layoutMode === "galaxy"
                    ? "bg-emerald-500/20 text-emerald-200"
                    : "text-emerald-500 hover:text-emerald-300"
                    }`}
                >
                  <Orbit className="h-3.5 w-3.5" />
                  {t.graph.modeGalaxy}
                </button>
                <button
                  onClick={() => setLayoutMode("map3d")}
                  className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition ${layoutMode === "map3d"
                    ? "bg-sky-500/20 text-sky-200"
                    : "text-emerald-500 hover:text-emerald-300"
                    }`}
                >
                  <Compass className="h-3.5 w-3.5" />
                  {t.graph.modeMap}
                </button>
              </div>

              {/* Direct Density Switcher */}
              <div
                className="flex items-center rounded-lg border border-emerald-900/70 bg-[#050a08] p-0.5 text-xs"
                title={t.graph.densityTitle}
              >
                {(
                  [
                    {
                      id: "atlas" as GraphScope,
                      label: t.graph.scopeAtlasShort,
                      title: `${t.graph.scopeAtlasTitle} (~${graphData.meta.atlasNodes ?? 420})`,
                    },
                    {
                      id: "core" as GraphScope,
                      label: t.graph.scopeCoreShort,
                      title: `${t.graph.scopeCoreTitle} (~${graphData.meta.coreNodes})`,
                    },
                    {
                      id: "extended" as GraphScope,
                      label: t.graph.scopeExtendedShort,
                      title: `${t.graph.scopeExtendedTitle} (${graphData.meta.totalNodes})`,
                    },
                  ] as const
                ).map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => {
                      if (isolation) onSetIsolation(null);
                      setScope(opt.id);
                    }}
                    title={opt.title}
                    className={`rounded-md px-2 py-1 font-medium transition ${scope === opt.id && !isolation
                      ? "bg-emerald-500/20 text-emerald-200"
                      : "text-emerald-500 hover:text-emerald-300"
                      }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>

              {/* Unified Filters Popover Button */}
              <div className="relative">
                <button
                  onClick={() => {
                    setShowFilters((v) => !v);
                    setShowPathFinder(false);
                  }}
                  className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition ${showFilters || activeFiltersCount > 0
                    ? "border-emerald-400/60 bg-emerald-500/18 text-emerald-100"
                    : "border-emerald-900/70 bg-[#050a08] text-emerald-300 hover:border-emerald-600"
                    }`}
                >
                  <SlidersHorizontal className="h-3.5 w-3.5" />
                  <span>{t.graph.filtersBtn}</span>
                  {activeFiltersCount > 0 && (
                    <span className="rounded bg-amber-500/25 px-1.5 py-0.2 font-mono text-[10px] text-amber-200">
                      {activeFiltersCount}
                    </span>
                  )}
                </button>

                {showFilters && (
                  <div className="absolute left-0 top-full z-50 mt-2 w-80 sm:w-96 rounded-2xl border border-emerald-800/70 bg-[#08110d]/96 p-4 shadow-2xl backdrop-blur-xl space-y-4">
                    {/* Density Presets */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-emerald-400">
                        <span className="flex items-center gap-1.5">
                          <Layers className="h-3.5 w-3.5" /> {t.graph.graphDetailHeading}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-1.5 text-xs">
                        {[
                          {
                            id: "atlas" as GraphScope,
                            label: t.graph.scopeAtlasLong,
                            sub: `~${graphData.meta.atlasNodes ?? 420}`,
                          },
                          {
                            id: "core" as GraphScope,
                            label: t.graph.scopeCoreLong,
                            sub: `~${graphData.meta.coreNodes}`,
                          },
                          {
                            id: "extended" as GraphScope,
                            label: t.graph.scopeExtendedLong,
                            sub: `${graphData.meta.totalNodes}`,
                          },
                        ].map((opt) => (
                          <button
                            key={opt.id}
                            onClick={() => setScope(opt.id)}
                            className={`rounded-lg border px-2 py-1.5 text-left transition ${scope === opt.id
                              ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-100"
                              : "border-emerald-900/60 bg-[#050a08] text-emerald-400 hover:border-emerald-700"
                              }`}
                          >
                            <div className="font-medium leading-tight">{opt.label}</div>
                            <div className="mt-0.5 font-mono text-[10px] opacity-75">
                              {opt.sub} {t.graph.nodesUnit}
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* DLC Filter */}
                    <div className="space-y-1.5">
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400">
                        {t.graph.moduleHeading}
                      </div>
                      <select
                        value={dlcFilter}
                        onChange={(e) => setDlcFilter(e.target.value as DlcId | "all")}
                        className="w-full rounded-lg border border-emerald-900/70 bg-[#050a08] px-2.5 py-1.5 text-xs text-emerald-100 focus:border-emerald-400 focus:outline-none"
                      >
                        <option value="all">{t.graph.allModulesOption}</option>
                        {(Object.keys(DLC_META) as DlcId[]).map((id) => (
                          <option key={id} value={id}>
                            {getDlcLabel(id, lang)}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Background loot edges toggle */}
                    <label className="flex cursor-pointer items-center justify-between rounded-lg border border-emerald-900/50 bg-[#050a08] px-3 py-2 text-xs">
                      <span className="text-emerald-200">{t.graph.bgLootEdgesLabel}</span>
                      <input
                        type="checkbox"
                        checked={showBgLootEdges}
                        onChange={(e) => setShowBgLootEdges(e.target.checked)}
                        className="accent-emerald-400"
                      />
                    </label>

                    {/* Edge Types */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-emerald-400">
                        <span>{t.graph.edgeTypesHeading}</span>
                        <button
                          onClick={() => setVisibleEdgeTypes(new Set(ALL_EDGE_TYPES))}
                          className="text-[11px] font-normal normal-case text-emerald-300 underline"
                        >
                          {t.graph.enableAll}
                        </button>
                      </div>
                      <div className="grid max-h-40 grid-cols-1 gap-1 overflow-y-auto pr-1">
                        {ALL_EDGE_TYPES.map((et) => {
                          const em = EDGE_META[et];
                          return (
                            <label
                              key={et}
                              className="flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 text-xs hover:bg-emerald-950/50"
                            >
                              <input
                                type="checkbox"
                                checked={visibleEdgeTypes.has(et)}
                                onChange={() => toggleEdgeType(et)}
                                className="accent-emerald-400"
                              />
                              <span
                                className="h-2 w-2 rounded-full"
                                style={{ backgroundColor: em.color }}
                              />
                              <span className="truncate text-emerald-100">
                                {getEdgeLabel(et, lang)}
                              </span>
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Shortest Path Finder Toggle */}
              <button
                onClick={() => {
                  setShowPathFinder((v) => !v);
                  setShowFilters(false);
                }}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition ${showPathFinder || shortestPath.nodeIds.length > 0
                  ? "border-amber-400/60 bg-amber-500/20 text-amber-200"
                  : "border-emerald-900/70 bg-[#050a08] text-emerald-300 hover:border-emerald-600"
                  }`}
              >
                <GitFork className="h-3.5 w-3.5" />
                {t.graph.pathFinderBtn}
              </button>
            </div>

            {/* Active Isolation Pill (when no node HUD row is active) */}
            {isolation && !selectedNode && (() => {
              const isoNode = nodeMap.get(isolation.rootId);
              const isoLabel = isoNode ? getNodeLabel(isoNode) : isolation.rootId;
              return (
                <div className="pointer-events-auto flex items-center gap-2 rounded-xl border border-sky-400/50 bg-sky-950/85 px-3 py-1.5 text-xs text-sky-100 shadow-xl backdrop-blur-md">
                  <Focus className="h-3.5 w-3.5 text-sky-300" />
                  <span>
                    {t.graph.isolationPrefix} <strong>{isoLabel}</strong>
                  </span>
                  <button
                    onClick={() =>
                      onSetIsolation({
                        rootId: isolation.rootId,
                        hops: isolation.hops === 1 ? 2 : 1,
                      })
                    }
                    className="rounded border border-sky-400/40 bg-sky-500/20 px-2 py-0.5 font-mono text-[10px] hover:bg-sky-500/35"
                  >
                    {isolation.hops}{" "}
                    {isolation.hops === 1 ? t.graph.hopSingular : t.graph.hopPlural}
                  </button>
                  <button
                    onClick={() => onSetIsolation(null)}
                    className="rounded border border-sky-400/40 bg-black/30 px-2 py-0.5 text-[10px] hover:bg-black/50"
                  >
                    {t.graph.exitIsolation}
                  </button>
                </div>
              );
            })()}

            {/* Quick-Jump Landmark Bar */}
            {!selectedNode && !showPathFinder && quickJumpLandmarks.length > 0 && (
              <div className="pointer-events-auto hidden max-w-full flex-wrap items-center gap-1.5 rounded-xl border border-emerald-900/55 bg-[#09120e]/85 px-2.5 py-1.5 text-xs shadow-xl backdrop-blur-md md:flex">
                <span className="mr-0.5 text-[11px] font-medium text-emerald-400/90">
                  {t.graph.quickJumpLabel}
                </span>
                {quickJumpLandmarks.map((lm) => {
                  const m = ENTITY_META[lm.type];
                  const lmLabel = getNodeLabel(lm);
                  const lmSub = getSubtypeLabel(lm.subtype, lang) ?? getEntitySingular(lm.type, lang);
                  return (
                    <button
                      key={lm.id}
                      type="button"
                      onClick={() => flyToNode(lm.id)}
                      className={`inline-flex items-center gap-1.5 rounded-lg border px-2 py-0.5 text-[11px] font-medium transition hover:brightness-125 ${m.bgClass} ${m.borderClass} ${m.textClass}`}
                      title={`${t.graph.flyToTitle} "${lmLabel}" (${lmSub})`}
                    >
                      <EntityIcon
                        iconKey={lm.icon}
                        type={lm.type}
                        label={lmLabel}
                        iconAtlas={iconAtlas}
                        size="sm"
                      />
                      <span className="max-w-[140px] truncate">{lmLabel}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Row 2A: Shortest Path Drawer */}
          {showPathFinder && (
            <div className="pointer-events-auto w-[min(92vw,720px)] rounded-xl border border-amber-500/40 bg-[#09120e]/95 p-3 shadow-2xl backdrop-blur-md space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="flex items-center gap-1.5 text-xs font-semibold text-amber-300">
                  <GitFork className="h-3.5 w-3.5" /> {t.graph.pathHeading}
                </span>

                <div className="relative min-w-[180px] flex-1">
                  <input
                    type="text"
                    value={pathStartQuery}
                    onChange={(e) => {
                      setPathStartQuery(e.target.value);
                      if (pathStartId) setPathStartId(null);
                    }}
                    placeholder={t.graph.pointAPlaceholder}
                    className="w-full rounded border border-emerald-900/70 bg-[#050a08] px-2.5 py-1 text-xs text-emerald-100 placeholder-emerald-600 focus:border-amber-400 focus:outline-none"
                  />
                  {pathStartCandidates.length > 0 && !pathStartId && (
                    <div className="absolute left-0 right-0 top-full z-40 mt-1 max-h-48 overflow-y-auto rounded-lg border border-emerald-800 bg-[#09120e] p-1 shadow-xl">
                      {pathStartCandidates.map((c) => {
                        const cLabel = getNodeLabel(c);
                        return (
                          <button
                            key={c.id}
                            onClick={() => {
                              setPathStartId(c.id);
                              setPathStartQuery(cLabel);
                            }}
                            className="block w-full truncate rounded px-2 py-1 text-left text-xs text-emerald-100 hover:bg-emerald-950"
                          >
                            {cLabel} ({getEntitySingular(c.type, lang)})
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>

                <span className="text-xs text-amber-400">→</span>

                <div className="relative min-w-[180px] flex-1">
                  <input
                    type="text"
                    value={pathEndQuery}
                    onChange={(e) => {
                      setPathEndQuery(e.target.value);
                      if (pathEndId) setPathEndId(null);
                    }}
                    placeholder={t.graph.pointBPlaceholder}
                    className="w-full rounded border border-emerald-900/70 bg-[#050a08] px-2.5 py-1 text-xs text-emerald-100 placeholder-emerald-600 focus:border-amber-400 focus:outline-none"
                  />
                  {pathEndCandidates.length > 0 && !pathEndId && (
                    <div className="absolute left-0 right-0 top-full z-40 mt-1 max-h-48 overflow-y-auto rounded-lg border border-emerald-800 bg-[#09120e] p-1 shadow-xl">
                      {pathEndCandidates.map((c) => {
                        const cLabel = getNodeLabel(c);
                        return (
                          <button
                            key={c.id}
                            onClick={() => {
                              setPathEndId(c.id);
                              setPathEndQuery(cLabel);
                            }}
                            className="block w-full truncate rounded px-2 py-1 text-left text-xs text-emerald-100 hover:bg-emerald-950"
                          >
                            {cLabel} ({getEntitySingular(c.type, lang)})
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>

                <button
                  onClick={() => {
                    stopPathTour();
                    setPathStartId(null);
                    setPathEndId(null);
                    setPathStartQuery("");
                    setPathEndQuery("");
                    setShowPathFinder(false);
                  }}
                  className="rounded border border-emerald-800 px-2 py-1 text-xs text-emerald-400 hover:text-emerald-200"
                >
                  {t.graph.close}
                </button>
              </div>

              {pathStartId && pathEndId && (
                <div className="flex flex-wrap items-center gap-1.5 text-xs">
                  {shortestPath.nodeIds.length > 0 ? (
                    <>
                      <button
                        type="button"
                        onClick={isTouringPath ? stopPathTour : startPathTour}
                        className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-0.5 text-[11px] font-semibold transition ${isTouringPath
                          ? "border-rose-400/60 bg-rose-500/20 text-rose-200"
                          : "border-amber-400/60 bg-amber-500/25 text-amber-100 hover:bg-amber-500/35"
                          }`}
                      >
                        {isTouringPath ? (
                          <>
                            <Pause className="h-3 w-3" />
                            {t.graph.stopFlightBtn}
                          </>
                        ) : (
                          <>
                            <Navigation className="h-3 w-3" />
                            {t.graph.flyPathBtn}
                          </>
                        )}
                      </button>
                      <span className="font-medium text-amber-300">
                        {t.graph.chainLabel} ({shortestPath.nodeIds.length - 1} {t.graph.stepsWord}):
                      </span>
                      {shortestPath.nodeIds.map((nid, idx) => {
                        const nd = nodeMap.get(nid);
                        if (!nd) return null;
                        const m = ENTITY_META[nd.type];
                        const prevNid = idx > 0 ? shortestPath.nodeIds[idx - 1] : null;
                        return (
                          <React.Fragment key={nid}>
                            {idx > 0 && <span className="text-amber-500">→</span>}
                            <button
                              onClick={() => {
                                stopPathTour();
                                if (selectedNodeId && selectedNodeId !== nid) {
                                  flyAlongEdge(selectedNodeId, nid);
                                } else if (prevNid) {
                                  flyAlongEdge(prevNid, nid);
                                } else {
                                  flyToNode(nid);
                                }
                              }}
                              className={`rounded border px-2 py-0.5 text-[11px] transition hover:brightness-125 ${m.bgClass} ${m.borderClass} ${m.textClass}`}
                            >
                              {getNodeLabel(nd)}
                            </button>
                          </React.Fragment>
                        );
                      })}
                    </>
                  ) : (
                    <span className="text-rose-300">{t.graph.noPathFound}</span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Row 2B: Unified Isolation Badge + Link-Flight & History HUD Bar */}
          {selectedNode && !showPathFinder && (
            <div className="pointer-events-auto flex max-w-full flex-wrap items-center gap-1.5 rounded-xl border border-emerald-800/65 bg-[#08120e]/92 px-2.5 py-1.5 text-xs shadow-xl backdrop-blur-md">
              {isolation && (
                <div className="mr-1 inline-flex items-center gap-1.5 rounded-lg border border-sky-400/45 bg-sky-950/85 px-2 py-0.5 text-[11px] text-sky-100">
                  <Focus className="h-3 w-3 text-sky-300" />
                  <button
                    type="button"
                    onClick={() =>
                      onSetIsolation({
                        rootId: isolation.rootId,
                        hops: isolation.hops === 1 ? 2 : 1,
                      })
                    }
                    className="rounded bg-sky-500/25 px-1.5 py-0.2 font-mono text-[10px] hover:bg-sky-500/40"
                  >
                    {isolation.hops}{" "}
                    {isolation.hops === 1 ? t.graph.hopSingular : t.graph.hopPlural}
                  </button>
                  <button
                    type="button"
                    onClick={() => onSetIsolation(null)}
                    className="text-[10px] text-sky-300 hover:text-white"
                  >
                    ✕
                  </button>
                </div>
              )}

              {flightHistory.length > 0 && (
                <button
                  type="button"
                  onClick={goBackAlongHistory}
                  title={t.graph.navBackTitle}
                  className="inline-flex items-center gap-1 rounded-lg border border-amber-500/45 bg-amber-500/15 px-2 py-0.5 text-[11px] font-medium text-amber-200 transition hover:bg-amber-500/25"
                >
                  <ArrowLeft className="h-3 w-3" />
                  <span>{t.graph.navBackBtn}</span>
                </button>
              )}

              <span className="inline-flex items-center gap-1 font-medium text-emerald-300">
                <Navigation className="h-3 w-3 text-emerald-400" />
                <span>{t.graph.navLinksLabel}</span>
              </span>

              {selectedNeighbors.slice(0, 6).map((entry) => {
                const nm = ENTITY_META[entry.node.type];
                const em = EDGE_META[entry.edge.type];
                const nbLabel = getNodeLabel(entry.node);
                return (
                  <button
                    key={`${entry.edge.id}-${entry.node.id}`}
                    type="button"
                    onClick={() =>
                      flyAlongEdge(selectedNode.id, entry.node.id, {
                        edgeId: entry.edge.id,
                        recordHistory: true,
                      })
                    }
                    title={`${getEdgeLabel(entry.edge.type, lang)} → ${nbLabel}`}
                    className={`inline-flex items-center gap-1.5 rounded-lg border px-2 py-0.5 text-[11px] font-medium transition hover:brightness-125 ${nm.bgClass} ${nm.borderClass} ${nm.textClass}`}
                  >
                    <span
                      className="h-1.5 w-1.5 shrink-0 rounded-full"
                      style={{ backgroundColor: em?.color ?? nm.color }}
                    />
                    <span className="max-w-[130px] truncate">{nbLabel}</span>
                    <ArrowRight className="h-2.5 w-2.5 shrink-0 opacity-75" />
                  </button>
                );
              })}

              {selectedNeighbors.length > 6 && (
                <span className="px-1 font-mono text-[10px] text-emerald-400/80">
                  +{selectedNeighbors.length - 6} {t.graph.navMoreLinks}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Bottom-Left Compact Navigation & Stats Dock */}
        <div className="pointer-events-auto absolute bottom-3 left-3 z-20 flex flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-emerald-900/60 bg-[#09120e]/88 px-3 py-1.5 text-xs text-emerald-300 shadow-xl backdrop-blur-md">
            <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
            <span className="font-mono">
              {t.graph.dockNodes} <strong>{formatNumber(visibleStats.nodes)}</strong> •{" "}
              {t.graph.dockEdges} <strong>{formatNumber(visibleStats.edges)}</strong>
            </span>
            <div className="mx-1 h-3.5 w-px bg-emerald-800/70" />
            <button
              onClick={() => zoomStep(0.75)}
              className="rounded p-1 hover:bg-emerald-950"
              title={t.graph.zoomIn}
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => zoomStep(1.3)}
              className="rounded p-1 hover:bg-emerald-950"
              title={t.graph.zoomOut}
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={resetCamera}
              className="rounded p-1 hover:bg-emerald-950"
              title={t.graph.centerCamera}
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={cycleDepthMode}
              className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] transition ${depthMode !== "off"
                ? "bg-emerald-500/20 text-emerald-200"
                : "text-emerald-500 hover:bg-emerald-950"
                }`}
              title={t.graph.depthShadeTitle}
            >
              <Eye className="h-3 w-3" />
              <span>
                {t.graph.depthShadeLabel}:{" "}
                {depthMode === "strong"
                  ? t.graph.depthStrong
                  : depthMode === "soft"
                    ? t.graph.depthSoft
                    : t.graph.depthOff}
              </span>
            </button>
            <button
              onClick={() => setAutoRotate((v) => !v)}
              className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] transition ${autoRotate
                ? "bg-emerald-500/20 text-emerald-200"
                : "text-emerald-400 hover:bg-emerald-950"
                }`}
              title={t.graph.autoOrbitTitle}
            >
              {autoRotate ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
              {t.graph.autoOrbitLabel}
            </button>
            <button
              onClick={handleResetAll}
              className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] text-emerald-400 hover:bg-emerald-950 hover:text-emerald-200"
              title={t.graph.resetAllTitle}
            >
              <RotateCcw className="h-3 w-3" />
              {t.graph.resetAllLabel}
            </button>
          </div>
          <div className="hidden rounded-lg bg-[#050a08]/75 px-2.5 py-1 text-[10px] text-emerald-500/80 backdrop-blur-sm sm:block">
            {selectedNode ? t.graph.navHint : t.graph.controlsHint}
          </div>
        </div>

        {/* Bottom-Right Interactive Legend Pills */}
        {!selectedNode && (
          <div className="pointer-events-auto absolute bottom-3 right-3 z-20 hidden flex-wrap justify-end gap-1.5 lg:flex">
            {ALL_TYPES.map((tKey) => {
              const m = ENTITY_META[tKey];
              const active = visibleTypes.has(tKey);
              return (
                <button
                  key={tKey}
                  onClick={() => toggleType(tKey)}
                  className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-medium backdrop-blur-md transition ${active
                    ? `${m.bgClass} ${m.borderClass} ${m.textClass}`
                    : "border-emerald-900/40 bg-[#09120e]/75 text-emerald-600 line-through"
                    }`}
                >
                  <span
                    className={`h-2 w-2 rounded-full ${active ? m.dotClass : "bg-emerald-800"}`}
                  />
                  {getEntityLabel(tKey, lang)}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Right Slide-Over Inspector */}
      {selectedNode && (
        <div className="h-full shrink-0">
          <InspectorPanel
            node={selectedNode}
            details={details}
            iconAtlas={iconAtlas}
            neighbors={selectedNeighbors}
            walkthrough={selectedWalkthrough}
            isIsolated={Boolean(isolation && isolation.rootId === selectedNode.id)}
            onClose={() => onSelectNode(null)}
            onSelectNode={(nid) =>
              selectedNodeId && selectedNodeId !== nid
                ? flyAlongEdge(selectedNodeId, nid, { recordHistory: true })
                : flyToNode(nid)
            }
            onIsolateNode={(nid, hops) => {
              onSelectNode(nid);
              onSetIsolation({ rootId: nid, hops });
            }}
            onClearIsolation={() => onSetIsolation(null)}
            onStartPathFrom={(nid) => {
              const nd = nodeMap.get(nid);
              setPathStartId(nid);
              setPathStartQuery(nd ? getNodeLabel(nd) : nid);
              setShowPathFinder(true);
            }}
            onOpenWalkthrough={onOpenWalkthrough}
          />
        </div>
      )}
    </div>
  );
};
