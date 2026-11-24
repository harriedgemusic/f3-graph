import React, { useCallback, useState } from "react";
import {
  BarChart3,
  BookOpen,
  Database,
  Globe,
  Loader2,
  Network,
  Radio,
} from "lucide-react";
import { CatalogView } from "./components/CatalogView";
import { GraphView } from "./components/GraphView";
import { StatsView } from "./components/StatsView";
import { WalkthroughsView } from "./components/WalkthroughsView";
import { useFalloutData } from "./data/useFalloutData";
import { useI18n } from "./i18n";
import { AppTab } from "./types";

export const App: React.FC = () => {
  const { lang, setLang, t, formatNumber } = useI18n();
  const {
    loading,
    error,
    graph,
    walkthroughs,
    details,
    iconAtlas,
    nodeMap,
    walkthroughByNodeId,
    adjacency,
  } = useFalloutData(lang);

  const [activeTab, setActiveTab] = useState<AppTab>("graph");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isolation, setIsolation] = useState<{ rootId: string; hops: 1 | 2 } | null>(null);
  const [selectedWalkthroughId, setSelectedWalkthroughId] = useState<string | null>(null);

  const handleOpenOnGraph = useCallback((nodeId: string, isolate = false) => {
    setSelectedNodeId(nodeId);
    setIsolation(isolate ? { rootId: nodeId, hops: 1 } : null);
    setActiveTab("graph");
  }, []);

  const handleOpenWalkthrough = useCallback((walkthroughId: string) => {
    setSelectedWalkthroughId(walkthroughId);
    setActiveTab("walkthroughs");
  }, []);

  if (loading) {
    return (
      <div className="flex h-screen w-screen flex-col items-center justify-center gap-4 bg-[#080d0b] text-emerald-300">
        <Loader2 className="h-10 w-10 animate-spin text-emerald-400" />
        <div className="text-center">
          <div className="font-mono text-sm font-semibold tracking-wider uppercase">
            ROBCO INDUSTRIES (TM) TERMLINK
          </div>
          <div className="mt-1 text-xs text-emerald-500">
            {t.loadingSubtitle}
          </div>
        </div>
      </div>
    );
  }

  if (error || !graph) {
    return (
      <div className="flex h-screen w-screen flex-col items-center justify-center gap-3 bg-[#080d0b] p-6 text-rose-300">
        <div className="font-mono text-base font-bold">{t.errorTitle}</div>
        <div className="text-xs text-rose-400">{error ?? t.errorGraphMissing}</div>
      </div>
    );
  }

  const navItems: { id: AppTab; label: string; icon: React.ReactNode; badge?: string | number }[] = [
    {
      id: "graph",
      label: t.tabs.graph,
      icon: <Network className="h-4 w-4" />,
      badge: formatNumber(graph.meta.totalNodes),
    },
    {
      id: "walkthroughs",
      label: t.tabs.walkthroughs,
      icon: <BookOpen className="h-4 w-4" />,
      badge: walkthroughs.length,
    },
    {
      id: "catalog",
      label: t.tabs.catalog,
      icon: <Database className="h-4 w-4" />,
    },
    {
      id: "stats",
      label: t.tabs.stats,
      icon: <BarChart3 className="h-4 w-4" />,
    },
  ];

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-[#080d0b] text-[#e2ece7]">
      {/* Top Pip-Boy Tactical Navigation Bar */}
      <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-emerald-900/60 bg-[#0b120f] px-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-emerald-500/40 bg-emerald-500/15 text-emerald-300 shadow-[0_0_14px_rgba(52,211,153,0.18)]">
            <Radio className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-wide text-emerald-50">
                FALLOUT 3 GOTY
              </span>
              <span className="rounded border border-emerald-500/35 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-emerald-300">
                VAULT-TEC GRAPH
              </span>
            </div>
            <div className="hidden text-[11px] text-emerald-500/85 sm:block">
              {t.headerSubtitle}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto">
          <nav className="flex items-center gap-1.5">
            {navItems.map((item) => {
              const active = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium whitespace-nowrap transition ${
                    active
                      ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-100 shadow-[0_0_12px_rgba(52,211,153,0.15)]"
                      : "border-emerald-900/40 bg-transparent text-emerald-400/80 hover:border-emerald-700/60 hover:bg-emerald-950/50 hover:text-emerald-200"
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                  {item.badge !== undefined && (
                    <span
                      className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${
                        active
                          ? "bg-emerald-400/20 text-emerald-200"
                          : "bg-emerald-950 text-emerald-500"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Language Switcher (RU | EN) */}
          <div
            className="flex shrink-0 items-center rounded-lg border border-emerald-800/70 bg-[#070d0a] p-0.5"
            role="group"
            aria-label={t.langToggleTitle}
            title={t.langToggleTitle}
          >
            <Globe className="mx-1.5 h-3.5 w-3.5 text-emerald-500/80" />
            {(["ru", "en"] as const).map((code) => {
              const isSelected = lang === code;
              return (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLang(code)}
                  aria-pressed={isSelected}
                  className={`rounded-md px-2 py-1 font-mono text-[11px] font-semibold uppercase transition ${
                    isSelected
                      ? "bg-emerald-500/25 text-emerald-100 shadow-[0_0_8px_rgba(52,211,153,0.2)]"
                      : "text-emerald-500/80 hover:text-emerald-200"
                  }`}
                >
                  {code}
                </button>
              );
            })}
          </div>
        </div>
      </header>

      {/* Main Content Workspace */}
      <div className="relative flex-1 overflow-hidden">
        {activeTab === "graph" && (
          <GraphView
            graphData={graph}
            details={details}
            iconAtlas={iconAtlas}
            nodeMap={nodeMap}
            walkthroughByNodeId={walkthroughByNodeId}
            adjacency={adjacency}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
            isolation={isolation}
            onSetIsolation={setIsolation}
            onOpenWalkthrough={handleOpenWalkthrough}
          />
        )}

        {activeTab === "walkthroughs" && (
          <WalkthroughsView
            walkthroughs={walkthroughs}
            details={details}
            iconAtlas={iconAtlas}
            nodeMap={nodeMap}
            selectedWalkthroughId={selectedWalkthroughId}
            onSelectWalkthrough={setSelectedWalkthroughId}
            onShowQuestOnGraph={(qid) => handleOpenOnGraph(qid, true)}
            onSelectEntityOnGraph={(nid) => handleOpenOnGraph(nid, true)}
          />
        )}

        {activeTab === "catalog" && (
          <CatalogView
            nodes={graph.nodes}
            details={details}
            iconAtlas={iconAtlas}
            walkthroughByNodeId={walkthroughByNodeId}
            onOpenOnGraph={handleOpenOnGraph}
            onOpenWalkthrough={handleOpenWalkthrough}
          />
        )}

        {activeTab === "stats" && (
          <StatsView
            graph={graph}
            walkthroughs={walkthroughs}
            details={details}
            iconAtlas={iconAtlas}
            onOpenOnGraph={handleOpenOnGraph}
          />
        )}
      </div>
    </div>
  );
};

export default App;
