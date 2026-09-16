import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { readFile, readdir } from 'node:fs/promises';
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
  // 原文只进服务端 console.error。设备契约错误（用户可修正）保留 400 透出原文。
  const server = await read('../server.js');

  // 设备错误 400 分支保留：正则守卫 + 原文透出
  assert.match(server, /device 仅支持\|CUDA 不可用\|江西项目仅支持 CPU/u);
  assert.match(server, /res\.status\(400\)\.json\(\{[\s\S]*?detail: message/u);

  // 其余 500：固定文案 + 原文进日志；500 返回体不得再携带 detail 键回显原文
  assert.match(
    server,
    /console\.error\('\[inference\] kml-roi 推理失败:', message\);\s*return res\.status\(500\)\.json\(\{\s*error: '推理任务执行失败，请稍后重试或联系管理员',?\s*\}\);/u
  );
  const failureReturn = server.match(/return res\.status\(500\)\.json\(\{[^}]*\}\);/u);
  assert.ok(failureReturn, 'kml-roi 500 分支应返回固定文案对象');
  assert.ok(!failureReturn[0].includes('detail'), '500 返回体不得回显内部异常原文 detail');
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
