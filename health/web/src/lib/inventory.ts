import type { SourceCoverage } from "./types";
export const failures = new Set([
  "permission_denied",
  "failed",
  "rate_limited",
  "storage_error",
]);
/** Match meta status coverage: every non-legacy row, including detail parents. */
export function summarizeSources(sources: SourceCoverage[]) {
  const current = sources.filter((s) => s.representation !== "legacy_json");
  const complete = current.filter(
    (s) => s.history_complete && ["complete", "empty"].includes(s.status),
  ).length;
  return {
    total: current.length,
    complete,
    failed: current.filter((s) => failures.has(s.status)).length,
    incomplete: current.length - complete,
    legacy: sources.length - current.length,
  };
}
export function sourceCounts(source: SourceCoverage) {
  return {
    pages: source.stored_pages ?? source.pages,
    points: source.stored_points ?? source.points,
    hasStoredTotals:
      source.stored_pages !== undefined && source.stored_points !== undefined,
  };
}
