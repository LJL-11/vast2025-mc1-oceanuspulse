# web · 前端系统 OceanusPulse

负责人：组长。技术栈：**Vite + Vue 3 + Pinia + ECharts 5 + D3（力导图）**。

## 环境

```bash
npm install
npm run dev        # 本地开发
npm run build      # 产物在 dist/，用于部署
```

## 视图规划（与赛题任务对应）

```
src/
├── views/
│   ├── InfluenceTrace.vue    # 模块一：Sailor Shift 影响力溯源（任务 1.1/1.2/1.3）
│   ├── GenreSpread.vue       # 模块二：Oceanus Folk 流派传播（任务 2.1/2.2/2.3）
│   └── RisingStar.vue        # 模块三：新星画像与预测（任务 3.1/3.2）
├── components/               # 共享组件
│   ├── ForceGraph.vue        # 力导图（D3，节点数据来自 pipeline 预计算布局）
│   ├── TimeScrubber.vue      # 时间轴刷选
│   ├── FilterPanel.vue       # 类型/流派/登榜筛选
│   └── DetailCard.vue        # 选中实体详情
├── lib/                      # 数据加载与公共函数
│   ├── dataService.js        # 读取 data/processed/ 产物
│   └── utils.js
├── stores/                   # Pinia：跨模块联动状态（选中实体、时间范围、筛选）
└── styles/
```

## 约定

- `components/` 与 `lib/` 是公共代码，改动前在群里打招呼，避免互相踩bug
- 新视图先在 `feat/视图名` 分支开发
- 数据只从 `data/processed/` 读，**不要在 web 里直接读 6.5MB 原图**
- 部署目标：GitHub Pages（或 Netlify/Vercel，结课前定）
