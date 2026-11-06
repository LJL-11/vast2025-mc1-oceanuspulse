import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { pipelineDataPlugin } from '../pipeline/examples/vite-data-plugin.mjs'

const repoRoot = fileURLToPath(new URL('../', import.meta.url))
const risingStarFile = fileURLToPath(new URL('../data/processed/rising_star.json', import.meta.url))

/** Module three owns a separate analysis asset that is not part of the pipeline contract. */
function risingStarPlugin() {
  return {
    name: 'oceanuspulse-rising-star',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const pathname = new URL(req.url, 'http://localhost').pathname
        if (!pathname.endsWith('/data/processed/rising_star.json')) return next()
        try {
          const body = await readFile(risingStarFile)
          res.setHeader('Content-Type', 'application/json; charset=utf-8')
          res.setHeader('Cache-Control', 'no-cache')
          res.end(body)
        } catch {
          res.statusCode = 503
          res.setHeader('Content-Type', 'text/plain; charset=utf-8')
          res.end('模块三数据未就绪，请在仓库根目录运行 python pipeline/features.py')
        }
      })
    },
    async generateBundle() {
      try {
        this.emitFile({
          type: 'asset',
          fileName: 'data/processed/rising_star.json',
          source: await readFile(risingStarFile),
        })
      } catch {
        this.warn('未找到 data/processed/rising_star.json，模块三页面会提示数据缺失。请先运行 python pipeline/features.py')
      }
    },
  }
}

export default defineConfig({
  plugins: [vue(), pipelineDataPlugin(), risingStarPlugin()],
  base: './',
  server: {
    fs: { allow: [repoRoot] },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/echarts') || id.includes('node_modules/zrender')) return 'echarts'
          if (id.includes('node_modules/d3') || id.includes('node_modules/internmap')) return 'd3'
          if (id.includes('node_modules/vue') || id.includes('node_modules/pinia')) return 'vue'
          return undefined
        },
      },
    },
  },
})
