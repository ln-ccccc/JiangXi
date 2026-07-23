const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const frontendRoot = path.resolve(__dirname, "..");
const repositoryRoot = path.resolve(frontendRoot, "..");
const readFrontend = (...segments) =>
  fs.readFileSync(path.join(frontendRoot, ...segments), "utf8");

function cssDeclarations(source) {
  return Object.fromEntries(
    [...source.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map((match) => [
      match[1],
      match[2].trim(),
    ]),
  );
}

function collectSourceFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return collectSourceFiles(entryPath);
    if (!/\.(?:css|html|js|less|vue)$/.test(entry.name)) return [];
    return [fs.readFileSync(entryPath, "utf8")];
  });
}

const theme = readFrontend("src", "assets", "css", "theme-dark.css");
const appCss = readFrontend("src", "assets", "css", "app.css");
const appLess = readFrontend("src", "assets", "css", "app.less");
const home = readFrontend("src", "views", "Home.vue");
const aside = readFrontend("src", "components", "AsideVue.vue");
const header = readFrontend("src", "components", "Tablogin.vue");
const login = readFrontend("src", "views", "Login.vue");
const notFound = readFrontend("src", "views", "NotFound.vue");
const html = readFrontend("public", "index.html");
const minerTheme = fs.readFileSync(
  path.join(repositoryRoot, "miner", "src", "assets", "base.css"),
  "utf8",
);

const expectedCanonicalTokens = {
  "--jx-bg": "#071923",
  "--jx-bg-elevated": "#0b222b",
  "--jx-surface": "#0d2630",
  "--jx-surface-muted": "rgba(230, 201, 140, 0.06)",
  "--jx-border": "rgba(156, 231, 189, 0.22)",
  "--jx-border-strong": "rgba(156, 231, 189, 0.5)",
  "--jx-text": "#e5f1ed",
  "--jx-text-muted": "#9bb0ab",
  "--jx-primary": "#9ce7bd",
  "--jx-primary-hover": "#b7f0d0",
  "--jx-success": "#82d7a7",
  "--jx-warning": "#d68058",
  "--jx-danger": "#d96b6b",
  "--jx-info": "#8fc6c8",
  "--jx-sand": "#e6c98c",
  "--jx-radius": "10px",
  "--jx-radius-large": "16px",
};

const themeTokens = cssDeclarations(theme);
const minerTokens = cssDeclarations(minerTheme);
for (const [name, value] of Object.entries(expectedCanonicalTokens)) {
  assert.equal(minerTokens[name], value, `Miner 基准令牌 ${name} 被意外改动`);
  assert.equal(themeTokens[name], minerTokens[name], `江西主题必须原值复制 ${name}`);
}

const expectedLegacyAliases = {
  "--primary-color": "var(--jx-primary)",
  "--primary-light": "var(--jx-primary-hover)",
  "--primary-dark": "var(--jx-primary)",
  "--primary-hover": "var(--jx-surface-muted)",
  "--bg-primary": "var(--jx-bg)",
  "--bg-secondary": "var(--jx-bg-elevated)",
  "--bg-tertiary": "var(--jx-surface-muted)",
  "--bg-card": "var(--jx-surface)",
  "--bg-hover": "var(--jx-surface-muted)",
  "--text-primary": "var(--jx-text)",
  "--text-secondary": "var(--jx-text-muted)",
  "--text-muted": "var(--jx-text-muted)",
  "--text-inverse": "var(--jx-bg)",
  "--border-color": "var(--jx-border)",
  "--border-light": "var(--jx-border)",
  "--border-dark": "var(--jx-border-strong)",
  "--success-color": "var(--jx-success)",
  "--warning-color": "var(--jx-warning)",
  "--error-color": "var(--jx-danger)",
  "--info-color": "var(--jx-info)",
  "--radius": "var(--jx-radius)",
  "--radius-large": "var(--jx-radius-large)",
};

for (const [name, value] of Object.entries(expectedLegacyAliases)) {
  assert.equal(themeTokens[name], value, `旧变量 ${name} 必须 alias 到 canonical token`);
}

const expectedElementAliases = {
  "--el-color-primary": "var(--jx-primary)",
  "--el-color-primary-dark-2": "var(--jx-primary)",
  "--el-color-primary-light-3": "var(--jx-primary-hover)",
  "--el-color-primary-light-5": "var(--jx-surface-muted)",
  "--el-color-primary-light-7": "var(--jx-surface-muted)",
  "--el-color-primary-light-8": "var(--jx-surface-muted)",
  "--el-color-primary-light-9": "var(--jx-surface-muted)",
  "--el-color-success": "var(--jx-success)",
  "--el-color-warning": "var(--jx-warning)",
  "--el-color-danger": "var(--jx-danger)",
  "--el-color-info": "var(--jx-info)",
  "--el-bg-color": "var(--jx-surface)",
  "--el-bg-color-page": "var(--jx-bg)",
  "--el-bg-color-overlay": "var(--jx-surface)",
  "--el-fill-color": "var(--jx-surface-muted)",
  "--el-fill-color-dark": "var(--jx-surface)",
  "--el-fill-color-darker": "var(--jx-surface)",
  "--el-fill-color-blank": "var(--jx-surface)",
  "--el-fill-color-light": "var(--jx-surface-muted)",
  "--el-fill-color-lighter": "var(--jx-surface-muted)",
  "--el-fill-color-extra-light": "var(--jx-surface-muted)",
  "--el-border-color": "var(--jx-border)",
  "--el-border-color-dark": "var(--jx-border-strong)",
  "--el-border-color-darker": "var(--jx-border-strong)",
  "--el-border-color-light": "var(--jx-border)",
  "--el-border-color-lighter": "var(--jx-border)",
  "--el-border-color-extra-light": "var(--jx-border)",
  "--el-border-color-hover": "var(--jx-border-strong)",
  "--el-text-color-primary": "var(--jx-text)",
  "--el-text-color-regular": "var(--jx-text-muted)",
  "--el-text-color-secondary": "var(--jx-text-muted)",
  "--el-text-color-placeholder": "var(--jx-text-muted)",
  "--el-text-color-disabled": "var(--jx-text-muted)",
  "--el-disabled-bg-color": "var(--jx-surface-muted)",
  "--el-disabled-text-color": "var(--jx-text-muted)",
  "--el-disabled-border-color": "var(--jx-border)",
};

for (const [family, token] of [
  ["success", "--jx-success"],
  ["warning", "--jx-warning"],
  ["danger", "--jx-danger"],
  ["info", "--jx-info"],
]) {
  expectedElementAliases[`--el-color-${family}-dark-2`] = `var(${token})`;
  expectedElementAliases[`--el-color-${family}-light-3`] = `var(${token})`;
  for (const level of [5, 7, 8, 9]) {
    expectedElementAliases[`--el-color-${family}-light-${level}`] =
      "var(--jx-surface-muted)";
  }
}

for (const [name, value] of Object.entries(expectedElementAliases)) {
  assert.equal(themeTokens[name], value, `Element Plus 变量 ${name} 必须 alias 到 canonical token`);
}

assert.match(appCss, /--theme--color:\s*var\(--jx-primary\);/);
assert.match(appLess, /--theme--color:\s*var\(--jx-primary\);/);

assert.match(home, /class="atlas-shell"/);
assert.match(home, /class="sidebar-toggle"/);
assert.match(home, /:aria-expanded="!isCollapse"/);
assert.match(home, /\.platform-header\s*{[^}]*min-width:\s*0;/s);
assert.match(aside, />江西</);
assert.match(aside, /生态图册/);
assert.match(aside, /解译与指数分析/);
assert.match(aside, /同步 CPU/);
assert.match(aside, /地物分类/);
assert.match(aside, /光谱指数/);
assert.match(aside, /操作提示/);
assert.match(header, /江西样区档案/);
assert.match(header, /返回矿山地图/);
assert.match(login, /江西生态图册/);
assert.match(login, /一次登录可访问江西地图与解译平台/);
assert.match(notFound, /江西生态图册/);
assert.match(notFound, /返回地物分类/);
assert.match(notFound, /\/segmentation/);
assert.match(html, /江西生态图册/);

const styleSources = [theme, home, aside, header, login, notFound].join("\n");
assert.match(styleSources, /@media\s*\(max-width:\s*1100px\)/);
assert.match(styleSources, /@media\s*\(max-width:\s*768px\)/);
assert.match(styleSources, /@media\s*\(max-width:\s*480px\)/);
assert.match(styleSources, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
assert.match(theme, /:focus-visible/);
assert.match(
  theme,
  /\.el-button:focus-visible,\s*\.el-menu-item:focus-visible,\s*\.el-input__inner:focus-visible,\s*\.el-textarea__inner:focus-visible,\s*\.el-select__input:focus-visible,\s*\.el-input-number__input:focus-visible,\s*\.el-switch:focus-visible,\s*\.el-upload:focus-visible\s*{[^}]*outline:\s*2px solid var\(--jx-primary\)\s*!important;[^}]*outline-offset:\s*3px\s*!important;[^}]*}/s,
);
assert.match(
  theme,
  /\.el-checkbox__original:focus-visible\s*\+\s*\.el-checkbox__inner,\s*\.el-radio__original:focus-visible\s*\+\s*\.el-radio__inner\s*{[^}]*box-shadow:\s*0 0 0 2px var\(--jx-primary\)\s*!important;[^}]*}/s,
);
assert.match(theme, /Noto Serif SC/);
assert.match(theme, /Microsoft YaHei/);
assert.match(theme, /Bahnschrift/);
assert.match(styleSources, /contour/);
assert.match(styleSources, /sample-record/);

const productSource = [
  ...collectSourceFiles(path.join(frontendRoot, "src")),
  html,
].join("\n");
const oldPalette = new RegExp(
  ["#4e", "cdc4|#07131f|#e0f7ff|rgba\\(\\s*78,\\s*205,\\s*196"].join(""),
  "i",
);
assert.doesNotMatch(productSource, oldPalette);
assert.doesNotMatch(productSource, /云南/);
assert.doesNotMatch(productSource, /detectchanges/i);

console.log("江西生态图册品牌与主题合同检查通过");
