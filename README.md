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
|---|---|---|---|
| 组长 · 前端架构 | （待填） | 仓库管理、前端框架、共享组件库（力导图/时间线/筛选/搜索）、三模块联动整合、部署 | 系统整合 + 模块一视图 |
| 数据工程 | （待填） | `pipeline/`：数据清洗、networkx 建图、图指标计算（中心性/自我网络/影响力传播）、导出前端数据 | pipeline + 指标 JSON |
| 分析 · 模块二 | （待填） | Oceanus Folk 传播分析：渐进 vs 爆发、受影响流派与艺人、反向影响 | 模块二视图 + 分析结论 |
| 分析 · 模块三 | （待填） | Rising Star 特征工程、三位艺人职业生涯对比、预测 Top3 及统计检验 | 模块三视图 + 预测报告 |
| 设计 · 文档 | （待填） | 手绘设计过程、设计规范、全部文档、答辩 PPT、进度管理 | 设计手绘 + PPT + 文档 |

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

## 快速开始

```bash
# 数据工程
cd pipeline && pip install -r requirements.txt

# 前端（Node.js ≥ 18）
cd web && npm install && npm run dev
```

## 协作规范

- **分支**：`main` 受保护，日常在 `feat/xxx` / `fix/xxx` 分支开发，完成后提 PR 由组长合并
- **Commit**：`feat:` 新功能 / `fix:` 修复 / `docs:` 文档 / `data:` 数据与指标 / `style:` 样式，中文说明写清楚改了什么
- **数据**：`data/raw/` 只读；要改数据走 `pipeline/` 产出到 `data/processed/`
- **进度**：每周例会后更新 `docs/04-会议记录.md`

## 数据来源

- 赛题：<https://vast-challenge.github.io/2025/MC1.html>
- 数据：`github.com/vast-challenge/2025-data`（国内下载走 `fastly.jsdelivr.net/gh/...` 镜像）
