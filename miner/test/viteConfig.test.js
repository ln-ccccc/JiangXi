import assert from 'node:assert/strict';
import { test } from 'node:test';

import viteConfig from '../vite.config.js';

test('Vite proxies local tile requests to the Miner backend', () => {
  const tilesProxy = viteConfig.server?.proxy?.['/tiles'];

  assert.equal(tilesProxy?.target, 'http://127.0.0.1:8000');
  assert.equal(tilesProxy?.changeOrigin, true);
});
