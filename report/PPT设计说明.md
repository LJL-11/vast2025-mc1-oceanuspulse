# DESIGN · OceanusPulse 结课答辩

## 全局视觉约定

- **画布**：1280×720；padding 上下/左右 60px；内容区 1160×600
- **风格**：学术风（高校结课答辩），白底 + 学术宝蓝，克制、证据驱动
- **配色**：主色 `#1E4FA8`（顶条/编号/强调）、辅色 `#3D7BD9` / `#E8EFF8`（信息横幅/浅底）、强调色 `#D9534F`（关键数字，≤3%）、正文 `#1A2230` / `#4A5568` / `#8B97A8`、底色 `#FFFFFF`、分隔线 `#D6DCE5`
- **字体**：中文思源黑体（fallback 微软雅黑），西文 Arial；封面主标 56、页主标 34、卡内小标 24、正文 20、注释 14
- **视觉母题**：所有内容页统一「深蓝顶条（76px）+ 浅蓝结论横幅 + 页脚细线」，封面/结尾不加顶条与页脚
- **配图清单**（全部来自本项目真实产物，非生成图）：

| 文件 | 等级 | 来源 | 使用页 |
|---|---|---|---|
| `assets/sketch_overview.png` | L1 | 手绘草图 01 转 PNG | P5 |
| `assets/sketch_module1.png` | L2 | 手绘草图 02 转 PNG | P5 |
| `assets/shot_module1.png` | L1 | 模块一系统截图 | P6 |
| `assets/shot_module2.png` | L1 | 模块二系统截图 | P8 |
| `assets/shot_module3.png` | L1 | 模块三系统截图 | P10 |

## 逐页规划

| 页 | type | role / rhythm | 标题 | 视觉 | anti_pattern |
|---:|---|---|---|---|---|
| 01 | cover | hero / peak | OceanusPulse · 潮音脉 | 无图，蓝色主标 | 封面不得出现数据指标 |
| 02 | content | supporting / valley | 选题与背景 | 三段式文字 + 结论条 | 禁止空泛「机遇与挑战」句式 |
| 03 | content | supporting / valley | 数据规模与三个口径陷阱 | KPI 三联数 | 禁止只摆数字不给判断 |
| 04 | content | supporting / valley | 系统总览：三模块对应三问 | 三栏文字 + 联动说明 | 禁止等宽装饰卡片堆叠 |
| 05 | content | hero / peak | 设计过程（课程硬性要求） | 草图 L1 | 禁止把草图缩成小贴片 |
| 06 | content | hero / peak | 模块一 · 影响力溯源 | 截图 L1 | 禁止图占 <40% |
| 07 | content | supporting / valley | 洞见 1–2：没有单一导师 / 两次代际交接 | 结论条 + 数据 | 禁止无证据的形容词 |
| 08 | content | hero / peak | 模块二 · 流派传播 | 截图 L1 | 禁止图占 <40% |
| 09 | content | supporting / valley | 洞见 3–4：多波次脉冲 / 双向互哺 | 结论条 + 数据 | 禁止把峰值占比说成渐进 |
| 10 | content | hero / peak | 模块三 · 新星预测 | 截图 L1 | 禁止图占 <40% |
| 11 | content | supporting / valley | 洞见 5–6 与方法可信度 | KPI + 局限清单 | 禁止把 AUC 说成准确率 |
| 12 | ending | hero / peak | 结论、分工与局限 | 分工表 | 禁止致谢金句横幅 |

数字全部来自 `report/项目总结报告.md` 与 `data/processed/` 实测结果，不编造。

## 最终实现与验证

- 正式交付为 `report/项目汇报.pptx`，画布 13.333 × 7.5 in（16:9，等价于上表 1280×720 规划），由 `report/generate_ppt.py` 使用 `python-pptx` 生成。
- 原计划用专用 PPT DSL 工具链生成，但其原生模块在本机加载失败（`Failed to load native binding`），改为本地 Python 直接产出，保证文件可交；`report/ppt_build/` 是这一过程留下的中间产物，已加入 `.gitignore`，不入库。
- 配图最终统一放在 `report/screenshots/`：P5 用 `04-design-sketch-overview.png`，P6/P8/P10 用三张模块截图，全部是本项目真实产物。
- 已用本机 PowerPoint 打开并导出 12 页 PDF 逐页检查：无越界形状、无文字溢出横幅、无孤立标点，4 张图片均完整嵌入。
- 版式迭代记录：横幅初版高度不足，长句会换行掉到白底上；改为 0.8 in 高并垂直居中；第 10 页 Top3 与第 11 页局限清单缩短为单行，消除难看折行。
