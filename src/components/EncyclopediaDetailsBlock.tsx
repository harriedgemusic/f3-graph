import React, { useEffect, useState } from "react";
import {
  Compass,
  Crosshair,
  ExternalLink,
  FileText,
  Heart,
  Info,
  KeyRound,
  Lock,
  MapPin,
  Package,
  Quote,
  Shield,
  Sparkles,
  Swords,
  Terminal,
  User,
  Wrench,
  Zap,
} from "lucide-react";
import { getSubtypeLabel } from "../constants";
import { Lang, useI18n } from "../i18n";
import { GraphNode, NodeDetail } from "../types";

export interface EncyclopediaDetailsBlockProps {
  node: GraphNode;
  detail?: NodeDetail;
  onSelectNode?: (nodeId: string) => void;
  compact?: boolean;
}

export const SPECIAL_ATTRS = [
  { key: "СИЛ", en: "STR", label: "Сила (Strength)", labelEn: "Strength" },
  { key: "ВОС", en: "PER", label: "Восприятие (Perception)", labelEn: "Perception" },
  { key: "ВЫН", en: "END", label: "Выносливость (Endurance)", labelEn: "Endurance" },
  { key: "ХАР", en: "CHA", label: "Харизма (Charisma)", labelEn: "Charisma" },
  { key: "ИНТ", en: "INT", label: "Интеллект (Intelligence)", labelEn: "Intelligence" },
  { key: "ЛОВ", en: "AGI", label: "Ловкость (Agility)", labelEn: "Agility" },
  { key: "УДЧ", en: "LCK", label: "Удача (Luck)", labelEn: "Luck" },
] as const;

export function formatSourceTag(tag?: string, lang: Lang = "ru"): string | null {
  if (!tag) return null;
  const trimmed = tag.trim();
  const lower = trimmed.toLowerCase();
  if (lang === "en") {
    if (lower === "esm+wiki" || lower === "wiki+esm" || lower.includes("wiki")) {
      return "Game Files + Fallout Wiki";
    }
    if (lower === "esm" || lower === ".esm" || lower.includes(".esm")) {
      return "Game Files (.ESM)";
    }
    if (lower.includes("энциклопед")) {
      return "Game Files + Encyclopedia";
    }
    return trimmed;
  }
  if (lower === "esm+wiki" || lower === "wiki+esm") return "Файлы игры + Fallout Wiki";
  if (lower === "esm" || lower === ".esm") return "Файлы игры (.ESM)";
  if (lower === "wiki") return "Fallout Wiki";
  return trimmed;
}

interface SpecEntry {
  label: string;
  value: string;
  valueClass?: string;
  icon?: React.ReactNode;
}

function getSafeHttpUrl(url?: string): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.toString() : null;
  } catch {
    return null;
  }
}

const TagChipList: React.FC<{
  title: string;
  items: string[];
  chipClass: string;
  icon?: React.ReactNode;
}> = ({ title, items, chipClass, icon }) => {
  if (items.length === 0) return null;
  return (
    <div className="pt-1">
      <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-medium text-emerald-400/85">
        {icon}
        <span>{title}</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {items.map((entry, idx) => (
          <span
            key={`${entry}-${idx}`}
            className={`rounded border px-2 py-0.5 text-[11px] ${chipClass}`}
          >
            {entry}
          </span>
        ))}
      </div>
    </div>
  );
};

const UnlocksSection: React.FC<{
  title: string;
  items: string[];
}> = ({ title, items }) => {
  if (items.length === 0) return null;
  return (
    <div className="pt-1">
      <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-medium text-amber-300/90">
        <KeyRound className="h-3.5 w-3.5" />
        <span>{title}</span>
      </div>
      <ul className="space-y-1">
        {items.map((entry, idx) => (
          <li
            key={`${entry}-${idx}`}
            className="flex items-start gap-2 rounded border border-amber-500/25 bg-amber-500/5 px-2.5 py-1 text-[11px] text-amber-100/90"
          >
            <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-amber-400" />
            <span>{entry}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

/**
 * Reusable Fallout 3 Encyclopedia article & entity datasheet block
 * shared by InspectorPanel and the CatalogView article drawer.
 */
export const EncyclopediaDetailsBlock: React.FC<EncyclopediaDetailsBlockProps> = ({
  node,
  detail,
  onSelectNode,
  compact = false,
}) => {
  const { lang, t } = useI18n();
  const [expandedLore, setExpandedLore] = useState(false);
  const [showAllInventory, setShowAllInventory] = useState(false);
  const [showAllMenuItems, setShowAllMenuItems] = useState(false);

  useEffect(() => {
    setExpandedLore(false);
    setShowAllInventory(false);
    setShowAllMenuItems(false);
  }, [node.id]);

  const cardPad = compact ? "p-3" : "p-3.5 sm:p-4";
  const bodyText = compact ? "text-xs" : "text-[13px]";
  const stackGap = compact ? "space-y-3" : "space-y-4";

  if (!detail) {
    return (
      <div
        className={`flex items-center gap-2 rounded-lg border border-emerald-900/40 bg-[#0f1914]/70 ${cardPad} text-xs text-emerald-400/75`}
      >
        <Info className="h-4 w-4 shrink-0 text-emerald-500/70" />
        <span>{t.details.noEntry}</span>
      </div>
    );
  }

  const safeWikiUrl = getSafeHttpUrl(detail.wikiUrl);
  const validSections = (detail.sections ?? []).filter(
    (s) => s.title.trim().length > 0 || s.text.trim().length > 0
  );

  const hasCharacterData =
    node.type === "character" &&
    Boolean(
      detail.race ||
        detail.level !== undefined ||
        detail.hp !== undefined ||
        detail.female !== undefined ||
        detail.essential !== undefined ||
        detail.unique !== undefined ||
        detail.behavior ||
        (detail.special && detail.special.length === 7) ||
        (detail.services && detail.services.length > 0) ||
        (detail.factions && detail.factions.length > 0) ||
        (detail.inventory && detail.inventory.length > 0)
    );

  const hasLocationData =
    node.type === "location" && Boolean(detail.worldspace || detail.markerType || detail.coords);

  const itemSpecs: SpecEntry[] = [];
  if (node.type === "item") {
    if (detail.weaponClass) {
      itemSpecs.push({
        label: t.details.weaponClass,
        value: detail.weaponClass,
        valueClass: "text-emerald-100",
        icon: <Crosshair className="h-3.5 w-3.5 text-violet-300" />,
      });
    }
    if (detail.damage !== undefined && detail.damage > 0) {
      itemSpecs.push({
        label: t.details.damage,
        value: `${detail.damage}`,
        valueClass: "text-rose-300 font-semibold",
        icon: <Swords className="h-3.5 w-3.5 text-rose-300" />,
      });
    }
    if (detail.dr !== undefined && detail.dr > 0) {
      itemSpecs.push({
        label: t.details.dr,
        value: `${detail.dr}`,
        valueClass: "text-sky-300 font-semibold",
        icon: <Shield className="h-3.5 w-3.5 text-sky-300" />,
      });
    }
    if (detail.ammo) {
      itemSpecs.push({
        label: t.details.ammo,
        value: detail.ammo,
        valueClass: "text-amber-200",
      });
    }
    if (detail.clipSize !== undefined && detail.clipSize > 0) {
      itemSpecs.push({
        label: t.details.clipSize,
        value: `${detail.clipSize}`,
        valueClass: "text-emerald-100",
      });
    }
    if (detail.fireRate !== undefined && detail.fireRate > 0) {
      itemSpecs.push({
        label: t.details.fireRate,
        value: `${detail.fireRate}`,
        valueClass: "text-emerald-100",
      });
    }
    if (detail.apCost !== undefined && detail.apCost > 0) {
      itemSpecs.push({
        label: t.details.apCost,
        value: `${detail.apCost} ${t.details.apUnit}`,
        valueClass: "text-emerald-200",
        icon: <Zap className="h-3.5 w-3.5 text-amber-300" />,
      });
    }
    if (
      (detail.critDamage !== undefined && detail.critDamage > 0) ||
      (detail.critMult !== undefined && detail.critMult > 0)
    ) {
      const critVal = `${detail.critDamage ?? 0}${
        detail.critMult !== undefined ? ` (×${detail.critMult})` : ""
      }`;
      itemSpecs.push({
        label: t.details.critDamage,
        value: critVal,
        valueClass: "text-amber-300 font-medium",
      });
    }
    if (detail.spread) {
      itemSpecs.push({
        label: t.details.spread,
        value: detail.spread,
        valueClass: "text-emerald-100",
      });
    }
    if (detail.health !== undefined && detail.health > 0) {
      itemSpecs.push({
        label: t.details.durability,
        value: `${detail.health}`,
        valueClass: "text-emerald-100",
        icon: <Wrench className="h-3.5 w-3.5 text-emerald-400" />,
      });
    }
    if (detail.value !== undefined) {
      itemSpecs.push({
        label: t.details.value,
        value: `${detail.value} ${t.details.capsShort}`,
        valueClass: "text-amber-300",
      });
    }
    if (detail.weight !== undefined) {
      itemSpecs.push({
        label: t.details.weight,
        value: `${detail.weight}`,
        valueClass: "text-emerald-100",
      });
    }
  }

  const hasItemData =
    node.type === "item" &&
    Boolean(
      itemSpecs.length > 0 ||
        (detail.effects && detail.effects.length > 0) ||
        (detail.unlocks && detail.unlocks.length > 0) ||
        detail.text
    );

  const hasObjectData =
    node.type === "object" &&
    Boolean(
      detail.lockDiff ||
        (detail.effects && detail.effects.length > 0) ||
        (detail.unlocks && detail.unlocks.length > 0) ||
        detail.text ||
        (detail.menuItems && detail.menuItems.length > 0)
    );

  const inventoryLimit = compact ? 12 : 20;
  const inventoryItems = detail.inventory ?? [];
  const visibleInventory = showAllInventory
    ? inventoryItems
    : inventoryItems.slice(0, inventoryLimit);

  const menuItems = detail.menuItems ?? [];
  const visibleMenuItems = showAllMenuItems ? menuItems : menuItems.slice(0, 8);

  const textPreviewLimit = 260;

  return (
    <div className={stackGap}>
      {/* Role, source tag, quest category, Wiki link */}
      {(detail.role || detail.sourceTag || detail.questCategory || safeWikiUrl) && (
        <div
          className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border border-emerald-900/50 bg-[#0d1712] ${
            compact ? "px-3 py-2" : "px-3.5 py-2.5"
          }`}
        >
          <div className="flex min-w-0 flex-wrap items-center gap-1.5">
            {detail.role && (
              <span className="text-xs font-semibold text-emerald-200">{detail.role}</span>
            )}
            {detail.questCategory && (
              <span className="rounded border border-amber-500/35 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-300">
                {getSubtypeLabel(detail.questCategory, lang) ?? detail.questCategory}
              </span>
            )}
            {detail.sourceTag && (
              <span className="rounded border border-sky-500/35 bg-sky-500/10 px-2 py-0.5 text-[10px] font-medium text-sky-300">
                {formatSourceTag(detail.sourceTag, lang)}
              </span>
            )}
          </div>
          {safeWikiUrl && (
            <a
              href={safeWikiUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-[11px] font-medium text-amber-300 transition hover:border-amber-400/70 hover:bg-amber-500/20"
            >
              <ExternalLink className="h-3 w-3" />
              Fallout Wiki
            </a>
          )}
        </div>
      )}

      {/* Main Encyclopedia Overview */}
      {detail.summary && (
        <div
          className={`rounded-lg border border-emerald-900/50 bg-[#0f1914] ${cardPad} ${bodyText} leading-relaxed text-emerald-100/95 whitespace-pre-line`}
        >
          {detail.summary}
        </div>
      )}

      {/* Structured Encyclopedia Sections */}
      {validSections.length > 0 && (
        <div className={compact ? "space-y-2.5" : "space-y-3"}>
          {validSections.map((sec, idx) => (
            <section
              key={`${sec.title}-${idx}`}
              className={`rounded-lg border border-emerald-900/50 bg-[#0d1712] ${cardPad} space-y-1.5`}
            >
              {sec.title && (
                <h4 className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-emerald-300">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                  <span>{sec.title}</span>
                </h4>
              )}
              {sec.text && (
                <p className={`${bodyText} leading-relaxed text-emerald-100/90 whitespace-pre-line`}>
                  {sec.text}
                </p>
              )}
            </section>
          ))}
        </div>
      )}

      {/* Character Block */}
      {hasCharacterData && (
        <div className={`rounded-lg border border-emerald-900/50 bg-[#0f1914] ${cardPad} space-y-3`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-300">
              <User className="h-3.5 w-3.5" />
              <span>{t.details.charParams}</span>
            </div>
            <div className="flex flex-wrap items-center gap-1">
              {detail.unique && (
                <span className="rounded border border-violet-500/40 bg-violet-500/15 px-1.5 py-0.5 text-[10px] font-medium text-violet-200">
                  {t.details.uniqueBadge}
                </span>
              )}
              {detail.essential && (
                <span className="rounded border border-amber-500/40 bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-300">
                  {t.details.essentialBadge}
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
            {detail.race && (
              <div>
                <span className="text-emerald-500/80">{t.details.raceLabel} </span>
                <span className="text-emerald-100">{detail.race}</span>
              </div>
            )}
            {detail.level !== undefined && (
              <div>
                <span className="text-emerald-500/80">{t.details.levelLabel} </span>
                <span className="text-emerald-100">{detail.level}</span>
              </div>
            )}
            {detail.hp !== undefined && (
              <div className="flex items-center gap-1">
                <Heart className="h-3 w-3 shrink-0 text-rose-400" />
                <span className="text-emerald-500/80">{t.details.hpLabel} </span>
                <span className="font-mono text-emerald-100">{detail.hp}</span>
              </div>
            )}
            {detail.female !== undefined && (
              <div>
                <span className="text-emerald-500/80">{t.details.sexLabel} </span>
                <span className="text-emerald-100">
                  {detail.female ? t.details.female : t.details.male}
                </span>
              </div>
            )}
            {detail.essential !== undefined && (
              <div>
                <span className="text-emerald-500/80">{t.details.essentialLabel} </span>
                <span
                  className={
                    detail.essential ? "font-medium text-amber-300" : "text-emerald-100"
                  }
                >
                  {detail.essential ? t.details.essentialYes : t.details.no}
                </span>
              </div>
            )}
            {detail.unique !== undefined && (
              <div>
                <span className="text-emerald-500/80">{t.details.uniqueLabel} </span>
                <span className="text-emerald-100">
                  {detail.unique ? t.details.yes : t.details.no}
                </span>
              </div>
            )}
          </div>

          {detail.behavior && (
            <div className="rounded border border-emerald-900/50 bg-black/30 px-2.5 py-1.5 text-xs">
              <span className="text-emerald-500/85">{t.details.behaviorLabel} </span>
              <span className="text-emerald-100/90">{detail.behavior}</span>
            </div>
          )}

          {/* 7-badge S.P.E.C.I.A.L. strip */}
          {detail.special && detail.special.length === 7 && (
            <div className="pt-0.5">
              <div className="mb-1.5 flex items-center justify-between text-[11px] font-medium text-emerald-400/85">
                <span>{t.details.specialHeading}</span>
                <span className="font-mono text-[10px] text-emerald-500/80">
                  {t.details.specialScale}
                </span>
              </div>
              <div className="grid grid-cols-7 gap-1">
                {SPECIAL_ATTRS.map((attr, idx) => {
                  const val = detail.special![idx] ?? 5;
                  const pct = Math.min(100, Math.max(10, Math.round((val / 10) * 100)));
                  const barColor =
                    val >= 8
                      ? "bg-amber-400"
                      : val >= 6
                      ? "bg-emerald-400"
                      : val >= 4
                      ? "bg-sky-400"
                      : "bg-rose-400";
                  const shortCode = lang === "en" ? attr.en : attr.key;
                  const titleLabel = lang === "en" ? attr.labelEn : attr.label;
                  return (
                    <div
                      key={attr.en}
                      title={`${titleLabel}: ${val} / 10`}
                      className="flex flex-col items-center rounded border border-emerald-800/60 bg-black/40 px-1 py-1.5 text-center"
                    >
                      <span className="font-mono text-[9px] font-semibold tracking-tight text-emerald-400">
                        {shortCode}
                      </span>
                      <span
                        className={`font-mono text-xs font-bold ${
                          val >= 8 ? "text-amber-300" : "text-emerald-100"
                        }`}
                      >
                        {val}
                      </span>
                      <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-emerald-950/90">
                        <div
                          className={`h-full rounded-full ${barColor}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {detail.services && detail.services.length > 0 && (
            <TagChipList
              title={t.details.servicesTitle}
              items={detail.services}
              chipClass="border-amber-500/35 bg-amber-500/10 text-amber-200"
            />
          )}

          {detail.factions && detail.factions.length > 0 && (
            <TagChipList
              title={t.details.factionsTitle}
              items={detail.factions}
              chipClass="border-emerald-800/60 bg-emerald-950/60 text-emerald-200"
            />
          )}

          {inventoryItems.length > 0 && (
            <div className="pt-1">
              <div className="mb-1.5 flex items-center justify-between text-[11px] font-medium text-emerald-400/85">
                <span>{t.details.inventoryTitle}</span>
                {inventoryItems.length > inventoryLimit && (
                  <button
                    type="button"
                    onClick={() => setShowAllInventory((v) => !v)}
                    className="text-emerald-300 underline hover:text-emerald-100"
                  >
                    {showAllInventory
                      ? t.details.collapse
                      : `${t.details.allBtn} (${inventoryItems.length})`}
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {visibleInventory.map((item, idx) =>
                  onSelectNode ? (
                    <button
                      type="button"
                      key={`${item.id}-${idx}`}
                      onClick={() => onSelectNode(item.id)}
                      className="rounded border border-violet-500/35 bg-violet-500/10 px-2 py-0.5 text-[11px] text-violet-200 transition hover:border-violet-400/60 hover:bg-violet-500/20"
                    >
                      {item.label}
                      {item.count > 1 ? ` ×${item.count}` : ""}
                    </button>
                  ) : (
                    <span
                      key={`${item.id}-${idx}`}
                      className="rounded border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-[11px] text-violet-200"
                    >
                      {item.label}
                      {item.count > 1 ? ` ×${item.count}` : ""}
                    </span>
                  )
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Location Block */}
      {hasLocationData && (
        <div className={`rounded-lg border border-emerald-900/50 bg-[#0f1914] ${cardPad} space-y-1.5 text-xs`}>
          <div className="flex items-center gap-1.5 font-semibold text-sky-300">
            <MapPin className="h-3.5 w-3.5" />
            <span>{t.details.locationGeo}</span>
          </div>
          {detail.worldspace && (
            <div>
              <span className="text-emerald-500/80">{t.details.worldspaceLabel} </span>
              <span className="text-emerald-100">{detail.worldspace}</span>
            </div>
          )}
          {detail.markerType && (
            <div>
              <span className="text-emerald-500/80">{t.details.markerTypeLabel} </span>
              <span className="text-emerald-100">{detail.markerType}</span>
            </div>
          )}
          {detail.coords && (
            <div className="font-mono text-[11px] text-emerald-400/85">
              <Compass className="mr-1 inline h-3 w-3" />
              X: {detail.coords[0]}, Y: {detail.coords[1]}, Z: {detail.coords[2]}
            </div>
          )}
        </div>
      )}

      {/* Item Block */}
      {hasItemData && (
        <div className={`rounded-lg border border-emerald-900/50 bg-[#0f1914] ${cardPad} space-y-2.5 text-xs`}>
          <div className="flex items-center gap-1.5 font-semibold text-violet-300">
            <Package className="h-3.5 w-3.5" />
            <span>{t.details.itemSpecsHeading}</span>
          </div>

          {itemSpecs.length > 0 && (
            <div
              className={`grid gap-2 ${
                compact ? "grid-cols-2" : "grid-cols-2 sm:grid-cols-3"
              }`}
            >
              {itemSpecs.map((spec) => (
                <div
                  key={spec.label}
                  className="rounded border border-emerald-900/45 bg-black/30 px-2.5 py-1.5"
                >
                  <div className="flex items-center gap-1 text-[10px] text-emerald-500/85">
                    {spec.icon}
                    <span>{spec.label}</span>
                  </div>
                  <div className={`mt-0.5 text-xs ${spec.valueClass ?? "text-emerald-100"}`}>
                    {spec.value}
                  </div>
                </div>
              ))}
            </div>
          )}

          {detail.effects && detail.effects.length > 0 && (
            <TagChipList
              title={t.details.effectsTitle}
              items={detail.effects}
              chipClass="border-violet-500/35 bg-violet-500/10 text-violet-200"
              icon={<Sparkles className="h-3.5 w-3.5 text-violet-300" />}
            />
          )}

          {detail.unlocks && detail.unlocks.length > 0 && (
            <UnlocksSection title={t.details.unlocksItemTitle} items={detail.unlocks} />
          )}

          {detail.text && (
            <div className="pt-1">
              <div className="mb-1 flex items-center justify-between text-[11px] text-emerald-400">
                <span className="flex items-center gap-1">
                  <FileText className="h-3.5 w-3.5" />
                  {t.details.noteTextTitle}
                </span>
                {detail.text.length > textPreviewLimit && (
                  <button
                    type="button"
                    onClick={() => setExpandedLore((v) => !v)}
                    className="text-emerald-300 underline hover:text-emerald-100"
                  >
                    {expandedLore ? t.details.collapse : t.details.expandFull}
                  </button>
                )}
              </div>
              <pre className="whitespace-pre-wrap rounded border border-emerald-900/60 bg-black/40 p-2.5 font-mono text-[11px] leading-relaxed text-emerald-100/90">
                {expandedLore || detail.text.length <= textPreviewLimit
                  ? detail.text
                  : `${detail.text.slice(0, textPreviewLimit)}...`}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Object / Terminal / Perk Block */}
      {hasObjectData && (
        <div className={`rounded-lg border border-emerald-900/50 bg-[#0f1914] ${cardPad} space-y-2.5 text-xs`}>
          <div className="flex items-center gap-1.5 font-semibold text-orange-300">
            {node.subtype === "perk" ? (
              <Sparkles className="h-3.5 w-3.5" />
            ) : (
              <Terminal className="h-3.5 w-3.5" />
            )}
            <span>
              {node.subtype === "perk"
                ? t.details.perkDetailsHeading
                : t.details.objectDetailsHeading}
            </span>
          </div>

          {detail.lockDiff && (
            <div className="inline-flex items-center gap-1.5 rounded border border-amber-500/35 bg-amber-500/10 px-2.5 py-1 text-xs">
              <Lock className="h-3.5 w-3.5 text-amber-400" />
              <span className="text-emerald-400/90">{t.details.lockDiffLabel}</span>
              <span className="font-medium text-amber-300">{detail.lockDiff}</span>
            </div>
          )}

          {detail.effects && detail.effects.length > 0 && (
            <TagChipList
              title={
                node.subtype === "perk"
                  ? t.details.perkEffectsTitle
                  : t.details.objectEffectsTitle
              }
              items={detail.effects}
              chipClass="border-orange-500/35 bg-orange-500/10 text-orange-200"
              icon={<Sparkles className="h-3.5 w-3.5 text-orange-300" />}
            />
          )}

          {detail.unlocks && detail.unlocks.length > 0 && (
            <UnlocksSection title={t.details.objectUnlocksTitle} items={detail.unlocks} />
          )}

          {detail.text && (
            <p className={`${bodyText} leading-relaxed text-emerald-100/90 whitespace-pre-line`}>
              {detail.text}
            </p>
          )}

          {menuItems.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <div className="flex items-center justify-between text-[11px] text-emerald-400/85">
                <span>
                  {t.details.terminalEntriesTitle} ({menuItems.length}):
                </span>
                {menuItems.length > 8 && (
                  <button
                    type="button"
                    onClick={() => setShowAllMenuItems((v) => !v)}
                    className="text-emerald-300 underline hover:text-emerald-100"
                  >
                    {showAllMenuItems
                      ? t.details.collapse
                      : `${t.details.showAllBtn} (${menuItems.length})`}
                  </button>
                )}
              </div>
              {visibleMenuItems.map((entry, idx) => (
                <details
                  key={`${entry.title}-${idx}`}
                  className="rounded border border-emerald-900/60 bg-black/35 px-2.5 py-1.5"
                >
                  <summary className="cursor-pointer font-medium text-emerald-200">
                    {entry.title || `${t.details.entryFallback}${idx + 1}`}
                  </summary>
                  {entry.text && (
                    <pre className="mt-1.5 whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-emerald-100/85">
                      {entry.text}
                    </pre>
                  )}
                </details>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Dialogue Quotes Block */}
      {detail.quotes && detail.quotes.length > 0 && (
        <div className={`rounded-lg border border-emerald-900/50 bg-[#0f1914] ${cardPad} space-y-2`}>
          <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-300">
            <Quote className="h-3.5 w-3.5" />
            <span>{t.details.quotesHeading}</span>
          </div>
          <div className="space-y-2">
            {detail.quotes.map((q, idx) => (
              <blockquote
                key={idx}
                className={`rounded-r-md border-l-2 border-amber-400/60 bg-black/35 px-3 py-2 ${bodyText} italic leading-relaxed text-emerald-100/90`}
              >
                {q}
              </blockquote>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
