export const NODE_COLORS = {
  Person: '#248480',
  Song: '#568fc3',
  Album: '#627996',
  MusicalGroup: '#b66b41',
  RecordLabel: '#9aa8b0',
}

export const NODE_LABELS = {
  Person: '艺人 / 创作者',
  Song: '歌曲',
  Album: '专辑',
  MusicalGroup: '乐队 / 组合',
  RecordLabel: '唱片厂牌',
}

export const NODE_RADIUS = {
  Person: 5.4, Song: 4, Album: 4.6, MusicalGroup: 6.4, RecordLabel: 4,
}

export const INFLUENCE_EDGE_TYPES = [
  'InStyleOf', 'CoverOf', 'DirectlySamples', 'InterpolatesFrom', 'LyricalReferenceTo',
]

export const CREDIT_EDGE_TYPES = [
  'PerformerOf', 'ComposerOf', 'LyricistOf', 'ProducerOf', 'RecordedBy', 'DistributedBy', 'MemberOf',
]

export const EDGE_LABELS = {
  PerformerOf: '表演', ComposerOf: '作曲', LyricistOf: '作词', ProducerOf: '制作',
  RecordedBy: '录制', DistributedBy: '发行', MemberOf: '成员',
  InStyleOf: '风格借鉴', CoverOf: '翻唱', DirectlySamples: '采样',
  InterpolatesFrom: '片段引用', LyricalReferenceTo: '歌词引用',
}

export const EDGE_COLOR_CREDIT = '#C8D4E0'
export const EDGE_COLOR_INFLUENCE = '#E8734A'

export const FLOW_TYPES = INFLUENCE_EDGE_TYPES

export const FLOW_COLORS = {
  InStyleOf: '#355a7a',
  CoverOf: '#ae6c33',
  DirectlySamples: '#307c73',
  InterpolatesFrom: '#6689b1',
  LyricalReferenceTo: '#7a7655',
}

export const GENRE_PALETTE = [
  '#2874a0', '#af6236', '#24827d', '#a65b56', '#607b54', '#597f9a',
  '#a87945', '#476888', '#4b8e99', '#a26b78', '#7b8060', '#b38d41',
]

export const CHART_TEXT = '#1F2D3D'
export const CHART_MUTED = '#536b80'
export const CHART_GRID = '#e0eaf0'

export function genreColor(index) {
  return GENRE_PALETTE[index % GENRE_PALETTE.length]
}

export function formatCount(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return Number(value).toLocaleString('zh-CN')
}

export function formatRatio(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(Number(value) * 100).toFixed(1)}%`
}

export function edgeGroup(type) {
  return INFLUENCE_EDGE_TYPES.includes(type) ? 'influence' : 'credit'
}
