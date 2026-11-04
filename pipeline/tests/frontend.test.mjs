import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createDataService, expandAnnual } from '../examples/data-service.mjs';
import { pipelineDataPlugin } from '../examples/vite-data-plugin.mjs';

const dataDir = fileURLToPath(new URL('../../data/processed/', import.meta.url));
const meta = { schema_version: '1.0.0', source_sha256: 'fixture', seed: 42, cutoff_year: 2040 };

test('fetch cache avoids duplicate requests and rejects mixed snapshots', async () => {
  const calls = [];
  const service = createDataService({ baseUrl: '/course/data/', fetchImpl: async url => {
    calls.push(url);
    return { ok: true, json: async () => ({ meta }) };
  } });
  await Promise.all([service.overview(), service.overview()]);
  assert.equal(calls.filter(url => url.endsWith('overview.json')).length, 1);
  assert.ok(calls.every(url => url.startsWith('/course/data/')));
  const mixed = createDataService({ fetchImpl: async url => ({ ok: true,
    json: async () => ({ meta: url.endsWith('manifest.json') ? meta : { ...meta, cutoff_year: 2035 } }),
  }) });
  await assert.rejects(mixed.overview(), /混合版本/);
});

test('failed fetch is retryable and D3 receives an isolated network copy', async () => {
  let fail = true;
  const service = createDataService({ fetchImpl: async () => {
    if (fail) return { ok: false, status: 404 };
    return { ok: true, json: async () => ({ meta, nodes: [{ id: 1, x: 10 }], links: [] }) };
  } });
  await assert.rejects(service.network(), /404/);
  fail = false;
  const network = await service.network();
  network.nodes[0].x = 999;
  assert.equal((await service.network()).nodes[0].x, 10);
});

test('sparse careers zero-fill counts and forward-fill cumulative values', () => {
  const rows = expandAnnual({ year_range: [2020, 2022], annual: [
    { year: 2020, releases: 2, new_chart_entries_known_date: 0, new_collaborators: 1,
      cumulative_works: 2, cumulative_known_charts: 0, cumulative_collaborators: 1 },
    { year: 2022, releases: 0, new_chart_entries_known_date: 1, new_collaborators: 0,
      cumulative_works: 2, cumulative_known_charts: 1, cumulative_collaborators: 1 },
  ] });
  assert.equal(rows[1].releases, 0);
  assert.equal(rows[1].cumulative_works, 2);
  assert.equal(rows[1].new_chart_entries_known_date, 0);
  assert.equal(rows[2].cumulative_known_charts, 1);
});

test('real bundle loads Sailor by shard without fetching the full graph', async () => {
  const files = [];
  const service = createDataService({ baseUrl: '/', fetchImpl: async url => {
    files.push(url);
    return { ok: true, json: async () => JSON.parse(await readFile(`${dataDir}${url.slice(1)}`, 'utf8')) };
  } });
  const artist = await service.artist(17255);
  assert.equal(artist.features.name, 'Sailor Shift');
  assert.equal(artist.features.work_count, 38);
  assert.ok(files.includes('/artists/39.json'));
  assert.ok(!files.includes('/clean_graph.json'));
  await assert.rejects(service.artist('17255'), /安全整数/);
  await assert.rejects(service.artist(0), /没有可用/);
});

test('Vite build assets include shards and exclude engineering-only graphs', async () => {
  const emitted = [];
  await pipelineDataPlugin({ dataDir }).generateBundle.call({ emitFile: asset => emitted.push(asset) });
  assert.ok(emitted.some(asset => asset.fileName === 'data/artists/39.json'));
  assert.ok(emitted.some(asset => asset.fileName === 'data/sailor_ego.json'));
  for (const name of ['influence_evidence.json', 'network_dynamics.json', 'robustness_report.json']) {
    assert.ok(emitted.some(asset => asset.fileName === `data/${name}`));
  }
  assert.ok(!emitted.some(asset => asset.fileName === 'data/clean_graph.json'));
  const manifest = JSON.parse(emitted.find(asset => asset.fileName === 'data/manifest.json').source);
  assert.equal(manifest.files.length, emitted.length - 1);
});

test('additive 1.1 contract is accepted and mixed minor versions are rejected', async () => {
  const current = { ...meta, schema_version: '1.1.0' };
  const service = createDataService({ fetchImpl: async () => ({ ok: true, json: async () => ({ meta: current }) }) });
  assert.equal((await service.overview()).meta.schema_version, '1.1.0');
  const mixed = createDataService({ fetchImpl: async url => ({ ok: true,
    json: async () => ({ meta: url.endsWith('manifest.json') ? current : meta }),
  }) });
  await assert.rejects(mixed.overview(), /混合版本/);
  const incompatible = createDataService({ fetchImpl: async () => ({ ok: true,
    json: async () => ({ meta: { ...meta, schema_version: '2.0.0' } }),
  }) });
  await assert.rejects(incompatible.overview(), /不兼容/);
});

test('new analytics are loaded on demand from the real bundle', async () => {
  const calls = [];
  const service = createDataService({ baseUrl: '/', fetchImpl: async url => {
    calls.push(url);
    return { ok: true, json: async () => JSON.parse(await readFile(`${dataDir}${url.slice(1)}`, 'utf8')) };
  } });
  const evidence = await service.influenceEvidence();
  const dynamics = await service.networkDynamics();
  const robustness = await service.robustness();
  assert.equal(evidence.summary.event_count, 7407);
  assert.equal(dynamics.artists.find(row => row.id === 17255).rows.at(-1).cumulative.collaborator_count, 48);
  assert.equal(robustness.influence_scenarios.length, 7);
  assert.equal(robustness.diagnostics.baseline_candidate_top3.unique_top_k_set, false);
  assert.ok(!calls.includes('/clean_graph.json'));
});

test('Vite dev middleware respects project base path and serves JSON', async () => {
  let middleware;
  pipelineDataPlugin({ dataDir }).configureServer({ config: { base: '/course/' },
    middlewares: { use: fn => { middleware = fn; } } });
  const response = { headers: {}, setHeader(k, v) { this.headers[k] = v; }, end(body) { this.body = body; } };
  await middleware({ url: '/course/data/overview.json' }, response, () => assert.fail('unexpected fallthrough'));
  assert.equal(JSON.parse(response.body).counts.nodes, 17412);
  assert.match(response.headers['Content-Type'], /application\/json/);
  const blocked = { ...response, statusCode: 200 };
  await middleware({ url: '/course/data/clean_graph.json' }, blocked, () => assert.fail('unexpected fallthrough'));
  assert.equal(blocked.statusCode, 404);
  let moduleThreePassedThrough = false;
  await middleware({ url: '/course/data/processed/rising_star.json' }, response,
    () => { moduleThreePassedThrough = true; });
  assert.equal(moduleThreePassedThrough, true);
});
