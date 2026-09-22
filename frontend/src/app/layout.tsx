import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Wolf Day — Schadenvisualisierung",
  description:
    "Multi-Vehicle 3D Visualizer für strukturierte Werkstatt-Schadenfälle",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="de"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex h-screen flex-col overflow-hidden bg-zinc-950 text-zinc-100">
        <header className="shrink-0 border-b border-zinc-900 px-6 py-3">
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/" className="font-semibold tracking-tight text-zinc-100">
              Wolf&nbsp;Day&nbsp;·&nbsp;3D-Viewer
            </Link>
            <Link
              href="/dashboard"
              className="text-zinc-400 transition-colors hover:text-zinc-200"
            >
              Fallübersicht
            </Link>
          </nav>
        </header>
        <main className="min-h-0 flex-1 overflow-hidden px-6 py-4">{children}</main>
      </body>
    </html>
  );
}
