# 江西平台整体字号与亮度调整 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将江西 Miner 与江西解译平台升级为已确认的 B「明显提亮」视觉方案，同时保证桌面与窄屏文字可读、业务图像不变、云南工程不受影响。

**Architecture:** 两套江西前端继续独立构建，分别在 `miner/src/assets/base.css` 与 `frontend/src/assets/css/theme-dark.css` 保存同名同值的语义令牌。先用静态契约锁定颜色、字号和响应式规则，再只清理当前运行链路关键组件中的小字号与旧界面色；地图、遥感影像和分类图例的数据颜色不纳入主题替换。

**Tech Stack:** Vue 3、Vite、Vue CLI、Element Plus 2、CSS/LESS、自带 `node:test`、Node.js 静态主题检查、Docker Compose、Codex in-app browser。

---

## 文件结构与职责

本计划不新增运行时代码模块，不建立跨前端共享包。

- `miner/src/assets/base.css`：Miner 的核心颜色、字体、字号、焦点和响应式令牌。
- `miner/src/assets/main.css`：Miner 应用根节点与全局控件基线。
- `miner/test/uiTheme.test.js`：Miner 令牌、跨端一致性、最小字号和响应式契约。
- `miner/src/components/*.vue`：只修正当前运行链路中覆盖主题令牌的小字号和旧界面色。
- `frontend/src/assets/css/theme-dark.css`：解译平台核心令牌、Element Plus 映射和响应式基线。
- `frontend/src/assets/css/app.css`：解译平台遗留全局控件样式与字体继承。
- `frontend/scripts/verify-brand-theme.cjs`：解译平台主题、跨端一致性和关键页面最小字号契约。
- `frontend/src/views/*.vue`、`frontend/src/components/*.vue`：只修正登录、工作流、历史结果和应用外壳中的覆盖样式。
- `docs/superpowers/reports/2026-08-01-jiangxi-ui-readability-brightness.md`：记录最终命令、浏览器视口验收、业务回归和云南隔离结果。

## Task 1: 先锁定 B 方案核心令牌与跨端一致性

**Files:**
- Modify: `miner/test/uiTheme.test.js`
- Modify: `frontend/scripts/verify-brand-theme.cjs`

- [ ] **Step 1: 将 Miner 主题测试改为 B 方案期望值**

在 `miner/test/uiTheme.test.js` 中把现有旧色值断言替换为以下完整令牌对象，并同时读取解译平台主题：

```js
const frontendTheme = await readFile(
  new URL('../../frontend/src/assets/css/theme-dark.css', import.meta.url),
  'utf8'
);
const mapDashboard = await readFile(
  new URL('../src/components/MapDashboard.vue', import.meta.url),
  'utf8'
);

const expectedTokens = {
  '--jx-bg': '#102a33',
  '--jx-bg-elevated': '#183a43',
  '--jx-surface': '#204650',
  '--jx-surface-muted': 'rgba(243, 220, 170, 0.10)',
  '--jx-border': 'rgba(190, 245, 215, 0.40)',
  '--jx-border-strong': 'rgba(190, 245, 215, 0.65)',
  '--jx-text': '#f4fbf8',
  '--jx-text-muted': '#c5d8d2',
  '--jx-primary': '#b8f2d1',
  '--jx-primary-hover': '#d2f8e2',
  '--jx-success': '#9ce5bb',
  '--jx-warning': '#e9a176',
  '--jx-danger': '#f18a8a',
  '--jx-info': '#a8dadd',
  '--jx-sand': '#f3dcaa',
  '--jx-text-xs': '13px',
  '--jx-text-sm': '14px',
  '--jx-text-control': '16px',
  '--jx-text-body': '17px',
  '--jx-text-section': '20px',
  '--jx-text-title': '28px',
};

for (const [name, value] of Object.entries(expectedTokens)) {
  const escaped = value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  assert.match(baseCss, new RegExp(`${name}:\\s*${escaped}\\s*;`, 'i'));
  assert.match(frontendTheme, new RegExp(`${name}:\\s*${escaped}\\s*;`, 'i'));
}

assert.match(baseCss, /@media\s*\(max-width:\s*1280px\)/);
assert.match(baseCss, /@media\s*\(max-width:\s*480px\)/);
assert.match(frontendTheme, /@media\s*\(max-width:\s*1280px\)/);
assert.match(frontendTheme, /@media\s*\(max-width:\s*480px\)/);
assert.doesNotMatch(mapDashboard, /filter:\s*brightness\(/i);
```

保留原测试中的 reduced-motion、focus-visible 和旧变量别名断言。

- [ ] **Step 2: 将解译平台品牌检查改为相同令牌**

在 `frontend/scripts/verify-brand-theme.cjs` 中把 `expectedCanonicalTokens` 的颜色值更新为 Task 1 Step 1 的值，并加入以下字号值：

```js
Object.assign(expectedCanonicalTokens, {
  '--jx-text-xs': '13px',
  '--jx-text-sm': '14px',
  '--jx-text-control': '16px',
  '--jx-text-body': '17px',
  '--jx-text-section': '20px',
  '--jx-text-title': '28px',
});

assert.match(theme, /@media\s*\(max-width:\s*1280px\)/);
assert.match(theme, /@media\s*\(max-width:\s*480px\)/);
assert.doesNotMatch(
  [
    readFrontend('src', 'components', 'ImgShow.vue'),
    readFrontend('src', 'views', 'mainfun', 'Segmentation.vue'),
    readFrontend('src', 'views', 'mainfun', 'SpectralIndices.vue'),
  ].join('\n'),
  /filter:\s*brightness\(/i,
  '业务图像和结果预览不得被主题滤镜增亮',
);
```

将 `cssDeclarations` 限定为读取首个 `:root` 块，避免响应式媒体查询中的令牌覆盖影响基准值读取：

```js
function cssDeclarations(source) {
  const rootBlock = source.match(/:root\s*\{([\s\S]*?)\}/);
  assert.ok(rootBlock, '主题必须包含 :root 令牌块');
  return Object.fromEntries(
    [...rootBlock[1].matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map((match) => [
      match[1],
      match[2].trim(),
    ]),
  );
}
```

- [ ] **Step 3: 运行测试并确认它们因旧主题而失败**

Run:

```powershell
Set-Location miner
npm test -- --test-name-pattern="ecology atlas theme"
```

Expected: FAIL，至少报告 `--jx-bg` 仍为 `#071923` 或缺少 `--jx-text-body`。

Run:

```powershell
Set-Location frontend
npm run test:ui
```

Expected: FAIL，报告 Miner 或解译平台令牌仍是旧值。

- [ ] **Step 4: 提交失败测试**

```powershell
git add -- miner/test/uiTheme.test.js frontend/scripts/verify-brand-theme.cjs
git commit -m "测试江西明亮主题契约"
```

## Task 2: 实现两端独立但一致的全局主题令牌

**Files:**
- Modify: `miner/src/assets/base.css`
- Modify: `miner/src/assets/main.css`
- Modify: `frontend/src/assets/css/theme-dark.css`
- Modify: `frontend/src/assets/css/app.css`
- Test: `miner/test/uiTheme.test.js`
- Test: `frontend/scripts/verify-brand-theme.cjs`

- [ ] **Step 1: 在 Miner 根主题中写入 B 方案令牌**

将 `miner/src/assets/base.css` 的 `:root` 更新为以下核心内容；保留现有圆角和兼容别名：

```css
:root {
  --jx-bg: #102a33;
  --jx-bg-elevated: #183a43;
  --jx-surface: #204650;
  --jx-surface-muted: rgba(243, 220, 170, 0.10);
  --jx-border: rgba(190, 245, 215, 0.40);
  --jx-border-strong: rgba(190, 245, 215, 0.65);
  --jx-text: #f4fbf8;
  --jx-text-muted: #c5d8d2;
  --jx-primary: #b8f2d1;
  --jx-primary-hover: #d2f8e2;
  --jx-success: #9ce5bb;
  --jx-warning: #e9a176;
  --jx-danger: #f18a8a;
  --jx-info: #a8dadd;
  --jx-sand: #f3dcaa;
  --jx-text-xs: 13px;
  --jx-text-sm: 14px;
  --jx-text-control: 16px;
  --jx-text-body: 17px;
  --jx-text-section: 20px;
  --jx-text-title: 28px;
  --jx-text-display: clamp(30px, 3.3vw, 48px);
  --jx-font-display: "Noto Serif SC", "Source Han Serif SC", STSong, serif;
  --jx-font-body: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
  --jx-font-data: Bahnschrift, "DIN Alternate", Consolas, monospace;
  --jx-radius: 10px;
  --jx-radius-large: 16px;
  --border-color: var(--jx-border);
  --color-background: var(--jx-bg);
  --color-text: var(--jx-text);
}
```

将 `body` 的字体和字号改为：

```css
body {
  font-family: var(--jx-font-body);
  font-size: var(--jx-text-body);
}

button,
input,
select,
textarea {
  font: inherit;
}
```

- [ ] **Step 2: 在解译平台根主题中写入同值令牌**

在 `frontend/src/assets/css/theme-dark.css` 的 `:root` 使用与 Miner 完全相同的 `--jx-*` 颜色、字号和字体值。保留全部 `--primary-*`、`--bg-*`、`--text-*`、`--el-*` 映射，并让 `body` 使用：

```css
body {
  margin: 0;
  background: var(--jx-bg);
  color: var(--jx-text);
  font-family: var(--jx-font-body);
  font-size: var(--jx-text-body);
  line-height: 1.6;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}
```

- [ ] **Step 3: 增加三档响应式字号覆盖**

在两个主题文件中都加入以下规则，位置放在 reduced-motion 规则之前：

```css
@media (max-width: 1280px) {
  :root {
    --jx-text-control: 15px;
    --jx-text-body: 16px;
    --jx-text-section: 18px;
    --jx-text-title: 26px;
  }
}

@media (max-width: 480px) {
  :root {
    --jx-text-control: 16px;
    --jx-text-body: 16px;
    --jx-text-section: 18px;
    --jx-text-title: 24px;
  }
}
```

`--jx-text-xs` 始终保持 13px，不在媒体查询中下调。

- [ ] **Step 4: 统一两端全局控件基线**

在 `miner/src/assets/main.css` 增加：

```css
button,
input,
select,
textarea {
  font-size: var(--jx-text-control);
}
```

在 `frontend/src/assets/css/app.css` 将 Element Plus 和遗留按钮的字体改为：

```css
.el-dialog,
.el-button,
.el-table,
.el-message {
  font-family: var(--jx-font-body);
}

.el-button,
.el-input,
.el-select,
.el-pagination {
  font-size: var(--jx-text-control);
}

.btn-animate {
  color: var(--jx-bg);
}
```

不要修改 `.legend-swatch-*`、ECharts 数据系列和结果预览图像的颜色。

- [ ] **Step 5: 运行主题契约并确认通过**

Run:

```powershell
Set-Location miner
node --test test/uiTheme.test.js
```

Expected: PASS，主题令牌、焦点和 reduced-motion 测试全部通过。

Run:

```powershell
Set-Location frontend
npm run test:ui
```

Expected: PASS，并输出江西主题合同检查通过信息。

- [ ] **Step 6: 提交全局主题**

```powershell
git add -- miner/src/assets/base.css miner/src/assets/main.css frontend/src/assets/css/theme-dark.css frontend/src/assets/css/app.css
git commit -m "统一江西明亮主题令牌"
```

## Task 3: 清理 Miner 当前运行链路中的小字号与旧界面色

**Files:**
- Modify: `miner/test/uiTheme.test.js`
- Modify: `miner/src/components/LoginPage.vue`
- Modify: `miner/src/components/TheHeader.vue`
- Modify: `miner/src/components/LeftSidebar.vue`
- Modify: `miner/src/components/RightSidebar.vue`
- Modify: `miner/src/components/MapDashboard.vue`
- Modify: `miner/src/components/EcologyDiagnosisPanels.vue`
- Modify: `miner/src/components/InferenceModal.vue`
- Modify: `miner/src/components/MineDetailModal.vue`
- Modify: `miner/src/components/ProjectWorkspace.vue`
- Modify: `miner/src/components/TrendReportModal.vue`

- [ ] **Step 1: 增加 Miner 关键组件最小字号测试**

在 `miner/test/uiTheme.test.js` 追加：

```js
const minerReadableComponents = [
  'LoginPage.vue',
  'TheHeader.vue',
  'LeftSidebar.vue',
  'RightSidebar.vue',
  'MapDashboard.vue',
  'EcologyDiagnosisPanels.vue',
  'InferenceModal.vue',
  'MineDetailModal.vue',
  'ProjectWorkspace.vue',
  'TrendReportModal.vue',
];

test('critical Miner UI does not use visible text below 13px', async () => {
  for (const fileName of minerReadableComponents) {
    const source = await readFile(
      new URL(`../src/components/${fileName}`, import.meta.url),
      'utf8'
    );
    assert.doesNotMatch(
      source,
      /font-size:\s*(?:[0-9]|1[0-2])px\s*;/i,
      `${fileName} 仍包含低于 13px 的 CSS 文字`
    );
    assert.doesNotMatch(
      source,
      /fontSize:\s*(?:[0-9]|1[0-2])(?:\D|$)/,
      `${fileName} 仍包含低于 13px 的图表文字`
    );
  }
});
```

- [ ] **Step 2: 运行测试并确认它因现有小字而失败**

Run:

```powershell
Set-Location miner
node --test test/uiTheme.test.js
```

Expected: FAIL，首个失败文件应为 `TheHeader.vue`、`LeftSidebar.vue` 或 `RightSidebar.vue`，并报告低于 13px 的文字。

- [ ] **Step 3: 将 Miner 可见小字替换为语义字号**

在 Task 3 文件列表内执行以下精确规则：

```css
/* 所有可见标签、眉题、状态和说明中的 8px–12px */
font-size: var(--jx-text-xs);

/* 普通说明和表格辅助文字 */
font-size: var(--jx-text-sm);

/* 按钮、输入框、筛选器和菜单 */
font-size: var(--jx-text-control);

/* 区块标题 */
font-size: var(--jx-text-section);

/* 页面或弹窗主标题 */
font-size: var(--jx-text-title);
```

ECharts 配置不能读取 CSS 变量，`RightSidebar.vue` 中 `fontSize: 10` 和 `fontSize: 11` 统一改为：

```js
fontSize: 13
```

不改变地图 marker、图例色块宽高、图标 SVG 尺寸和数据系列颜色。

- [ ] **Step 4: 将 Miner 旧界面色替换为 B 方案令牌**

只在 `<style>` 中按以下映射修正界面颜色：

```text
#0a1929、rgba(7, 20, 31, 0.94)  -> var(--jx-surface)
#4ecdc4                         -> var(--jx-primary)
#fff、#cfe8f3                   -> var(--jx-text)
#8da3b6、#666、#ccc             -> var(--jx-text-muted)
#00b894                         -> var(--jx-success)
#ff7675、#ff9a9a                -> var(--jx-danger)
rgba(255, 255, 255, 0.08/0.1)  -> var(--jx-border)
rgba(255, 255, 255, 0.2)       -> var(--jx-border-strong)
```

`EcologyDiagnosisPanels.vue` 的 ECharts 线条、`TheHeader.vue` 的生态等级色带和其他具有数据含义的颜色保持不变。遮罩层 `rgba(0, 0, 0, 0.6/0.7)` 保留，避免弹窗内容与地图混淆。

- [ ] **Step 5: 运行 Miner 主题、格式、Lint 与构建**

Run:

```powershell
Set-Location miner
node --test test/uiTheme.test.js
npm run format:check
npm run lint
npm run build
```

Expected: 四个命令均以 0 退出；Vite 构建生成 `dist`，没有新增 ESLint 或格式错误。

- [ ] **Step 6: 提交 Miner 可读性修改**

```powershell
git add -- miner/test/uiTheme.test.js miner/src/components/LoginPage.vue miner/src/components/TheHeader.vue miner/src/components/LeftSidebar.vue miner/src/components/RightSidebar.vue miner/src/components/MapDashboard.vue miner/src/components/EcologyDiagnosisPanels.vue miner/src/components/InferenceModal.vue miner/src/components/MineDetailModal.vue miner/src/components/ProjectWorkspace.vue miner/src/components/TrendReportModal.vue
git commit -m "提升江西 Miner 字号与面板亮度"
```

## Task 4: 清理解译平台当前运行链路中的小字号与旧界面色

**Files:**
- Modify: `frontend/scripts/verify-brand-theme.cjs`
- Modify: `frontend/src/views/Login.vue`
- Modify: `frontend/src/views/Home.vue`
- Modify: `frontend/src/views/mainfun/Segmentation.vue`
- Modify: `frontend/src/views/mainfun/SpectralIndices.vue`
- Modify: `frontend/src/views/history/History.vue`
- Modify: `frontend/src/components/AsideVue.vue`
- Modify: `frontend/src/components/Bottominfor.vue`
- Modify: `frontend/src/components/ImgShow.vue`
- Modify: `frontend/src/components/Tabinfor.vue`
- Modify: `frontend/src/components/Tablogin.vue`

- [ ] **Step 1: 增加解译平台关键页面最小字号检查**

在 `frontend/scripts/verify-brand-theme.cjs` 中追加：

```js
const readableFrontendFiles = [
  ['src', 'views', 'Login.vue'],
  ['src', 'views', 'Home.vue'],
  ['src', 'views', 'mainfun', 'Segmentation.vue'],
  ['src', 'views', 'mainfun', 'SpectralIndices.vue'],
  ['src', 'views', 'history', 'History.vue'],
  ['src', 'components', 'AsideVue.vue'],
  ['src', 'components', 'Bottominfor.vue'],
  ['src', 'components', 'ImgShow.vue'],
  ['src', 'components', 'Tabinfor.vue'],
  ['src', 'components', 'Tablogin.vue'],
];

for (const segments of readableFrontendFiles) {
  const source = readFrontend(...segments);
  const label = segments.join('/');
  assert.doesNotMatch(
    source,
    /font-size:\s*(?:[0-9]|1[0-2])px\s*;/i,
    `${label} 仍包含低于 13px 的可见文字`,
  );
  assert.doesNotMatch(
    source,
    /fontSize:\s*(?:[0-9]|1[0-2])(?:\D|$)/,
    `${label} 仍包含低于 13px 的图表文字`,
  );
}
```

- [ ] **Step 2: 运行检查并确认它因现有小字而失败**

Run:

```powershell
Set-Location frontend
npm run test:ui
```

Expected: FAIL，报告 `Login.vue`、`AsideVue.vue`、`Tablogin.vue`、`Segmentation.vue` 或 `SpectralIndices.vue` 中低于 13px 的文字。

- [ ] **Step 3: 将解译平台小字替换为语义字号**

在 Task 4 文件列表内使用与 Miner 相同的语义规则：

```css
font-size: var(--jx-text-xs);      /* 眉题、编号、状态、辅助说明 */
font-size: var(--jx-text-sm);      /* 次要正文 */
font-size: var(--jx-text-control); /* 按钮、菜单、表单 */
font-size: var(--jx-text-section); /* 面板标题 */
font-size: var(--jx-text-title);   /* 页面标题 */
```

必须覆盖以下已知小字位置：

- `Login.vue`：平台眉题、访问说明编号、档案字段名、登录错误。
- `AsideVue.vue`：项目标识、导航说明、工具说明、操作提示。
- `Tablogin.vue`：样区标签、FID、用户名说明、返回地图按钮。
- `Segmentation.vue` 与 `SpectralIndices.vue`：说明文字、工作流编号、执行信息。
- `ImgShow.vue`：分类图例眉题和光谱统计字段名。

- [ ] **Step 4: 修正历史结果和全局外壳的旧亮色主题残留**

在 `frontend/src/views/history/History.vue` 中按以下映射修改：

```text
rgb(252, 252, 252) -> var(--jx-surface)
rgb(237, 242, 245) -> var(--jx-bg-elevated)
rgb(228, 235, 240) -> var(--jx-surface-muted)
#000                -> var(--jx-text)
```

保留 `ImgShow.vue` 中以下分类图例数据色，不改成主题色：

```css
.legend-swatch--grass { background: rgb(0, 255, 0); }
.legend-swatch--forest { background: rgb(0, 128, 0); }
.legend-swatch--building { background: rgb(255, 0, 0); }
.legend-swatch--road { background: rgb(255, 255, 0); }
.legend-swatch--bare { background: rgb(255, 0, 255); }
.legend-swatch--water { background: rgb(0, 191, 255); }
```

- [ ] **Step 5: 运行解译平台合同测试与构建**

Run:

```powershell
Set-Location frontend
npm run test:backend-url
npm run test:navigation
npm run test:ui
npm run test:workflow
npm run build
```

Expected: 五个命令均以 0 退出；Vue CLI 构建成功，现有 bundle-size 警告可以记录但不得出现编译错误。

- [ ] **Step 6: 提交解译平台可读性修改**

```powershell
git add -- frontend/scripts/verify-brand-theme.cjs frontend/src/views/Login.vue frontend/src/views/Home.vue frontend/src/views/mainfun/Segmentation.vue frontend/src/views/mainfun/SpectralIndices.vue frontend/src/views/history/History.vue frontend/src/components/AsideVue.vue frontend/src/components/Bottominfor.vue frontend/src/components/ImgShow.vue frontend/src/components/Tabinfor.vue frontend/src/components/Tablogin.vue
git commit -m "提升江西解译平台字号与亮度"
```

## Task 5: 验证三档响应式布局并做最小布局修正

**Files:**
- Modify if required by observed overflow: `miner/src/components/TheHeader.vue`
- Modify if required by observed overflow: `miner/src/components/MapDashboard.vue`
- Modify if required by observed overflow: `miner/src/components/RightSidebar.vue`
- Modify if required by observed overflow: `frontend/src/views/Home.vue`
- Modify if required by observed overflow: `frontend/src/views/Login.vue`
- Modify if required by observed overflow: `frontend/src/views/mainfun/Segmentation.vue`
- Modify if required by observed overflow: `frontend/src/views/mainfun/SpectralIndices.vue`
- Modify if required by observed overflow: `frontend/src/components/AsideVue.vue`
- Modify if required by observed overflow: `frontend/src/components/Tablogin.vue`
- Test: `miner/test/uiTheme.test.js`
- Test: `frontend/scripts/verify-brand-theme.cjs`

- [ ] **Step 1: 启动两个前端的本地预览服务**

Run in terminal A:

```powershell
Set-Location miner
npm run dev -- --host 127.0.0.1 --port 4173
```

Expected: Vite reports `http://127.0.0.1:4173/`.

Run in terminal B:

```powershell
Set-Location frontend
$env:VUE_APP_MINER_URL='http://127.0.0.1:4173/'
$env:VUE_APP_BACKEND_URL='http://127.0.0.1:5178/'
npm run serve -- --host 127.0.0.1 --port 4174
```

Expected: Vue CLI reports `http://127.0.0.1:4174/`.

- [ ] **Step 2: 用浏览器检查 1440×900**

使用 `browser:control-in-app-browser` 打开：

```text
http://127.0.0.1:4173/#/map
http://127.0.0.1:4174/#/segmentation
http://127.0.0.1:4174/#/spectralindices
http://127.0.0.1:4174/#/history
```

检查主标题 28px、正文 17px、小标签不低于 13px；顶栏、侧栏、面板和弹窗层级清晰；地图和结果预览无滤镜。

- [ ] **Step 3: 用浏览器检查 1280×720 与 390×844**

在浏览器中依次设置 1280×720 和 390×844。检查：

```text
1280×720：正文 16px，页面标题 26px，主要按钮不被截断。
390×844：正文 16px，小标签 13px，页面标题 24px；多列内容转单列或可滚动。
```

- [ ] **Step 4: 只对实际观察到的溢出应用以下布局规则**

如果 1280×720 出现横向溢出，在对应现有媒体查询中优先使用：

```css
gap: 12px;
padding-inline: 14px;
min-width: 0;
overflow-wrap: anywhere;
```

如果 390×844 出现多列挤压，在对应现有 `@media (max-width: 480px)` 中使用：

```css
grid-template-columns: minmax(0, 1fr);
max-width: 100%;
overflow-x: auto;
```

不得把 `--jx-text-xs` 降到 13px 以下，也不得对地图或预览图片使用 `filter: brightness(...)`。

- [ ] **Step 5: 重新运行两端主题测试和构建**

Run:

```powershell
Set-Location miner
node --test test/uiTheme.test.js
npm run build
Set-Location ..\frontend
npm run test:ui
npm run build
```

Expected: 四个命令均通过。

- [ ] **Step 6: 如有响应式修改则提交；无修改则记录无需提交**

```powershell
git add -- miner/src/components/TheHeader.vue miner/src/components/MapDashboard.vue miner/src/components/RightSidebar.vue frontend/src/views/Home.vue frontend/src/views/Login.vue frontend/src/views/mainfun/Segmentation.vue frontend/src/views/mainfun/SpectralIndices.vue frontend/src/components/AsideVue.vue frontend/src/components/Tablogin.vue
git commit -m "修正江西明亮主题响应式布局"
```

只有 `git status --short` 显示上述文件确有修改时才执行提交。

## Task 6: 全量验证、运行栈验收与修改报告

**Files:**
- Create: `docs/superpowers/reports/2026-08-01-jiangxi-ui-readability-brightness.md`

- [ ] **Step 1: 运行 Miner 全量验证**

Run:

```powershell
Set-Location miner
npm run verify
```

Expected: format check、ESLint、全部 `node:test` 和 Vite build 均通过。

- [ ] **Step 2: 运行解译平台全量验证**

Run:

```powershell
Set-Location frontend
npm run test:backend-url
npm run test:navigation
npm run test:ui
npm run test:workflow
npm run build
```

Expected: 全部合同测试与 Vue CLI 构建通过。

- [ ] **Step 3: 运行隔离测试和 Compose 配置检查**

Run from repository root:

```powershell
python -m pytest docker/tests/test_source_isolation.py docker/tests/test_compose_isolation.py -q
docker compose --env-file .env -f docker-compose.prod.yml config --quiet
```

Expected: Python 测试全部 PASS，Compose 配置命令以 0 退出。

- [ ] **Step 4: 重建并启动江西独立栈**

Run:

```powershell
docker compose --env-file .env -f docker-compose.prod.yml up -d --build --force-recreate backend frontend miner-api miner-web
docker compose --env-file .env -f docker-compose.prod.yml ps
```

Expected: `jiangxi-backend`、`jiangxi-frontend`、`jiangxi-miner-api`、`jiangxi-miner-web` 为 running/healthy；宿主机入口仍为 4173、4174、5178。

- [ ] **Step 5: 完成运行栈业务与视觉回归**

使用 `browser:control-in-app-browser`：

1. 登录 `http://127.0.0.1:4173/#/map`。
2. 检查 Miner 登录页、顶栏、左右侧栏、矿区详情和推理弹窗。
3. 打开 `http://127.0.0.1:4174/#/segmentation`，确认无需再次输入密码。
4. 完成一次地物分类，并确认结果预览颜色没有被主题 CSS 改变。
5. 完成一次光谱指数流程并打开历史结果。
6. 在 1440×900、1280×720、390×844 重复关键页面视觉检查。
7. 返回 Miner，确认会话仍有效。

Expected: 所有操作成功，界面符合 B 方案，业务图像保持原始数据颜色。

- [ ] **Step 6: 确认云南工程没有本次修改**

在云南工程根目录执行只读检查：

```powershell
git status --short
```

Expected: 没有由本次江西 UI 调整产生的文件变化。不得在云南目录执行格式化、构建写入或提交。

- [ ] **Step 7: 写入验证报告**

仅在前述命令和浏览器验收全部通过后，创建 `docs/superpowers/reports/2026-08-01-jiangxi-ui-readability-brightness.md`，内容至少包含以下已验证结论：

```markdown
# 江西平台整体字号与亮度调整报告

## 修改结果

- 江西 Miner 与江西解译平台已采用 B「明显提亮」主题。
- 桌面正文为 17px，1280 与 390 宽度正文为 16px，可见辅助文字最低 13px。
- 两端核心 `--jx-*` 令牌值一致，但源码、构建和运行部署保持独立。
- 地图、遥感影像、分类图例和结果预览未应用亮度滤镜。

## 验证结果

| 检查项 | 结果 |
|---|---|
| Miner `npm run verify` | 通过 |
| 解译平台合同测试与构建 | 通过 |
| 江西/云南源码与 Compose 隔离测试 | 通过 |
| 1440×900 | 通过 |
| 1280×720 | 通过 |
| 390×844 | 通过 |
| 地物分类、光谱指数、历史结果 | 通过 |
| 江西跨端单点登录 | 通过 |
| 云南工程未改动 | 通过 |

## 刻意保持不变

- 云南解译平台的 UI、异步任务和 GPU 调度不变。
- 江西推理接口、CPU 执行方式、模型、结果目录和认证逻辑不变。
- 业务数据色和影像像素不参与主题替换。
```

- [ ] **Step 8: 提交报告并检查最终工作区**

```powershell
git add -- docs/superpowers/reports/2026-08-01-jiangxi-ui-readability-brightness.md
git commit -m "记录江西 UI 提亮验收结果"
git status --short
```

Expected: 报告提交成功，最终 `git status --short` 无输出；如果存在用户原有文件变化，保持原样并在交付说明中单独列出。
