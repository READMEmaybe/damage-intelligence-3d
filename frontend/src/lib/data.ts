import fs from "node:fs";
import path from "node:path";
import type { ViewerCase } from "./types";

const DATA_PATH = path.join(process.cwd(), "public", "data", "viewer_cases.json");

let cache: ViewerCase[] | null = null;

export function getCases(): ViewerCase[] {
  if (!cache) {
    cache = JSON.parse(fs.readFileSync(DATA_PATH, "utf-8")) as ViewerCase[];
  }
  return cache;
}

export function getCase(id: string): ViewerCase | null {
  return getCases().find((c) => c.id === id) ?? null;
}
