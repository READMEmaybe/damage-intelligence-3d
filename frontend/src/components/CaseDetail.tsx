"use client";

import { useState } from "react";

import type { ViewerCase } from "@/lib/types";
import CarViewer from "./CarViewer";
import DamagePanel from "./DamagePanel";
import { ARCHETYPE_LABELS } from "@/lib/archetypes";

export default function CaseDetail({ kase }: { kase: ViewerCase }) {
  const [selectedZone, setSelectedZone] = useState<string | null>(null);

  return (
    <div className="grid h-full grid-cols-1 gap-4 lg:grid-cols-[1fr_420px]">
      <div className="flex min-h-0 flex-col gap-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border border-zinc-800 bg-zinc-900/60 px-4 py-2.5 text-sm">
          <span className="font-semibold text-zinc-100">
            {kase.vehicle_make} {kase.vehicle_model}
          </span>
          <span className="text-zinc-500">#{kase.case_id}</span>
          <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-xs text-zinc-300">
            {ARCHETYPE_LABELS[kase.vehicle_archetype]}
          </span>
          <span className="text-zinc-300">{kase.case_kind}</span>
          {kase.severity && (
            <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-xs text-zinc-300">
              {kase.severity}
            </span>
          )}
        </div>
        <div className="min-h-[420px] flex-1 lg:min-h-0">
          <CarViewer
            archetype={kase.vehicle_archetype}
            damages={kase.damages}
            severity={kase.severity}
            selectedZone={selectedZone}
            onSelectZone={setSelectedZone}
          />
        </div>
      </div>
      <div className="flex min-h-0 flex-col gap-3">
        <h2 className="text-sm font-semibold text-zinc-200">
          Schadenszonen & Empfehlungen
        </h2>
        <div className="min-h-0 flex-1 overflow-y-auto pr-1">
          <DamagePanel
            kase={kase}
            selectedZone={selectedZone}
            onSelectZone={setSelectedZone}
          />
        </div>
        <details className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3 text-xs text-zinc-400">
          <summary className="cursor-pointer font-medium text-zinc-300">
            Originale Werkstattnotiz
          </summary>
          <p className="mt-2 whitespace-pre-wrap text-zinc-500">
            {kase.freitext}
          </p>
        </details>
      </div>
    </div>
  );
}
