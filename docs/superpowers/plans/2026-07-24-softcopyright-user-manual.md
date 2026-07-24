# 矿山生态修复智能监测平台软著用户手册 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一份内容准确、嵌入全部指定截图并通过逐页渲染检查的软著申报型 Word 用户手册。

**Architecture:** 以项目源码、用户文档和素材截图为事实来源，先整理可证实的功能与图示对应关系，再以独立 Python 生成器创建 Word 文档。生成器只产出指定的最终文件；输出后使用文档渲染工具逐页检查并按发现的问题修订。

**Tech Stack:** Python 3（工作区捆绑运行时）、python-docx、Pillow、LibreOffice 渲染器、PowerShell。

---

## 文件结构

- 新建：`D:\项目\JiangXi\tools\build_softcopyright_user_manual.py` — 读取素材并创建 Word 文档，集中定义样式、章节、图题、页眉页脚和图片插入规则。
- 新建：`D:\项目\JiangXi\用户手册.docx` — 最终交付的软著用户手册。
- 临时输出：`D:\项目\JiangXi\_manual_qa\` — 仅用于渲染审阅的 PNG 与 PDF，不交付。
- 已有素材：`D:\项目\JiangXi\材料\*.png` — 手册中唯一的界面截图来源。
- 已有规格：`D:\项目\JiangXi\JiangXi-Platform\docs\superpowers\specs\2026-07-24-softcopyright-user-manual-design.md` — 手册的已确认范围与质量门槛。

### Task 1: 核验功能事实与素材清单

**Files:**
- Read: `D:\项目\JiangXi\JiangXi-Platform\README.md`
- Read: `D:\项目\JiangXi\JiangXi-Platform\docs\project_summary.md`
- Read: `D:\项目\JiangXi\JiangXi-Platform\miner\src\components\LeftSidebar.vue`
- Read: `D:\项目\JiangXi\JiangXi-Platform\miner\src\components\MineDetailModal.vue`
- Read: `D:\项目\JiangXi\JiangXi-Platform\frontend\src\views\mainfun\Segmentation.vue`
- Read: `D:\项目\JiangXi\材料\*.png`

- [ ] **Step 1: 提取已实现功能的可证实表述**

运行：

```powershell
rg -n "基础资料|所属地市|治理状态|气候背景|恢复诊断|模型研判|NDVI|FCV|LAI|LST|NPP|TVDI|变化矩阵|趋势" `
  'D:\项目\JiangXi\JiangXi-Platform\README.md' `
  'D:\项目\JiangXi\JiangXi-Platform\docs\project_summary.md' `
  'D:\项目\JiangXi\JiangXi-Platform\miner\src' `
  'D:\项目\JiangXi\JiangXi-Platform\frontend\src'
```

预期：输出与地图查询、图斑详情、修复分析和指数分析对应的源码或文档位置；不使用输出中没有依据的功能名称。

- [ ] **Step 2: 读取每张截图的像素尺寸**

运行：

```powershell
$py='C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -c "from pathlib import Path; from PIL import Image; [print(f'{p.name}: {Image.open(p).size}') for p in Path(r'D:\项目\JiangXi\材料').glob('*.png')]"
```

预期：输出 14 个 PNG 文件名及尺寸，为后续按比例嵌入提供依据。

- [ ] **Step 3: 建立功能—截图映射并人工复核**

将下列映射写入生成器的 `FIGURES` 常量，并确保每个文件只出现一次：

```python
FIGURES = [
    ("登录页.png", "图 1 系统登录界面", "输入已分配的账号和密码后进入系统。"),
    ("主界面.png", "图 2 系统主界面", "展示地图、概览统计、筛选入口与功能导航。"),
    ("基础资料.png", "图 3 基础资料查询界面", "查看当前图斑的基础业务属性。"),
    ("所属地市功能.png", "图 4 所属地市查询界面", "按地市范围定位和查看图斑。"),
    ("治理状态功能.png", "图 5 治理状态查询界面", "按治理状态筛选图斑。"),
    ("气候背景.png", "图 6 气候背景分析界面", "查看与矿区生态状况相关的气候背景信息。"),
    ("恢复诊断.png", "图 7 恢复诊断界面", "查看修复状态与诊断结果。"),
    ("模型研判.png", "图 8 模型研判界面", "查看模型对矿区生态修复情况的研判结果。"),
    ("NDVI.png", "图 9 NDVI 指数分析界面", "用于查看植被覆盖变化特征。"),
    ("FCV.png", "图 10 FCV 指数分析界面", "用于查看植被覆盖度信息。"),
    ("LAI.png", "图 11 LAI 指数分析界面", "用于查看叶面积指数信息。"),
    ("LST.png", "图 12 LST 指数分析界面", "用于查看地表温度信息。"),
    ("NPP.png", "图 13 NPP 指数分析界面", "用于查看植被净初级生产力信息。"),
    ("TVDI.png", "图 14 TVDI 指数分析界面", "用于查看地表干湿状况信息。"),
]
```

预期：14 张截图均有中性图题、功能说明和连续编号。

### Task 2: 编写可重复执行的 Word 生成器

**Files:**
- Create: `D:\项目\JiangXi\tools\build_softcopyright_user_manual.py`

- [ ] **Step 1: 实现文档版式与基础样式**

在生成器中使用 `python-docx` 创建 A4 纵向文档，设置上下边距 2.54 cm、左右边距 2.54 cm，定义“正文”“标题 1”“标题 2”“图题”四类样式；正文使用 10.5 pt 宋体，一级标题使用 16 pt 深蓝色黑体，二级标题使用 13 pt 深蓝色黑体，图题使用 9 pt 宋体居中。

生成器必须包含以下可直接使用的函数：

```python
def add_heading(doc, text, level):
    return doc.add_heading(text, level=level)

def add_steps(doc, steps):
    for step in steps:
        doc.add_paragraph(step, style='List Number')

def add_figure(doc, image_path, caption, note, width_cm=15.6):
    paragraph = doc.add_paragraph()
    paragraph.alignment = 1
    paragraph.add_run().add_picture(str(image_path), width=Cm(width_cm))
    doc.add_paragraph(caption, style='图题')
    note_paragraph = doc.add_paragraph()
    note_paragraph.add_run('界面说明：').bold = True
    note_paragraph.add_run(note)
```

- [ ] **Step 2: 实现封面、页眉、页脚和目录页**

封面依次写入：“矿山生态修复智能监测平台”“用户手册”“适用用途：软件著作权申请材料”“编制日期：2026 年 7 月”。页眉写入“矿山生态修复智能监测平台用户手册”；页脚居中插入连续页码字段。封面后插入分页，再插入“修订说明”和“目录”两节；目录使用列出 1 至 8 章标题的静态目录，不依赖 Word 自动更新字段。

- [ ] **Step 3: 实现全部正文内容**

正文按照以下章、节标题与内容要求生成：

```text
1 软件概述
  1.1 建设目的
  1.2 主要功能
  1.3 运行环境
2 快速开始
  2.1 用户登录
  2.2 主界面说明
  2.3 退出登录
3 地图监测与查询
  3.1 图斑检索与地图浏览
  3.2 基础资料查询
  3.3 所属地市查询
  3.4 治理状态查询
4 生态修复分析
  4.1 气候背景
  4.2 恢复诊断
  4.3 模型研判
5 遥感指数分析
  5.1 NDVI 与 FCV
  5.2 LAI 与 LST
  5.3 NPP 与 TVDI
6 使用提示与常见问题
```

对 2 至 5 章的每个功能节写入：一个功能说明段、3 至 5 条编号操作步骤、嵌入的对应截图、一个“结果与提示”段。指标解释只能使用可稳健理解的普通表述，不写未在当前系统中实现的定量阈值、预测精度或自动处置功能。

- [ ] **Step 4: 执行生成器并检查结构**

运行：

```powershell
$py='C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py 'D:\项目\JiangXi\tools\build_softcopyright_user_manual.py'
& $py -c "from docx import Document; d=Document(r'D:\项目\JiangXi\用户手册.docx'); print({'paragraphs':len(d.paragraphs),'inline_shapes':len(d.inline_shapes),'tables':len(d.tables)})"
```

预期：生成 `D:\项目\JiangXi\用户手册.docx`，并输出至少 14 个 `inline_shapes`；文件可由 `python-docx` 正常打开。

### Task 3: 渲染审阅并修订最终文件

**Files:**
- Modify: `D:\项目\JiangXi\tools\build_softcopyright_user_manual.py`（仅在渲染发现版式问题时）
- Modify: `D:\项目\JiangXi\用户手册.docx`
- Create: `D:\项目\JiangXi\_manual_qa\page-*.png`

- [ ] **Step 1: 渲染 DOCX 为 PNG 页面**

运行：

```powershell
$py='C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py 'D:\UserDataMirror\Users\Administrator\.codex\plugins\cache\openai-primary-runtime\documents\26.723.12215\skills\documents\render_docx.py' `
  'D:\项目\JiangXi\用户手册.docx' --output_dir 'D:\项目\JiangXi\_manual_qa' --emit_pdf
```

预期：`_manual_qa` 中出现连续的 `page-1.png` 至最后一页 PNG，且生成的 PDF 非空。

- [ ] **Step 2: 逐页视觉检查**

使用图像查看器逐页检查以下条件：

```text
1. 封面软件名称为“矿山生态修复智能监测平台”，未出现“江西省”。
2. 无图片裁切、变形、重叠或超出页边距；界面文字在 100% 查看时可辨识。
3. 图题从“图 1”连续至“图 14”，且位于正确的截图下方。
4. 章节标题、编号步骤、页眉和页脚均未被截断；无空白页和大面积意外空白。
5. 正文不含账号口令、数据库凭据、部署命令或未证实功能。
```

- [ ] **Step 3: 对发现的问题最小化修订并重新渲染**

若图片过高导致其图题与图片分离，将该图的 `width_cm` 从 `15.6` 调整为 `14.4`；若页面文字过密，将对应节的正文拆为两个段落，而不缩小至小于 10.5 pt。每次修改后重新运行生成器和渲染命令，直至 Task 3 Step 2 的五项检查全部通过。

- [ ] **Step 4: 执行最终结构和辅助功能检查**

运行：

```powershell
$py='C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py 'D:\UserDataMirror\Users\Administrator\.codex\plugins\cache\openai-primary-runtime\documents\26.723.12215\skills\documents\scripts\a11y_audit.py' `
  'D:\项目\JiangXi\用户手册.docx' --fix_image_alt from_filename --out 'D:\项目\JiangXi\用户手册.docx'
& $py -c "from docx import Document; d=Document(r'D:\项目\JiangXi\用户手册.docx'); assert len(d.inline_shapes)==14, len(d.inline_shapes); print('图片数量检查通过：',len(d.inline_shapes))"
```

预期：输出“图片数量检查通过：14”，且最终文件具备图像替代文本。

### Task 4: 最终交付检查

**Files:**
- Read: `D:\项目\JiangXi\用户手册.docx`

- [ ] **Step 1: 确认最终文件存在且非空**

运行：

```powershell
Get-Item 'D:\项目\JiangXi\用户手册.docx' | Select-Object FullName,Length,LastWriteTime
```

预期：文件存在，长度大于 1 MB，最后修改时间为本次生成时间。

- [ ] **Step 2: 交付文件**

在最终回复中仅引用 `D:\项目\JiangXi\用户手册.docx`，说明手册已按软著申报型结构重写、包含 14 张指定界面截图，并已完成渲染校验。

## 自检结论

- 规格覆盖：封面名称、软著用途、功能章节、14 张截图、正式版式和逐页渲染检查均有对应任务。
- 占位符检查：计划不含 TBD、TODO 或“后续补充”等未落实要求。
- 一致性检查：唯一最终交付路径始终为 `D:\项目\JiangXi\用户手册.docx`；截图清单和最终图片数量检查均为 14。
