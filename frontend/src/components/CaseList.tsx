"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { ARCHETYPE_LABELS } from "@/lib/archetypes";
import type { ViewerCase } from "@/lib/types";

const KIND_FILTERS = [
  "Alle",
  "Parkschaden",
  "Vandalismus",
  "Auffahrunfall",
  "Hagelschaden",
  "Rangierschaden",
  "Wildunfall",
  "Steinschlag",
  "Inspektion",
];

export default function CaseList({ cases }: { cases: ViewerCase[] }) {
  const [kind, setKind] = useState("Alle");
  const [severity, setSeverity] = useState("Alle");
  const [action, setAction] = useState("Alle");
  const [archetype, setArchetype] = useState("Alle");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    return cases.filter((c) => {
      if (kind !== "Alle" && c.case_kind !== kind) return false;
      if (severity !== "Alle" && c.severity !== severity) return false;
      if (action !== "Alle" && !c.damages.some((d) => d.action === action))
        return false;
      if (archetype !== "Alle" && c.vehicle_archetype !== archetype)
        return false;
      if (query) {
        const q = query.toLowerCase();
        const hay = `${c.vehicle_make} ${c.vehicle_model} ${c.case_id} ${c.case_kind} ${c.freitext}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [cases, kind, severity, action, archetype, query]);

  const selectCls =
    "rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-300 outline-none focus:border-zinc-600";

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <select value={kind} onChange={(e) => setKind(e.target.value)} className={selectCls}>
          {KIND_FILTERS.map((k) => (
            <option key={k} value={k}>
              {k === "Alle" ? "Alle Fallarten" : k}
            </option>
          ))}
        </select>
        <select value={severity} onChange={(e) => setSeverity(e.target.value)} className={selectCls}>
          <option value="Alle">Alle Schweregrade</option>
          <option value="leicht">Leicht</option>
          <option value="mittel">Mittel</option>
          <option value="schwer">Schwer</option>
        </select>
        <select value={action} onChange={(e) => setAction(e.target.value)} className={selectCls}>
          <option value="Alle">Alle Empfehlungen</option>
          <option value="repair">Reparieren</option>
          <option value="replace">Austauschen</option>
          <option value="assess">Begutachten</option>
        </select>
        <select value={archetype} onChange={(e) => setArchetype(e.target.value)} className={selectCls}>
          <option value="Alle">Alle Karosserien</option>
          {Object.entries(ARCHETYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Suchen…"
          className="min-w-0 flex-1 rounded-md border border-zinc-800 bg-zinc-900 px-2 py-1 text-xs text-zinc-300 outline-none placeholder:text-zinc-600 focus:border-zinc-600"
        />
        <span className="text-xs text-zinc-500">{filtered.length} Fälle</span>
      </div>
      <div className="flex-1 space-y-1.5 overflow-y-auto pr-1">
        {filtered.map((c) => (
          <Link
            key={c.id}
            href={`/cases/${c.id}`}
            className="flex items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2.5 transition-colors hover:border-zinc-600"
          >
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-zinc-100">
                #{c.case_id} · {c.vehicle_make} {c.vehicle_model}
              </div>
              <div className="truncate text-xs text-zinc-500">
                {c.case_kind}
                {c.severity ? ` · ${c.severity}` : ""} ·{" "}
                {ARCHETYPE_LABELS[c.vehicle_archetype]}
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              {c.damages.length > 0 ? (
                <span className="rounded bg-red-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-red-400">
                  {c.damages.length} {c.damages.length === 1 ? "Zone" : "Zonen"}
                </span>
              ) : (
                <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">
                  Service
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
