import { describe, expect, it } from "vitest";
import { defaultEligibilityForCatalog } from "./discoveryScope";
import type { HealthData } from "./contracts";
const make = (qualified: number, candidates: number): HealthData => ({
  status: "ready", offline: true, dense_status: "unavailable",
  index_version: "sqlite-v1", paper_count: qualified + candidates,
  eligibility_counts: {
    "verified-qualified": qualified, "verified-not-qualified": 0,
    unknown: candidates, exploratory: 0,
  },
});
describe("honest local startup scope", () => {
  it("starts in candidate discovery if verification has not happened", () => {
    expect(defaultEligibilityForCatalog(make(0, 2478), "local")).toBe("unknown");
  });
  it("keeps strict qualification when verified records exist", () => {
    expect(defaultEligibilityForCatalog(make(2, 2476), "local")).toBe("verified-qualified");
  });
  it("never silently relaxes empty, demo, or legacy uncounted libraries", () => {
    expect(defaultEligibilityForCatalog(make(0, 0), "local")).toBe("verified-qualified");
    expect(defaultEligibilityForCatalog(make(0, 2478), "mock")).toBe("verified-qualified");
    expect(defaultEligibilityForCatalog(null, "local")).toBe("verified-qualified");
  });
});
