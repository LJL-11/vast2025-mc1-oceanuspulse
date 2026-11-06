export const NODE_COLORS = {
  Person: '#2A9D8F',
  Song: '#5B8FF9',
  Album: '#7262FD',
  MusicalGroup: '#E8734A',
  RecordLabel: '#9AA7B4',
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
  InStyleOf: '#E8734A',
  CoverOf: '#F2B447',
  DirectlySamples: '#2A9D8F',
  InterpolatesFrom: '#5B8FF9',
  LyricalReferenceTo: '#7262FD',
}

export const GENRE_PALETTE = [
  '#E8734A', '#2A9D8F', '#5B8FF9', '#7262FD', '#F2B447', '#3C7D6E',
  '#B85C8E', '#4A7BB5', '#C4613B', '#7C8AA0', '#8C6FD8', '#D1A03C',
]

export const CHART_TEXT = '#1F2D3D'
export const CHART_MUTED = '#7A8899'
export const CHART_GRID = '#EBF0F5'

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
