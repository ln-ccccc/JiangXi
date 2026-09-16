import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { saveKmlUpload } from '../services/kmlUpload.js';

test('saveKmlUpload stores a valid kml file and returns a bare filename for the policy-checked submit', () => {
  const uploadRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'kml-upload-'));
  const result = saveKmlUpload({
    uploadRoot,
    filename: '../新增矿山.kml',
    content: '<kml><Document></Document></kml>',
  });

  // kml_path 必须是裸文件名：提交推理走 inferencePathPolicy，绝对路径会被
  // 400「kml_path 只能是受控目录内的文件名」拒掉（上传→提交链路必断）
  assert.equal(result.kml_path, '新增矿山.kml');
  assert.equal(path.isAbsolute(result.kml_path), false);
  assert.equal(
    fs.readFileSync(result.kml_path_absolute, 'utf-8'),
    '<kml><Document></Document></kml>'
  );
  assert.equal(
    fs.readFileSync(path.join(uploadRoot, '新增矿山.kml'), 'utf-8'),
    '<kml><Document></Document></kml>'
  );
});

test('saveKmlUpload rejects non-kml names and blank content', () => {
  const uploadRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'kml-upload-'));

  assert.throws(
    () => saveKmlUpload({ uploadRoot, filename: 'bad.txt', content: '<kml />' }),
    /只支持 \.kml 文件/
  );
  assert.throws(
    () => saveKmlUpload({ uploadRoot, filename: 'bad.kml', content: '   ' }),
    /KML 内容不能为空/
  );
});
