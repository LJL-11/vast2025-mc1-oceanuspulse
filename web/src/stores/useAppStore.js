import { defineStore } from "pinia";
import { moduleNavigation } from "../lib/navigation";

/** Cross-module state. Every view reads and writes the same focus, filters and time window. */
export const useAppStore = defineStore("app", {
  state: () => ({
    activeModule: "overview",
    motionEnabled: !globalThis.matchMedia?.("(prefers-reduced-motion: reduce)")
      .matches,
    focusNode: null,
    yearRange: [1975, 2040],
    visibleTypes: ["Person", "Song", "Album", "MusicalGroup", "RecordLabel"],
    visibleFlowTypes: [
      "InStyleOf",
      "CoverOf",
      "DirectlySamples",
      "InterpolatesFrom",
      "LyricalReferenceTo",
    ],
    focusGenres: ["Oceanus Folk"],
    trendMetric: "outbound_events",
  }),
  actions: {
    setModule(key) {
      if (moduleNavigation) return moduleNavigation(key);
      this.activeModule = key;
    },
    selectNode(node) {
      this.focusNode = node
        ? {
            id: node.id,
            name: node.display_name || node.name,
            type: node.type,
            genre: node.genre || null,
            release_year: node.release_year ?? null,
            chart_year: node.chart_year ?? null,
            notable: node.notable ?? null,
          }
        : null;
    },
    clearFocus() {
      this.focusNode = null;
    },
    /** Module one -> module two: jump straight to the genre of the selected entity. */
    focusGenre(genre) {
      if (!genre) return;
      this.focusGenres = [genre];
      return this.setModule("genre");
    },
    setYearRange(range) {
      this.yearRange = range;
    },
  },
});
