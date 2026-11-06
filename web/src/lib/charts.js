import { use, init, getInstanceByDom } from "echarts/core";
import {
  LineChart,
  ScatterChart,
  BarChart,
  RadarChart,
  HeatmapChart,
  SankeyChart,
} from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
  DataZoomComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import { CHART_TEXT, CHART_MUTED, CHART_GRID, GENRE_PALETTE } from "./palette";

use([
  LineChart,
  ScatterChart,
  BarChart,
  RadarChart,
  HeatmapChart,
  SankeyChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
  DataZoomComponent,
  SVGRenderer,
]);

const theme = {
  color: GENRE_PALETTE,
  backgroundColor: "transparent",
  textStyle: {
    fontFamily: "Host Grotesk, Microsoft YaHei, sans-serif",
    color: CHART_TEXT,
    fontSize: 13,
  },
  title: { textStyle: { color: CHART_TEXT } },
  legend: {
    textStyle: { color: CHART_MUTED, fontSize: 13 },
    inactiveColor: "#4b5f78",
    pageTextStyle: { color: CHART_MUTED },
  },
  tooltip: {
    backgroundColor: "#192a40",
    borderColor: "#3d536f",
    textStyle: { color: CHART_TEXT, fontSize: 13 },
    padding: 12,
    confine: true,
    extraCssText: "box-shadow:0 8px 32px #0003;border-radius:8px;",
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: CHART_GRID } },
    axisTick: { show: false },
    axisLabel: { color: CHART_MUTED, fontSize: 13 },
    splitLine: { show: false },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: CHART_MUTED, fontSize: 13 },
    splitLine: { lineStyle: { color: CHART_GRID, type: "dashed" } },
  },
};
export function createChart(el) {
  return getInstanceByDom(el) || init(el, theme, { renderer: "svg" });
}

export function motionOption() {
  return {
    animation: !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    animationDuration: 450,
    animationDurationUpdate: 240,
  };
}
