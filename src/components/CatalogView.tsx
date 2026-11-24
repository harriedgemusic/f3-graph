import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowUpDown,
  BookOpen,
  FileText,
  Focus,
  Network,
  Search,
  X,
} from "lucide-react";
import {
  DLC_META,
  ENTITY_META,
  getDlcLabel,
  getDlcShort,
  getEntityLabel,
  getEntitySingular,
  getSubtypeLabel,
} from "../constants";
import { useI18n } from "../i18n";
import { DetailsMap, DlcId, EntityType, GraphNode, IconAtlasData, Walkthrough } from "../types";
import { EncyclopediaDetailsBlock, SPECIAL_ATTRS } from "./EncyclopediaDetailsBlock";
import { EntityIcon } from "./EntityIcon";

interface CatalogViewProps {
  nodes: GraphNode[];
  details: DetailsMap | null;
  iconAtlas: IconAtlasData | null;
  walkthroughByNodeId: Map<string, Walkthrough>;
  onOpenOnGraph: (nodeId: string, isolate?: boolean) => void;
  onOpenWalkthrough: (walkthroughId: string) => void;
}

const ALL_TYPES: EntityType[] = [
  "character",
  "location",
  "quest",
  "event",
  "item",
  "object",
];

const PAGE_SIZE = 60;

export const CatalogView: React.FC<CatalogViewProps> = ({
  nodes,
  details,
  iconAtlas,
  walkthroughByNodeId,
  onOpenOnGraph,
  onOpenWalkthrough,
}) => {
  const { lang, t, getNodeLabel, getNodeAltLabel } = useI18n();
  const [activeType, setActiveType] = useState<EntityType | "all">("all");
  const [activeDlc, setActiveDlc] = useState<DlcId | "all">("all");
  const [activeSubtype, setActiveSubtype] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [sortBy, setSortBy] = useState<"degree" | "name">("degree");
  const [page, setPage] = useState(1);
  const [articleHistory, setArticleHistory] = useState<string[]>([]);

  const drawerScrollRef = useRef<HTMLDivElement>(null);

  const nodeById = useMemo(() => {
    const map = new Map<string, GraphNode>();
    for (const n of nodes) {
      map.set(n.id, n);
    }
    return map;
  }, [nodes]);

  const activeArticleId = articleHistory[articleHistory.length - 1] ?? null;
  const activeNode = activeArticleId ? nodeById.get(activeArticleId) ?? null : null;
  const activeDetail = activeNode ? details?.[activeNode.id] : undefined;
  const activeWalkthrough = activeNode ? walkthroughByNodeId.get(activeNode.id) : undefined;

  const openArticle = useCallback((nodeId: string) => {
    setArticleHistory([nodeId]);
  }, []);

  const closeArticle = useCallback(() => {
    setArticleHistory([]);
  }, []);

  const handleDrawerSelectNode = useCallback(
    (targetId: string) => {
      if (nodeById.has(targetId)) {
        setArticleHistory((prev) =>
          prev[prev.length - 1] === targetId ? prev : [...prev, targetId]
        );
      } else {
        setArticleHistory([]);
        onOpenOnGraph(targetId, true);
      }
    },
    [nodeById, onOpenOnGraph]
  );

  useEffect(() => {
    if (!activeArticleId) return;
    drawerScrollRef.current?.scrollTo({ top: 0 });
  }, [activeArticleId]);

  useEffect(() => {
    if (!activeNode) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        closeArticle();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeNode, closeArticle]);

  const availableSubtypes = useMemo(() => {
    const set = new Set<string>();
    for (const n of nodes) {
      if (activeType === "all" || n.type === activeType) {
        set.add(n.subtype);
      }
    }
    return Array.from(set).sort();
  }, [nodes, activeType]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = nodes.filter((n) => {
      if (activeType !== "all" && n.type !== activeType) return false;
      if (activeDlc !== "all" && n.dlc !== activeDlc) return false;
      if (activeSubtype !== "all" && n.subtype !== activeSubtype) return false;
      if (q) {
        const det = details?.[n.id];
        const matchesNode =
          n.label.toLowerCase().includes(q) ||
          n.labelEn.toLowerCase().includes(q) ||
          n.edid.toLowerCase().includes(q) ||
          n.fid.toLowerCase().includes(q) ||
          (det?.summary?.toLowerCase().includes(q) ?? false) ||
          (det?.role?.toLowerCase().includes(q) ?? false);
        if (!matchesNode) return false;
      }
      return true;
    });
    const locale = lang === "en" ? "en" : "ru";
    list.sort((a, b) => {
      const la = getNodeLabel(a);
      const lb = getNodeLabel(b);
      if (sortBy === "degree") {
        return b.degree - a.degree || la.localeCompare(lb, locale);
      }
      return la.localeCompare(lb, locale);
    });
    return list;
  }, [nodes, details, activeType, activeDlc, activeSubtype, query, sortBy, lang, getNodeLabel]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const activeNodeLabel = activeNode ? getNodeLabel(activeNode) : "";
  const activeNodeAltLabel = activeNode ? getNodeAltLabel(activeNode) : null;

  return (
    <div className="relative flex h-full flex-col overflow-hidden bg-[#080d0b]">
      {/* Top Filters */}
      <div className="border-b border-emerald-900/50 bg-[#0b120f] p-4 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => {
              setActiveType("all");
              setActiveSubtype("all");
              setPage(1);
            }}
            className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
              activeType === "all"
                ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-200"
                : "border-emerald-900/60 bg-[#080d0b] text-emerald-400/80 hover:border-emerald-700"
            }`}
          >
            {t.catalog.allCategories} ({nodes.length})
          </button>
          {ALL_TYPES.map((tKey) => {
            const m = ENTITY_META[tKey];
            const count = nodes.filter((n) => n.type === tKey).length;
            const active = activeType === tKey;
            return (
              <button
                key={tKey}
                onClick={() => {
                  setActiveType(tKey);
                  setActiveSubtype("all");
                  setPage(1);
                }}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                  active
                    ? `${m.bgClass} ${m.borderClass} ${m.textClass}`
                    : "border-emerald-900/60 bg-[#080d0b] text-emerald-400/80 hover:border-emerald-700"
                }`}
              >
                <span className={`h-2 w-2 rounded-full ${m.dotClass}`} />
                {getEntityLabel(tKey, lang)} ({count})
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative min-w-[240px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-emerald-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              placeholder={t.catalog.searchPlaceholder}
              className="w-full rounded-lg border border-emerald-900/60 bg-[#080d0b] py-2 pl-9 pr-3 text-xs text-emerald-100 placeholder-emerald-600 focus:border-emerald-500 focus:outline-none"
            />
          </div>

          <select
            value={activeDlc}
            onChange={(e) => {
              setActiveDlc(e.target.value as DlcId | "all");
              setPage(1);
            }}
            className="rounded-lg border border-emerald-900/60 bg-[#080d0b] px-3 py-2 text-xs text-emerald-200 focus:border-emerald-500 focus:outline-none"
          >
            <option value="all">{t.catalog.allDlcs}</option>
            {(Object.keys(DLC_META) as DlcId[]).map((id) => (
              <option key={id} value={id}>
                {getDlcLabel(id, lang)}
              </option>
            ))}
          </select>

          <select
            value={activeSubtype}
            onChange={(e) => {
              setActiveSubtype(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-emerald-900/60 bg-[#080d0b] px-3 py-2 text-xs text-emerald-200 focus:border-emerald-500 focus:outline-none"
          >
            <option value="all">{t.catalog.allSubtypes}</option>
            {availableSubtypes.map((st) => (
              <option key={st} value={st}>
                {getSubtypeLabel(st, lang) ?? st}
              </option>
            ))}
          </select>

          <button
            onClick={() => setSortBy((s) => (s === "degree" ? "name" : "degree"))}
            className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-900/60 bg-[#080d0b] px-3 py-2 text-xs text-emerald-200 hover:border-emerald-600"
          >
            <ArrowUpDown className="h-3.5 w-3.5" />
            {sortBy === "degree" ? t.catalog.sortByLinks : t.catalog.sortByName}
          </button>
        </div>
      </div>

      {/* Results grid */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-3 flex items-center justify-between text-xs text-emerald-400/80">
          <span>
            {t.catalog.foundRecords} <strong className="text-emerald-200">{filtered.length}</strong>
          </span>
          <span>
            {t.catalog.page} {safePage} {t.catalog.of} {totalPages}
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {pageItems.map((n) => {
            const m = ENTITY_META[n.type];
            const dlc = DLC_META[n.dlc];
            const wt = walkthroughByNodeId.get(n.id);
            const det = details?.[n.id];
            const nodeLabel = getNodeLabel(n);
            const nodeAltLabel = getNodeAltLabel(n);

            const statChips: { label: string; className: string; title?: string }[] = [];
            if (det) {
              if (n.type === "item") {
                if (det.damage !== undefined && det.damage > 0) {
                  statChips.push({
                    label: `${t.catalog.dmgChip} ${det.damage}`,
                    className: "border-rose-500/40 bg-rose-500/15 text-rose-200 font-medium",
                  });
                }
                if (det.dr !== undefined && det.dr > 0) {
                  statChips.push({
                    label: `${t.catalog.drChip} ${det.dr}`,
                    className: "border-sky-500/40 bg-sky-500/15 text-sky-200 font-medium",
                  });
                }
                if (det.ammo) {
                  statChips.push({
                    label: `${t.catalog.ammoChip} ${det.ammo}`,
                    className: "border-amber-500/35 bg-amber-500/10 text-amber-200",
                  });
                }
                if (det.apCost !== undefined && det.apCost > 0) {
                  statChips.push({
                    label: `${det.apCost} ${t.catalog.apChip}`,
                    className: "border-emerald-700/60 bg-emerald-950/60 text-emerald-200",
                  });
                }
                if (det.value !== undefined && det.value > 0 && statChips.length < 4) {
                  statChips.push({
                    label: `${det.value} ${t.catalog.capsWord}`,
                    className: "border-amber-500/30 bg-amber-500/10 text-amber-300",
                  });
                }
              } else if (n.type === "character") {
                if (det.level !== undefined || det.hp !== undefined) {
                  const parts: string[] = [];
                  if (det.level !== undefined) parts.push(`${t.catalog.lvlChip} ${det.level}`);
                  if (det.hp !== undefined) parts.push(`${t.catalog.hpChip} ${det.hp}`);
                  statChips.push({
                    label: parts.join(" · "),
                    className: "border-emerald-600/45 bg-emerald-500/10 text-emerald-200 font-medium",
                  });
                }
                if (det.race) {
                  statChips.push({
                    label: det.race,
                    className: "border-emerald-800/60 bg-emerald-950/60 text-emerald-300",
                  });
                }
                if (det.essential) {
                  statChips.push({
                    label: t.catalog.essentialChip,
                    className: "border-amber-500/40 bg-amber-500/15 text-amber-300",
                  });
                }
                if (det.special && det.special.length === 7) {
                  const tooltip = SPECIAL_ATTRS.map(
                    (a, idx) => `${lang === "en" ? a.en : a.key} ${det.special![idx]}`
                  ).join(" · ");
                  statChips.push({
                    label: `S.P.E.C.I.A.L.: ${det.special.join("-")}`,
                    className: "border-sky-500/35 bg-sky-500/10 text-sky-200 font-mono",
                    title: tooltip,
                  });
                }
              } else if (n.type === "location") {
                if (det.markerType) {
                  statChips.push({
                    label: det.markerType,
                    className: "border-sky-500/35 bg-sky-500/10 text-sky-200",
                  });
                }
                if (det.worldspace) {
                  statChips.push({
                    label: det.worldspace,
                    className: "border-emerald-800/60 bg-emerald-950/60 text-emerald-300",
                  });
                }
              } else if (n.type === "object") {
                if (det.lockDiff) {
                  statChips.push({
                    label: `${t.catalog.lockChip} ${det.lockDiff}`,
                    className: "border-amber-500/40 bg-amber-500/15 text-amber-200 font-medium",
                  });
                }
                if (det.menuItems && det.menuItems.length > 0) {
                  statChips.push({
                    label: `${t.catalog.terminalChip} ${det.menuItems.length} ${t.catalog.entriesShort}`,
                    className: "border-orange-500/35 bg-orange-500/10 text-orange-200",
                  });
                }
              }
            }

            return (
              <div
                key={n.id}
                className="flex flex-col justify-between rounded-xl border border-emerald-900/50 bg-[#0d1612] p-3.5 transition hover:border-emerald-600/60"
              >
                <div>
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[11px] font-medium ${m.bgClass} ${m.borderClass} ${m.textClass}`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${m.dotClass}`} />
                      {getSubtypeLabel(n.subtype, lang) ?? getEntitySingular(n.type, lang)}
                    </span>
                    <span
                      className="rounded border border-emerald-900/50 bg-black/30 px-2 py-0.5 text-[10px] font-medium"
                      style={{ color: dlc.color, borderColor: `${dlc.color}35` }}
                    >
                      {getDlcShort(n.dlc, lang)}
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <EntityIcon
                      iconKey={n.icon}
                      type={n.type}
                      label={nodeLabel}
                      iconAtlas={iconAtlas}
                      size="md"
                    />
                    <div className="min-w-0 flex-1">
                      <button
                        type="button"
                        onClick={() => openArticle(n.id)}
                        className="text-left text-sm font-semibold text-emerald-50 transition hover:text-emerald-300"
                      >
                        {nodeLabel}
                      </button>
                      {nodeAltLabel && (
                        <p className="text-xs text-emerald-400/65">{nodeAltLabel}</p>
                      )}
                      {det?.role && (
                        <p className="mt-1 inline-block rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-[11px] font-medium text-emerald-200">
                          {det.role}
                        </p>
                      )}
                    </div>
                  </div>

                  {statChips.length > 0 && (
                    <div className="mt-2.5 flex flex-wrap gap-1.5">
                      {statChips.map((chip, cIdx) => (
                        <span
                          key={`${chip.label}-${cIdx}`}
                          title={chip.title}
                          className={`rounded border px-2 py-0.5 text-[10px] ${chip.className}`}
                        >
                          {chip.label}
                        </span>
                      ))}
                    </div>
                  )}

                  {det?.summary && (
                    <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-emerald-200/80">
                      {det.summary}
                    </p>
                  )}
                </div>

                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-emerald-900/40 pt-2.5">
                  <div className="flex items-center gap-2 text-xs text-emerald-400/80">
                    <span>
                      {t.catalog.linksLabel} <strong className="text-emerald-200">{n.degree}</strong>
                    </span>
                    <span className="font-mono text-[10px] text-emerald-600/80" title={`FormID: ${n.fid}`}>
                      {n.edid || n.fid}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => openArticle(n.id)}
                      className="inline-flex items-center gap-1 rounded border border-emerald-600/50 bg-emerald-500/15 px-2.5 py-1 text-[11px] font-medium text-emerald-200 transition hover:border-emerald-400/70 hover:bg-emerald-500/25"
                    >
                      <FileText className="h-3 w-3" />
                      {t.catalog.articleBtn}
                    </button>
                    {wt && (
                      <button
                        type="button"
                        onClick={() => onOpenWalkthrough(wt.id)}
                        className="inline-flex items-center gap-1 rounded border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[11px] font-medium text-amber-300 hover:bg-amber-500/20"
                      >
                        <BookOpen className="h-3 w-3" />
                        {t.catalog.guideBtn}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => onOpenOnGraph(n.id, true)}
                      className="inline-flex items-center gap-1 rounded border border-emerald-700/60 bg-emerald-950/60 px-2.5 py-1 text-[11px] font-medium text-emerald-200 hover:border-emerald-400/60 hover:bg-emerald-900/50"
                    >
                      <Network className="h-3 w-3" />
                      {t.catalog.toGraphBtn}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {totalPages > 1 && (
          <div className="mt-6 flex items-center justify-center gap-2">
            <button
              disabled={safePage <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="rounded-lg border border-emerald-900/60 bg-[#0d1612] px-3 py-1.5 text-xs text-emerald-200 disabled:opacity-40"
            >
              {t.catalog.prevPage}
            </button>
            <span className="px-2 text-xs text-emerald-400">
              {safePage} / {totalPages}
            </span>
            <button
              disabled={safePage >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="rounded-lg border border-emerald-900/60 bg-[#0d1612] px-3 py-1.5 text-xs text-emerald-200 disabled:opacity-40"
            >
              {t.catalog.nextPage}
            </button>
          </div>
        )}
      </div>

      {/* Slide-Over Encyclopedia Article Drawer */}
      {activeNode && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-sm"
          onClick={closeArticle}
          role="dialog"
          aria-modal="true"
          aria-label={activeNodeLabel}
        >
          <aside
            onClick={(e) => e.stopPropagation()}
            className="flex h-full w-full max-w-2xl flex-col border-l border-emerald-800/60 bg-[#0b120f] shadow-2xl"
          >
            {/* Drawer Header */}
            <div className="border-b border-emerald-900/50 p-4 sm:p-5">
              {articleHistory.length > 1 && (
                <button
                  type="button"
                  onClick={() => setArticleHistory((prev) => prev.slice(0, -1))}
                  className="mb-3 inline-flex items-center gap-1.5 rounded-md border border-emerald-800/70 bg-emerald-950/60 px-2.5 py-1 text-[11px] font-medium text-emerald-300 transition hover:border-emerald-500/60 hover:text-emerald-100"
                >
                  <ArrowLeft className="h-3 w-3" />
                  {t.catalog.backToPrevArticle}
                </button>
              )}

              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <EntityIcon
                    iconKey={activeNode.icon}
                    type={activeNode.type}
                    label={activeNodeLabel}
                    iconAtlas={iconAtlas}
                    size="lg"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[11px] font-medium ${ENTITY_META[activeNode.type].bgClass} ${ENTITY_META[activeNode.type].borderClass} ${ENTITY_META[activeNode.type].textClass}`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${ENTITY_META[activeNode.type].dotClass}`}
                        />
                        {getSubtypeLabel(activeNode.subtype, lang) ??
                          getEntitySingular(activeNode.type, lang)}
                      </span>
                      <span
                        className="inline-flex items-center rounded border border-emerald-800/60 bg-emerald-950/60 px-2 py-0.5 text-[11px]"
                        style={{
                          borderColor: `${DLC_META[activeNode.dlc].color}40`,
                          color: DLC_META[activeNode.dlc].color,
                        }}
                      >
                        {getDlcLabel(activeNode.dlc, lang)}
                      </span>
                    </div>
                    <h2 className="text-lg font-bold leading-snug text-emerald-50 break-words">
                      {activeNodeLabel}
                    </h2>
                    {activeNodeAltLabel && (
                      <p className="mt-0.5 text-xs text-emerald-400/75">
                        {activeNodeAltLabel}
                      </p>
                    )}
                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-emerald-500/80">
                      <span>FormID: {activeNode.fid}</span>
                      <span>EDID: {activeNode.edid || "—"}</span>
                      <span>
                        {t.catalog.linksLabel} {activeNode.degree}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={closeArticle}
                  className="rounded-lg border border-emerald-900/50 bg-emerald-950/40 p-1.5 text-emerald-400 transition hover:border-emerald-500/50 hover:text-emerald-200"
                  title={t.catalog.closeArticleTitle}
                  aria-label={t.catalog.closeArticleAria}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Drawer Action Bar */}
            <div className="flex flex-wrap items-center gap-2 border-b border-emerald-900/40 bg-[#080d0b]/70 px-4 py-2.5 sm:px-5">
              <button
                type="button"
                onClick={() => {
                  const id = activeNode.id;
                  closeArticle();
                  onOpenOnGraph(id, false);
                }}
                className="inline-flex items-center gap-1.5 rounded-md border border-emerald-600/60 bg-emerald-500/15 px-3 py-1.5 text-xs font-medium text-emerald-200 transition hover:border-emerald-400/70 hover:bg-emerald-500/25"
              >
                <Network className="h-3.5 w-3.5" />
                {t.catalog.to3dGraphBtn}
              </button>
              <button
                type="button"
                onClick={() => {
                  const id = activeNode.id;
                  closeArticle();
                  onOpenOnGraph(id, true);
                }}
                className="inline-flex items-center gap-1.5 rounded-md border border-sky-500/50 bg-sky-500/15 px-3 py-1.5 text-xs font-medium text-sky-200 transition hover:border-sky-400/70 hover:bg-sky-500/25"
              >
                <Focus className="h-3.5 w-3.5" />
                {t.catalog.focus3dBtn}
              </button>
              {activeWalkthrough && (
                <button
                  type="button"
                  onClick={() => {
                    const wtId = activeWalkthrough.id;
                    closeArticle();
                    onOpenWalkthrough(wtId);
                  }}
                  className="inline-flex items-center gap-1.5 rounded-md border border-amber-500/50 bg-amber-500/15 px-3 py-1.5 text-xs font-semibold text-amber-300 transition hover:bg-amber-500/25"
                >
                  <BookOpen className="h-3.5 w-3.5" />
                  {t.catalog.walkthroughBtn}
                </button>
              )}
            </div>

            {/* Drawer Scrollable Article Body */}
            <div ref={drawerScrollRef} className="flex-1 overflow-y-auto p-4 sm:p-5">
              <EncyclopediaDetailsBlock
                node={activeNode}
                detail={activeDetail}
                onSelectNode={handleDrawerSelectNode}
              />
            </div>
          </aside>
        </div>
      )}
    </div>
  );
};
