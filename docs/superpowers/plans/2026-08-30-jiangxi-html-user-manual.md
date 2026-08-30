# 江西 HTML 使用说明书 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一份可在断网环境直接打开的中文 HTML 使用说明书，使江西矿山生态修复智能监测平台的业务人员能完成登录、地图检索、项目管理、ROI 推理、地物分类、光谱指数和结果判读；管理员能按当前 GPU standalone 基线完成有限且可回滚的健康检查与恢复。

**Architecture:** 手册是一个独立的静态页面 `docs/manual/index.html`，样式与交互使用内联 CSS/原生 JavaScript，所有截图放在 `docs/manual/assets/` 并由 HTML 以相对路径引用。用一个 Python 标准库校验器把“离线、无敏感数据、无遗留 CPU 流程、章节齐全、图片可用”的交付规则变成可重复执行的检查。旧 Markdown 手册只保留迁移入口，避免和新 GPU 基线冲突。

**Tech Stack:** HTML5、CSS3、原生 JavaScript、SVG、Python 标准库（`html.parser`、`pathlib`、`unittest`）。

**范围约束：** 本计划只新增/更新文档和验证工具。不修改应用、模型、Docker 镜像、数据卷、凭据、CPU 代码或历史容器；不删除任何运行镜像或数据。说明书只以已验收的江西 GPU standalone 为准，业务关联只使用 `TBBH`，`map_fid` 仅说明为地图和历史目录的技术编号。

---

## 任务 1：先用测试锁定静态手册的交付契约

**Files:**

- Create: `tools/validate_html_user_manual.py`
- Create: `tools/test_validate_html_user_manual.py`

- [ ] **Step 1: 写出会失败的校验器测试样例。**

  在 `tools/test_validate_html_user_manual.py` 使用 `tempfile.TemporaryDirectory()` 构造最小手册目录，覆盖下列失败场景：缺少必需章节、重复 `id`、失效的 `#anchor`、外部图片/脚本资源、图片文件缺失、空或非中文 `alt`、绝对文件路径、遗留 `mine_fid`、CPU 操作文本、敏感配置名或示例密码。测试还必须覆盖一个完整合法的最小页面可通过。

  测试入口固定为：

  ```powershell
  python -m unittest tools.test_validate_html_user_manual
  ```

- [ ] **Step 2: 实现 `validate_html_user_manual.py`。**

  使用 `html.parser.HTMLParser` 解析 `docs/manual/index.html`，不要引入第三方依赖。提供一个可复用的 `validate_manual(root: Path) -> list[str]`，CLI 以每项一行的方式输出问题并在存在问题时返回 `1`。

  校验器必须至少强制以下契约：

  ```python
  REQUIRED_SECTION_IDS = (
      "quick-start", "login-security", "mine-map", "project-workspace",
      "roi-inference", "land-cover", "spectral-index", "result-reading",
      "admin-maintenance", "faq-glossary",
  )

  WORKFLOW_HEADINGS = (
      "何时使用", "前置条件", "操作步骤", "成功标志", "注意事项与失败处理",
  )
  ```

  - 每个业务章节（地图、工作台、ROI、地物分类、光谱指数）必须带 `data-workflow`，并含有全部五个工作流标题。
  - 每个 `img` 必须有包含中文字符的非空 `alt`；`src` 必须是 `assets/...` 的相对路径且解析后仍在手册根目录内，且文件存在。
  - 所有 `script src`、`link href`、`img src` 均不得引用 `http://`、`https://`、`//`、盘符绝对路径或根路径；页面不允许 `@import url(...)`。
  - 每个内部 `href="#..."` 必须命中唯一 `id`；所有 `id` 必须唯一。
  - 禁止 `mine_fid`、`device=cpu`、`--device cpu`、`geoview-jiangxi:cpu`、`docker compose.*cpu`、`SECRET_KEY`、`MYSQL_PASSWORD`、`MYSQL_ROOT_PASSWORD`、`123456` 和 Windows 用户盘符路径等易造成口径冲突或泄露的字面值。
  - 允许正文中出现 `http://127.0.0.1:4173`、`4174` 和 `5178` 作为本机服务入口，但它们不能出现在资源加载属性里。

  核心结构保持简单明确：

  ```python
  def main() -> int:
      root = Path(__file__).resolve().parents[1] / "docs" / "manual"
      errors = validate_manual(root)
      for error in errors:
          print(f"ERROR: {error}")
      if errors:
          return 1
      print("HTML user manual: PASS")
      return 0
  ```

- [ ] **Step 3: 运行测试，确认先红后绿。**

  运行：

  ```powershell
  python -m unittest tools.test_validate_html_user_manual
  ```

  预期：所有临时目录中的非法样例被拒绝，合法样例通过；此阶段真实手册尚不存在时，CLI 校验器可以因缺少 `index.html` 失败，但不能抛出 traceback。

## 任务 2：整理安全、可追溯的手册素材

**Files:**

- Create: `docs/manual/assets/README.md`
- Create: `docs/manual/assets/login-current.png`
- Create: `docs/manual/assets/map-overview.png`
- Create: `docs/manual/assets/project-workspace-current.png`
- Create: `docs/manual/assets/project-workspace-actions-current.png`

- [ ] **Step 1: 建立手册专用素材目录并复制已验证截图。**

  二进制图片仅复制，不重编码或覆盖原始项目素材：

  | 目标文件 | 已确认来源 | 用途 |
  | --- | --- | --- |
  | `login-current.png` | `D:\项目\JiangXi\screenshot.png` | 登录、会话与退出说明 |
  | `map-overview.png` | `D:\项目\JiangXi\材料\主界面.png` | 地图、筛选、统计与入口说明 |

  复制前后用 SHA-256 核对副本一致。不得复制 `docs/images/user-manual-workspace.png`，它是裁切不完整的旧图；不得复制带浏览器标签页、私有路径、错误状态、云南内容或密码输入的图片。

- [ ] **Step 2: 从当前 GPU 正式界面采集两张无浏览器外壳的页面截图。**

  在已运行的 `geoview-jiangxi-gpu` 环境中完成登录后，仅截取应用视口并保存为：

  - `project-workspace-current.png`：`http://127.0.0.1:4173/#/projects` 的顶部视口，应可见项目列表和矿山绑定/数据集入口。
  - `project-workspace-actions-current.png`：同一页面滚动到导出/备份操作区后的原始视口。
  当前分类页面的可见运行文案与正式交付口径不一致，因此不导入任何该页面截图；地物分类由后续 HTML/SVG 图示和文字步骤说明，不能以旧图或模拟截图替代。

  截图必须来自当前江西 GPU UI，不能包含密码、Token、浏览器标签/地址栏、宿主机用户目录、日志或其它项目页面。长页面按上述原始视口分别截取，不使用缩放后全页截图、拼接图或旧截图。若当前运行环境不能显示页面，应停止本任务并报告运行问题；不能以旧截图或模拟截图替代。

- [ ] **Step 3: 写出素材来源清单。**

  `assets/README.md` 以表格记录每张图的目标文件、来源页面或来源文件、采集日期、对应章节、是否可见敏感信息（均应为“否”）及其红框/编号标注说明。它不记录管理员密码、真实绝对用户路径或浏览器历史。

- [ ] **Step 4: 验证素材边界。**

  运行：

  ```powershell
  Get-ChildItem docs\manual\assets -File | Select-Object Name,Length
  Get-FileHash docs\manual\assets\login-current.png, docs\manual\assets\map-overview.png -Algorithm SHA256
  ```

  预期：四张 PNG 和一个来源清单均存在；登录页与地图页副本哈希和源文件一致；两张新采集图不含浏览器或敏感信息。

## 任务 3：编写离线单页手册与完整业务内容

**Files:**

- Create: `docs/manual/index.html`

- [ ] **Step 1: 搭建离线页面骨架和当前基线状态带。**

  建立语义化 `header`、`nav`、`main`、`section`、`figure`、`footer` 结构；顶栏明确“当前交付基线：江西 GPU standalone”，并只写已验证的容器、稳定镜像、服务入口、348 条记录/唯一 TBBH 与“示例结果不等于精度评测”。所有 CSS 和 JavaScript 直接写入该 HTML，不加载 CDN、在线字体或外部库。

  左侧目录必须对应校验器中的十个章节 ID；正文首部增加一张 SVG 工作流图：

  ```text
  登录 → 地图按 TBBH 检索 → 项目绑定/数据集 → ROI 推理或地物分类/光谱指数
       → 结果判读与人工复核 → 导出或历史追溯
  ```

- [ ] **Step 2: 写完业务人员的七个功能章节。**

  对下列五个带 `data-workflow` 的章节，逐一使用相同的五段式结构“何时使用 / 前置条件 / 操作步骤 / 成功标志 / 注意事项与失败处理”：

  1. `#mine-map`：按 TBBH、矿山名称或地图编号检索；定位、查看图斑详情、生态诊断、趋势；明确 `TBBH` 是唯一业务身份，`map_fid` 仅是技术编号。
  2. `#project-workspace`：新建/编辑/归档项目，按 TBBH 绑定矿山，管理数据集和时间线，导出 GeoJSON、CSV、SHP，创建与恢复备份。
  3. `#roi-inference`：选择 KML、旧/新影像与单年/双年参数，提交、读取结果与失败提示。只描述页面可见操作，不编造模型精度。
  4. `#land-cover`：选择数据源、检查参数、执行 GPU 推理、查看和下载结果；六类图例必须标明为模型分类标签。
  5. `#spectral-index`：选择影像、指数、年份与 TBBH，执行计算，查看预览与历史结果。

  同时写完 `#quick-start` 与 `#login-security`：本机入口、服务可用前提、共享会话、会话失效、退出与“密码由管理员安全交付，不写入手册”。

- [ ] **Step 3: 写完结果判读、管理员维护和 FAQ。**

  - `#result-reading`：并列解释原始影像、ROI 边界、道路类别和六类分类图例；黄色边界只能表示 ROI 范围，不能被解读为道路；所有模型输出必须人工复核。
  - `#admin-maintenance`：只列安全、只读或可回滚操作：确认 `geoview-jiangxi-gpu` 运行、访问 `http://127.0.0.1:4173/api/health/jiangxi`、核对 348/348、唯一 TBBH、manifest 与 GPU Worker 状态、查看服务日志、使用保留的回退容器。不要给出删除镜像/卷、清空数据库、重建模型或更改凭据的操作命令。
  - `#faq-glossary`：区分登录失效、TBBH 不存在、TBBH 存在但无历史结果、`map_fid` 映射缺失、数据文件损坏、分类结果加载失败；增加 TBBH、map_fid、ROI、manifest、GPU Worker 的术语表。

- [ ] **Step 4: 将截图和注释嵌入可访问的图文块。**

  每张图使用 `figure`、中文 `alt`、`figcaption` 和一个文字版编号说明列表。红框与编号用 HTML 覆盖层实现，不修改图片本身，例如：

  ```html
  <figure class="annotated-figure" data-zoomable>
    <img src="assets/map-overview.png" alt="江西矿山地图，展示筛选区、矿山统计和解译入口">
    <span class="callout callout-1" aria-hidden="true">1</span>
    <span class="callout callout-2" aria-hidden="true">2</span>
    <figcaption>图 2　矿山地图：按编号检索并进入详情。</figcaption>
  </figure>
  <ol class="figure-notes"><li>筛选与检索区：输入 TBBH、名称或地图编号。</li></ol>
  ```

  只使用任务 2 的四张本地图片。对截图未覆盖的流程，使用 HTML/SVG 流程图而非伪造界面图片。

- [ ] **Step 5: 初次运行真实页面校验。**

  ```powershell
  python tools\validate_html_user_manual.py
  ```

  预期：输出 `HTML user manual: PASS`。任何缺章节、图片或敏感文本，均须先修正文档后再进入交互优化。

## 任务 4：补齐阅读、交互、可访问性与迁移入口

**Files:**

- Modify: `docs/manual/index.html`
- Modify: `docs/user_manual.md`
- Modify: `tools/validate_html_user_manual.py`
- Modify: `tools/test_validate_html_user_manual.py`

- [ ] **Step 1: 先为交互与无障碍交付契约补失败测试。**

  在现有校验器测试中先增加一个完整手册样例的失败断言，要求 HTML 同时具备：目录开关标记、阅读进度、图片放大层、图片放大触发标记、代码复制按钮、`prefers-reduced-motion` 与 `@media print`。将“CPU”加入 HTML 手册禁用字面值，确保截图之外的正文不会重新引入过期运行口径。校验器只验证可稳定解析的结构和样式交付契约；`IntersectionObserver`、复制降级和 Escape 等实际行为放在最终浏览器验收中验证，避免用源码字符串代替行为测试。先运行测试确认缺少这些标记时失败，再以最小方式扩展校验器与有效样例。

- [ ] **Step 2: 完成原生交互，不改变离线可读性。**

  在 `index.html` 中实现以下功能，JavaScript 在禁用时页面正文仍应完整可读：

  - `IntersectionObserver` 根据当前章节更新目录高亮和顶部阅读进度；不可用时静默降级。
  - 窄屏目录按钮切换侧栏，并保留 `aria-expanded`、可见焦点和 Escape 关闭。
  - `data-zoomable` 图片打开无外部依赖的遮罩放大层；点击遮罩、关闭按钮和 Escape 都能关闭，并在关闭时恢复触发元素焦点。
  - 管理员命令块的“复制”按钮使用 `navigator.clipboard`；不可用时显示“请手动复制”，不得导致页面报错。
  - CSS 添加 `:focus-visible`、`prefers-reduced-motion` 和 `@media print`；打印时隐藏侧栏、按钮与遮罩，但保留章节、图注和分页规则。

- [ ] **Step 3: 把旧 Markdown 手册改为无冲突的迁移页。**

  以最小内容替换 `docs/user_manual.md`：说明正式使用说明已迁移到 [`manual/index.html`](manual/index.html)，适用当前江西 GPU standalone，包含一个简短的打开方法和十章目录摘要。不要保留 CPU 启动命令、CPU 推理描述、旧环境变量操作、`mine_fid` 或凭据示例。

- [ ] **Step 4: 重新执行静态和文本回归检查。**

  ```powershell
  python -m unittest tools.test_validate_html_user_manual
  python tools\validate_html_user_manual.py
  rg -n -i "mine_fid|device=cpu|--device cpu|geoview-jiangxi:cpu|docker compose.*cpu|SECRET_KEY|MYSQL_PASSWORD|MYSQL_ROOT_PASSWORD|123456" docs\manual docs\user_manual.md
  ```

  预期：前两条通过；最后一条无匹配。若命令因无匹配返回退出码 `1`，这是正确结果，应在交付记录中说明。

## 任务 5：按离线、视觉与事实三个维度验收交付物

**Files:**

- Verify: `docs/manual/index.html`
- Verify: `docs/manual/assets/*`
- Verify: `docs/user_manual.md`
- Verify: `tools/validate_html_user_manual.py`
- Verify: `tools/test_validate_html_user_manual.py`

- [ ] **Step 1: 执行自动化验证。**

  ```powershell
  python -m unittest tools.test_validate_html_user_manual
  python tools\validate_html_user_manual.py
  git diff --check -- docs/manual docs/user_manual.md tools/validate_html_user_manual.py tools/test_validate_html_user_manual.py
  ```

  预期：单元测试和校验器通过，`git diff --check` 无空白错误。不要因仓库已有的其它脏文件而清理、重置或覆盖无关改动。

- [ ] **Step 2: 执行离线与视觉验收。**

  用现代浏览器直接打开 `docs/manual/index.html`（`file://`），断开网络或在网络不可用状态下逐项确认：目录锚点、图片、本地样式、目录开关与章节高亮、图片放大、Escape、Tab/Shift+Tab 模态焦点循环、窄屏无脚本降级、代码复制降级和打印预览均可用。至少在 1440×900 与 390×844 两个视口检查：正文未被固定导航遮挡、图片不溢出、红框编号可读、图注与步骤不被切断。

- [ ] **Step 3: 进行内容事实核对并记录结果。**

  对照 `AGENTS.md` 和当前运行验收口径核对：容器名 `geoview-jiangxi-gpu`、稳定镜像 `geoview-jiangxi:jiangxi-gpu`、三个本机入口、348 条权威记录、TBBH/map_fid 语义、GPU Worker 和“示例结果非精度评测”。确认没有把模型结果描述为真值、没有写出管理员密码、密钥、Token、私人绝对路径或删除数据的常规命令。

- [ ] **Step 4: 交付说明。**

  最终汇报只列出新增手册入口、素材、迁移页、校验命令和验收结果；明确说明本次没有改动应用、模型、容器、数据卷、密码或 CPU 运行代码。
