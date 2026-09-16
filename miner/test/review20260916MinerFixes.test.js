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
