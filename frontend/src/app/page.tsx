import Link from "next/link";

export default function HomePage() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 text-center">
      <h1 className="max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
        Schadensfälle verstehen —{" "}
        <span className="text-zinc-500">in 3D, auf einen Blick.</span>
      </h1>
      <p className="max-w-xl text-sm text-zinc-500">
        Strukturierte Extraktion aus deutschen Werkstattnotizen, ein
        regelbasierter + LLM-Reasoning-Layer und ein interaktiver
        Multi-Fahrzeug-3D-Viewer: Reparieren, Austauschen oder Begutachten —
        mit Beleg und Begründung für jede Zone.
      </p>
      <Link
        href="/dashboard"
        className="rounded-lg bg-zinc-100 px-5 py-2.5 text-sm font-semibold text-zinc-950 transition-colors hover:bg-white"
      >
        Zur Fallübersicht →
      </Link>
      <div className="flex gap-6 text-xs text-zinc-600">
        <span>450 Schadensfälle</span>
        <span>22 semantische Zonen</span>
        <span>5 Fahrzeug-Archetypen</span>
      </div>
    </div>
  );
}
