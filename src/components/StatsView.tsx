import React, { useMemo } from "react";
import { BarChart3, Cpu, Database, Network } from "lucide-react";
import {
  DLC_META,
  EDGE_META,
  ENTITY_META,
  getDlcLabel,
  getEdgeLabel,
  getEntityLabel,
  getEntitySingular,
  getSubtypeLabel,
} from "../constants";
import { useI18n } from "../i18n";
import { DetailsMap, DlcId, EdgeType, EntityType, GraphData, IconAtlasData, Walkthrough } from "../types";
import { EntityIcon } from "./EntityIcon";

interface StatsViewProps {
  graph: GraphData;
  walkthroughs: Walkthrough[];
  details: DetailsMap | null;
  iconAtlas: IconAtlasData | null;
  onOpenOnGraph: (nodeId: string, isolate?: boolean) => void;
}

export const StatsView: React.FC<StatsViewProps> = ({
  graph,
  walkthroughs,
  details,
  iconAtlas,
  onOpenOnGraph,
}) => {
  const { lang, t, formatNumber, getNodeLabel } = useI18n();

  const topHubs = useMemo(() => {
    const byType = new Map<EntityType, typeof graph.nodes>();
    for (const tType of ["quest", "character", "location", "event", "item", "object"] as EntityType[]) {
      const list = graph.nodes
        .filter((n) => n.type === tType && !/^(DC\d|test|dummy)/i.test(n.label))
        .sort((a, b) => b.degree - a.degree)
        .slice(0, 6);
      byType.set(tType, list);
    }
    return Array.from(byType.entries());
  }, [graph]);

  const curatedCount = useMemo(
    () => walkthroughs.filter((w) => w.curated).length,
    [walkthroughs]
  );

  return (
    <div className="h-full overflow-y-auto bg-[#080d0b] p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Hero KPIs */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-emerald-900/50 bg-[#0d1612] p-4">
            <div className="flex items-center gap-2 text-xs text-emerald-400">
              <Database className="h-4 w-4" /> {t.stats.totalNodes}
            </div>
            <div className="mt-2 font-mono text-2xl font-bold text-emerald-100">
              {formatNumber(graph.meta.totalNodes)}
            </div>
            <div className="mt-1 text-xs text-emerald-500">
              {t.stats.storyCore} {formatNumber(graph.meta.coreNodes)}
            </div>
          </div>

          <div className="rounded-xl border border-emerald-900/50 bg-[#0d1612] p-4">
            <div className="flex items-center gap-2 text-xs text-sky-400">
              <Network className="h-4 w-4" /> {t.stats.totalEdges}
            </div>
            <div className="mt-2 font-mono text-2xl font-bold text-sky-100">
              {formatNumber(graph.meta.totalEdges)}
            </div>
            <div className="mt-1 text-xs text-emerald-500">
              {t.stats.edgeTypesSubtitle}
            </div>
          </div>

          <div className="rounded-xl border border-emerald-900/50 bg-[#0d1612] p-4">
            <div className="flex items-center gap-2 text-xs text-amber-400">
              <BarChart3 className="h-4 w-4" /> {t.stats.questsWithWt}
            </div>
            <div className="mt-2 font-mono text-2xl font-bold text-amber-100">
              {formatNumber(walkthroughs.length)}
            </div>
            <div className="mt-1 text-xs text-emerald-500">
              {t.stats.curatedGuides} {curatedCount}
            </div>
          </div>

          <div className="rounded-xl border border-emerald-900/50 bg-[#0d1612] p-4">
            <div className="flex items-center gap-2 text-xs text-violet-400">
              <Cpu className="h-4 w-4" /> {t.stats.dataSource}
            </div>
            <div className="mt-2 text-sm font-semibold text-violet-100">
              {t.stats.sourceValue}
            </div>
            <div className="mt-1 text-xs text-emerald-500">
              {t.stats.sourceSub}
            </div>
          </div>
        </div>

        {/* Category & DLC breakdown */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-emerald-900/50 bg-[#0d1612] p-5 space-y-3">
            <h3 className="text-sm font-semibold text-emerald-200">
              {t.stats.byCategory}
            </h3>
            <div className="space-y-2.5">
              {(Object.keys(ENTITY_META) as EntityType[]).map((tKey) => {
                const count = graph.meta.countsByType[tKey] ?? 0;
                const pct = Math.round((count / Math.max(1, graph.meta.totalNodes)) * 100);
                const m = ENTITY_META[tKey];
                return (
                  <div key={tKey} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className={m.textClass}>{getEntityLabel(tKey, lang)}</span>
                      <span className="font-mono text-emerald-200">
                        {formatNumber(count)} ({pct}%)
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-black/50">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${Math.max(2, pct)}%`, backgroundColor: m.color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-xl border border-emerald-900/50 bg-[#0d1612] p-5 space-y-3">
            <h3 className="text-sm font-semibold text-emerald-200">
              {t.stats.byModule}
            </h3>
            <div className="space-y-2.5">
              {(Object.keys(DLC_META) as DlcId[]).map((d) => {
                const count = graph.meta.countsByDlc[d] ?? 0;
                const pct = Math.round((count / Math.max(1, graph.meta.totalNodes)) * 100);
                const dm = DLC_META[d];
                return (
                  <div key={d} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span style={{ color: dm.color }}>{getDlcLabel(d, lang)}</span>
                      <span className="font-mono text-emerald-200">
                        {formatNumber(count)} ({pct}%)
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-black/50">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${Math.max(2, pct)}%`, backgroundColor: dm.color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Edge distribution */}
        <div className="rounded-xl border border-emerald-900/50 bg-[#0d1612] p-5 space-y-3">
          <h3 className="text-sm font-semibold text-emerald-200">
            {t.stats.edgeTypesHeading}
          </h3>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(graph.meta.countsByEdgeType)
              .sort((a, b) => b[1] - a[1])
              .map(([etype, count]) => {
                const em = EDGE_META[etype as EdgeType];
                return (
                  <div
                    key={etype}
                    className="flex items-center justify-between rounded-lg border border-emerald-900/40 bg-[#09100d] px-3 py-2 text-xs"
                  >
                    <span className="flex items-center gap-2 text-emerald-100">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: em?.color ?? "#34d399" }}
                      />
                      {getEdgeLabel(etype as EdgeType, lang)}
                    </span>
                    <span className="font-mono text-emerald-300">
                      {formatNumber(count)}
                    </span>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Top Hubs */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-emerald-200">
            {t.stats.topHubsHeading}
          </h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {topHubs.map(([type, items]) => {
              const m = ENTITY_META[type];
              return (
                <div
                  key={type}
                  className="rounded-xl border border-emerald-900/50 bg-[#0d1612] p-4 space-y-2.5"
                >
                  <div className={`text-xs font-semibold uppercase tracking-wider ${m.textClass}`}>
                    {getEntityLabel(type, lang)}
                  </div>
                  <div className="space-y-1.5">
                    {items.map((item) => {
                      const itemLabel = getNodeLabel(item);
                      const role =
                        details?.[item.id]?.role ??
                        getSubtypeLabel(item.subtype, lang) ??
                        getEntitySingular(item.type, lang);
                      return (
                        <button
                          key={item.id}
                          onClick={() => onOpenOnGraph(item.id, true)}
                          className="flex w-full items-center justify-between gap-2.5 rounded-lg border border-emerald-900/40 bg-[#080d0b] px-2.5 py-2 text-left text-xs transition hover:border-emerald-500/60"
                        >
                          <div className="flex min-w-0 items-center gap-2">
                            <EntityIcon
                              iconKey={item.icon}
                              type={item.type}
                              label={itemLabel}
                              iconAtlas={iconAtlas}
                              size="sm"
                            />
                            <div className="min-w-0">
                              <div className="truncate font-medium text-emerald-100">
                                {itemLabel}
                              </div>
                              <div className="truncate text-[10px] text-emerald-400/75">
                                {role}
                              </div>
                            </div>
                          </div>
                          <span className="shrink-0 rounded border border-emerald-900/50 bg-emerald-950/60 px-1.5 py-0.5 font-mono text-[11px] text-emerald-300">
                            {item.degree}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
