import { defineStore } from 'pinia'

/** Cross-module state. Every view reads and writes the same focus, filters and time window. */
export const useAppStore = defineStore('app', {
  state: () => ({
    activeModule: 'influence',
    focusNode: null,
    yearRange: [1975, 2040],
    visibleTypes: ['Person', 'Song', 'Album', 'MusicalGroup', 'RecordLabel'],
    visibleFlowTypes: [
      'InStyleOf', 'CoverOf', 'DirectlySamples', 'InterpolatesFrom', 'LyricalReferenceTo',
    ],
    focusGenres: ['Oceanus Folk'],
    trendMetric: 'outbound_events',
    // 00 全景图谱的动效开关；尊重系统「减少动态效果」时应设为 false。
    motionEnabled: true,
  }),
  actions: {
    setModule(key) {
      this.activeModule = key
    },
    selectNode(node) {
      this.focusNode = node ? {
        id: node.id,
        name: node.display_name || node.name,
        type: node.type,
        genre: node.genre || null,
        release_year: node.release_year ?? null,
        chart_year: node.chart_year ?? null,
        notable: node.notable ?? null,
      } : null
    },
    clearFocus() {
      this.focusNode = null
    },
    /** Module one -> module two: jump straight to the genre of the selected entity. */
    focusGenre(genre) {
      if (!genre) return
      this.focusGenres = [genre]
      this.activeModule = 'genre'
    },
    setYearRange(range) {
      this.yearRange = range
    },
  },
})
