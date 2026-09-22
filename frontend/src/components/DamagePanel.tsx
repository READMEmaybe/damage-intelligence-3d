"use client";

import type { ViewerCase } from "@/lib/types";
import { ACTION_COLORS } from "./CarViewer";

const ACTION_LABELS: Record<string, string> = {
  replace: "Austauschen",
  repair: "Reparieren",
  assess: "Begutachten",
};

const SOURCE_LABELS: Record<string, string> = {
  explicit: "Explizit",
  inferred: "Gefolgert",
  insufficient_information: "Unzureichende Infos",
};

function ConfidenceBar({ value }: { value: number }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
      <div
        className="h-full rounded-full bg-zinc-300"
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  );
}

export default function DamagePanel({
  kase,
  selectedZone,
  onSelectZone,
}: {
  kase: ViewerCase;
  selectedZone: string | null;
  onSelectZone: (zone: string | null) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      {kase.damages.length === 0 && (
        <p className="rounded-lg border border-zinc-800 p-4 text-sm text-zinc-500">
          Keine Schadenszonen — Service-Fall ohne Schäden.
        </p>
      )}
      {kase.damages.map((d) => {
        const active = selectedZone === d.zone;
        return (
          <button
            key={d.zone}
            onClick={() => onSelectZone(active ? null : d.zone)}
            className={`w-full rounded-lg border p-3 text-left transition-colors ${
              active
                ? "border-zinc-500 bg-zinc-800/80"
                : "border-zinc-800 bg-zinc-900/60 hover:border-zinc-700"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span
                  className="h-3 w-3 shrink-0 rounded-full"
                  style={{ backgroundColor: ACTION_COLORS[d.action] }}
                />
                <span className="text-sm font-medium text-zinc-100">
                  {d.zone}
                </span>
              </div>
              <span
                className="shrink-0 rounded px-1.5 py-0.5 text-[11px] font-semibold"
                style={{
                  backgroundColor: `${ACTION_COLORS[d.action]}22`,
                  color: ACTION_COLORS[d.action],
                }}
              >
                {ACTION_LABELS[d.action] ?? d.action}
              </span>
            </div>
            <div className="mt-2 flex items-center justify-between gap-2 text-[11px] text-zinc-500">
              <span>{SOURCE_LABELS[d.action_source] ?? d.action_source}</span>
              <span>Konfidenz {Math.round(d.confidence * 100)}%</span>
            </div>
            <div className="mt-1.5">
              <ConfidenceBar value={d.confidence} />
            </div>
            {active && (
              <div className="mt-3 space-y-2 border-t border-zinc-800 pt-3 text-xs">
                <p className="text-zinc-400">
                  <span className="font-semibold text-zinc-300">Beleg:</span>{" "}
                  {d.evidence}
                </p>
                <p className="text-zinc-400">
                  <span className="font-semibold text-zinc-300">Begründung:</span>{" "}
                  {d.reason}
                </p>
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
