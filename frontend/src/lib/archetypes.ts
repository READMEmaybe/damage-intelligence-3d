import type { Archetype } from "./types";

export const MODEL_MAP: Record<Archetype, string> = {
  hatchback: "/models/hatchback.glb",
  wagon: "/models/wagon.glb",
  suv: "/models/suv.glb",
  mpv: "/models/mpv.glb",
  transporter: "/models/transporter.glb",
};

export const FALLBACK_ARCHETYPE: Archetype = "hatchback";

export const ARCHETYPE_LABELS: Record<Archetype, string> = {
  hatchback: "Kleinwagen / Kompakt",
  wagon: "Kombi / Limousine",
  suv: "SUV",
  mpv: "Van (MPV)",
  transporter: "Transporter",
};

export function modelUrl(archetype: Archetype): string {
  return MODEL_MAP[archetype] ?? MODEL_MAP[FALLBACK_ARCHETYPE];
}
