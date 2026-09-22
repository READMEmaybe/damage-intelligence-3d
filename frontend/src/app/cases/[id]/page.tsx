import Link from "next/link";
import { notFound } from "next/navigation";

import CaseDetail from "@/components/CaseDetail";
import { getCase } from "@/lib/data";

export default async function CasePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const kase = getCase(id);
  if (!kase) notFound();

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div>
        <Link
          href="/dashboard"
          className="text-xs text-zinc-500 transition-colors hover:text-zinc-300"
        >
          ← Zurück zur Fallübersicht
        </Link>
      </div>
      <div className="min-h-0 flex-1">
        <CaseDetail kase={kase} />
      </div>
    </div>
  );
}
