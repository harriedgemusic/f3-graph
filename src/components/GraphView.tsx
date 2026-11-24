import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  Compass,
  Focus,
  GitFork,
  Layers,
  Maximize2,
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
      ? 4.5
      : nd.type === "event"
      ? 3.2
      : nd.subtype === "marker" || nd.subtype === "world"
      ? 2.0
      : 0;
  return Math.min(24, 10.5 + boost + Math.sqrt(Math.max(1, nd.degree)) * 1.45);
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
    const perRing = Math.max(10, Math.min(22, Math.ceil(n / 2)));
    for (let i = 0; i < n; i++) {
      const ringIdx = Math.floor(i / perRing);
      const posInRing = i % perRing;
      const countInThisRing = Math.min(perRing, n - ringIdx * perRing);
      const t = countInThisRing === 1 ? 0.5 : posInRing / (countInThisRing - 1 + (angleSpan >= Math.PI * 1.99 ? 1 : 0));
      const ang = angleStart + t * angleSpan + ringIdx * 0.25;
      const r = radiusBase + ringIdx * 48;
      const y = yCenter + Math.sin(i * 1.7) * yWave + ringIdx * 12;
      posMap.set(
        list[i].id,
        new THREE.Vector3(Math.cos(ang) * r, y, Math.sin(ang) * r)
      );
    }
  };

  // Hop 1 concentric 3D bands
  placeRing(groups.quest.hop1, 105, 115, 0, Math.PI * 2, 14);
  placeRing(groups.event.hop1, 72, 130, 0.3, Math.PI * 2, 12);
  placeRing(groups.character.hop1, 18, 135, -Math.PI * 0.45, Math.PI * 0.9, 16);
  placeRing(groups.location.hop1, -18, 140, Math.PI * 0.55, Math.PI * 0.9, 16);
  placeRing(groups.item.hop1, -85, 130, 0.15, Math.PI * 2, 14);
  placeRing(groups.object.hop1, -120, 120, 0.45, Math.PI * 2, 14);

  // Hop 2 outer bands
  placeRing(groups.quest.hop2, 150, 235, 0.2, Math.PI * 2, 18);
  placeRing(groups.event.hop2, 120, 245, 0.5, Math.PI * 2, 16);
  placeRing(groups.character.hop2, 35, 255, -Math.PI * 0.5, Math.PI, 20);
  placeRing(groups.location.hop2, -35, 265, Math.PI * 0.5, Math.PI, 20);
  placeRing(groups.item.hop2, -135, 245, 0.1, Math.PI * 2, 18);
  placeRing(groups.object.hop2, -165, 235, 0.4, Math.PI * 2, 18);

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

  // Popover drawers
  const [showFilters, setShowFilters] = useState(false);
  const [showPathFinder, setShowPathFinder] = useState(false);
  const [autoRotate, setAutoRotate] = useState(false);

  // Search autocomplete
  const [searchQuery, setSearchQuery] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);

  // Path finder
  const [pathStartId, setPathStartId] = useState<string | null>(null);
  const [pathEndId, setPathEndId] = useState<string | null>(null);
  const [pathStartQuery, setPathStartQuery] = useState("");
  const [pathEndQuery, setPathEndQuery] = useState("");

  // Hover + Tooltip
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
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
    fgLines: THREE.LineSegments;
    selectedHalo: THREE.Sprite;
    hoveredHalo: THREE.Sprite;
    pathHaloGroup: THREE.Group;
    glowTex: THREE.CanvasTexture;
    nodePositions: Map<string, THREE.Vector3>;
    nodeSizes: Map<string, number>;
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
      startTime: number;
      duration: number;
      fromPos: THREE.Vector3;
      toPos: THREE.Vector3;
      fromTarget: THREE.Vector3;
      toTarget: THREE.Vector3;
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
  // Hovering only gently accents a single node; full dimming/edges happen on explicit selection
  const focusNodeId = selectedNodeId;
  const neighborsOfFocus = useMemo(() => {
    const set = new Set<string>();
    if (!focusNodeId) return set;
    for (const nb of adjacency.get(focusNodeId) ?? []) {
      set.add(nb.node.id);
    }
    return set;
  }, [focusNodeId, adjacency]);

  const visualStateRef = useRef({
    selectedNodeId: null as string | null,
    hoveredNodeId: null as string | null,
    focusNodeId: null as string | null,
    neighborsOfFocus: new Set<string>(),
    pathNodeIds: [] as string[],
    pathNodeSet: new Set<string>(),
    pathEdgeSet: new Set<string>(),
    isolationActive: false,
    isolationRootId: null as string | null,
    autoRotate: false,
  });

  visualStateRef.current = {
    selectedNodeId,
    hoveredNodeId,
    focusNodeId,
    neighborsOfFocus,
    pathNodeIds: shortestPath.nodeIds,
    pathNodeSet: shortestPath.nodeSet,
    pathEdgeSet: shortestPath.edgeSet,
    isolationActive: Boolean(isolatedSet),
    isolationRootId: isolation?.rootId ?? null,
    autoRotate,
  };

  // Start smooth 3D camera flight
  const flyCameraTo = useCallback((toPos: THREE.Vector3, toTarget: THREE.Vector3, duration = 520) => {
    const st = threeRef.current;
    if (!st) return;
    st.flight = {
      active: true,
      startTime: performance.now(),
      duration,
      fromPos: st.camera.position.clone(),
      toPos: toPos.clone(),
      fromTarget: st.controls.target.clone(),
      toTarget: toTarget.clone(),
    };
  }, []);

  const resetCamera = useCallback(() => {
    const st = threeRef.current;
    if (!st) return;
    if (visualStateRef.current.isolationActive) {
      flyCameraTo(new THREE.Vector3(0, 145, 420), new THREE.Vector3(0, 0, 0), 480);
    } else if (layoutMode === "map3d") {
      flyCameraTo(new THREE.Vector3(0, 390, 620), new THREE.Vector3(0, 0, 0), 500);
    } else {
      flyCameraTo(new THREE.Vector3(0, 175, 495), new THREE.Vector3(0, 0, 0), 500);
    }
  }, [flyCameraTo, layoutMode]);

  // Apply billboard icon buffers, halos, and line buffers based on selection/path/hover
  const refreshVisualHighlights = useCallback(() => {
    const st = threeRef.current;
    if (!st) return;
    const vs = visualStateRef.current;
    const hasPath = vs.pathNodeSet.size > 0;
    const activeId = vs.focusNodeId;
    const atlas = iconAtlasRef.current;

    const tmpColor = new THREE.Color();

    // Classify draw order so highlighted/active icons always render on top of dimmed ones
    const ordered: {
      nd: GraphNode;
      pos: THREE.Vector3;
      size: number;
      colorHex: string;
      alpha: number;
      highlight: number;
      tierOrder: number;
    }[] = [];

    st.nodeSizes.clear();

    for (const nd of st.visibleNodes) {
      const pos = st.nodePositions.get(nd.id);
      if (!pos) continue;
      const baseSize = getNodeCardSize(nd);
      const baseHex = ENTITY_META[nd.type].color;

      let scaleMult = 1.0;
      let colorHex = baseHex;
      let alpha = 0.96;
      let highlight = 0.0;
      let tierOrder = 1;

      if (hasPath) {
        if (vs.pathNodeSet.has(nd.id)) {
          scaleMult = 1.48;
          colorHex = "#fbbf24";
          alpha = 1.0;
          highlight = 1.0;
          tierOrder = 3;
        } else {
          scaleMult = 0.7;
          colorHex = baseHex;
          alpha = 0.16;
          highlight = 0.0;
          tierOrder = 0;
        }
      } else if (activeId) {
        if (nd.id === activeId) {
          scaleMult = 1.55;
          alpha = 1.0;
          highlight = 1.0;
          tierOrder = 3;
        } else if (vs.neighborsOfFocus.has(nd.id)) {
          scaleMult = 1.24;
          alpha = 0.98;
          highlight = 0.55;
          tierOrder = 2;
        } else {
          scaleMult = 0.72;
          alpha = 0.15;
          highlight = 0.0;
          tierOrder = 0;
        }
      } else {
        if (nd.id === vs.hoveredNodeId) {
          scaleMult = 1.24;
          alpha = 1.0;
          highlight = 0.75;
          tierOrder = 3;
        } else if (vs.isolationActive && nd.id === vs.isolationRootId) {
          scaleMult = 1.45;
          alpha = 1.0;
          highlight = 0.9;
          tierOrder = 3;
        }
      }

      if (nd.id === vs.hoveredNodeId && tierOrder < 3) {
        scaleMult = Math.max(scaleMult, 1.22);
        alpha = 1.0;
        highlight = Math.max(highlight, 0.75);
        tierOrder = 3;
      }

      const finalSize = baseSize * scaleMult;
      st.nodeSizes.set(nd.id, finalSize);
      ordered.push({ nd, pos, size: finalSize, colorHex, alpha, highlight, tierOrder });
    }

    ordered.sort((a, b) => a.tierOrder - b.tierOrder || a.nd.degree - b.nd.degree);

    const cArr = st.attrCenter.array as Float32Array;
    const sArr = st.attrSize.array as Float32Array;
    const uArr = st.attrUvRect.array as Float32Array;
    const colArr = st.attrColor.array as Float32Array;
    const aArr = st.attrAlpha.array as Float32Array;
    const hArr = st.attrHighlight.array as Float32Array;
    const icArr = st.attrIsColor.array as Float32Array;

    const count = ordered.length;
    for (let i = 0; i < count; i++) {
      const item = ordered[i];
      const i3 = i * 3;
      const i4 = i * 4;

      cArr[i3] = item.pos.x;
      cArr[i3 + 1] = item.pos.y;
      cArr[i3 + 2] = item.pos.z;
      sArr[i] = item.size;

      const entry = item.nd.icon && atlas ? atlas.icons[item.nd.icon] : undefined;
      if (entry) {
        uArr[i4] = entry.u;
        uArr[i4 + 1] = entry.v;
        uArr[i4 + 2] = entry.uw;
        uArr[i4 + 3] = entry.vh;
        icArr[i] = entry.isColor ? 1.0 : 0.0;
      } else {
        uArr[i4] = 0;
        uArr[i4 + 1] = 0;
        uArr[i4 + 2] = 0;
        uArr[i4 + 3] = 0;
        icArr[i] = 0.0;
      }

      tmpColor.set(item.colorHex);
      colArr[i3] = tmpColor.r;
      colArr[i3 + 1] = tmpColor.g;
      colArr[i3 + 2] = tmpColor.b;
      aArr[i] = item.alpha;
      hArr[i] = item.highlight;
    }

    st.iconMesh.count = count;
    st.attrCenter.needsUpdate = true;
    st.attrSize.needsUpdate = true;
    st.attrUvRect.needsUpdate = true;
    st.attrColor.needsUpdate = true;
    st.attrAlpha.needsUpdate = true;
    st.attrHighlight.needsUpdate = true;
    st.attrIsColor.needsUpdate = true;

    // Halos for selected, hovered, and path nodes
    if (vs.selectedNodeId && st.nodePositions.has(vs.selectedNodeId)) {
      const nd = nodeMap.get(vs.selectedNodeId);
      const pos = st.nodePositions.get(vs.selectedNodeId)!;
      const r = nd ? getNodeCardSize(nd) : 14;
      st.selectedHalo.position.copy(pos);
      st.selectedHalo.scale.setScalar(r * 2.6);
      (st.selectedHalo.material as THREE.SpriteMaterial).color.set(
        nd ? ENTITY_META[nd.type].color : "#34d399"
      );
      st.selectedHalo.visible = true;
    } else {
      st.selectedHalo.visible = false;
    }

    if (vs.hoveredNodeId && st.nodePositions.has(vs.hoveredNodeId)) {
      const nd = nodeMap.get(vs.hoveredNodeId);
      const pos = st.nodePositions.get(vs.hoveredNodeId)!;
      const r = nd ? getNodeCardSize(nd) : 14;
      st.hoveredHalo.position.copy(pos);
      st.hoveredHalo.scale.setScalar(r * 2.2);
      (st.hoveredHalo.material as THREE.SpriteMaterial).color.set("#ffffff");
      st.hoveredHalo.visible = true;
    } else {
      st.hoveredHalo.visible = false;
    }

    // Path halos
    st.pathHaloGroup.clear();
    if (hasPath) {
      for (const pid of vs.pathNodeIds) {
        const pos = st.nodePositions.get(pid);
        if (!pos) continue;
        const spr = new THREE.Sprite(
          new THREE.SpriteMaterial({
            map: st.glowTex,
            color: 0xfbbf24,
            transparent: true,
            opacity: 0.75,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
          })
        );
        spr.position.copy(pos);
        spr.scale.setScalar(34);
        st.pathHaloGroup.add(spr);
      }
    }

    // Rebuild foreground vs background LineSegments
    const bgCoords: number[] = [];
    const bgColors: number[] = [];
    const fgCoords: number[] = [];
    const fgColors: number[] = [];
    const cTmp = new THREE.Color();

    for (const e of st.visibleEdges) {
      const p1 = st.nodePositions.get(e.source);
      const p2 = st.nodePositions.get(e.target);
      if (!p1 || !p2) continue;

      const isPathEdge = hasPath && vs.pathEdgeSet.has(e.id);
      const isFocusEdge = !hasPath && activeId && (e.source === activeId || e.target === activeId);

      if (isPathEdge) {
        fgCoords.push(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z);
        cTmp.set("#fbbf24");
        fgColors.push(cTmp.r, cTmp.g, cTmp.b, cTmp.r, cTmp.g, cTmp.b);
      } else if (isFocusEdge) {
        fgCoords.push(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z);
        cTmp.set(EDGE_META[e.type]?.color ?? "#34d399");
        fgColors.push(cTmp.r, cTmp.g, cTmp.b, cTmp.r, cTmp.g, cTmp.b);
      } else if (vs.isolationActive && !hasPath && !activeId) {
        fgCoords.push(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z);
        cTmp.set(EDGE_META[e.type]?.color ?? "#34d399").multiplyScalar(0.7);
        fgColors.push(cTmp.r, cTmp.g, cTmp.b, cTmp.r, cTmp.g, cTmp.b);
      } else {
        if (
          !vs.isolationActive &&
          !st.showBgLootEdges &&
          (e.type === "location_item" || e.type === "location_object")
        ) {
          continue;
        }
        bgCoords.push(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z);
        cTmp.set(EDGE_META[e.type]?.color ?? "#254d3c");
        bgColors.push(cTmp.r, cTmp.g, cTmp.b, cTmp.r, cTmp.g, cTmp.b);
      }
    }

    const bgGeo = st.bgLines.geometry;
    bgGeo.setAttribute("position", new THREE.Float32BufferAttribute(bgCoords, 3));
    bgGeo.setAttribute("color", new THREE.Float32BufferAttribute(bgColors, 3));
    bgGeo.computeBoundingSphere();
    (st.bgLines.material as THREE.LineBasicMaterial).opacity =
      hasPath || activeId ? 0.045 : 0.22;

    const fgGeo = st.fgLines.geometry;
    fgGeo.setAttribute("position", new THREE.Float32BufferAttribute(fgCoords, 3));
    fgGeo.setAttribute("color", new THREE.Float32BufferAttribute(fgColors, 3));
    fgGeo.computeBoundingSphere();
  }, [nodeMap]);

  // Initialize Three.js WebGL scene once
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 1200;
    const height = container.clientHeight || 800;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#050a08");
    scene.fog = new THREE.FogExp2(0x050a08, 0.00048);

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
    controls.minDistance = 24;
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
      opacity: 0.45,
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
      gm.opacity = 0.22;
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
        opacity: 0.14,
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
            opacity: 0.12,
          })
        )
      );
    }
    scene.add(stratumRings);

    // Instanced 3D Billboard Icon Plaques
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

    const iconMat = new THREE.ShaderMaterial({
      uniforms: {
        uAtlas: { value: null },
        uHasAtlas: { value: 0.0 },
      },
      vertexShader: `
        attribute vec3 aCenter;
        attribute float aSize;
        attribute vec4 aUvRect;
        attribute vec3 aColor;
        attribute float aAlpha;
        attribute float aHighlight;
        attribute float aIsColor;

        varying vec2 vUv;
        varying vec4 vUvRect;
        varying vec3 vColor;
        varying float vAlpha;
        varying float vHighlight;
        varying float vIsColor;

        void main() {
          vUv = uv;
          vUvRect = aUvRect;
          vColor = aColor;
          vAlpha = aAlpha;
          vHighlight = aHighlight;
          vIsColor = aIsColor;

          vec4 mvCenter = viewMatrix * modelMatrix * vec4(aCenter, 1.0);
          float effSize = min(aSize, max(4.0, abs(mvCenter.z) * 0.13));
          mvCenter.xy += position.xy * effSize;
          gl_Position = projectionMatrix * mvCenter;
        }
      `,
      fragmentShader: `
        uniform sampler2D uAtlas;
        uniform float uHasAtlas;

        varying vec2 vUv;
        varying vec4 vUvRect;
        varying vec3 vColor;
        varying float vAlpha;
        varying float vHighlight;
        varying float vIsColor;

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
          vec3 bgCol = vec3(0.005, 0.014, 0.010) + vColor * (0.09 * radialGlow + 0.07 * vHighlight);
          vec3 borderCol = mix(vColor, vec3(0.95, 1.0, 0.98), 0.15 + 0.45 * vHighlight);

          vec3 col = mix(bgCol, borderCol, borderMask * (0.78 + 0.22 * vHighlight));
          float outAlpha = outerMask * mix(0.90, 1.0, max(borderMask, vHighlight));

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

          gl_FragColor = vec4(col, outAlpha * vAlpha);
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

    // Background & foreground LineSegments
    const bgLines = new THREE.LineSegments(
      new THREE.BufferGeometry(),
      new THREE.LineBasicMaterial({
        vertexColors: true,
        transparent: true,
        opacity: 0.22,
        depthWrite: false,
      })
    );
    bgLines.frustumCulled = false;
    bgLines.renderOrder = 0;
    scene.add(bgLines);

    const fgLines = new THREE.LineSegments(
      new THREE.BufferGeometry(),
      new THREE.LineBasicMaterial({
        vertexColors: true,
        transparent: true,
        opacity: 0.92,
        depthWrite: false,
      })
    );
    fgLines.frustumCulled = false;
    fgLines.renderOrder = 1;
    scene.add(fgLines);

    // Halos
    const glowTex = createGlowTexture();
    const selectedHalo = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: glowTex,
        color: 0x34d399,
        transparent: true,
        opacity: 0.85,
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
        opacity: 0.5,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      })
    );
    hoveredHalo.visible = false;
    hoveredHalo.renderOrder = 3;
    scene.add(hoveredHalo);

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
      fgLines,
      selectedHalo,
      hoveredHalo,
      pathHaloGroup,
      glowTex,
      nodePositions: new Map(),
      nodeSizes: new Map(),
      visibleNodes: [],
      visibleEdges: [],
      showBgLootEdges: false,
      flight: {
        active: false,
        startTime: 0,
        duration: 500,
        fromPos: new THREE.Vector3(),
        toPos: new THREE.Vector3(),
        fromTarget: new THREE.Vector3(),
        toTarget: new THREE.Vector3(),
      },
      pressedKeys,
    };

    // Cancel camera flight when user takes manual control
    const cancelFlight = () => {
      if (threeRef.current) threeRef.current.flight.active = false;
    };
    controls.addEventListener("start", cancelFlight);

    // Exact 3D ray-to-billboard picking & calm debounced hover
    const raycaster = new THREE.Raycaster();
    const pointerNdc = new THREE.Vector2();
    const tmpRayDiff = new THREE.Vector3();
    let downPos = { x: 0, y: 0 };
    let isPointerDown = false;
    let hoverTimer: number | null = null;
    let pendingHoverId: string | null = null;
    let committedHoverId: string | null = null;

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
      pointerNdc.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
      pointerNdc.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointerNdc, camera);
      const ray = raycaster.ray;

      let bestNode: GraphNode | null = null;
      let bestT = Infinity;

      for (const nd of st.visibleNodes) {
        const pos = st.nodePositions.get(nd.id);
        if (!pos) continue;
        tmpRayDiff.subVectors(pos, ray.origin);
        const t = tmpRayDiff.dot(ray.direction);
        if (t <= 1) continue;
        const size = st.nodeSizes.get(nd.id) ?? getNodeCardSize(nd);
        const pickR = size * 0.56;
        if (ray.distanceSqToPoint(pos) <= pickR * pickR) {
          if (t < bestT) {
            bestT = t;
            bestNode = nd;
          }
        }
      }
      return bestNode;
    };

    const onPointerDown = (ev: PointerEvent) => {
      isPointerDown = true;
      downPos = { x: ev.clientX, y: ev.clientY };
      clearHoverTimer();
      pendingHoverId = null;
      if (committedHoverId !== null) {
        committedHoverId = null;
        setHoveredNodeId(null);
      }
      if (tooltipRef.current) {
        tooltipRef.current.style.opacity = "0";
      }
    };

    const onPointerMove = (ev: PointerEvent) => {
      if (isPointerDown) return;
      const hit = pickNodeAtEvent(ev);
      const hitId = hit ? hit.id : null;
      renderer.domElement.style.cursor = hit ? "pointer" : "grab";

      if (hitId) {
        if (tooltipRef.current) {
          tooltipRef.current.style.transform = `translate3d(${ev.clientX + 16}px, ${ev.clientY + 16}px, 0)`;
          if (committedHoverId === hitId) {
            tooltipRef.current.style.opacity = "1";
          }
        }
        if (pendingHoverId !== hitId) {
          pendingHoverId = hitId;
          clearHoverTimer();
          hoverTimer = window.setTimeout(() => {
            committedHoverId = hitId;
            setHoveredNodeId(hitId);
            if (tooltipRef.current) {
              tooltipRef.current.style.opacity = "1";
            }
          }, 160);
        }
      } else {
        if (tooltipRef.current) {
          tooltipRef.current.style.opacity = "0";
        }
        if (pendingHoverId !== null || committedHoverId !== null) {
          pendingHoverId = null;
          clearHoverTimer();
          hoverTimer = window.setTimeout(() => {
            committedHoverId = null;
            setHoveredNodeId(null);
          }, 80);
        }
      }
    };

    const onPointerLeave = () => {
      pendingHoverId = null;
      committedHoverId = null;
      clearHoverTimer();
      setHoveredNodeId(null);
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
      const hit = pickNodeAtEvent(ev);
      onSelectNode(hit ? hit.id : null);
    };

    const onDblClick = (ev: MouseEvent) => {
      const hit = pickNodeAtEvent(ev);
      if (hit) {
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

    // Keyboard WASD / QE / R / Esc / /
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
      if (ev.key === "Escape") {
        setShowFilters(false);
        setShowPathFinder(false);
        onSelectNode(null);
        return;
      }
      if (ev.key.toLowerCase() === "r" || ev.key.toLowerCase() === "к") {
        if (threeRef.current) {
          threeRef.current.flight = {
            active: true,
            startTime: performance.now(),
            duration: 450,
            fromPos: camera.position.clone(),
            toPos: new THREE.Vector3(0, 175, 495),
            fromTarget: controls.target.clone(),
            toTarget: new THREE.Vector3(0, 0, 0),
          };
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
      }
    });
    ro.observe(container);

    // Animation loop + projected DOM 3D labels
    let rafId = 0;
    const projVec = new THREE.Vector3();
    const forwardVec = new THREE.Vector3();
    const rightVec = new THREE.Vector3();
    const upVec = new THREE.Vector3(0, 1, 0);
    let lastTime = performance.now();

    const animate = (now: number) => {
      rafId = requestAnimationFrame(animate);
      const dt = Math.min(0.05, (now - lastTime) / 1000);
      lastTime = now;

      const st = threeRef.current;
      if (!st) return;

      // Keyboard flight
      if (st.pressedKeys.size > 0) {
        st.flight.active = false;
        camera.getWorldDirection(forwardVec);
        forwardVec.y = 0;
        if (forwardVec.lengthSq() > 1e-6) forwardVec.normalize();
        rightVec.crossVectors(forwardVec, upVec).normalize();

        const speed = Math.max(140, camera.position.distanceTo(controls.target) * 0.65) * dt;
        const delta = new THREE.Vector3();
        if (st.pressedKeys.has("KeyW") || st.pressedKeys.has("ArrowUp")) delta.addScaledVector(forwardVec, speed);
        if (st.pressedKeys.has("KeyS") || st.pressedKeys.has("ArrowDown")) delta.addScaledVector(forwardVec, -speed);
        if (st.pressedKeys.has("KeyD") || st.pressedKeys.has("ArrowRight")) delta.addScaledVector(rightVec, speed);
        if (st.pressedKeys.has("KeyA") || st.pressedKeys.has("ArrowLeft")) delta.addScaledVector(rightVec, -speed);
        if (st.pressedKeys.has("KeyE")) delta.y += speed;
        if (st.pressedKeys.has("KeyQ")) delta.y -= speed;

        camera.position.add(delta);
        controls.target.add(delta);
      }

      // Smooth camera flight
      if (st.flight.active) {
        const rawT = Math.min(1, (now - st.flight.startTime) / st.flight.duration);
        const ease = 1 - Math.pow(1 - rawT, 3);
        camera.position.lerpVectors(st.flight.fromPos, st.flight.toPos, ease);
        controls.target.lerpVectors(st.flight.fromTarget, st.flight.toTarget, ease);
        if (rawT >= 1) st.flight.active = false;
      }

      controls.autoRotate = visualStateRef.current.autoRotate && !st.flight.active;
      controls.autoRotateSpeed = 0.55;
      controls.update();

      renderer.render(scene, camera);

      // Project crisp 2D HTML labels for top visible 3D nodes (zero React re-renders)
      const cw = container.clientWidth;
      const ch = container.clientHeight;
      const vs = visualStateRef.current;
      const hasFocus = Boolean(vs.focusNodeId);
      const hasPath = vs.pathNodeSet.size > 0;

      const vFovTan = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
      const candidates: {
        node: GraphNode;
        pos: THREE.Vector3;
        dist: number;
        priority: number;
      }[] = [];

      for (const nd of st.visibleNodes) {
        const p = st.nodePositions.get(nd.id);
        if (!p) continue;
        const dist = camera.position.distanceTo(p);

        let prio = 0;
        const isTechLabel =
          /^(DC\d|test|dummy|temp|000)/i.test(nd.label) || /^[A-Z0-9_]{6,}$/.test(nd.label);
        if (nd.id === vs.selectedNodeId) prio = 1000;
        else if (nd.id === vs.hoveredNodeId) prio = 950;
        else if (hasPath && vs.pathNodeSet.has(nd.id)) prio = 850;
        else if (hasFocus && vs.neighborsOfFocus.has(nd.id)) prio = 700 + nd.degree;
        else if (vs.isolationActive) prio = (nd.id === vs.isolationRootId ? 900 : 480) + nd.degree;
        else if (!hasFocus && !hasPath && !isTechLabel && nd.degree > 1) {
          if (nd.type === "quest" && nd.subtype === "main") prio = 360 + nd.degree;
          else if (nd.type === "quest" || nd.type === "event") prio = 260 + nd.degree;
          else if (nd.subtype === "marker" && nd.degree >= 10) prio = 185 + nd.degree;
          else if (nd.degree >= 14 || dist < 240) prio = 140 + nd.degree + (dist < 240 ? 90 : 0);
        }
        if (prio <= 0) continue;

        candidates.push({ node: nd, pos: p, dist, priority: prio - dist * 0.08 });
      }
      candidates.sort((a, b) => b.priority - a.priority);

      const occupied: { x1: number; y1: number; x2: number; y2: number }[] = [];
      let poolIdx = 0;

      for (let i = 0; i < candidates.length && poolIdx < LABEL_POOL_SIZE; i++) {
        const cand = candidates[i];
        projVec.copy(cand.pos).project(camera);
        if (projVec.z < -1 || projVec.z > 1) continue;

        const sx = (projVec.x * 0.5 + 0.5) * cw;
        const sy = (-projVec.y * 0.5 + 0.5) * ch;
        if (sx < 40 || sx > cw - 60 || sy < 72 || sy > ch - 50) continue;

        const rawCardSize = st.nodeSizes.get(cand.node.id) ?? getNodeCardSize(cand.node);
        const cardSize = Math.min(rawCardSize, Math.max(4, cand.dist * 0.13));
        const halfPx = (cardSize * ch) / (4 * Math.max(20, cand.dist) * vFovTan);
        const labelTopY = sy + Math.max(7, halfPx) + 4;

        const candLabel = getLocalizedNodeLabel(cand.node, langRef.current);
        const approxW = Math.min(250, candLabel.length * 7.6 + 28);
        const approxH = 24;
        const bx1 = sx - approxW / 2;
        const by1 = labelTopY;
        const bx2 = sx + approxW / 2;
        const by2 = labelTopY + approxH;

        let overlaps = false;
        // Always show selected/hovered/path even if close
        if (cand.priority < 800) {
          for (const box of occupied) {
            if (!(bx2 < box.x1 || bx1 > box.x2 || by2 < box.y1 || by1 > box.y2)) {
              overlaps = true;
              break;
            }
          }
        }
        if (overlaps) continue;
        occupied.push({ x1: bx1, y1: by1, x2: bx2, y2: by2 });

        const div = labelDivRefs.current[poolIdx];
        const dot = labelDotRefs.current[poolIdx];
        const txt = labelTextRefs.current[poolIdx];
        if (div && dot && txt) {
          div.style.transform = `translate3d(${Math.round(sx)}px, ${Math.round(labelTopY)}px, 0) translate(-50%, 0)`;
          div.style.opacity = "1";
          dot.style.backgroundColor = ENTITY_META[cand.node.type].color;
          if (txt.textContent !== candLabel) txt.textContent = candLabel;
        }
        poolIdx++;
      }

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
      (bgLines.material as THREE.Material).dispose();
      fgLines.geometry.dispose();
      (fgLines.material as THREE.Material).dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
      threeRef.current = null;
    };
  }, [graphData, onSelectNode, onSetIsolation, refreshVisualHighlights]);

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

    // Positions: 3D radial constellation if isolated, else x3d/y3d/z3d or mapX/mapY/mapZ
    const isoPositions =
      isolatedSet && isolation
        ? computeIsolationPositions3D(isolation.rootId, visNodes, adjacency, langRef.current)
        : null;

    st.nodePositions.clear();

    for (const nd of visNodes) {
      const p = isoPositions
        ? isoPositions.get(nd.id) ?? new THREE.Vector3(0, 0, 0)
        : layoutMode === "map3d"
        ? new THREE.Vector3(nd.mapX, nd.mapY, nd.mapZ)
        : new THREE.Vector3(nd.x3d, nd.y3d, nd.z3d);
      st.nodePositions.set(nd.id, p);
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
    resetCamera();
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

  // Refresh highlights when selection / hover / path / atlas changes
  useEffect(() => {
    refreshVisualHighlights();
  }, [hoveredNodeId, selectedNodeId, shortestPath, iconAtlas, refreshVisualHighlights]);

  // Fly camera to a specific node smoothly
  const flyToNode = useCallback(
    (nodeId: string) => {
      const nd = nodeMap.get(nodeId);
      if (!nd) return;

      if (!isolatedSet) {
        if (nd.tier === "extended") setScope("extended");
        else if (nd.tier === "core" && scope === "atlas") setScope("core");
        if (!visibleTypes.has(nd.type)) {
          setVisibleTypes((prev) => new Set([...prev, nd.type]));
        }
        if (dlcFilter !== "all" && nd.dlc !== dlcFilter) {
          setDlcFilter("all");
        }
      }

      onSelectNode(nodeId);

      setTimeout(() => {
        const st = threeRef.current;
        if (!st) return;
        const target = st.nodePositions.get(nodeId);
        if (!target) return;
        const offset = st.camera.position.clone().sub(st.controls.target);
        if (offset.length() < 1) offset.set(0, 70, 170);
        offset.setLength(180);
        flyCameraTo(target.clone().add(offset), target, 550);
      }, 60);
    },
    [nodeMap, isolatedSet, scope, visibleTypes, dlcFilter, onSelectNode, flyCameraTo]
  );

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

  const handleResetAll = () => {
    onSetIsolation(null);
    onSelectNode(null);
    setScope("atlas");
    setDlcFilter("all");
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
              className="absolute left-0 top-0 inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border border-emerald-900/60 bg-[#07100c]/85 px-2 py-0.5 text-[11px] font-medium text-emerald-50 shadow-lg backdrop-blur-sm transition-opacity duration-100"
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
              />
            </div>
          ))}
        </div>

        {/* Floating Hover Tooltip */}
        <div
          ref={tooltipRef}
          style={{ opacity: 0 }}
          className="pointer-events-none fixed left-0 top-0 z-40 max-w-xs rounded-lg border border-emerald-700/60 bg-[#08110d]/95 px-3 py-2 text-xs shadow-2xl backdrop-blur-md transition-opacity duration-150"
        >
          {hoveredNode && (() => {
            const hoveredLabel = getNodeLabel(hoveredNode);
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
                  <div className="font-mono text-[10px] text-emerald-500/90">
                    {t.graph.linksPrefix} {hoveredNode.degree} · {t.graph.tooltipHint}
                  </div>
                </div>
              </div>
            );
          })()}
        </div>

        {/* Top-Left Minimal Floating Toolbar */}
        <div className="pointer-events-none absolute left-3 right-3 top-3 z-30 flex flex-wrap items-start justify-between gap-2">
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
                className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition ${
                  layoutMode === "galaxy"
                    ? "bg-emerald-500/20 text-emerald-200"
                    : "text-emerald-500 hover:text-emerald-300"
                }`}
              >
                <Orbit className="h-3.5 w-3.5" />
                {t.graph.modeGalaxy}
              </button>
              <button
                onClick={() => setLayoutMode("map3d")}
                className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition ${
                  layoutMode === "map3d"
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
                  className={`rounded-md px-2 py-1 font-medium transition ${
                    scope === opt.id && !isolation
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
                className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition ${
                  showFilters || activeFiltersCount > 0
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
                          className={`rounded-lg border px-2 py-1.5 text-left transition ${
                            scope === opt.id
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
              className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition ${
                showPathFinder || shortestPath.nodeIds.length > 0
                  ? "border-amber-400/60 bg-amber-500/20 text-amber-200"
                  : "border-emerald-900/70 bg-[#050a08] text-emerald-300 hover:border-emerald-600"
              }`}
            >
              <GitFork className="h-3.5 w-3.5" />
              {t.graph.pathFinderBtn}
            </button>
          </div>

          {/* Active Isolation Pill */}
          {isolation && (() => {
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

        {/* Shortest Path Drawer (only when open) */}
        {showPathFinder && (
          <div className="pointer-events-auto absolute left-3 top-16 z-30 w-[min(92vw,720px)] rounded-xl border border-amber-500/40 bg-[#09120e]/95 p-3 shadow-2xl backdrop-blur-md space-y-2">
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
                    <span className="font-medium text-amber-300">
                      {t.graph.chainLabel} ({shortestPath.nodeIds.length - 1} {t.graph.stepsWord}):
                    </span>
                    {shortestPath.nodeIds.map((nid, idx) => {
                      const nd = nodeMap.get(nid);
                      if (!nd) return null;
                      const m = ENTITY_META[nd.type];
                      return (
                        <React.Fragment key={nid}>
                          {idx > 0 && <span className="text-amber-500">→</span>}
                          <button
                            onClick={() => flyToNode(nid)}
                            className={`rounded border px-2 py-0.5 text-[11px] ${m.bgClass} ${m.borderClass} ${m.textClass}`}
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
              onClick={() => setAutoRotate((v) => !v)}
              className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] transition ${
                autoRotate
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
            {t.graph.controlsHint}
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
                  className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-medium backdrop-blur-md transition ${
                    active
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
            onSelectNode={(nid) => flyToNode(nid)}
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
