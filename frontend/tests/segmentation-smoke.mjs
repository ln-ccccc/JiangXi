// 解译平台「地物分类」GUI 冒烟测试——Segmentation.vue 组件拆分的安全网。
// 覆盖：工作流渲染 / 文件选择注入 / 年份校验 / 执行按钮状态机 / 全局导航。
// 上传→推理的请求契约由 tests/upload-contract.test.mjs 在 Node 层覆盖。
// 运行：npm run smoke（需 4174/5178 容器在运行）
import { createRequire } from 'node:module';
// playwright 安装在仓库外的测试基建目录（不进 package.json，离线镜像构建不受影响）
const require = createRequire(import.meta.url);
function loadPlaywright() {
  const candidates = [
    process.env.SMOKE_PLAYWRIGHT_DIR,
    'D:/项目/jiangxi-smoke',
  ].filter(Boolean);
  for (const dir of candidates) {
    try {
      return createRequire(dir + '/package.json')('playwright');
    } catch (_) {
      /* 尝试下一个 */
    }
  }
  return require('playwright');
}
const { chromium } = loadPlaywright();
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const MINER_ORIGIN = process.env.SMOKE_MINER_ORIGIN || 'http://127.0.0.1:4174';
const BACKEND_ORIGIN = process.env.SMOKE_BACKEND_ORIGIN || 'http://127.0.0.1:5178';
const ENV_FILE = process.env.JX_ENV_FILE || 'D:/项目/JiangXi/jx_env_gpu_20260909.env';

function loadAdminCredentials() {
  const text = readFileSync(ENV_FILE, 'utf-8');
  const env = Object.fromEntries(
    text
      .split('\n')
      .filter((line) => line.includes('='))
      .map((line) => [line.slice(0, line.indexOf('=')), line.slice(line.indexOf('=') + 1)])
  );
  assert.ok(env.ADMIN_USERNAME && env.ADMIN_PASSWORD, 'env 文件缺少管理员凭据');
  return { username: env.ADMIN_USERNAME, password: env.ADMIN_PASSWORD };
}

function dummyTif(name) {
  // 客户端只按扩展名过滤 tif/tiff，占位字节足够走通选择与暂存链路
  return { name, mimeType: 'image/tiff', buffer: Buffer.from(`SMOKE-${name}`) };
}

async function main() {
  const creds = loadAdminCredentials();
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  // —— 登录（共享 jiangxi_session）——
  await page.goto(`${MINER_ORIGIN}/#/login`);
  await page.evaluate(
    async ({ backend, user, pass }) => {
      const res = await fetch(`${backend}/api/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password: pass }),
      });
      if (!res.ok) throw new Error(`登录失败: ${res.status}`);
    },
    { backend: BACKEND_ORIGIN, user: creds.username, pass: creds.password }
  );

  // —— T1 渲染：工作流四步 + 标题 + 全局导航 ——
  await page.goto(`${MINER_ORIGIN}/#/segmentation`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector('.workflow-panel', { timeout: 30000 });
  const panels = await page.locator('.workflow-panel').count();
  assert.equal(panels, 4, '应有 4 个工作流面板');
  assert.ok(await page.getByRole('heading', { name: '地物分类' }).isVisible(), '标题应可见');
  assert.ok(
    await page.locator('.el-menu-item', { hasText: '矿山地图' }).isVisible(),
    '侧边导航应有「矿山地图」返回入口'
  );

  const runButton = page.getByRole('button', { name: '开始地物分类' });
  assert.ok(await runButton.isDisabled(), '未选影像时执行按钮应禁用');

  // —— T2 选择文件：走真实用户路径（点按钮 → filechooser 事件）——
  // 教训 2026-09-12：setInputFiles 直连 input 会绕过按钮点击路径，
  // 曾放过「按钮点击无效」的回归（refs 在组件拆分后失联）
  const [chooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    page.getByRole('button', { name: '选择文件' }).click(),
  ]);
  await chooser.setFiles([dummyTif('smoke-a.tif'), dummyTif('smoke-b.tif')]);
  await page.waitForSelector('.selected-files__title');
  assert.match(
    await page.locator('.selected-files__title').innerText(),
    /已选择 2 个 tif\/tiff 文件/,
    '应显示已选文件数'
  );
  assert.ok(await runButton.isEnabled(), '选择影像后执行按钮应可用');

  // —— T3 年份校验：空年份直接报错，不发请求 ——
  await runButton.click();
  await page.waitForSelector('.run-status p[data-state="error"]');
  assert.match(
    await page.locator('.run-status p').innerText(),
    /四位年份/,
    '空年份应提示填写年份'
  );

  // —— T4 结果删除接线：点「删除该组」应弹出确认框（取消，不破坏真实数据）——
  const deleteButtons = page.locator('.result-delete');
  const deleteCount = await deleteButtons.count();
  if (deleteCount > 0) {
    await deleteButtons.first().click();
    const confirmBox = page.locator('.el-message-box');
    await confirmBox.waitFor({ state: 'visible', timeout: 5000 });
    assert.match(
      await confirmBox.innerText(),
      /删除/,
      '点击删除该组应弹出确认框'
    );
    await page.locator('.el-message-box__btns button').first().click(); // 取消
    await confirmBox.waitFor({ state: 'hidden', timeout: 5000 });
  }

  await browser.close();
  console.log(
    `SMOKE PASS: 渲染/文件选择(真实路径)/年份校验/导航/删除接线${deleteCount ? '' : '(历史为空,跳过)'} 全部通过`
  );
}

main().catch((err) => {
  console.error('SMOKE FAIL:', err.message);
  process.exit(1);
});
