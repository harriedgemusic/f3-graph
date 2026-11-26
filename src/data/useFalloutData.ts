import { useEffect, useMemo, useRef, useState } from "react";
import { getNodeLabel, Lang } from "../i18n";
import {
  DetailsMap,
  GraphData,
  GraphEdge,
  GraphNode,
  IconAtlasData,
  Walkthrough,
} from "../types";

export interface NeighborEntry {
  node: GraphNode;
  edge: GraphEdge;
  direction: "out" | "in";
}

function getNeighborNavPriority(entry: NeighborEntry): number {
  const n = entry.node;
  const et = entry.edge.type;
  let score = 0;

  if (et === "quest_chain") score += 900;
  else if (et === "quest_event") score += 820;
  else if (et === "quest_npc" || et === "quest_location") score += 760;
  else if (et === "event_entity") score += 680;
  else if (et === "npc_location") score += 620;
  else if (et === "quest_item" || et === "quest_object" || et === "object_key") score += 540;
  else if (et === "location_connection") score += 460;
  else if (et === "npc_item") score += 260;
  else if (et === "location_object") score += 130;
  else if (et === "location_item") score += 50;

  if (n.type === "quest") score += n.subtype === "main" ? 340 : 250;
  else if (n.type === "event") score += 240;
  else if (n.type === "character") score += n.subtype === "npc" ? 200 : 120;
  else if (n.type === "location") {
    if (n.subtype === "marker") score += 220;
    else if (n.subtype === "world") score -= 220;
    else score += 110;
  } else if (n.type === "item") {
    if (n.subtype === "key" || n.subtype === "note" || n.subtype === "book") score += 140;
    else if (n.degree > 40) score -= 260;
  } else if (n.type === "object") {
    if (n.subtype === "perk" || n.subtype === "terminal") score += 150;
    else if (/^(дверь|door|лестница|ladder|люк)$/i.test(n.label)) score -= 180;
  }

  score += Math.min(35, Math.sqrt(Math.max(1, n.degree)) * 4.5);
  return score;
}

export interface FalloutDataState {
  loading: boolean;
  error: string | null;
  graph: GraphData | null;
  walkthroughs: Walkthrough[];
  details: DetailsMap | null;
  iconAtlas: IconAtlasData | null;
  nodeMap: Map<string, GraphNode>;
  walkthroughById: Map<string, Walkthrough>;
  walkthroughByNodeId: Map<string, Walkthrough>;
  adjacency: Map<string, NeighborEntry[]>;
}

export function useFalloutData(lang: Lang): FalloutDataState {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [walkthroughs, setWalkthroughs] = useState<Walkthrough[]>([]);
  const [details, setDetails] = useState<DetailsMap | null>(null);
  const [iconAtlas, setIconAtlas] = useState<IconAtlasData | null>(null);

  const wtCacheRef = useRef<Partial<Record<Lang, Walkthrough[]>>>({});
  const detCacheRef = useRef<Partial<Record<Lang, DetailsMap>>>({});

  // Load graph.json and icon atlas once (language-independent structure)
  useEffect(() => {
    let cancelled = false;
    async function loadBase() {
      try {
        setLoading(true);
        const [graphRes, atlasRes] = await Promise.all([
          fetch("/data/graph.json"),
          fetch("/icons/atlas.json"),
        ]);
        if (!graphRes.ok) {
          throw new Error(`Failed to load graph.json (${graphRes.status})`);
        }
        const graphJson = (await graphRes.json()) as GraphData;
        let atlasJson: IconAtlasData | null = null;
        if (atlasRes.ok) {
          atlasJson = (await atlasRes.json()) as IconAtlasData;
        }
        if (cancelled) return;
        setGraph(graphJson);
        setIconAtlas(atlasJson);
        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown data loading error");
          setLoading(false);
        }
      }
    }
    void loadBase();
    return () => {
      cancelled = true;
    };
  }, []);

  // Load localized walkthroughs and details on initial mount and language switch, with caching
  useEffect(() => {
    let cancelled = false;
    const wtUrl = lang === "en" ? "/data/walkthroughs.en.json" : "/data/walkthroughs.json";
    const detUrl = lang === "en" ? "/data/details.en.json" : "/data/details.json";

    async function loadLocalized() {
      const cachedWt = wtCacheRef.current[lang];
      const cachedDet = detCacheRef.current[lang];
      if (cachedWt) {
        setWalkthroughs(cachedWt);
      }
      if (cachedDet) {
        setDetails(cachedDet);
      }
      if (cachedWt && cachedDet) return;

      try {
        if (!cachedWt) {
          const wtRes = await fetch(wtUrl);
          if (!wtRes.ok) throw new Error(`Failed to load ${wtUrl} (${wtRes.status})`);
          const wtJson = (await wtRes.json()) as Walkthrough[];
          if (cancelled) return;
          wtCacheRef.current[lang] = wtJson;
          setWalkthroughs(wtJson);
        }

        if (!cachedDet) {
          const detRes = await fetch(detUrl);
          if (detRes.ok && !cancelled) {
            const detJson = (await detRes.json()) as DetailsMap;
            if (!cancelled) {
              detCacheRef.current[lang] = detJson;
              setDetails(detJson);
            }
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown data loading error");
        }
      }
    }

    void loadLocalized();
    return () => {
      cancelled = true;
    };
  }, [lang]);

  const nodeMap = useMemo(() => {
    const map = new Map<string, GraphNode>();
    if (graph) {
      for (const n of graph.nodes) map.set(n.id, n);
    }
    return map;
  }, [graph]);

  const walkthroughById = useMemo(() => {
    const map = new Map<string, Walkthrough>();
    for (const w of walkthroughs) map.set(w.id, w);
    return map;
  }, [walkthroughs]);

  const walkthroughByNodeId = useMemo(() => {
    const map = new Map<string, Walkthrough>();
    for (const w of walkthroughs) map.set(w.nodeId, w);
    return map;
  }, [walkthroughs]);

  const adjacency = useMemo(() => {
    const map = new Map<string, NeighborEntry[]>();
    if (!graph) return map;
    for (const e of graph.edges) {
      const src = nodeMap.get(e.source);
      const tgt = nodeMap.get(e.target);
      if (!src || !tgt) continue;
      let listA = map.get(e.source);
      if (!listA) {
        listA = [];
        map.set(e.source, listA);
      }
      listA.push({ node: tgt, edge: e, direction: "out" });

      let listB = map.get(e.target);
      if (!listB) {
        listB = [];
        map.set(e.target, listB);
      }
      listB.push({ node: src, edge: e, direction: "in" });
    }
    const locale = lang === "en" ? "en" : "ru";
    for (const list of map.values()) {
      list.sort(
        (a, b) =>
          getNeighborNavPriority(b) - getNeighborNavPriority(a) ||
          b.node.degree - a.node.degree ||
          getNodeLabel(a.node, lang).localeCompare(getNodeLabel(b.node, lang), locale)
      );
    }
    return map;
  }, [graph, nodeMap, lang]);

  return {
    loading,
    error,
    graph,
    walkthroughs,
    details,
    iconAtlas,
    nodeMap,
    walkthroughById,
    walkthroughByNodeId,
    adjacency,
  };
}
