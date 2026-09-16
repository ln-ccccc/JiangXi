import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { saveKmlUpload } from '../services/kmlUpload.js';
import { resolvePathInRoots } from '../services/inferencePathPolicy.js';

// 复审 B1 贯通断言：上传接口的返回值必须能直接作为推理提交参数通过路径策略。
// 此前两段各有过测试（上传断言绝对路径、策略只收裸名）却从未对接，
// 导致「上传成功 → 提交必 400」的集成断链漏网。
test('上传返回的 kml_path 可直接喂给推理提交的路径策略解析', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kml-upload-link-'));
  try {
    const result = saveKmlUpload({
      uploadRoot: root,
      filename: 'new_mine.kml',
      content: '<kml><Document></Document></kml>',
    });

    // 契约：kml_path 必须是裸文件名（提交端点只收受控目录内文件名）
    assert.equal(path.isAbsolute(result.kml_path), false);
    assert.equal(result.kml_path, 'new_mine.kml');
    assert.ok(fs.existsSync(path.join(root, result.kml_path)));

    // 贯通：该值直接作为 /api/inference/kml-roi 的 kml_path 提交可解析
    const resolved = resolvePathInRoots(result.kml_path, [root], 'kml_path', ['.kml', '.kmz']);
    // policy 返回 realpath 后的绝对路径（Windows 临时目录可能为 8.3 短名）
    assert.equal(resolved, fs.realpathSync(path.join(root, 'new_mine.kml')));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
