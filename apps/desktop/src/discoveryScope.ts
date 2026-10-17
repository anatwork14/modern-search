import type { HealthData } from "./contracts";

/** Prefer visibly labeled candidate discovery ONLY when there are unknown
 * papers and no verified-qualified records. Owner scope choices always win.
 */
export function defaultEligibilityForCatalog(
  health: HealthData | null,
  source: "mock" | "local",
): "verified-qualified" | "unknown" {
  if (source === "local" && health?.eligibility_counts?.["verified-qualified"] === 0 &&
      (health.eligibility_counts.unknown ?? 0) > 0) return "unknown";
  return "verified-qualified";
}
