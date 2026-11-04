/** Browser-side adapter. Pass `${import.meta.env.BASE_URL}data/` from the Vue app. */
export function createDataService({ baseUrl = '/data/', fetchImpl = globalThis.fetch } = {}) {
  const base = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
  const cache = new Map();
  async function read(name) {
    if (!cache.has(name)) {
      const request = (async () => {
        const response = await fetchImpl(`${base}${name}`);
        if (!response.ok) throw new Error(`数据加载失败 (${response.status}): ${name}，请先运行 pipeline/run.py`);
        const value = await response.json();
        if (!/^1\.\d+\.\d+$/.test(value.meta?.schema_version ?? '')) throw new Error(`数据契约版本不兼容: ${name}`);
        if (name !== 'manifest.json') {
          const manifest = await read('manifest.json');
          for (const key of ['schema_version', 'source_sha256', 'cutoff_year', 'seed']) {
            if (value.meta[key] !== manifest.meta[key]) throw new Error(`检测到混合版本数据: ${name}/${key}`);
          }
        }
        return value;
      })();
      cache.set(name, request);
      // A failed fetch must be retryable after running the pipeline.
      request.catch(() => cache.delete(name));
    }
    return cache.get(name);
  }
  return {
    manifest: () => read('manifest.json'),
    overview: () => read('overview.json'),
    sailor: () => read('sailor_shift.json'),
    // D3 mutates source/target and coordinates; callers receive their own copy.
    network: async () => structuredClone(await read('network_overview.json')),
    sailorEgo: async () => structuredClone(await read('sailor_ego.json')),
    nodeIndex: () => read('node_index.json'),
    genreTrends: () => read('genre_trends.json'),
    genreFlows: () => read('genre_flows.json'),
    influenceEvents: () => read('influence_events.json'),
    influenceEvidence: () => read('influence_evidence.json'),
    networkDynamics: () => read('network_dynamics.json'),
    robustness: () => read('robustness_report.json'),
    artistIndex: () => read('artist_index.json'),
    candidates: () => read('rising_star_baseline.json'),
    async artist(id) {
      if (!Number.isSafeInteger(id) || id < 0) throw new TypeError('artist id 必须是非负安全整数');
      const index = await read('artist_index.json');
      const shard = (id % index.meta.shard_count).toString().padStart(2, '0');
      const data = await read(`artists/${shard}.json`);
      const artist = data.artists[String(id)];
      if (!artist) throw new Error(`该实体没有可用的作品署名记录: ${id}`);
      return artist;
    },
    clearCache: () => cache.clear(),
  };
}

/** Turn sparse career events into continuous ECharts series without inventing events. */
export function expandAnnual(timeline) {
  const byYear = new Map(timeline.annual.map(row => [row.year, row]));
  const result = [];
  let cumulativeWorks = 0, cumulativeCharts = 0, cumulativeCollaborators = 0;
  for (let year = timeline.year_range[0]; year <= timeline.year_range[1]; year += 1) {
    const event = byYear.get(year);
    if (event) {
      cumulativeWorks = event.cumulative_works;
      cumulativeCharts = event.cumulative_known_charts;
      cumulativeCollaborators = event.cumulative_collaborators;
    }
    result.push({
      year, career_year: year - timeline.year_range[0], releases: event?.releases ?? 0,
      new_chart_entries_known_date: event?.new_chart_entries_known_date ?? 0,
      new_collaborators: event?.new_collaborators ?? 0,
      cumulative_works: cumulativeWorks, cumulative_known_charts: cumulativeCharts,
      cumulative_collaborators: cumulativeCollaborators,
    });
  }
  return result;
}
