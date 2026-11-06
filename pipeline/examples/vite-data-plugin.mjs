/** Optional Vite 5 adapter: serve processed JSON in dev and emit selected assets on build. */
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const frontendFiles = new Set([
  'overview.json', 'network_overview.json', 'sailor_ego.json', 'node_index.json',
  'artist_index.json', 'sailor_shift.json', 'influence_events.json', 'genre_trends.json',
  'genre_flows.json', 'rising_star_baseline.json',
  'influence_evidence.json', 'network_dynamics.json', 'robustness_report.json',
]);
const isFrontendFile = name => frontendFiles.has(name) || /^artists\/(?:[0-5][0-9]|6[0-3])\.json$/.test(name);

export function pipelineDataPlugin({ dataDir = fileURLToPath(new URL('../../data/processed/', import.meta.url)) } = {}) {
  async function manifest() {
    const value = JSON.parse(await readFile(path.join(dataDir, 'manifest.json'), 'utf8'));
    return { ...value, files: value.files.filter(entry => isFrontendFile(entry.path)) };
  }
  async function asset(entry) {
    const source = await readFile(path.join(dataDir, entry.path));
    const digest = createHash('sha256').update(source).digest('hex');
    if (digest !== entry.sha256 || source.length !== entry.bytes) {
      throw new Error(`数据文件与 manifest 不一致: ${entry.path}，请重新运行 python -m pipeline.run`);
    }
    return source;
  }
  return {
    name: 'oceanuspulse-processed-data',
    configureServer(server) {
      const base = server.config.base === './' ? '/' : server.config.base;
      const prefix = `${base.endsWith('/') ? base : `${base}/`}data/`;
      server.middlewares.use(async (req, res, next) => {
        const pathname = new URL(req.url, 'http://localhost').pathname;
        if (!pathname.startsWith(prefix)) return next();
        const name = pathname.slice(prefix.length);
        // Module three owns this separate static asset and its output contract.
        if (name === 'processed/rising_star.json') return next();
        if (name !== 'manifest.json' && !isFrontendFile(name)) {
          res.statusCode = 404;
          return res.end('Unknown processed data asset');
        }
        try {
          const index = await manifest();
          const entry = index.files.find(file => file.path === name);
          if (name !== 'manifest.json' && !entry) {
            res.statusCode = 404;
            return res.end('Missing processed data asset');
          }
          const body = name === 'manifest.json' ? JSON.stringify(index) : await asset(entry);
          res.setHeader('Content-Type', 'application/json; charset=utf-8');
          res.setHeader('Cache-Control', 'no-cache');
          res.end(body);
        } catch (error) {
          res.statusCode = 503;
          res.setHeader('Content-Type', 'text/plain; charset=utf-8');
          res.end(`数据未就绪，请在仓库根目录运行 python -m pipeline.run\n${error.message}`);
        }
      });
    },
    async generateBundle() {
      const index = await manifest();
      this.emitFile({ type: 'asset', fileName: 'data/manifest.json', source: JSON.stringify(index) });
      for (const entry of index.files) {
        this.emitFile({ type: 'asset', fileName: `data/${entry.path}`, source: await asset(entry) });
      }
    },
  };
}
