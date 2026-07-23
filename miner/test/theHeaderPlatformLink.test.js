import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const headerSource = await readFile(
  new URL('../src/components/TheHeader.vue', import.meta.url),
  'utf8'
);

test('TheHeader 通过唯一 helper 构建解译平台地址', () => {
  assert.match(
    headerSource,
    /import\s+\{\s*buildGeoViewUrl\s*\}\s+from\s+['"]\.\.\/navigation\/platformLinks\.js['"]/u
  );
  assert.match(headerSource, /buildGeoViewUrl\(import\.meta\.env\.VITE_GEOVIEW_URL\)/u);
  assert.doesNotMatch(headerSource, /localhost:3000|detectchanges/u);
  assert.doesNotMatch(headerSource, /endsWith\(['"]\/['"]\)|hasHash|const\s+target/u);
});

test('TheHeader 在解译平台地址不可用时禁用导航并提供可见提示', () => {
  assert.match(headerSource, /:disabled=['"]!geoViewUrl['"]/u);
  assert.match(headerSource, /:title=['"]geoViewButtonLabel['"]/u);
  assert.match(headerSource, /:aria-label=['"]geoViewButtonLabel['"]/u);
  assert.match(headerSource, /解译平台地址未配置/u);
  assert.match(headerSource, /if\s*\(!geoViewUrl\)\s*\{\s*return;\s*\}/u);
});
