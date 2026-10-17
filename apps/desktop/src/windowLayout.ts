/** Pure logical-pixel window bounds for the monitor hosting the floating launcher. */
export interface WorkArea { x: number; y: number; width: number; height: number }
export interface Point { x: number; y: number }
export interface WindowFrame extends WorkArea { }

/** Work-area dimensions exclude the macOS Dock/menu bar, unlike monitor.size. */
export function fitLauncherToWorkArea(
  area: WorkArea,
  previous: Point,
  expanded: boolean,
): WindowFrame {
  const padding = 12;
  const width = Math.max(560, Math.min(760, area.width - padding * 2));
  const height = Math.max(160, Math.min(expanded ? 620 : 165, area.height - padding * 2));
  const x = Math.max(area.x + padding, Math.min(previous.x, area.x + area.width - width - padding));
  const y = Math.max(area.y + padding, Math.min(previous.y, area.y + area.height - height - padding));
  return { x, y, width, height };
}
