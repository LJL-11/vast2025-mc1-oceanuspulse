import { createDataService, expandAnnual } from '../../../pipeline/examples/data-service.mjs'

export const dataService = createDataService({
  baseUrl: `${import.meta.env.BASE_URL}data/`,
})

export { expandAnnual }

export async function loadRisingStar() {
  const url = `${import.meta.env.BASE_URL}data/processed/rising_star.json`
  const response = await fetch(url)
  if (!response.ok) throw new Error(`模块三数据未就绪 (${response.status})，请运行 python pipeline/features.py`)
  return response.json()
}

export function friendlyDataError(error) {
  const message = String(error?.message || error)
  if (/manifest|数据加载失败|503|404|Failed to fetch/i.test(message)) {
    return '数据未就绪：请先在仓库根目录运行 python -m pipeline.run 生成 data/processed/，再刷新页面。'
  }
  return message
}
