import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { resolvePathInRoots } from '../services/inferencePathPolicy.js';

test('resolvePathInRoots resolves a basename inside a configured root', () => {
  const root = path.join(os.tmpdir(), 'miner-inputs');
  const resolved = resolvePathInRoots('scene.tif', [root], 'old_tif_path', ['.tif']);

  assert.equal(resolved, path.resolve(root, 'scene.tif'));
});

test('resolvePathInRoots rejects client paths and unsupported suffixes', () => {
  const root = path.join(os.tmpdir(), 'miner-inputs');

  assert.throws(
    () =>
      resolvePathInRoots(path.join(root, '..', 'outside.tif'), [root], 'old_tif_path', ['.tif']),
    /old_tif_path/
  );
  assert.throws(
    () => resolvePathInRoots('scene.png', [root], 'old_tif_path', ['.tif']),
    /old_tif_path/
  );
});

test('resolvePathInRoots rejects a symlink that escapes the managed root', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'miner-input-policy-'));
  const root = path.join(tempDir, 'managed');
  const outside = path.join(tempDir, 'outside.tif');
  fs.mkdirSync(root);
  fs.writeFileSync(outside, 'tif');
  try {
    fs.symlinkSync(outside, path.join(root, 'linked.tif'));
  } catch (error) {
    if (error.code === 'EPERM') return;
    throw error;
  }

  assert.throws(() => resolvePathInRoots('linked.tif', [root], 'old_tif_path', ['.tif']));
});
