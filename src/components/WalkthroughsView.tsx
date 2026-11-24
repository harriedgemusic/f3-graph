import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Award,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  Compass,
  ExternalLink,
  FileText,
  GitBranch,
  Lightbulb,
  Network,
  Search,
  Sparkles,
} from "lucide-react";
import {
  DLC_META,
  ENTITY_META,
  WALKTHROUGH_GROUP_ORDER,
  getDlcLabel,
} from "../constants";
import { useI18n } from "../i18n";
import { DetailsMap, DlcId, GraphNode, IconAtlasData, Walkthrough } from "../types";
import { EntityIcon } from "./EntityIcon";

interface WalkthroughsViewProps {
  walkthroughs: Walkthrough[];
  details: DetailsMap | null;
  iconAtlas: IconAtlasData | null;
  nodeMap: Map<string, GraphNode>;
  selectedWalkthroughId: string | null;
  onSelectWalkthrough: (id: string) => void;
  onShowQuestOnGraph: (questNodeId: string) => void;
  onSelectEntityOnGraph: (entityNodeId: string) => void;
}

type CategoryFilter = "all" | "main" | "side" | "dlc" | "freeform";

const STORAGE_KEY = "f3_graph_walkthrough_progress_v1";

interface ProgressState {
  completedQuests: Record<string, boolean>;
  completedSteps: Record<string, boolean>;
}

const TONE_CLASS_MAP: Record<
  "good" | "evil" | "neutral" | "alt",
  { border: string; bg: string; badge: string }
> = {
  good: {
    border: "border-emerald-500/40",
    bg: "bg-emerald-500/10",
    badge: "bg-emerald-500/20 text-emerald-300",
  },
  evil: {
    border: "border-rose-500/40",
    bg: "bg-rose-500/10",
    badge: "bg-rose-500/20 text-rose-300",
  },
  neutral: {
    border: "border-sky-500/40",
    bg: "bg-sky-500/10",
    badge: "bg-sky-500/20 text-sky-300",
  },
  alt: {
    border: "border-amber-500/40",
    bg: "bg-amber-500/10",
    badge: "bg-amber-500/20 text-amber-300",
  },
};

export const WalkthroughsView: React.FC<WalkthroughsViewProps> = ({
  walkthroughs,
  details,
  iconAtlas,
  nodeMap,
  selectedWalkthroughId,
  onSelectWalkthrough,
  onShowQuestOnGraph,
  onSelectEntityOnGraph,
}) => {
  const { lang, t, getNodeLabel, getWalkthroughTitle } = useI18n();
  const [query, setQuery] = useState("");
  const [dlcFilter, setDlcFilter] = useState<DlcId | "all">("all");
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("all");
  const [showEsmLogs, setShowEsmLogs] = useState(false);
  const [showQuestLore, setShowQuestLore] = useState(true);

  const [progress, setProgress] = useState<ProgressState>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved) as ProgressState;
    } catch {
      // ignore storage errors
    }
    return { completedQuests: {}, completedSteps: {} };
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
    } catch {
      // ignore storage errors
    }
  }, [progress]);

  const activeWalkthrough = useMemo(() => {
    if (selectedWalkthroughId) {
      const found = walkthroughs.find((w) => w.id === selectedWalkthroughId);
      if (found) return found;
    }
    return walkthroughs[0] ?? null;
  }, [walkthroughs, selectedWalkthroughId]);

  const filteredList = useMemo(() => {
    const q = query.trim().toLowerCase();
    return walkthroughs.filter((w) => {
      if (dlcFilter !== "all" && w.dlc !== dlcFilter) return false;
      if (categoryFilter === "main" && w.category !== "main") return false;
      if (categoryFilter === "side" && w.category !== "side") return false;
      if (categoryFilter === "freeform" && w.category !== "freeform") return false;
      if (
        categoryFilter === "dlc" &&
        !["anchorage", "pitt", "brokensteel", "pointlookout", "zeta"].includes(w.category)
      ) {
        return false;
      }
      if (
        q &&
        !w.title.toLowerCase().includes(q) &&
        !w.titleEn.toLowerCase().includes(q) &&
        !w.edid.toLowerCase().includes(q) &&
        !w.summary.toLowerCase().includes(q)
      ) {
        return false;
      }
      return true;
    });
  }, [walkthroughs, query, dlcFilter, categoryFilter]);

  const groupedList = useMemo(() => {
    const groups: { id: string; label: string; items: Walkthrough[] }[] = [];
    for (const g of WALKTHROUGH_GROUP_ORDER) {
      const items = filteredList.filter((w) => w.category === g.id);
      if (items.length > 0) {
        groups.push({ id: g.id, label: lang === "en" ? g.labelEn : g.label, items });
      }
    }
    return groups;
  }, [filteredList, lang]);

  const completedCount = useMemo(
    () => walkthroughs.filter((w) => progress.completedQuests[w.id]).length,
    [walkthroughs, progress.completedQuests]
  );

  const activeStepProgress = useMemo(() => {
    if (!activeWalkthrough) return { done: 0, total: 0, pct: 0 };
    const total = activeWalkthrough.steps.length;
    if (total === 0) return { done: 0, total: 0, pct: 0 };
    let done = 0;
    for (let i = 0; i < total; i++) {
      if (progress.completedSteps[`${activeWalkthrough.id}:${i}`]) done++;
    }
    return { done, total, pct: Math.round((done / total) * 100) };
  }, [activeWalkthrough, progress.completedSteps]);

  const activeQuestDetail = activeWalkthrough ? details?.[activeWalkthrough.nodeId] : undefined;
  const activeQuestSections = useMemo(
    () =>
      (activeQuestDetail?.sections ?? []).filter(
        (s) => s.title.trim().length > 0 || s.text.trim().length > 0
      ),
    [activeQuestDetail]
  );

  const toggleQuestDone = (id: string) => {
    setProgress((prev) => ({
      ...prev,
      completedQuests: {
        ...prev.completedQuests,
        [id]: !prev.completedQuests[id],
      },
    }));
  };

  const toggleStepDone = (questId: string, stepIdx: number) => {
    const key = `${questId}:${stepIdx}`;
    setProgress((prev) => ({
      ...prev,
      completedSteps: {
        ...prev.completedSteps,
        [key]: !prev.completedSteps[key],
      },
    }));
  };

  const toneLabels: Record<"good" | "evil" | "neutral" | "alt", string> = {
    good: t.walkthroughs.toneGood,
    evil: t.walkthroughs.toneEvil,
    neutral: t.walkthroughs.toneNeutral,
    alt: t.walkthroughs.toneAlt,
  };

  const entityGroups = useMemo(() => {
    if (!activeWalkthrough) return [];
    const le = activeWalkthrough.linkedEntities;
    const defs: {
      key: keyof Walkthrough["linkedEntities"];
      type: "character" | "location" | "event" | "item" | "object" | "quest";
      title: string;
    }[] = [
      { key: "characters", type: "character", title: t.walkthroughs.groupCharacters },
      { key: "locations", type: "location", title: t.walkthroughs.groupLocations },
      { key: "events", type: "event", title: t.walkthroughs.groupEvents },
      { key: "items", type: "item", title: t.walkthroughs.groupItems },
      { key: "objects", type: "object", title: t.walkthroughs.groupObjects },
      { key: "quests", type: "quest", title: t.walkthroughs.groupQuests },
    ];
    return defs
      .map((d) => ({
        ...d,
        nodes: le[d.key]
          .map((id) => nodeMap.get(id))
          .filter((n): n is GraphNode => Boolean(n)),
      }))
      .filter((g) => g.nodes.length > 0);
  }, [activeWalkthrough, nodeMap, t]);

  const activeTitle = activeWalkthrough ? getWalkthroughTitle(activeWalkthrough) : "";
  const showAltTitle =
    lang === "ru" &&
    activeWalkthrough &&
    activeWalkthrough.titleEn &&
    activeWalkthrough.titleEn !== activeWalkthrough.title;

  return (
    <div className="flex h-full overflow-hidden bg-[#080d0b]">
      {/* Left Sidebar: Mission List */}
      <aside className="flex h-full w-80 shrink-0 flex-col border-r border-emerald-900/50 bg-[#0b120f] lg:w-96">
        <div className="border-b border-emerald-900/40 p-3.5 space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-300">
              <BookOpen className="h-4 w-4" />
              {t.walkthroughs.archiveTitle}
            </div>
            <span className="rounded bg-emerald-950 px-2 py-0.5 font-mono text-[11px] text-emerald-300">
              {completedCount}/{walkthroughs.length} {t.walkthroughs.completedRatio}
            </span>
          </div>

          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-emerald-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t.walkthroughs.searchPlaceholder}
              className="w-full rounded-lg border border-emerald-900/60 bg-[#080d0b] py-1.5 pl-8 pr-3 text-xs text-emerald-100 placeholder-emerald-600 focus:border-emerald-500 focus:outline-none"
            />
          </div>

          {/* Quick Category Filter Pills */}
          <div className="flex flex-wrap gap-1">
            {(
              [
                { id: "all" as CategoryFilter, label: t.walkthroughs.filterAll },
                { id: "main" as CategoryFilter, label: t.walkthroughs.filterMain },
                { id: "side" as CategoryFilter, label: t.walkthroughs.filterSide },
                { id: "dlc" as CategoryFilter, label: t.walkthroughs.filterDlc },
                { id: "freeform" as CategoryFilter, label: t.walkthroughs.filterFreeform },
              ] as const
            ).map((pill) => (
              <button
                key={pill.id}
                type="button"
                onClick={() => setCategoryFilter(pill.id)}
                className={`rounded-md border px-2 py-0.5 text-[11px] font-medium transition ${
                  categoryFilter === pill.id
                    ? "border-amber-400/60 bg-amber-500/20 text-amber-200"
                    : "border-emerald-900/60 bg-[#080d0b] text-emerald-400/80 hover:border-emerald-700 hover:text-emerald-200"
                }`}
              >
                {pill.label}
              </button>
            ))}
          </div>

          <select
            value={dlcFilter}
            onChange={(e) => setDlcFilter(e.target.value as DlcId | "all")}
            className="w-full rounded-lg border border-emerald-900/60 bg-[#080d0b] px-2.5 py-1.5 text-xs text-emerald-200 focus:border-emerald-500 focus:outline-none"
          >
            <option value="all">
              {t.walkthroughs.allCampaigns} ({walkthroughs.length})
            </option>
            {(Object.keys(DLC_META) as DlcId[]).map((id) => (
              <option key={id} value={id}>
                {getDlcLabel(id, lang)}
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1 overflow-y-auto p-2.5 space-y-4">
          {groupedList.length === 0 ? (
            <p className="p-3 text-xs text-emerald-500">{t.walkthroughs.notFound}</p>
          ) : (
            groupedList.map((group) => (
              <div key={group.id} className="space-y-1">
                <div className="sticky top-0 z-10 bg-[#0b120f]/95 px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-emerald-400/90 backdrop-blur">
                  {group.label} ({group.items.length})
                </div>
                {group.items.map((w) => {
                  const isActive = activeWalkthrough?.id === w.id;
                  const isDone = Boolean(progress.completedQuests[w.id]);
                  const wTitle = getWalkthroughTitle(w);
                  return (
                    <button
                      key={w.id}
                      onClick={() => {
                        onSelectWalkthrough(w.id);
                        setShowEsmLogs(false);
                      }}
                      className={`flex w-full items-start gap-2 rounded-lg border px-2.5 py-2 text-left transition ${
                        isActive
                          ? "border-amber-500/60 bg-amber-500/12 text-amber-100"
                          : "border-transparent bg-transparent text-emerald-200/85 hover:border-emerald-900/60 hover:bg-emerald-950/40"
                      }`}
                    >
                      <span className="mt-0.5 shrink-0">
                        {isDone ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                        ) : (
                          <Circle className="h-3.5 w-3.5 text-emerald-700" />
                        )}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-1.5">
                          <span className="truncate text-xs font-medium">{wTitle}</span>
                          {w.curated && (
                            <span className="shrink-0 rounded bg-amber-500/15 px-1.5 py-0.5 text-[9px] font-semibold text-amber-300">
                              {t.walkthroughs.guideBadge}
                            </span>
                          )}
                        </div>
                        <div className="mt-0.5 flex items-center gap-2 font-mono text-[10px] text-emerald-500/80">
                          <span>{w.edid}</span>
                          <span>
                            • {w.steps.length} {t.walkthroughs.stepsShort}
                          </span>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>
      </aside>

      {/* Main Walkthrough Detail View */}
      <main className="flex-1 overflow-y-auto p-6">
        {!activeWalkthrough ? (
          <div className="flex h-full items-center justify-center text-sm text-emerald-500">
            {t.walkthroughs.emptyState}
          </div>
        ) : (
          <div className="mx-auto max-w-4xl space-y-6">
            {/* Header Card */}
            <div className="rounded-2xl border border-emerald-900/50 bg-[#0d1612] p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex items-start gap-3.5">
                  <EntityIcon
                    iconKey={nodeMap.get(activeWalkthrough.nodeId)?.icon}
                    type="quest"
                    label={activeTitle}
                    iconAtlas={iconAtlas}
                    size="lg"
                  />
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className="rounded border px-2 py-0.5 text-xs font-medium"
                        style={{
                          borderColor: `${DLC_META[activeWalkthrough.dlc].color}45`,
                          color: DLC_META[activeWalkthrough.dlc].color,
                          backgroundColor: `${DLC_META[activeWalkthrough.dlc].color}15`,
                        }}
                      >
                        {getDlcLabel(activeWalkthrough.dlc, lang)}
                      </span>
                      <span className="rounded border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 font-mono text-xs text-amber-300">
                        {activeWalkthrough.edid} • {activeWalkthrough.fid}
                      </span>
                    </div>
                    <h1 className="text-2xl font-bold text-emerald-50">{activeTitle}</h1>
                    {showAltTitle && (
                      <p className="text-sm text-emerald-400/75">{activeWalkthrough.titleEn}</p>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => toggleQuestDone(activeWalkthrough.id)}
                    className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold transition ${
                      progress.completedQuests[activeWalkthrough.id]
                        ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-200"
                        : "border-emerald-800/70 bg-[#080d0b] text-emerald-300 hover:border-emerald-500"
                    }`}
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {progress.completedQuests[activeWalkthrough.id]
                      ? t.walkthroughs.questCompleted
                      : t.walkthroughs.markCompleted}
                  </button>

                  <button
                    onClick={() => onShowQuestOnGraph(activeWalkthrough.nodeId)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-amber-400/60 bg-amber-500/20 px-3.5 py-2 text-xs font-semibold text-amber-200 transition hover:bg-amber-500/30"
                  >
                    <Network className="h-4 w-4" />
                    {t.walkthroughs.showOnGraph}
                  </button>
                </div>
              </div>

              <p className="mt-4 text-sm leading-relaxed text-emerald-100/90">
                {activeWalkthrough.summary}
              </p>

              {/* Step-Completion Progress Bar */}
              {activeStepProgress.total > 0 && (
                <div className="mt-4 rounded-xl border border-emerald-900/50 bg-[#080d0b] px-4 py-3">
                  <div className="mb-1.5 flex items-center justify-between text-xs">
                    <span className="font-medium text-emerald-300">
                      {t.walkthroughs.stepsProgressPrefix}{" "}
                      <strong className="font-mono text-emerald-100">
                        {activeStepProgress.done}
                      </strong>{" "}
                      {t.walkthroughs.of}{" "}
                      <strong className="font-mono text-emerald-100">
                        {activeStepProgress.total}
                      </strong>
                    </span>
                    <span className="font-mono text-[11px] font-semibold text-amber-300">
                      {activeStepProgress.pct}%
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-emerald-950/90">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-amber-400 transition-all duration-300"
                      style={{ width: `${activeStepProgress.pct}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Brief Meta Grid */}
              <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-emerald-900/50 bg-[#080d0b] p-3.5">
                  <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-sky-300">
                    <Compass className="h-3.5 w-3.5" />
                    {t.walkthroughs.howToStart}
                  </div>
                  <p className="text-xs leading-relaxed text-emerald-200/85">
                    {activeWalkthrough.startCondition}
                  </p>
                </div>

                <div className="rounded-xl border border-emerald-900/50 bg-[#080d0b] p-3.5">
                  <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-amber-300">
                    <Award className="h-3.5 w-3.5" />
                    {t.walkthroughs.keyRewards}
                  </div>
                  <ul className="space-y-1 text-xs text-emerald-200/85">
                    {activeWalkthrough.rewards.map((r, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-amber-400">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Warnings */}
              {activeWalkthrough.missableWarnings &&
                activeWalkthrough.missableWarnings.length > 0 && (
                  <div className="mt-3 rounded-xl border border-rose-500/35 bg-rose-500/10 p-3.5">
                    <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-rose-300">
                      <AlertTriangle className="h-4 w-4" />
                      {t.walkthroughs.missableWarnings}
                    </div>
                    <ul className="space-y-1 text-xs text-rose-100/90">
                      {activeWalkthrough.missableWarnings.map((w, i) => (
                        <li key={i}>• {w}</li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>

            {/* Integrated Encyclopedia Lore & Background Sections */}
            {activeQuestSections.length > 0 && (
              <div className="rounded-2xl border border-emerald-900/50 bg-[#0d1612] overflow-hidden">
                <button
                  type="button"
                  onClick={() => setShowQuestLore((v) => !v)}
                  className="flex w-full items-center justify-between px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-emerald-300 hover:bg-emerald-950/30"
                >
                  <span className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-emerald-400" />
                    <span>
                      {t.walkthroughs.loreHeading} ({activeQuestSections.length})
                    </span>
                  </span>
                  {showQuestLore ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </button>

                {showQuestLore && (
                  <div className="border-t border-emerald-900/40 p-5 space-y-3">
                    {activeQuestDetail?.wikiUrl && (
                      <div className="flex items-center justify-between rounded-lg border border-emerald-900/50 bg-[#080d0b] px-3.5 py-2 text-xs">
                        <span className="text-emerald-300/90">
                          {activeQuestDetail.role ?? t.details.wikiDefaultLabel}
                        </span>
                        <a
                          href={activeQuestDetail.wikiUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 rounded border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-[11px] font-medium text-amber-300 transition hover:border-amber-400/70 hover:bg-amber-500/20"
                        >
                          <ExternalLink className="h-3 w-3" />
                          Fallout Wiki
                        </a>
                      </div>
                    )}
                    <div className="grid grid-cols-1 gap-3">
                      {activeQuestSections.map((sec, sIdx) => (
                        <section
                          key={`${sec.title}-${sIdx}`}
                          className="rounded-xl border border-emerald-900/50 bg-[#080d0b] p-4 space-y-1.5"
                        >
                          {sec.title && (
                            <h3 className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-emerald-300">
                              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                              <span>{sec.title}</span>
                            </h3>
                          )}
                          {sec.text && (
                            <p className="text-[13px] leading-relaxed text-emerald-100/90 whitespace-pre-line">
                              {sec.text}
                            </p>
                          )}
                        </section>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step-by-Step Walkthrough */}
            <div className="space-y-3">
              <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-emerald-300">
                <Sparkles className="h-4 w-4 text-amber-400" />
                {t.walkthroughs.stepsHeading} ({activeWalkthrough.steps.length})
              </h2>

              <div className="space-y-3">
                {activeWalkthrough.steps.map((step, idx) => {
                  const stepKey = `${activeWalkthrough.id}:${idx}`;
                  const done = Boolean(progress.completedSteps[stepKey]);
                  return (
                    <div
                      key={idx}
                      className={`rounded-xl border p-4 transition ${
                        done
                          ? "border-emerald-500/40 bg-emerald-950/25"
                          : "border-emerald-900/50 bg-[#0d1612]"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <button
                          onClick={() => toggleStepDone(activeWalkthrough.id, idx)}
                          className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border font-mono text-xs font-bold transition ${
                            done
                              ? "border-emerald-400 bg-emerald-500/25 text-emerald-200"
                              : "border-emerald-700 bg-[#080d0b] text-emerald-400 hover:border-emerald-400"
                          }`}
                          title={t.walkthroughs.markStepTitle}
                        >
                          {done ? "✓" : idx + 1}
                        </button>

                        <div className="min-w-0 flex-1 space-y-2">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <h3
                              className={`text-sm font-semibold ${
                                done ? "text-emerald-300 line-through" : "text-emerald-50"
                              }`}
                            >
                              {step.title}
                            </h3>

                            {step.skillChecks && step.skillChecks.length > 0 && (
                              <div className="flex flex-wrap gap-1.5">
                                {step.skillChecks.map((sc, sIdx) => (
                                  <span
                                    key={sIdx}
                                    className="rounded border border-violet-500/40 bg-violet-500/15 px-2 py-0.5 font-mono text-[11px] text-violet-200"
                                  >
                                    {sc}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>

                          <p className="text-xs leading-relaxed text-emerald-100/85">
                            {step.description}
                          </p>

                          {step.tip && (
                            <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs text-amber-100/90">
                              <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-300" />
                              <span>{step.tip}</span>
                            </div>
                          )}

                          {step.branches && step.branches.length > 0 && (
                            <div className="grid grid-cols-1 gap-2 pt-1 md:grid-cols-2">
                              {step.branches.map((br, bIdx) => {
                                const st = TONE_CLASS_MAP[br.tone];
                                return (
                                  <div
                                    key={bIdx}
                                    className={`rounded-lg border p-3 ${st.border} ${st.bg}`}
                                  >
                                    <div className="mb-1.5 flex items-center justify-between gap-2">
                                      <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-50">
                                        <GitBranch className="h-3.5 w-3.5" />
                                        {br.label}
                                      </span>
                                      <span
                                        className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${st.badge}`}
                                      >
                                        {toneLabels[br.tone]}
                                      </span>
                                    </div>
                                    <p className="text-xs text-emerald-100/85">
                                      {br.summary}
                                    </p>
                                    <p className="mt-1.5 text-[11px] font-medium text-emerald-200">
                                      {t.walkthroughs.outcomePrefix} {br.outcome}
                                    </p>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Linked Graph Entities */}
            {entityGroups.length > 0 && (
              <div className="rounded-2xl border border-emerald-900/50 bg-[#0d1612] p-5 space-y-4">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-emerald-300">
                  {t.walkthroughs.linkedEntitiesHeading}
                </h2>
                <div className="space-y-3">
                  {entityGroups.map((g) => {
                    const m = ENTITY_META[g.type];
                    return (
                      <div key={g.key} className="space-y-1.5">
                        <div className={`text-xs font-semibold ${m.textClass}`}>
                          {g.title} ({g.nodes.length})
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {g.nodes.map((node) => {
                            const nodeLabel = getNodeLabel(node);
                            const iconUrl =
                              node.icon && iconAtlas ? iconAtlas.icons[node.icon]?.url : undefined;
                            return (
                              <button
                                key={node.id}
                                onClick={() => onSelectEntityOnGraph(node.id)}
                                className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs transition hover:brightness-125 ${m.bgClass} ${m.borderClass} ${m.textClass}`}
                                title={t.walkthroughs.showEntityTitle}
                              >
                                {iconUrl ? (
                                  <img
                                    src={iconUrl}
                                    alt=""
                                    className="h-4 w-4 shrink-0 object-contain"
                                    loading="lazy"
                                  />
                                ) : (
                                  <span className={`h-1.5 w-1.5 rounded-full ${m.dotClass}`} />
                                )}
                                {nodeLabel}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Official ESM Objectives & Stage Journal Logs */}
            {(activeWalkthrough.objectives.length > 0 ||
              activeWalkthrough.stageLogs.length > 0) && (
              <div className="rounded-2xl border border-emerald-900/50 bg-[#0d1612] overflow-hidden">
                <button
                  onClick={() => setShowEsmLogs((v) => !v)}
                  className="flex w-full items-center justify-between px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-emerald-300 hover:bg-emerald-950/30"
                >
                  <span>
                    {t.walkthroughs.esmHeadingPrefix}{" "}
                    {activeWalkthrough.objectives.length} {t.walkthroughs.esmObjectivesWord},{" "}
                    {activeWalkthrough.stageLogs.length} {t.walkthroughs.esmStagesWord})
                  </span>
                  {showEsmLogs ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </button>

                {showEsmLogs && (
                  <div className="border-t border-emerald-900/40 p-5 space-y-4 text-xs">
                    {activeWalkthrough.objectives.length > 0 && (
                      <div className="space-y-1.5">
                        <div className="font-semibold text-amber-300">
                          {t.walkthroughs.esmObjectivesSub}
                        </div>
                        <ul className="space-y-1 text-emerald-100/85">
                          {activeWalkthrough.objectives.map((o) => (
                            <li key={o.index} className="font-mono text-[11px]">
                              <span className="text-amber-400">[{o.index}]</span> {o.text}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {activeWalkthrough.stageLogs.length > 0 && (
                      <div className="space-y-1.5">
                        <div className="font-semibold text-emerald-300">
                          {t.walkthroughs.esmStagesSub}
                        </div>
                        <div className="space-y-1.5">
                          {activeWalkthrough.stageLogs.map((st) => (
                            <div
                              key={st.stage}
                              className="rounded border border-emerald-900/40 bg-[#080d0b] px-3 py-2"
                            >
                              <div className="mb-0.5 flex items-center gap-2 font-mono text-[11px] text-emerald-400">
                                <span>
                                  {t.walkthroughs.stageWord} {st.stage}
                                </span>
                                {st.completes && (
                                  <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] text-emerald-300">
                                    {t.walkthroughs.completesBadge}
                                  </span>
                                )}
                                {st.fails && (
                                  <span className="rounded bg-rose-500/20 px-1.5 py-0.5 text-[10px] text-rose-300">
                                    {t.walkthroughs.failsBadge}
                                  </span>
                                )}
                              </div>
                              {st.logs.map((l, li) => (
                                <p key={li} className="text-emerald-100/80">
                                  {l}
                                </p>
                              ))}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};
