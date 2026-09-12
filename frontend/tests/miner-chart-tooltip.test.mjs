// 矿端地图（4173）右栏图表悬浮层回归测试——防 tooltip 溢出遮挡与类目截断。
// 背景：2026-09-12 用户报告「图斑类型分布」悬停信息框溢出图外压住相邻内容；
// 长类目名被截断又迫使读者依赖悬停。修复：tooltip confine + 标签换行。
// 运行：node tests/miner-chart-tooltip.test.mjs（需 4173/5178 容器在运行）
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const require = createRequire(import.meta.url);
function loadPlaywright() {
  const candidates = [process.env.SMOKE_PLAYWRIGHT_DIR, 'D:/项目/jiangxi-smoke'].filter(Boolean);
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

const MINER_ORIGIN = process.env.SMOKE_MINER_ORIGIN || 'http://127.0.0.1:4173';
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
  return { username: env.ADMIN_USERNAME, password: env.ADMIN_PASSWORD };
}

async function main() {
  const creds = loadAdminCredentials();
  const browser = await chromium.launch();
  const page = await (
    await browser.newContext({ viewport: { width: 1440, height: 900 } })
  ).newPage();

  await page.goto(`${MINER_ORIGIN}/#/map`);
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
  await page.reload();
  await page.waitForSelector('.chart-box canvas', { timeout: 30000 });
  await page.waitForTimeout(4000);

  const charts = await page.locator('.chart-box').all();
  assert.ok(charts.length >= 4, `应有至少 4 个图表，实际 ${charts.length}`);

  let checkedTooltips = 0;
  for (const chart of charts) {
    const box = await chart.boundingBox();
    if (!box) continue;
    // 逐条悬停（从上往下扫）
    const rows = 6;
    for (let i = 0; i < rows; i += 1) {
      const y = box.y + 16 + (i * (box.height - 24)) / rows;
      await page.mouse.move(box.x + box.width - 24, y);
      await page.waitForTimeout(250);
      const tipBox = await page.evaluate(() => {
        // ECharts tooltip 渲染在图表容器内的绝对定位 div
        const hosts = document.querySelectorAll('.chart-box');
        for (const host of hosts) {
          const t = host.querySelector('div[style*="pointer-events: none"]');
          if (t && t.textContent.trim()) {
            const r = t.getBoundingClientRect();
            if (r.width > 0) {
              return { rect: r, host: host.getBoundingClientRect(), viewport: { w: innerWidth, h: innerHeight } };
            }
          }
        }
        return null;
      });
      if (tipBox) {
        const { rect, host, viewport } = tipBox;
        assert.ok(
          rect.x >= host.x - 1 && rect.y >= host.y - 1 &&
            rect.right <= host.right + 1 && rect.bottom <= host.bottom + 1,
          `tooltip 溢出图表容器: tip=[${rect.x},${rect.y},${rect.right},${rect.bottom}] chart=[${host.x},${host.y},${host.right},${host.bottom}]`
        );
        assert.ok(
          rect.x >= 0 && rect.y >= 0 && rect.right <= viewport.w && rect.bottom <= viewport.h,
          'tooltip 超出视口'
        );
        checkedTooltips += 1;
      }
    }
  }
  assert.ok(checkedTooltips > 0, '至少应触发并校验一次 tooltip');

  // 类目标签不再截断：断言右栏不再出现省略号结尾的类目文本
  const truncated = await page.evaluate(() =>
    Array.from(document.querySelectorAll('.right-sidebar *'))
      .filter((el) => el.children.length === 0 && el.textContent.trim().endsWith('…'))
      .map((el) => el.textContent.trim())
      .slice(0, 5)
  );
  assert.deepEqual(truncated, [], `仍有被截断的类目标签: ${truncated.join(' | ')}`);

  await browser.close();
  console.log(`TOOLTIP PASS: ${checkedTooltips} 次 tooltip 全部限定在图表容器内，类目标签无截断`);
}

main().catch((err) => {
  console.error('TOOLTIP FAIL:', err.message);
  process.exit(1);
});
