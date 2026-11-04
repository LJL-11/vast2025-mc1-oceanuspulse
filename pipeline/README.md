# pipeline · 数据工程

负责人：数据工程。产出全部进 `data/processed/`（已被 gitignore，本地生成）。

## 环境

```bash
pip install -r requirements.txt   # networkx / pandas / numpy / scipy / scikit-learn
```

## 脚本规划

| 脚本 | 职责 | 状态 |
|---|---|---|
| `explore.py` | 数据探查：分量、类型分布、时间字段异常、Sailor Shift 子图 | 待办 |
| `build_graph.py` | 加载 + 清洗 + 导出清洗后的图（pickle/json） | 待办 |
| `metrics.py` | 图指标：度/中心性、ego network、InStyleOf 流派时序聚合 | 待办 |
| `features.py` | rising star 特征 + 三人对比 + Top3 预测 + 统计检验，产出 `data/processed/rising_star.json` | 已完成（模块三） |
| `export_frontend.py` | 生成前端 JSON（含 D3 力导图预计算布局，17k 节点不能前端实时算） | 待办 |

## 模块三产物（`features.py`）

```bash
python features.py        # 生成 data/processed/rising_star.json
```

- `comparison`：Sailor Shift / Orla Seabloom / The Brine Choir 三条职业轨迹
- `predictions`：2040–2045 年 Oceanus Folk 新星 Top3
- `validation`：GroupKFold AUC / AP / Brier、Mann–Whitney + BH-FDR、Logistic 系数
- 前端视图 `web/src/views/RisingStar.vue` 读取该 JSON

## 约定

- 每个脚本可独立运行：`python explore.py`
- 输出文件带日期后缀或固定名 + 在 `docs/02-数据说明.md` 登记
- 发现数据坑（异常年份/重复节点/孤立分量）记到 `docs/04-会议记录.md`
