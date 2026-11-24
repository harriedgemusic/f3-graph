import React from "react";
import { ENTITY_META } from "../constants";
import { EntityType, IconAtlasData } from "../types";

interface EntityIconProps {
  iconKey?: string;
  type: EntityType;
  label: string;
  iconAtlas: IconAtlasData | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZE_CLASSES = {
  sm: "h-6 w-6 p-0.5 rounded-md",
  md: "h-9 w-9 p-1 rounded-lg",
  lg: "h-12 w-12 p-1.5 rounded-xl",
};

export const EntityIcon: React.FC<EntityIconProps> = ({
  iconKey,
  type,
  label,
  iconAtlas,
  size = "md",
  className = "",
}) => {
  const meta = ENTITY_META[type];
  const entry = iconKey && iconAtlas ? iconAtlas.icons[iconKey] : undefined;

  return (
    <div
      className={`inline-flex shrink-0 items-center justify-center border bg-[#07110d] ${SIZE_CLASSES[size]} ${meta.borderClass} ${className}`}
      style={{ boxShadow: `0 0 10px ${meta.color}22` }}
    >
      {entry ? (
        <img
          src={entry.url}
          alt={label}
          className="h-full w-full object-contain select-none"
          loading="lazy"
          draggable={false}
        />
      ) : (
        <span className={`h-2.5 w-2.5 rounded-full ${meta.dotClass}`} />
      )}
    </div>
  );
};
