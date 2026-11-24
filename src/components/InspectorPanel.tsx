import React, { useMemo, useState } from "react";
import { BookOpen, Focus, GitFork, Layers, Maximize2, Minimize2, X } from "lucide-react";
import {
  DLC_META,
  EDGE_META,
  ENTITY_META,
  getDlcLabel,
  getDlcShort,
  getEdgeLabel,
  getEntitySingular,
  getSubtypeLabel,
} from "../constants";
import { NeighborEntry } from "../data/useFalloutData";
import { useI18n } from "../i18n";
import { DetailsMap, EdgeType, GraphNode, IconAtlasData, Walkthrough } from "../types";
import { EncyclopediaDetailsBlock } from "./EncyclopediaDetailsBlock";
import { EntityIcon } from "./EntityIcon";

interface InspectorPanelProps {
  node: GraphNode;
  details: DetailsMap | null;
  iconAtlas: IconAtlasData | null;
  neighbors: NeighborEntry[];
  walkthrough?: Walkthrough;
  isIsolated: boolean;
  onClose: () => void;
  onSelectNode: (nodeId: string) => void;
  onIsolateNode: (nodeId: string, hops: 1 | 2) => void;
  onClearIsolation: () => void;
  onStartPathFrom: (nodeId: string) => void;
  onOpenWalkthrough: (walkthroughId: string) => void;
}

export const InspectorPanel: React.FC<InspectorPanelProps> = ({
  node,
  details,
  iconAtlas,
  neighbors,
  walkthrough,
  isIsolated,
  onClose,
  onSelectNode,
  onIsolateNode,
  onClearIsolation,
  onStartPathFrom,
  onOpenWalkthrough,
}) => {
  const { lang, t, getNodeLabel, getNodeAltLabel } = useI18n();
  const [neighborFilter, setNeighborFilter] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);

  const meta = ENTITY_META[node.type];
  const dlc = DLC_META[node.dlc];
  const detail = details?.[node.id];
  const displayLabel = getNodeLabel(node);
  const altLabel = getNodeAltLabel(node);

  const groupedNeighbors = useMemo(() => {
    const q = neighborFilter.trim().toLowerCase();
    const groups = new Map<EdgeType, NeighborEntry[]>();
    for (const entry of neighbors) {
      if (
        q &&
        !entry.node.label.toLowerCase().includes(q) &&
        !entry.node.labelEn.toLowerCase().includes(q) &&
        !entry.node.edid.toLowerCase().includes(q)
      ) {
        continue;
      }
      const list = groups.get(entry.edge.type) ?? [];
      list.push(entry);
      groups.set(entry.edge.type, list);
    }
    return Array.from(groups.entries());
  }, [neighbors, neighborFilter]);

  return (
    <aside
      className={`flex h-full flex-col border-l border-emerald-900/50 bg-[#0b120f]/95 backdrop-blur-md transition-[width] duration-200 ${
        isExpanded
          ? "w-88 sm:w-[640px] lg:w-[740px]"
          : "w-88 sm:w-[430px] lg:w-[470px]"
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 border-b border-emerald-900/40 p-4">
        <EntityIcon
          iconKey={node.icon}
          type={node.type}
          label={displayLabel}
          iconAtlas={iconAtlas}
          size="lg"
        />
        <div className="min-w-0 flex-1">
          <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
            <span
              className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[11px] font-medium ${meta.bgClass} ${meta.borderClass} ${meta.textClass}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${meta.dotClass}`} />
              {getSubtypeLabel(node.subtype, lang) ?? getEntitySingular(node.type, lang)}
            </span>
            <span
              className="inline-flex items-center rounded border border-emerald-800/60 bg-emerald-950/60 px-2 py-0.5 text-[11px] text-emerald-300/90"
              style={{ borderColor: `${dlc.color}40`, color: dlc.color }}
            >
              {getDlcShort(node.dlc, lang)}
            </span>
            <span className="inline-flex items-center rounded border border-emerald-900/60 bg-black/30 px-2 py-0.5 font-mono text-[11px] text-emerald-400">
              {t.graph.linksPrefix} {node.degree}
            </span>
          </div>
          <h2 className="text-base font-bold leading-snug text-emerald-50 break-words sm:text-lg">
            {displayLabel}
          </h2>
          {altLabel && <p className="mt-0.5 text-xs text-emerald-400/75">{altLabel}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            type="button"
            onClick={() => setIsExpanded((v) => !v)}
            className={`hidden items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-medium transition sm:inline-flex ${
              isExpanded
                ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-100"
                : "border-emerald-900/50 bg-emerald-950/40 text-emerald-300 hover:border-emerald-500/50 hover:text-emerald-100"
            }`}
            title={isExpanded ? t.inspector.collapseTitle : t.inspector.expandTitle}
          >
            {isExpanded ? (
              <>
                <Minimize2 className="h-3.5 w-3.5" />
                <span>{t.inspector.compactLabel}</span>
              </>
            ) : (
              <>
                <Maximize2 className="h-3.5 w-3.5" />
                <span>{t.inspector.expandLabel}</span>
              </>
            )}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-emerald-900/50 bg-emerald-950/40 p-1.5 text-emerald-400 transition hover:border-emerald-500/50 hover:text-emerald-200"
            title={t.inspector.closeTitle}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2 border-b border-emerald-900/40 px-4 py-2.5">
        {walkthrough && (
          <button
            onClick={() => onOpenWalkthrough(walkthrough.id)}
            className="inline-flex items-center gap-1.5 rounded-md border border-amber-500/50 bg-amber-500/15 px-2.5 py-1.5 text-xs font-semibold text-amber-300 transition hover:bg-amber-500/25"
          >
            <BookOpen className="h-3.5 w-3.5" />
            {t.inspector.openWalkthrough}
          </button>
        )}
        <button
          onClick={() => (isIsolated ? onClearIsolation() : onIsolateNode(node.id, 1))}
          className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition ${
            isIsolated
              ? "border-sky-400/60 bg-sky-500/20 text-sky-200"
              : "border-emerald-800/70 bg-emerald-950/60 text-emerald-200 hover:border-emerald-500/60"
          }`}
        >
          <Focus className="h-3.5 w-3.5" />
          {isIsolated ? t.inspector.clearIsolation : t.inspector.isolate1Hop}
        </button>
        <button
          onClick={() => onIsolateNode(node.id, 2)}
          className="inline-flex items-center gap-1.5 rounded-md border border-emerald-800/70 bg-emerald-950/60 px-2.5 py-1.5 text-xs font-medium text-emerald-200 transition hover:border-emerald-500/60"
        >
          <Layers className="h-3.5 w-3.5" />
          {t.inspector.isolate2Hops}
        </button>
        <button
          onClick={() => onStartPathFrom(node.id)}
          className="inline-flex items-center gap-1.5 rounded-md border border-emerald-800/70 bg-emerald-950/60 px-2.5 py-1.5 text-xs font-medium text-emerald-200 transition hover:border-emerald-500/60"
        >
          <GitFork className="h-3.5 w-3.5" />
          {t.inspector.findPath}
        </button>
      </div>

      {/* Scrollable Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <EncyclopediaDetailsBlock
          node={node}
          detail={detail}
          onSelectNode={onSelectNode}
          compact={!isExpanded}
        />

        {/* Neighbors list */}
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
              {t.inspector.connectedEntities} ({neighbors.length})
            </h3>
          </div>
          {neighbors.length > 6 && (
            <input
              type="text"
              value={neighborFilter}
              onChange={(e) => setNeighborFilter(e.target.value)}
              placeholder={t.inspector.filterLinksPlaceholder}
              className="w-full rounded-md border border-emerald-900/60 bg-[#080d0b] px-2.5 py-1.5 text-xs text-emerald-100 placeholder-emerald-600 focus:border-emerald-500 focus:outline-none"
            />
          )}
          {groupedNeighbors.length === 0 ? (
            <p className="text-xs text-emerald-500/70">{t.inspector.noMatchingLinks}</p>
          ) : (
            <div className="space-y-3">
              {groupedNeighbors.map(([edgeType, list]) => {
                const em = EDGE_META[edgeType] ?? { label: edgeType, labelEn: edgeType, color: "#34d399" };
                return (
                  <div key={edgeType} className="space-y-1">
                    <div className="flex items-center justify-between text-[11px] font-medium text-emerald-400/90">
                      <span className="flex items-center gap-1.5">
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ backgroundColor: em.color }}
                        />
                        {getEdgeLabel(edgeType, lang)}
                      </span>
                      <span className="font-mono text-emerald-600">{list.length}</span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {list.slice(0, 40).map((entry) => {
                        const nm = ENTITY_META[entry.node.type];
                        const entryLabel = getNodeLabel(entry.node);
                        const iconUrl =
                          entry.node.icon && iconAtlas
                            ? iconAtlas.icons[entry.node.icon]?.url
                            : undefined;
                        return (
                          <button
                            key={`${entry.edge.id}-${entry.node.id}`}
                            onClick={() => onSelectNode(entry.node.id)}
                            className={`inline-flex max-w-full items-center gap-1.5 rounded border px-2 py-0.5 text-left text-[11px] transition hover:brightness-125 ${nm.bgClass} ${nm.borderClass} ${nm.textClass}`}
                            title={`${entryLabel} (${entry.node.edid})`}
                          >
                            {iconUrl ? (
                              <img
                                src={iconUrl}
                                alt=""
                                className="h-3.5 w-3.5 shrink-0 object-contain"
                                loading="lazy"
                              />
                            ) : (
                              <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${nm.dotClass}`} />
                            )}
                            <span className="truncate">{entryLabel}</span>
                          </button>
                        );
                      })}
                      {list.length > 40 && (
                        <span className="px-1.5 py-0.5 text-[11px] text-emerald-500">
                          +{list.length - 40} {t.inspector.moreCount}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Muted Technical ESM Footer */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-emerald-900/35 pt-2.5 font-mono text-[10px] text-emerald-600/80">
          <span>FormID: {node.fid}</span>
          <span>EDID: {node.edid || "—"}</span>
          <span>{getDlcLabel(node.dlc, lang)}</span>
        </div>
      </div>
    </aside>
  );
};
