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
├── App.vue                   # 蓝色渐变流光表头 + 四模块 Tab（00 全景 + 01/02/03）+ 全局焦点条 + KeepAlive 动态视图
├── views/
│   ├── NetworkOverview.vue   # 模块零：全景图谱总览入口（26 流派 / 342 关系 / 600 有界实体）
│   ├── InfluenceTrace.vue    # 模块一：两跳关系图 / 合作者 / 轨迹 / 路径证据（任务 1.1–1.3）
│   ├── GenreSpread.vue       # 模块二：趋势 / 流向矩阵 / 堆叠面积 / 钻取（任务 2.1–2.3）
│   └── RisingStar.vue        # 模块三：Top3 / 轨迹 / 雷达 / 排行 / 检验（任务 3.1–3.2）
├── components/
│   ├── SpatialNetwork.vue    # Three.js WebGL 三维球形图谱（按需异步加载）
│   ├── NetworkFallback.vue   # WebGL 不可用时的二维 Canvas 后备
│   ├── NetworkCanvas.vue     # 二者切换包装
│   ├── AppIcon.vue           # 内联 Lucide 路径图标
│   ├── ForceGraph.vue        # D3 缩放拖拽 + 预计算坐标渲染，不做浏览器力仿真
│   ├── ChartPanel.vue        # ECharts 容器，deep watch + ResizeObserver + 点击事件
│   ├── TimeScrubber.vue      # 双滑块时间窗 + 快捷区间
│   ├── FilterPanel.vue       # 通用多选 chips
│   └── DetailCard.vue        # 选中实体详情与关系构成
├── lib/
│   ├── dataService.js        # 官方 createDataService 包装 + 友好错误提示
│   ├── palette.js            # 节点/关系/流派配色与格式化工具
│   ├── genre-icons.js        # 流派主题图标 SVG（Lucide 0.468.0 / ISC）
│   └── genre-icon-map.js     # 流派名 → 图标名映射
├── stores/useAppStore.js     # Pinia：焦点实体、时间窗、类型、流派、趋势指标、00 动效开关
└── styles/
    ├── main.css              # 全部 .op- 组件样式 + 模块三 legacy 变量兼容
    ├── network.css           # 00 图谱基础样式（来自 PR #4，未改）
    └── overview-scope.css    # 00 白底学术蓝适配层（新建，.op-overview 作用域隔离）
```

## 00 全景图谱（PR #4 摘入）

- 依赖 `three@0.170.0`（仅 00 使用，由 `NetworkCanvas.vue` 异步加载，不影响其它模块首屏）。
- 数据仍走既有契约：`dataService.overview()` / `network()` / `genreFlows()`；没有新增接口，也没有改动 `dataService.js` / `palette.js`。
- 主题适配全部在 `styles/overview-scope.css`：选择器一律以 `.op-overview` 开头（`App.vue` 只在 overview 激活时给 `<main>` 加这个类），页面框架引用 `main.css` 的浅色变量，三维画布内部保留深色并把文字反转成浅色。**不要在这里写全局 `body` / `:root` 覆盖**，否则会污染其它模块。
- `network.css` 里画布是 `height:100%`，`.network-stage` 必须有确定高度（桌面 560 / 平板 440 / 手机 360px）；只给 `min-height` 会被节点标签撑到 6000+px，WebGL 相机投影失效、页面只剩黑底。
- 深链接：`?module=overview`。图标许可见 `src/lib/LICENSE-lucide.txt`。

## 已知修复（改动前请留意）

- `RisingStar.vue` 的图表容器位于 `v-else` 分支内，原实现在 `loading` 尚未结束时初始化 ECharts，导致三张图全空白。已改为 `loading=false → await nextTick() → renderCharts()`。
- `App.vue` 在切换模块后派发一次 `resize`，让 KeepAlive 缓存视图里的 ECharts 重新读取容器尺寸。
- 模块三原有 `--c-primary` / `--c-muted` / `--c-border` 变量由 `styles/main.css` 继续提供，不要删。

## 约定

- `components/` 与 `lib/` 是公共代码，改动前在群里打招呼
- 新视图先在 `feat/视图名` 分支开发，提 PR 合并
- 数据只从 `data/processed/` 读，**不要在 web 里直接读 6.5MB 原图**
- 部署目标：GitHub Pages（或 Netlify/Vercel，结课前定）；`npm run build` 会一并把所需 JSON 输出到 `dist/data/`
- 后续 PR 的分层所有权与 rebase 规则见 `docs/09-协作规范.md`：**Shell 层**（`App.vue` / `main.css` / `useAppStore.js` / `dataService.js` / `vite.config.js` / `package.json`）只有组长能改；组员 PR 只提交自己负责的那个 `views/*.vue` 文件
