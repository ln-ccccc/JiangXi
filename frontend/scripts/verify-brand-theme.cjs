const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const frontendRoot = path.resolve(__dirname, '..');
const read = (...segments) => fs.readFileSync(path.join(frontendRoot, ...segments), 'utf8');

const aside = read('src', 'components', 'AsideVue.vue');
const login = read('src', 'views', 'Login.vue');
const header = read('src', 'components', 'Tablogin.vue');
const router = read('src', 'router', 'index.js');
const globalConfig = read('src', 'global.vue');
const theme = read('src', 'assets', 'css', 'theme-dark.css');
const html = read('public', 'index.html');
const sourceFiles = [aside, login, header, html].join('\n');

assert.match(aside, /江西省矿山生态修复智能监测平台/);
assert.match(login, /江西省矿山生态修复智能监测平台/);
assert.match(header, /江西省矿山生态修复智能监测平台/);
assert.match(html, /江西省矿山生态修复智能监测平台/);
assert.doesNotMatch(sourceFiles, /云南省矿山生态修复智能监测平台/);

assert.match(theme, /--bg-primary:\s*#07131f;/);
assert.match(theme, /--primary-color:\s*#4ecdc4;/);
assert.match(theme, /--text-primary:\s*#e0f7ff;/);
assert.match(login, /var\(--bg-primary\)/);
assert.match(aside, /width:\s*48px;/);
assert.match(aside, /height:\s*48px;/);
assert.match(aside, /object-fit:\s*contain;/);
assert.match(theme, /@media \(max-width: 768px\)/);
assert.match(theme, /\.prehandle-label/);
assert.match(theme, /\.option-row/);
assert.match(router, /createWebHashHistory/);
assert.match(header, /window\.location\.assign\(this\.minerUrl\)/);
assert.match(globalConfig, /window\.location\.hostname/);

console.log('品牌与深色主题检查通过');
