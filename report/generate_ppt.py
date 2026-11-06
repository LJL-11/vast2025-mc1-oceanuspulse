# -*- coding: utf-8 -*-
"""Generate the 12-slide course defense deck for OceanusPulse.

复现方式（在仓库根目录）：
    python -m pip install python-pptx==1.0.2 pillow
    python report/generate_ppt.py

输出 report/项目汇报.pptx。所有数字来自 report/项目总结报告.md 与
data/processed/ 下的实测产物，配图来自 report/screenshots/。
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image
import os

REPORT_DIR = os.path.dirname(os.path.abspath(__file__))   # 本脚本位于 report/
ROOT = os.path.dirname(REPORT_DIR)                        # 仓库根目录
SHOTS = os.path.join(REPORT_DIR, 'screenshots')
OUT = os.path.join(REPORT_DIR, '项目汇报.pptx')

BLUE = RGBColor(0x1E, 0x4F, 0xA8)
MID = RGBColor(0x3D, 0x7B, 0xD9)
LIGHT = RGBColor(0xE8, 0xEF, 0xF8)
INK = RGBColor(0x1A, 0x22, 0x30)
MUTED = RGBColor(0x4A, 0x55, 0x68)
GREY = RGBColor(0x8B, 0x97, 0xA8)
RED = RGBColor(0xD9, 0x53, 0x4F)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LINE = RGBColor(0xD6, 0xDC, 0xE5)
FONT = 'Microsoft YaHei'

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def rect(slide, x, y, w, h, fill=None, border=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    if border is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = border
        shape.line.width = Pt(0.75)
    return shape


def text(slide, x, y, w, h, lines, size=18, color=INK, bold=False,
         align=PP_ALIGN.LEFT, spacing=1.35, after=6):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    items = lines if isinstance(lines, (list, tuple)) else [lines]
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = color
        p.font.name = FONT
        p.alignment = align
        p.line_spacing = spacing
        p.space_after = Pt(after)
    return box


def image(slide, path, x, y, max_w, max_h):
    iw, ih = Image.open(path).size
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    px = x + (max_w - w) / 2
    py = y + (max_h - h) / 2
    slide.shapes.add_picture(path, Inches(px), Inches(py), width=Inches(w), height=Inches(h))
    return px, py, w, h


def header(slide, title, page, tag=''):
    rect(slide, 0, 0, 13.333, 0.88, BLUE)
    text(slide, 0.6, 0.12, 10.5, 0.64, title, size=30, color=WHITE, bold=True)
    if tag:
        text(slide, 10.4, 0.22, 2.35, 0.44, tag, size=14, color=WHITE, align=PP_ALIGN.RIGHT)
    rect(slide, 0.6, 7.02, 12.13, 0.012, LINE)
    text(slide, 0.6, 7.08, 8.0, 0.3,
         'OceanusPulse · 潮音脉  |  VAST 2025 MC1 课程项目答辩', size=11, color=GREY)
    text(slide, 10.6, 7.08, 2.13, 0.3, f'{page:02d} / 12', size=11, color=GREY,
         align=PP_ALIGN.RIGHT)


def banner(slide, label, sentence, y=1.02):
    # 横幅允许两行：加高底色并垂直居中，避免长句溢出到白底上。
    rect(slide, 0.6, y, 12.13, 0.8, LIGHT)
    rect(slide, 0.6, y, 0.08, 0.8, BLUE)
    label_box = text(slide, 0.82, y + 0.08, 2.1, 0.64, label, size=16,
                     color=BLUE, bold=True, spacing=1.0, after=0)
    label_box.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    body_box = text(slide, 2.9, y + 0.05, 9.6, 0.7, sentence, size=15,
                    color=INK, spacing=1.12, after=0)
    body_box.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE


def conclusion(slide, sentence):
    rect(slide, 0.6, 6.42, 12.13, 0.46, LIGHT)
    text(slide, 0.8, 6.47, 11.75, 0.36, sentence, size=15, color=BLUE, bold=True)


def kpi(slide, x, value, label, note=''):
    rect(slide, x, 2.0, 3.85, 1.9, WHITE, LINE)
    text(slide, x + 0.18, 2.16, 3.5, 0.8, value, size=46, color=BLUE, bold=True)
    text(slide, x + 0.18, 3.0, 3.5, 0.35, label, size=17, color=INK, bold=True)
    if note:
        text(slide, x + 0.18, 3.38, 3.5, 0.4, note, size=13, color=MUTED)


def bullet_block(slide, x, y, w, h, title, items, tone=BLUE):
    rect(slide, x, y, w, h, WHITE, LINE)
    rect(slide, x, y, w, 0.09, tone)
    text(slide, x + 0.24, y + 0.24, w - 0.48, 0.5, title, size=22, color=tone, bold=True)
    text(slide, x + 0.24, y + 0.92, w - 0.48, h - 1.1,
         ['• ' + item for item in items], size=16, color=INK, spacing=1.3, after=8)


# P1 cover
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, 13.333, 7.5, WHITE)
rect(s, 0.85, 1.45, 0.16, 3.2, BLUE)
text(s, 1.3, 1.6, 11.2, 1.0, 'OceanusPulse · 潮音脉', size=52, color=BLUE, bold=True)
text(s, 1.3, 2.72, 11.2, 0.6,
     'IEEE VAST Challenge 2025 MC1 音乐知识图谱可视分析', size=24, color=INK)
text(s, 1.3, 3.42, 11.2, 0.5, '《数据可视化》课程项目 · 结课答辩', size=20, color=MUTED)
rect(s, 1.3, 4.35, 10.7, 0.012, LINE)
text(s, 1.3, 4.6, 11.2, 0.9,
     ['付嘉一 · 邬昊文 · 资丰瑞 · 周涛 · 隋咏轩',
      '指导教师：周芳芳　｜　中南大学　｜　2026 年 11 月'],
     size=16, color=GREY, spacing=1.4)

# P2 background
s = prs.slides.add_slide(BLANK)
header(s, '选题与研究背景', 2, '01 · Background')
banner(s, '研究问题', '三个问题：Sailor 如何崛起、Oceanus Folk 如何扩散、谁是下一个新星。')
bullet_block(s, 0.6, 1.95, 3.85, 3.9, '为什么选 MC1', [
    '同班无人选，撞题风险为零',
    '官方数据可直接下载，含时序',
    '契合课程图数据 / 时序教学重点',
    '任务边界清晰，可拆成三个模块',
])
bullet_block(s, 4.74, 1.95, 3.85, 3.9, '数据基础', [
    '17,412 节点 / 37,857 条关系',
    '5 类节点：艺人、歌曲、专辑、乐队、厂牌',
    '12 类边：署名、录制、成员与五类音乐影响',
    '观测截点 2040 年，全部为官方合成数据',
])
bullet_block(s, 8.88, 1.95, 3.85, 3.9, '三问 → 三模块', [
    'Q1 职业画像与影响网络',
    'Q2 Oceanus Folk 的全球传播',
    'Q3 新星画像与 Top3 预测',
    '每问都能回查原始边 ID',
])
conclusion(s, '选题依据：数据可得、任务可拆、结论可核查，且不与全班 28 个已选题目重复。')

# P3 data
s = prs.slides.add_slide(BLANK)
header(s, '数据规模与三个口径陷阱', 3, '02 · Data')
banner(s, '关键观察', '官方说明与本地复现并不一致，报告必须以后者为准。')
kpi(s, 0.6, '17,412', '图谱节点', '5 类实体，ID 唯一')
kpi(s, 4.74, '37,857', '关系边', '12 类，含平行边')
kpi(s, 8.88, '84.9%', '缺登榜年份', '3,648 / 4,297 notable 作品')
text(s, 0.6, 4.12, 12.13, 1.9, [
    '• 官方说明称 18 个连通分量，本地按弱连通重算为 16，最大分量 17,277 节点。',
    '• notable 只表示上过热榜，不代表冠军或销量；缺失年份保持未知，绝不能补 0。',
    '• 84 条引用时间顺序存疑、1 条自环、67 条无日期的艺人间引用，排除年度统计但保留结构证据。',
    '• 全部产物带原始文件 SHA-256 与契约版本，84 份 JSON 可逐字节重建。',
], size=17, color=INK, spacing=1.35, after=9)
conclusion(s, '口径纪律：任何「逐年影响力增长」的图，都必须先排除无日期证据。')

# P4 system
s = prs.slides.add_slide(BLANK)
header(s, '系统总览：三模块对应三问', 4, '03 · System')
banner(s, '架构', 'Vite + Vue 3 + Pinia + ECharts 5 + D3；前端只读 84 份契约 JSON，不加载 6.5MB 原图。')
bullet_block(s, 0.6, 1.95, 3.85, 3.9, '模块一 · 影响力溯源', [
    '两跳网络：269 节点 / 546 边',
    '预计算布局，浏览器不做力仿真',
    '类型 / 时间窗筛选、悬停与点击钻取',
    '可回溯上游路径与原始边 ID',
])
bullet_block(s, 4.74, 1.95, 3.85, 3.9, '模块二 · 流派传播', [
    '26 流派 × 66 年趋势，4 种指标可切换',
    '12×12 流向矩阵（替代有环桑基图）',
    '五类影响关系堆叠面积',
    '点格子回查年份与原始证据',
])
bullet_block(s, 8.88, 1.95, 3.85, 3.9, '模块三 · 新星预测', [
    'Top3 卡片：综合分 / 概率 / 稳定性',
    '轨迹折线、能力雷达、综合分排行',
    '交叉验证与 FDR 检验面板',
    '全部数字来自可复现脚本',
], tone=MID)
conclusion(s, '跨模块联动：选中实体 → 全局焦点条 → 一键跳转该流派的传播视图；?module= 可直达指定模块。')

# P5 design process
s = prs.slides.add_slide(BLANK)
header(s, '设计过程（课程硬性要求）', 5, '04 · Design')
banner(s, '三轮迭代', '从手绘草图到组件化前端，每轮都记录被否决的方案与理由。')
image(s, os.path.join(SHOTS, '04-design-sketch-overview.png'), 0.6, 1.95, 6.9, 4.3)
rect(s, 0.6, 1.95, 6.9, 4.3, None, LINE)
text(s, 7.75, 1.98, 4.98, 0.4, '被否决 → 最终采用', size=22, color=BLUE, bold=True)
text(s, 7.75, 2.55, 4.98, 3.6, [
    '× 单页长滚动：三问差异大，证据钻取埋太深',
    '√ 三模块 Tab + 全局焦点 / 时间窗联动',
    '× 浏览器端力仿真：全图 17,412 节点会卡死',
    '√ Python 预计算布局，筛选时结构不跳变',
    '× 桑基图：流派间存在双向环，渲染报错',
    '√ 流向矩阵热力图 + 净流量聚合',
    '× 柱图 / 饼图充数：课程明确禁止',
    '√ 关系网络、矩阵、累积面积、雷达',
], size=15, color=INK, spacing=1.25, after=6)
conclusion(s, '草图与视觉 / 交互规范见 docs/03-设计手绘/，共 3 张，可打印后补手写批注。')

# P6 module 1
s = prs.slides.add_slide(BLANK)
header(s, '模块一 · 影响力溯源', 6, '05 · Module 1')
banner(s, '现场演示', '悬停聚焦邻域 → 点击 Sailor → 切到 2030+ → 点开一条上游路径核查证据。')
image(s, os.path.join(SHOTS, '01-module1-influence.png'), 0.6, 1.92, 6.5, 4.4)
rect(s, 0.6, 1.92, 6.5, 4.4, None, LINE)
text(s, 7.35, 2.0, 5.38, 0.4, '视图与证据', size=22, color=BLUE, bold=True)
text(s, 7.35, 2.55, 5.38, 3.6, [
    '• 38 部直接署名作品、48 位共同署名合作者',
    '• 30 个上游影响来源、81 条可回溯路径（一跳 30 / 二跳 36 / 三跳 15）',
    '• 7 个下游受影响对象，引用全部无日期',
    '• 合作者排行、作品累积轨迹、关系类型构成',
    '• 时间窗外节点淡化而不删除，保留网络结构',
], size=16, color=INK, spacing=1.3, after=9)
conclusion(s, '回答 Q1：影响来源与合作关系可逐条回查，不依赖不可验证的「影响力评分」。')

# P7 insight 1-2
s = prs.slides.add_slide(BLANK)
header(s, '洞见 1–2：没有单一导师，两次代际交接', 7, '06 · Findings')
banner(s, '关键发现', 'Sailor 的崛起不是师承某位巨星，而是广度吸收 + 把新人写进自己的作品署名。')
bullet_block(s, 0.6, 1.95, 5.95, 3.9, '洞见 1 · 广度吸收', [
    '30 个上游来源，每个引用次数都只有 1 次',
    '横跨 Indie Rock、Doom Metal、Synthwave、Americana、Indie Folk 等 ≥7 个流派',
    '81 条上游路径中 75 条日期完整，可核查',
    '结论：不存在支配性导师，风格来自广泛取样',
], tone=RED)
bullet_block(s, 6.78, 1.95, 5.95, 3.9, '洞见 2 · 代际交接', [
    '2024–2026：前乐队 Ivy Echos 成员（Maya Jensen 共同署名 4 部）',
    '2034–2038：转向新一代，The Brine Choir 等各 3 部',
    '多数依附 Coastal Harmony Studios 厂牌',
    'The Brine Choir 正是模块三预测的第一名',
])
conclusion(s, '三个模块因此连成一条证据闭环：她的社区影响不是「被模仿」，而是制造下一代候选者。')

# P8 module 2
s = prs.slides.add_slide(BLANK)
header(s, '模块二 · 流派传播', 8, '07 · Module 2')
banner(s, '现场演示', '切换趋势指标 → 点流向矩阵格子 → 证据表回查年份、关系类型与原始边 ID。')
image(s, os.path.join(SHOTS, '02-module2-genre.png'), 0.6, 1.92, 6.5, 4.4)
rect(s, 0.6, 1.92, 6.5, 4.4, None, LINE)
text(s, 7.35, 2.0, 5.38, 0.4, '视图与口径', size=22, color=BLUE, bold=True)
text(s, 7.35, 2.55, 5.38, 3.6, [
    '• 26 流派 × 66 年（1975–2040）年度趋势',
    '• 12×12 流向矩阵：纵轴来源 / 横轴受影响者',
    '• 五类关系堆叠面积 + 证据钻取表',
    '• 影响边统一为「来源 → 受影响者」，与原图引用方向相反',
    '• 自流排除，缺失分母保持 null 而非 0',
], size=16, color=INK, spacing=1.3, after=9)
conclusion(s, '回答 Q2：向外辐射与向内吸收分开统计，避免把借鉴者误当成来源。')

# P9 insight 3-4
s = prs.slides.add_slide(BLANK)
header(s, '洞见 3–4：多波次脉冲与双向互哺', 9, '08 · Findings')
banner(s, '结论修正', '初版判为「渐进扩散」过于粗糙；按峰值占比与滚动均值重算后应为多波次脉冲。')
bullet_block(s, 0.6, 1.95, 5.95, 3.9, '洞见 3 · 多波次脉冲', [
    '全期 224 条外向影响事件，分布在 23 个年份',
    '峰值 2027 年 38 条，仅占 17.0%',
    '但 2023–2030 集中了 79.9%，滚动均值 2030 年达 27.6',
    '2032 年后仅 1.8%，是样本变少而非影响力消失',
], tone=RED)
bullet_block(s, 6.78, 1.95, 5.95, 3.9, '洞见 4 · 双向互哺', [
    '向外 Top3：Desert Rock 48 / Indie Folk 42 / Dream Pop 41',
    '向内 Top3：Indie Folk 100 / Synthwave 19 / Dream Pop 15',
    'Indie Folk 同时是最大来源与第二大受众',
    '全期 3,266 条跨流派流向记录、4,502 单位流量',
])
conclusion(s, '扩散既不是单年爆发，也不是匀速线性上升；峰值与集中度必须一起看。')

# P10 module 3
s = prs.slides.add_slide(BLANK)
header(s, '模块三 · Rising Star 预测', 10, '09 · Module 3')
banner(s, '预测结果', '候选池严格条件下恰好 3 个 act，本问实质是排序而非从大池筛选。')
image(s, os.path.join(SHOTS, '03-module3-rising.png'), 0.6, 1.92, 6.5, 4.4)
rect(s, 0.6, 1.92, 6.5, 4.4, None, LINE)
text(s, 7.35, 2.0, 5.38, 0.4, '2040–2045 Top3', size=22, color=BLUE, bold=True)
text(s, 7.35, 2.55, 5.38, 3.6, [
    '#1  The Brine Choir   79.84   p .796 / BS 67%',
    "#2  Selkie's Hollow   70.82   p .571 / BS 0%",
    '#3  Tidal Reverie   64.71   p .571 / BS 33%',
    '',
    '综合分 6 维：导师 30% / 动量 25% / 质量 15%',
    '合作 10% / 影响力 10% / 厂牌 10%',
    '三者都与 Sailor 直接共同署名，',
    '且都合作 Coastal Harmony Studios',
], size=14, color=INK, spacing=1.25, after=7)
conclusion(s, '登榜是结果而非过程特征：Orla 单年 7 部登榜却无持续影响，Sailor 只有 1 条 notoriety 记录。')

# P11 validation
s = prs.slides.add_slide(BLANK)
header(s, '洞见 5–6 与方法可信度', 11, '10 · Validation')
banner(s, '诚实报告', 'AUC 0.625 只说明「五年内首次登榜」噪声大，模型用于候选排序而非成名概率。')
kpi(s, 0.6, '0.625', '5 折 ROC-AUC', '13,141 样本 / 1,777 act')
kpi(s, 4.74, '53', '项自动化测试', '45 Python + 8 前端适配器')
kpi(s, 8.88, '84', '份可复现 JSON', 'SHA-256 校验 + 固定 seed 42')
text(s, 0.6, 4.12, 12.13, 1.9, [
    '• 洞见 5：登榜数高 ≠ 持续影响；团体归属显著为正（FDR q=0.030），流派跨度方向为负。',
    '• 洞见 6：官方 18 个分量实为 16；84.9% 作品缺登榜年份；7 条下游引用全无日期。',
    '• 局限：无 2040–2045 真值；候选池仅 3 个 act；权重为专家设定；AUC 随依赖版本微幅漂移。',
], size=16, color=INK, spacing=1.3, after=8)
conclusion(s, '所有数字以 data/processed/rising_star.json 为准，并在报告注明复现环境版本。')

# P12 closing
s = prs.slides.add_slide(BLANK)
header(s, '结论、分工与提交物', 12, '11 · Closing')
banner(s, '一句话主线', '她从七个流派各借一点，真正的影响是把新人写进作品署名。')
bullet_block(s, 0.6, 1.95, 5.95, 3.9, '三问的答案', [
    'Q1：没有单一导师，两次代际合作构成社区影响',
    'Q2：多波次脉冲扩散，与 Indie Folk 双向互哺',
    'Q3：Top3 = Brine Choir / Selkie / Tidal',
    '交付：可交互系统 + 84 份数据 + 逐题答卷',
])
bullet_block(s, 6.78, 1.95, 5.95, 3.9, '分工与待办', [
    '付嘉一：前端架构、模块一、整合与部署',
    '邬昊文：数据工程管线与 84 份数据契约',
    '资丰瑞：模块二传播分析；周涛：模块三预测',
    '隋咏轩：手绘设计、答辩 PPT 与文档',
    '待办：5 人各自 5 页个人总结、打包提交',
])
conclusion(s, '局限已主动说明：合成数据不外推、无未来真值、缺日期证据不进年度统计。')

prs.save(OUT)
print('saved:', OUT)
print('slides:', len(prs.slides))
print('size:', os.path.getsize(OUT), 'bytes')
