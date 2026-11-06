export const NODE_COLORS = {
  Person: "#8fd7f8",
  Song: "#7eadd8",
  Album: "#dfc180",
  MusicalGroup: "#e7b58a",
  RecordLabel: "#93a6bf",
};

export const NODE_LABELS = {
  Person: "艺人 / 创作者",
  Song: "歌曲",
  Album: "专辑",
  MusicalGroup: "乐队 / 组合",
  RecordLabel: "唱片厂牌",
};

export const NODE_RADIUS = {
  Person: 5.4,
  Song: 4,
  Album: 4.6,
  MusicalGroup: 6.4,
  RecordLabel: 4,
};

export const INFLUENCE_EDGE_TYPES = [
  "InStyleOf",
  "CoverOf",
  "DirectlySamples",
  "InterpolatesFrom",
  "LyricalReferenceTo",
];

export const CREDIT_EDGE_TYPES = [
  "PerformerOf",
  "ComposerOf",
  "LyricistOf",
  "ProducerOf",
  "RecordedBy",
  "DistributedBy",
  "MemberOf",
];

export const EDGE_LABELS = {
  PerformerOf: "表演",
  ComposerOf: "作曲",
  LyricistOf: "作词",
  ProducerOf: "制作",
  RecordedBy: "录制",
  DistributedBy: "发行",
  MemberOf: "成员",
  InStyleOf: "风格借鉴",
  CoverOf: "翻唱",
  DirectlySamples: "采样",
  InterpolatesFrom: "片段引用",
  LyricalReferenceTo: "歌词引用",
};

export const EDGE_COLOR_CREDIT = "#8195af";
export const EDGE_COLOR_INFLUENCE = "#e7b58a";

export const FLOW_TYPES = INFLUENCE_EDGE_TYPES;

export const FLOW_COLORS = {
  InStyleOf: "#8fd7f8",
  CoverOf: "#dfc180",
  DirectlySamples: "#7eadd8",
  InterpolatesFrom: "#e7b58a",
  LyricalReferenceTo: "#77accb",
};

export const GENRE_PALETTE = [
  "#8fd7f8",
  "#7eadd8",
  "#e7b58a",
  "#dfc180",
  "#77accb",
  "#d2ddea",
  "#83bacd",
  "#A0BED1",
  "#CDAD8A",
  "#9cacc2",
  "#D6B0A0",
  "#9cc5d8",
];

export const CHART_TEXT = "#ebf0f7";
export const CHART_MUTED = "#95a4b9";
export const CHART_GRID = "#263349";

export function genreColor(index) {
  return GENRE_PALETTE[index % GENRE_PALETTE.length];
}

export function formatCount(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number(value).toLocaleString("zh-CN");
}

export function formatRatio(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(Number(value) * 100).toFixed(1)}%`;
}

export function edgeGroup(type) {
  return INFLUENCE_EDGE_TYPES.includes(type) ? "influence" : "credit";
}
