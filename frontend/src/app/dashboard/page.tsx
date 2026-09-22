import CaseList from "@/components/CaseList";
import { getCases } from "@/lib/data";

export default function DashboardPage() {
  const cases = getCases();
  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-zinc-100">
          Schadenfälle — Werkstattübersicht
        </h1>
        <span className="text-xs text-zinc-500">
          {cases.length} Fälle · Reasoning-Status: valid
        </span>
      </div>
      <div className="min-h-0 flex-1">
        <CaseList cases={cases} />
      </div>
    </div>
  );
}
