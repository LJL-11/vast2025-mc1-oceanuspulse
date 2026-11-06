# pipeline · 数据工程

数据工程负责人：**邬昊文**；模块三分析脚本 `features.py` 由 **周涛**负责。本目录实现 IEEE VAST Challenge 2025 MC1 的可复现数据管线与分析；原始文件只读，全部数据生成到 `data/processed/`，生成物不提交 Git。

当前契约 **v1.1.0** 在原有字段上新增影响归属证据、年度/滚动指标和敏感性报告。仍属于数据清洗、图建模、指标计算与核验职责，详见 [本次优化说明](../docs/07-数据工程优化与稳健性.md)。

## 一键运行

在仓库根目录执行（推荐 Python 3.11–3.13；本次验证为 3.13.0）：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r pipeline/requirements.txt
.venv/Scripts/python -m pipeline.run
.venv/Scripts/python -m pipeline.validate
.venv/Scripts/python -m unittest discover -s pipeline/tests -v
node --test pipeline/tests/frontend.test.mjs
```

已经有满足依赖的 Python 时，直接执行 `python -m pipeline.run`。Linux/macOS 的虚拟环境解释器路径为 `.venv/bin/python`。前端适配器测试使用 Node.js ≥18；纯 Python 管线无需 Node。

从 `pipeline/` 目录也能执行 `python run.py`，所有默认路径均相对脚本定位，不依赖当前工作目录。默认 `cutoff=2040` 是赛题故事时间，不取电脑当前年份。

```powershell
# 指标的历史截面；另存，避免覆盖默认 2040 交付
python -m pipeline.run --cutoff 2035 --out data/processed/snapshots/2035

# 调整可视化节点预算、介数抽样数；seed 默认 42
python -m pipeline.run --max-nodes 600 --samples 96 --seed 42

# 添加职业对比对象；默认会包含 Sailor、原乐队成员和最多 10 位候选
python -m pipeline.run --compare-ids 17349 17355 --out data/processed/comparison

# 新版网络动态指标的滚动窗；旧有 recent_5y 特征仍固定为五年
python -m pipeline.run --window-years 5

# 可选：限制候选艺人近五年有记录。默认不按缺失记录断言不活跃
python -m pipeline.artist_features --candidate-career-years 10 --candidate-active-within 5 --out data/processed/experiments
```

## 脚本与职责

| 文件 | 职责 | 可独立运行 |
|---|---|---|
| `explore.py` | 类型、分量、时间、同名实体、重复关系、端点模式与异常审计 | `python explore.py` |
| `build_graph.py` | 标准字段、整数年份、原属性保留、NetworkX 有向多重图 | `python build_graph.py` |
| `metrics.py` | 度、合作 PageRank、抽样介数、影响来源 PageRank、Sailor 子图与证据路径 | `python metrics.py` |
| `genres.py` | 五类影响边按流派/年份/关系聚合，正反影响及归一化分母 | 由整条管线调用 |
| `influence.py` | 明确艺人关系与作品归属推导分开，保留引用和署名边证据 | 由整条管线调用 |
| `temporal.py` | 全网络逐年重算、有限对比对象导出、滚动流派传播指标 | 由整条管线调用 |
| `robustness.py`、`rankings.py` | 7 套影响规则、5 套评分权重，保留并列的排名对照 | 由整条管线调用 |
| `artist_features.py` | 数据工程：历史截面特征、职业轨迹、带解释的候选基线 | `python artist_features.py` |
| `features.py` | 模块三：三人对比、Top3 预测与统计检验，生成 `rising_star.json` | `python features.py` |
| `export_frontend.py` | 有限节点力导布局、索引、64 份艺人分片；独立执行会完整重建 | `python export_frontend.py` |
| `run.py` | 全量编排、原始文件哈希核验、生成 manifest、自动验证 | `python run.py` |
| `validate.py` | 哈希、计数、引用、时间、布局、流量与职业轨迹一致性 | `python validate.py` |
| `validate_analytics.py` | 引用/署名路径、年度截面和敏感性报告的交叉核验 | 由完整验证调用 |
| `common.py` | 公共契约与图投影；不依赖 pickle 或不安全反序列化 | 库模块 |

单独执行脚本只重写自己的输出，可能使旧 manifest 失效。**正式交接、前端开发与部署前执行完整 `run.py`**；不要混用不同截点、不同版本的 JSON。

## 模块三原有入口

模块三代码、输出格式及运行入口保持。仓库根目录执行：

```powershell
python pipeline/features.py
# 仅验证运行兼容性时，可用 --bootstrap 0 跳过 Bootstrap；完整分析使用上面的默认命令。
```

该脚本另行生成 `data/processed/rising_star.json`，包含三位艺人的 `comparison`、未来五年的 `predictions` 和统计检验 `validation`，由 `web/src/views/RisingStar.vue` 读取。其方法与结论见 [模块三报告](../docs/05-模块三-新星预测.md)。

数据工程的 `artist_features.py` 和 `rising_star_baseline.json` 是独立的通用特征与探索基线；`run.py` 不调用或覆盖模块三的 `features.py`、`rising_star.json`。84 份产物清单仅包含数据工程输出，不包含模块三独立生成的文件。

## 主要产物

| 产物 | 用途 |
|---|---|
| `overview.json`、`manifest.json` | 首屏概况、版本、输入哈希、参数、软件版本、文件校验和 |
| `quality_report.json`、`clean_graph.json` | 全量审计与保留证据的规范图，供工程核查 |
| `node_metrics.json`、`artist_networks.json` | 全量指标与两个独立的艺人网络 |
| `sailor_shift.json`、`sailor_ego.json` | 模块一：作品、合作者、影响来源、传播路径、两跳布局 |
| `genre_trends.json`、`genre_flows.json`、`influence_events.json` | 模块二：年度趋势、流向及逐条原始关系证据 |
| `artist_features.json`、`artist_timelines.json` | 模块三：完整特征和稀疏年度轨迹，供分析计算 |
| `artist_index.json`、`artists/00.json` … `artists/63.json` | 前端搜索及按需读取艺人详情 |
| `rising_star_baseline.json` | 可解释的探索性候选排序、并列名次、无区分力特征与筛选敏感性 |
| `network_overview.json`、`node_index.json` | 有界网络概览及全实体查询索引 |
| `influence_evidence.json` | 明确艺人关系与作品推导关系、署名边 ID 和可核查路径 |
| `network_dynamics.json` | 默认 12 位对比对象的年度网络指标，以及 26 流派的滚动统计 |
| `robustness_report.json` | 规则和权重变化后的排名一致性、并列诊断及常量特征占比 |

默认生成 **84 份 JSON**，本次完整运行约 14 秒；耗时受机器和参数影响。最终生成物约 72.5 MiB，其中包含供工程检查的全图、全量特征及前端分片，不应一次性下载到浏览器。首屏概况约 3.4 KiB，选中艺人后只加载对应的约 295–373 KiB 分片；D3 使用预计算 `x/y`。新版证据文件约 6.6 MiB、动态指标约 714 KiB、稳健性报告约 56 KiB，分别按分析需要加载。

## 重要口径

- 保留 17,412 个节点、37,857 条边。**实际弱连通分量为 16**，不是说明文件中的 18。
- 五类音乐影响关系在原图中为“借鉴者 → 来源”；`influence_events.json` 和流派流向改为“来源 → 受影响者”，并保留 `raw_source/raw_target`。
- 同一作品上多个署名角色只计一次合作。`MemberOf` 没有时间，不展开为成员参与过每一首乐队作品。
- `notable` 表示上过热门榜单，不能推导冠军、销量或流媒体量。4,297 个 notable 作品中 3,648 个没有登榜年份，不能补成发行年或零时差。
- 84 条影响时间顺序疑点、1 条自环在分析中排除；67 条无日期的艺人间影响关系单独保留，不放进年度统计。
- `rising_star_baseline.json` 的候选评分是透明启发式，**没有经过预测效果验证，不是成名概率**。默认得到 7 位候选；最终 Top3 和检验由模块三负责。
- 中心性是指定图投影中的结构指标，不代表流行度或因果效应。新版 `network_dynamics.json` 已按年度重新建图和计算 PageRank；前端时间刷选应取对应年度记录，不能直接筛掉静态图节点后继续沿用原分数。更早的最终观察截点仍用 `--cutoff` 重算。
- 原始数据缺失的日期不会因优化而补成某个年份。去掉常量特征或改变权重，也不会自动消除原本无法区分的候选并列。

详细依据见 [数据工程交接](../docs/05-数据工程交接.md)、[前端数据契约](../docs/06-前端数据契约.md) 和 [优化与稳健性](../docs/07-数据工程优化与稳健性.md)。原始数据陷阱及官方说明差异记录在 [数据说明](../docs/02-数据说明.md)。

## 前端接入

`examples/` 提供已测试的浏览器数据服务和 Vite 适配器。接入只需组长在 `web/vite.config.js` 加插件，见数据契约中的两段示例。适配器会在开发时读取 processed 目录、构建时复制需要的 JSON；不会让前端读原始图或运行全图力仿真。

本分支未改动 `web/src/` 的公共组件或视图。生成数据的约 72.5 MiB 文件不入 Git，其他成员拉取脚本后本地一键生成。
