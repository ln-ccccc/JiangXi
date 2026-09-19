import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { readFile, readdir, writeFile, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const read = (relativePath) => readFile(new URL(relativePath, import.meta.url), 'utf8');

const minerRoot = fileURLToPath(new URL('..', import.meta.url));
const skipDirs = new Set(['node_modules', 'test', 'dist', 'public', 'data', 'uploads']);

async function collectSourceFiles(dir) {
  const files = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!skipDirs.has(entry.name)) files.push(...(await collectSourceFiles(fullPath)));
    } else if (/\.(js|mjs|vue)$/.test(entry.name)) {
      files.push(fullPath);
    }
  }
  return files;
}

test('kml_update 死键不回潮：BFF 链路从不产生该键，server 与前端不得再引用', async () => {
  // 2026-09-16 审查 P1-2（删除裁决）：BFF execFile 的 kml_roi_infer.py 输出 summary
  // 键集不含 kml_update，透传恒 null，前端 kmlChangedCount 分支与“KML 已更新”文案
  // 永久不可达。若回潮会重新制造不可达分支与误导性成功提示。
  for (const file of await collectSourceFiles(minerRoot)) {
    const text = await readFile(file, 'utf8');
    assert.ok(
      !text.includes('kml_update'),
      `${path.relative(minerRoot, file)} 不应再引用 kml_update 死键`
    );
  }
});

test('runtime 键注释与 kml_roi_infer.py 实际输出一致：实际键为 runtime', async () => {
  const server = await read('../server.js');
  assert.match(server, /runtime: parsed\?\.inference_runtime \|\| parsed\?\.runtime \|\| null/u);
  assert.match(server, /改名 runtime/u);
});

test('启动链子进程必须带超时：探测类 15s、SHP 加载 120s、KMZ 解压 30s', async () => {
  // 这些调用全部位于 initData()→app.listen 之前，挂起则 miner 永不 bind
  // （2026-09-16 审查 P2-14）。
  const server = await read('../server.js');
  const geoSource = await read('../services/jiangxiGeoJsonSource.js');

  // server.js：commandExists / pythonRunnable 的 spawnSync 探测
  assert.match(server, /STARTUP_PROBE_TIMEOUT_MS = 15000/u);
  assert.match(
    server,
    /spawnSync\('where', \[cmd\], \{ encoding: 'utf-8', timeout: STARTUP_PROBE_TIMEOUT_MS \}\)/u
  );
  assert.match(
    server,
    /spawnSync\('which', \[cmd\], \{ encoding: 'utf-8', timeout: STARTUP_PROBE_TIMEOUT_MS \}\)/u
  );
  assert.match(server, /print\(sys\.executable\)'[\s\S]*?timeout: STARTUP_PROBE_TIMEOUT_MS/u);

  // jiangxiGeoJsonSource.js：geopandas execFile（首次 import 慢，放宽）+ powershell 解压
  assert.match(geoSource, /timeout: 120000/u);
  assert.match(geoSource, /killSignal: 'SIGTERM'/u);
  assert.match(geoSource, /Expand-Archive[\s\S]{0,600}timeout: 30000/u);
});

test('kml-roi 500 分支固定文案：内部异常原文不回显，仅设备契约错误 400 透出', async () => {
  // 2026-09-16 审查 P2-6：err.message 含完整命令行/绝对路径，不得经 detail 回显；
  // 原文只进服务端 console.error。设备契约错误（用户可修正）保留 400，
  // 但 detail 经 safeDeviceDetail 只透出命中设备契约的行（M1，2026-09-19）。
  const server = await read('../server.js');

  // 设备错误 400 分支保留：正则守卫 + detail 必须经 safeDeviceDetail 清洗
  assert.match(server, /device 仅支持\|CUDA 不可用\|江西项目仅支持 CPU/u);
  assert.match(server, /function safeDeviceDetail\(err\)/u);
  assert.match(
    server,
    /res\.status\(400\)\.json\(\{\s*error: 'Failed to run kml roi inference',\s*detail: safeDeviceDetail\(err\),?\s*\}\);/u
  );
  assert.doesNotMatch(server, /detail: message\b/u);

  // 其余 500：固定文案 + 原文进日志；500 返回体不得再携带 detail 键回显原文
  assert.match(
    server,
    /console\.error\('\[inference\] kml-roi 推理失败:', message\);\s*return res\.status\(500\)\.json\(\{\s*error: '推理任务执行失败，请稍后重试或联系管理员',?\s*\}\);/u
  );
  const failureReturn = server.match(/return res\.status\(500\)\.json\(\{[^}]*\}\);/u);
  assert.ok(failureReturn, 'kml-roi 500 分支应返回固定文案对象');
  assert.ok(!failureReturn[0].includes('detail'), '500 返回体不得回显内部异常原文 detail');
});

test('kml-roi 入参校验错误只回显裸文件名（M9，2026-09-19）', async () => {
  // `old_tif_path not found: <绝对路径>` 式回显向客户端泄露服务器目录结构
  const server = await read('../server.js');
  assert.match(server, /old_tif_path not found: \$\{path\.basename\(oldTifPath\)\}/u);
  assert.match(server, /new_tif_path not found: \$\{path\.basename\(newTifPath\)\}/u);
  assert.match(server, /kml_path not found: \$\{path\.basename\(kmlPath\)\}/u);
  assert.match(server, /Script not found: \$\{path\.basename\(kmlRoiScriptPath\)\}/u);
  assert.doesNotMatch(server, /not found: \$\{oldTifPath\}/u);
  assert.doesNotMatch(server, /not found: \$\{kmlRoiScriptPath\}/u);
});

test('npm scripts 不得指向不存在的 scripts/ 目录（import:ndvi 死链不回潮）', async () => {
  // 2026-09-16 审查 P2-16：scripts/ 目录从未存在，import:ndvi 一跑即 MODULE_NOT_FOUND。
  const pkg = JSON.parse(await read('../package.json'));

  assert.ok(!('import:ndvi' in pkg.scripts), 'import:ndvi 死链不应存在');
  for (const [name, command] of Object.entries(pkg.scripts)) {
    assert.ok(
      !/(^|\s|"|')scripts\/[^\s"']+/u.test(String(command)),
      `npm script ${name} 指向不存在的 scripts/ 文件: ${command}`
    );
  }
});

test('后端 fetch 超时分级：普通 CRUD 15s，导出/备份恢复慢操作 120s', async () => {
  // 2026-09-16 审查 P2-15：15s 无差别套用会让导出/备份恢复类慢操作
  // 「用户看到 502 而后端任务实际成功」，诱导重复提交。
  const projectBackend = await read('../services/projectBackend.js');
  const authBackend = await read('../services/authBackend.js');

  // 分级常量 + 透传
  assert.match(projectBackend, /const DEFAULT_TIMEOUT_MS = 15000;/u);
  assert.match(projectBackend, /const SLOW_OP_TIMEOUT_MS = 120000;/u);
  assert.match(projectBackend, /signal: AbortSignal\.timeout\(timeoutMs\)/u);

  // 恰好三个慢操作调用点显式放宽
  assert.equal(
    (projectBackend.match(/timeoutMs: SLOW_OP_TIMEOUT_MS/gu) || []).length,
    3,
    '应且仅应导出/备份/恢复三个慢操作放宽超时'
  );
  assert.match(projectBackend, /\/exports`, \{[\s\S]{0,160}?timeoutMs: SLOW_OP_TIMEOUT_MS/u);
  assert.match(projectBackend, /\/backups`, \{[\s\S]{0,160}?timeoutMs: SLOW_OP_TIMEOUT_MS/u);
  assert.match(projectBackend, /\/restore`, \{[\s\S]{0,160}?timeoutMs: SLOW_OP_TIMEOUT_MS/u);

  // 认证操作均为轻量请求，保持 15s 常量分级
  assert.match(authBackend, /const AUTH_TIMEOUT_MS = 15000;/u);
  assert.match(authBackend, /signal: AbortSignal\.timeout\(AUTH_TIMEOUT_MS\)/u);
  assert.doesNotMatch(authBackend, /AbortSignal\.timeout\(15000\)/u);
});

test('lint/format 清单 glob 化：全部测试文件纳入风格门，禁止回退枚举（2026-09-16 审查验证门）', async () => {
  // 77674c0 的清单缺 8+ 个测试文件形成风格门盲区；改为 glob 后新增测试自动纳入。
  const pkg = JSON.parse(await read('../package.json'));

  for (const scriptName of ['format', 'format:check', 'lint']) {
    const command = String(pkg.scripts[scriptName]);
    assert.match(command, /"test\/\*\*\/\*\.test\.js"/u, `${scriptName} 应含 test glob`);
    assert.doesNotMatch(
      command,
      /test\/[A-Za-z0-9_]+\.test\.js/u,
      `${scriptName} 不得回退为枚举测试文件`
    );
  }

  const testFiles = (await readdir(new URL('../test', import.meta.url))).filter((name) =>
    /\.test\.js$/u.test(name)
  );
  assert.ok(testFiles.length >= 30, `测试文件数量异常: ${testFiles.length}`);

  // 行为证明：在 test/ 投放一个格式违规探针文件，glob 化的 format:check 必须让它失败——
  // 即「任何新增测试文件无需登记自动被风格门覆盖」。
  const { spawnSync } = await import('node:child_process');
  const probePath = path.join(minerRoot, 'test', '__style_gate_probe__.test.js');
  await writeFile(probePath, 'const probe=[1,2,3];\nexport default probe;\n', 'utf8');
  try {
    const probe = spawnSync('npm run --silent format:check', {
      cwd: minerRoot,
      encoding: 'utf8',
      shell: true,
      windowsHide: true,
    });
    assert.notEqual(probe.status, 0, '格式违规探针文件必须被 glob 化风格门拦截');
    const combined = `${probe.stdout || ''}${probe.stderr || ''}`;
    assert.match(combined, /__style_gate_probe__\.test\.js/u, '拦截输出应点名探针文件');
  } finally {
    await rm(probePath, { force: true });
  }
});
