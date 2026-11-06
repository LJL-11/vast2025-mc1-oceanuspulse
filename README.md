# OceanusPulse · 潮音脉

**IEEE VAST Challenge 2025 Mini-Challenge 1 可视分析系统** —— 《数据可视化》课程项目（指导教师：周芳芳）

> 记者 Silas Reed 要写一篇《Oceanus Folk: Then-and-Now》。我们基于官方音乐产业知识图谱（17,412 节点 / 37,857 边），构建可交互可视分析系统，追踪巨星 Sailor Shift 的崛起之路、Oceanus Folk 流派的全球传播，并预测下一位爆红新星。

## 赛题任务（详见 docs/01-任务书中文翻译.md）

| # | 任务 | 对应系统模块 |
|---|---|---|
| 1 | Sailor Shift 职业画像：影响力来源、合作网络、社区影响 | 模块一 · 影响力溯源 |
| 2 | Oceanus Folk 传播路径：渐进 or 爆发？影响谁？被谁影响？ | 模块二 · 流派传播 |
| 3 | Rising Star 画像：三人对比 + 预测未来五年三颗新星 | 模块三 · 新星预测 |

## 队伍分工（5 人）

| 角色 | 成员 | 职责 | 主要交付物 |
|:--|---|---|---|
| 组长 · 前端架构 | 付嘉一 | 仓库管理、前端框架、共享组件库（力导图/时间线/筛选/搜索）、三模块联动整合、00 全景图谱接入、部署 | 系统整合 + 模块一视图 |
| 数据工程 | 邬昊文 | `pipeline/`：数据清洗、networkx 建图、图指标计算（中心性/自我网络/影响力传播）、导出前端数据 | pipeline + 指标 JSON |
| 分析 · 模块二 | 资丰瑞 | Oceanus Folk 传播分析：渐进 vs 爆发、受影响流派与艺人、反向影响 | 模块二视图 + 分析结论 |
| 分析 · 模块三 | 周涛 | Rising Star 特征工程、三位艺人职业生涯对比、预测 Top3 及统计检验 | 模块三视图 + 预测报告 |
| 设计 · 文档 | 隋咏轩 | 手绘设计过程、设计规范、全部文档、答辩 PPT、进度管理 | 设计手绘 + PPT + 文档 |

> 分工原则：每人既背分析任务也领视图实现，数据工程独立成线；课程评分看"提交文档质量 + 数据分析质量"，文档线责任到人。

## 仓库结构

```
vast2025-mc1/
├── data/
│   ├── raw/                    # 官方原始数据（已入库，勿改）
│   │   ├── MC1_graph.json      # 主数据：音乐知识图谱 6.5MB
│   │   ├── MC1-数据说明-官方.docx
│   │   └── MC1-答卷模板-官方.htm
│   └── processed/              # pipeline 产出（生成物，不进库）
├── pipeline/                   # Python 数据处理（数据工程负责）
├── web/                        # Vue 3 + ECharts + D3 前端系统（组长负责）
├── docs/                       # 任务书翻译 / 数据说明 / 设计手绘 / 会议记录
└── report/                     # 结课提交物（PPT / 总结报告 / 个人总结）
```

## 快速开始（clone 后必须先生成数据）

`data/processed/` 的 84 份 JSON **不入库**，前端所有视图都依赖它；没生成数据页面会提示「数据未就绪」。

```bash
# 1) Python 数据管线（仓库根目录，Windows；Linux/macOS 用 .venv/bin/python）
python -m venv .venv
.venv/Scripts/python -m pip install -r pipeline/requirements.txt
.venv/Scripts/python -m pipeline.run          # 84 份 JSON，约 15.8 秒
.venv/Scripts/python pipeline/features.py     # 模块三独立产物 rising_star.json
.venv/Scripts/python -m unittest discover -s pipeline/tests -v   # 45 项
node --test pipeline/tests/frontend.test.mjs                     # 8 项

# 2) 前端（Node.js ≥ 18）
cd web && npm install && npm run dev
```

打开 <http://127.0.0.1:5173/>。`web/vite.config.js` 已接入官方 `pipelineDataPlugin` 与模块三独立数据插件：开发时从本地 `data/processed/` 提供 JSON，构建时把所需文件输出到 `dist/data/`；**前端从不直接读 6.5MB 原图**。

URL 深链接：`?module=overview` / `?module=influence` / `?module=genre` / `?module=rising` 可直达指定模块，答辩演示直接给链接即可。

## 已实现的系统（2026-11-06）

| 模块 | 主要视图 | 交互 |
|---|---|---|
| 零 · 全景图谱（新增） | 26 流派球形三维网络、音乐主题图标、方向流光、实体档案侧栏 | 旋转 / 拖拽 / 缩放、搜索、流入流出筛选、WebGL 二维后备 |
| 一 · 影响力溯源 | Sailor 两跳关系图、合作者排行、作品累积轨迹、上游影响路径表 | 类型/关系筛选、时间窗、缩放拖拽、悬停聚焦、点击详情、证据钻取 |
| 二 · 流派传播 | 26 流派年度趋势、流向矩阵热力图、五类关系堆叠面积、证据钻取表 | 指标切换、流派/关系多选、时间窗、点格子回查原始边 ID |
| 三 · 新星预测 | Top3 卡片、三人轨迹、能力雷达、综合分排行、统计检验面板 | 卡片证据链、图表联动 |

共享状态（焦点实体 / 时间窗 / 关系类型 / 流派）由 Pinia 管理；任一模块选中实体后，可从顶部焦点条一键跳到模块二查看该实体流派的传播。

## 交付物与文档

- `report/项目总结报告.md` — 按官方三问逐条作答的答卷 + 6 条深度洞见
- `report/答辩PPT大纲.md` — 13 页 / 15 分钟逐页大纲与讲稿主线
- `report/个人总结模板.md` — 5 人各自填写的 5 页总结模板
- `docs/03-设计手绘/` — 三轮手绘草图与视觉 / 交互规范
- `docs/05`–`07` — 数据工程交接、前端数据契约、稳健性说明

## 复现口径

本机实测环境：Python 3.13 / NetworkX 3.5 / NumPy 2.2.4 / SciPy 1.15.2 / pandas 3.1.1 / scikit-learn 1.9.1。`requirements.txt` 未锁定 pandas、scikit-learn 的小版本，不同环境的回溯 AUC 会微幅漂移（本机 0.625，模块三初版报告 0.619）；答辩引用数字以 `data/processed/rising_star.json` 的 `validation.cross_validation.auc` 为准，并注明环境版本。

## 协作规范

- **分支**：`main` 受保护，日常在 `feat/xxx` / `fix/xxx` 分支开发，完成后提 PR 由组长合并
- **Commit**：`feat:` 新功能 / `fix:` 修复 / `docs:` 文档 / `data:` 数据与指标 / `style:` 样式，中文说明写清楚改了什么
- **数据**：`data/raw/` 只读；要改数据走 `pipeline/` 产出到 `data/processed/`
- **进度**：每周例会后更新 `docs/04-会议记录.md`

## 数据来源

- 赛题：<https://vast-challenge.github.io/2025/MC1.html>
- 数据：`github.com/vast-challenge/2025-data`（国内下载走 `fastly.jsdelivr.net/gh/...` 镜像）
