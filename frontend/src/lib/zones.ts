import type { Archetype } from "./types";

export interface ZoneDef {
  center: [number, number, number];
  radius: [number, number, number];
}

/** Canonical vehicle space all zone configs are authored in. */
export const CANON = {
  halfLength: 2.35,
  halfWidth: 0.9,
  height: 1.45,
};

/** Canonical body height per archetype (configs are authored against these). */
const CANON_HEIGHT: Record<Archetype, number> = {
  hatchback: 1.45,
  wagon: 1.45,
  suv: 1.65,
  mpv: 1.65,
  transporter: 2.0,
};

export interface VehicleBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  maxZ: number;
}

/**
 * Semantic damage zones in canonical vehicle space:
 *   +x = front, +y = left, +z = up, wheels on z = 0, length ~4.7 units.
 */
const BASE: Record<string, ZoneDef> = {
  Motorhaube: { center: [1.55, 0, 1.0], radius: [0.8, 0.85, 0.12] },
  Windschutzscheibe: { center: [0.95, 0, 1.25], radius: [0.7, 0.9, 0.35] },
  Dach: { center: [0, 0, 1.45], radius: [1.6, 0.95, 0.08] },
  Heckklappe: { center: [-1.95, 0, 1.0], radius: [0.4, 0.9, 0.5] },
  "Stoßstange vorne": { center: [2.3, 0, 0.5], radius: [0.15, 0.9, 0.3] },
  "Stoßstange hinten": { center: [-2.3, 0, 0.5], radius: [0.15, 0.9, 0.3] },
  "Stoßstange vorne links": { center: [2.25, 0.45, 0.45], radius: [0.2, 0.45, 0.25] },
  "Stoßstange vorne rechts": { center: [2.25, -0.45, 0.45], radius: [0.2, 0.45, 0.25] },
  "Stoßstange hinten links": { center: [-2.25, 0.45, 0.45], radius: [0.2, 0.45, 0.25] },
  "Stoßstange hinten rechts": { center: [-2.25, -0.45, 0.45], radius: [0.2, 0.45, 0.25] },
  Fahrertür: { center: [0.85, 0.6, 0.8], radius: [0.55, 0.3, 0.45] },
  Beifahrertür: { center: [0.85, -0.6, 0.8], radius: [0.55, 0.3, 0.45] },
  "Tür hinten links": { center: [-0.45, 0.6, 0.8], radius: [0.55, 0.3, 0.45] },
  "Tür hinten rechts": { center: [-0.45, -0.6, 0.8], radius: [0.55, 0.3, 0.45] },
  "Kotflügel vorne links": { center: [1.55, 0.62, 0.72], radius: [0.5, 0.22, 0.28] },
  "Kotflügel vorne rechts": { center: [1.55, -0.62, 0.72], radius: [0.5, 0.22, 0.28] },
  "Kotflügel hinten links": { center: [-1.55, 0.62, 0.72], radius: [0.5, 0.22, 0.28] },
  "Kotflügel hinten rechts": { center: [-1.55, -0.62, 0.72], radius: [0.5, 0.22, 0.28] },
  "Schweller links": { center: [0.2, 0.85, 0.25], radius: [1.6, 0.15, 0.12] },
  "Schweller rechts": { center: [0.2, -0.85, 0.25], radius: [1.6, 0.15, 0.12] },
  "Außenspiegel links": { center: [1.05, 0.95, 1.1], radius: [0.2, 0.12, 0.15] },
  "Außenspiegel rechts": { center: [1.05, -0.95, 1.1], radius: [0.2, 0.12, 0.15] },
};

/** Per-archetype overrides for body-shape differences. */
const OVERRIDES: Record<Archetype, Record<string, Partial<ZoneDef>>> = {
  hatchback: {},
  wagon: {
    Heckklappe: { center: [-2.05, 0, 1.0] },
    "Stoßstange hinten": { center: [-2.35, 0, 0.5] },
    "Stoßstange hinten links": { center: [-2.3, 0.45, 0.45] },
    "Stoßstange hinten rechts": { center: [-2.3, -0.45, 0.45] },
  },
  suv: {
    Dach: { center: [0, 0, 1.7], radius: [1.55, 0.95, 0.08] },
    Motorhaube: { center: [1.55, 0, 1.15] },
    Windschutzscheibe: { center: [0.95, 0, 1.4] },
    Heckklappe: { center: [-1.95, 0, 1.15] },
  },
  mpv: {
    Dach: { center: [0, 0, 1.65], radius: [1.6, 0.95, 0.08] },
    Motorhaube: { center: [1.6, 0, 1.15] },
    Windschutzscheibe: { center: [1.0, 0, 1.35] },
    Heckklappe: { center: [-1.95, 0, 1.15] },
  },
  transporter: {
    Dach: { center: [0, 0, 1.95], radius: [2.0, 0.95, 0.1] },
    Motorhaube: { center: [1.75, 0, 0.95], radius: [0.5, 0.85, 0.25] },
    Windschutzscheibe: { center: [1.15, 0, 1.3], radius: [0.5, 0.9, 0.5] },
    Heckklappe: { center: [-2.15, 0, 1.2], radius: [0.3, 0.9, 0.7] },
    Fahrertür: { center: [0.75, 0.55, 0.9], radius: [0.45, 0.25, 0.55] },
    Beifahrertür: { center: [0.75, -0.55, 0.9], radius: [0.45, 0.25, 0.55] },
    "Tür hinten links": { center: [-1.05, 0.55, 1.0], radius: [0.8, 0.25, 0.6] },
    "Tür hinten rechts": { center: [-1.05, -0.55, 1.0], radius: [0.8, 0.25, 0.6] },
  },
};

const ZONES: Record<Archetype, Record<string, ZoneDef>> = Object.fromEntries(
  (Object.keys(OVERRIDES) as Archetype[]).map((a) => [
    a,
    Object.fromEntries(
      Object.entries(BASE).map(([zone, def]) => [
        zone,
        { ...def, ...OVERRIDES[a][zone] },
      ]),
    ),
  ]),
) as Record<Archetype, Record<string, ZoneDef>>;

export function zoneDef(archetype: Archetype, zone: string): ZoneDef | null {
  return ZONES[archetype]?.[zone] ?? null;
}

/** Map a canonical zone definition onto the actual bounds of a loaded model. */
export function toWorld(
  def: ZoneDef,
  b: VehicleBounds,
  archetype: Archetype = "hatchback",
): ZoneDef {
  const spanX = b.maxX - b.minX;
  const spanY = b.maxY - b.minY;
  const canonH = CANON_HEIGHT[archetype];
  const fx = (def.center[0] + CANON.halfLength) / (CANON.halfLength * 2);
  const fy = (def.center[1] + CANON.halfWidth) / (CANON.halfWidth * 2);
  const fz = def.center[2] / canonH;
  return {
    center: [
      b.minX + fx * spanX,
      b.minY + fy * spanY,
      fz * b.maxZ,
    ],
    radius: [
      (def.radius[0] / (CANON.halfLength * 2)) * spanX,
      (def.radius[1] / (CANON.halfWidth * 2)) * spanY,
      (def.radius[2] / canonH) * b.maxZ,
    ],
  };
}
