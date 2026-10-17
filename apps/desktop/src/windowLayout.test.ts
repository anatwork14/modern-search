import { describe, expect, it } from "vitest";
import { fitLauncherToWorkArea } from "./windowLayout";

describe("macOS floating launcher work-area bounds", () => {
  it("keeps a compact launcher near its previous position", () => {
    expect(fitLauncherToWorkArea({ x: 0, y: 24, width: 1440, height: 810 }, { x: 330, y: 260 }, false))
      .toEqual({ x: 330, y: 260, width: 760, height: 165 });
  });
  it("moves upward before expansion to avoid the Dock", () => {
    const area = { x: 0, y: 24, width: 1440, height: 810 };
    const frame = fitLauncherToWorkArea(area, { x: 330, y: 260 }, true);
    expect(frame.y).toBeLessThan(260);
    expect(frame.y + frame.height).toBeLessThanOrEqual(area.y + area.height - 12);
  });
  it("bounds the card on small external monitors and shifted monitor origins", () => {
    const area = { x: -1300, y: 80, width: 1100, height: 620 };
    const frame = fitLauncherToWorkArea(area, { x: -400, y: 480 }, true);
    expect(frame.width).toBe(760);
    expect(frame.height).toBe(596);
    expect(frame.x).toBeGreaterThanOrEqual(area.x + 12);
    expect(frame.x + frame.width).toBeLessThanOrEqual(area.x + area.width - 12);
    expect(frame.y + frame.height).toBeLessThanOrEqual(area.y + area.height - 12);
  });
});
