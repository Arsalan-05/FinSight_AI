/**
 * Returns recharts color tokens that match the active theme.
 * Uses CSS variable values so charts honour both light and dark mode.
 */
export function useChartColors() {
  if (typeof window === "undefined") {
    return {
      grid: "#3f3f46",
      tooltipBg: "#18181b",
      tooltipBorder: "#3f3f46",
      axis: "#a1a1aa",
    };
  }
  const style = getComputedStyle(document.documentElement);
  return {
    grid: style.getPropertyValue("--chart-grid").trim() || "#3f3f46",
    tooltipBg: style.getPropertyValue("--chart-tooltip-bg").trim() || "#18181b",
    tooltipBorder: style.getPropertyValue("--chart-tooltip-border").trim() || "#3f3f46",
    axis: style.getPropertyValue("--chart-axis").trim() || "#a1a1aa",
  };
}
