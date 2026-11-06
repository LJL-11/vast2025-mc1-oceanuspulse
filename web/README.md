# web · 前端系统 OceanusPulse

负责人：组长。技术栈：**Vite + Vue 3 + Pinia + ECharts 5 + D3（力导图）**。

## 环境

```bash
npm install
npm run dev        # 本地开发
npm run build      # 产物在 dist/，用于部署
```

## 前置条件

前端所有视图都从 `data/processed/` 读 JSON，而该目录不入库。**先在仓库根目录运行**：

```bash
.venv/Scripts/python -m pipeline.run
.venv/Scripts/python pipeline/features.py
```

`vite.config.js` 中 `pipelineDataPlugin()` 提供契约内的 84 份产物，`risingStarPlugin()` 单独提供模块三的 `rising_star.json`（不在数据工程契约内）。两者在 dev 时通过中间件返回本地文件，在 build 时输出到 `dist/data/`。

## 已实现的目录结构

```
src/
├── App.vue                   # 深蓝导航 + 三模块 Tab + 全局焦点条 + KeepAlive 动态视图
├── views/
│   ├── InfluenceTrace.vue    # 模块一：两跳关系图 / 合作者 / 轨迹 / 路径证据（任务 1.1–1.3）
│   ├── GenreSpread.vue       # 模块二：趋势 / 流向矩阵 / 堆叠面积 / 钻取（任务 2.1–2.3）
│   └── RisingStar.vue        # 模块三：Top3 / 轨迹 / 雷达 / 排行 / 检验（任务 3.1–3.2）
├── components/
│   ├── ForceGraph.vue        # D3 缩放拖拽 + 预计算坐标渲染，不做浏览器力仿真
│   ├── ChartPanel.vue        # ECharts 容器，deep watch + ResizeObserver + 点击事件
│   ├── TimeScrubber.vue      # 双滑块时间窗 + 快捷区间
│   ├── FilterPanel.vue       # 通用多选 chips
│   └── DetailCard.vue        # 选中实体详情与关系构成
├── lib/
│   ├── dataService.js        # 官方 createDataService 包装 + 友好错误提示
│   └── palette.js            # 节点/关系/流派配色与格式化工具
├── stores/useAppStore.js     # Pinia：焦点实体、时间窗、类型、流派、趋势指标
└── styles/main.css           # 全部 .op- 组件样式 + 模块三 legacy 变量兼容
```

## 已知修复（改动前请留意）

- `RisingStar.vue` 的图表容器位于 `v-else` 分支内，原实现在 `loading` 尚未结束时初始化 ECharts，导致三张图全空白。已改为 `loading=false → await nextTick() → renderCharts()`。
- `App.vue` 在切换模块后派发一次 `resize`，让 KeepAlive 缓存视图里的 ECharts 重新读取容器尺寸。
- 模块三原有 `--c-primary` / `--c-muted` / `--c-border` 变量由 `styles/main.css` 继续提供，不要删。

## 约定

- `components/` 与 `lib/` 是公共代码，改动前在群里打招呼
- 新视图先在 `feat/视图名` 分支开发，提 PR 合并
- 数据只从 `data/processed/` 读，**不要在 web 里直接读 6.5MB 原图**
- 部署目标：GitHub Pages（或 Netlify/Vercel，结课前定）；`npm run build` 会一并把所需 JSON 输出到 `dist/data/`
