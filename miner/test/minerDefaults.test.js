import assert from 'node:assert/strict';
import test from 'node:test';

import {
  APP_KICKER,
  APP_TITLE,
  DEFAULT_MAP_LAYER,
  DEFAULT_MAP_PROVIDER,
  JIANGXI_FALLBACK_CENTER,
  JIANGXI_FALLBACK_ZOOM,
  LOGIN_SUBTITLE,
  WORKSPACE_SUBTITLE,
  normalizeMapProvider,
} from '../src/config/minerDefaults.js';

test('uses Jiangxi branding copy by default', () => {
  assert.equal(APP_TITLE, '江西省矿山生态修复智能监测平台');
  assert.equal(APP_KICKER, APP_TITLE);
  assert.equal(
    LOGIN_SUBTITLE,
    '输入管理员账号和密码后，直接进入江西矿山在线地图；可按需进入解译与指数分析。'
  );
  assert.equal(WORKSPACE_SUBTITLE, '江西版默认入口，承接项目建档、矿山绑定、数据登记和只读溯源。');
});

test('uses Jiangxi fallback map view and online satellite defaults', () => {
  assert.deepEqual(JIANGXI_FALLBACK_CENTER, [27.61, 115.95]);
  // 离线瓦片从 z8 起步：初始视野必须落在原生层级，进入即见影像
  assert.equal(JIANGXI_FALLBACK_ZOOM, 8);
  assert.equal(DEFAULT_MAP_PROVIDER, 'gaode');
  assert.equal(DEFAULT_MAP_LAYER, 'satellite');
});

test('normalizeMapProvider falls back to online satellite when env is empty or unsupported', () => {
  assert.equal(normalizeMapProvider(''), 'gaode');
  assert.equal(normalizeMapProvider(undefined), 'gaode');
  assert.equal(normalizeMapProvider('unknown-provider'), 'gaode');
  assert.equal(normalizeMapProvider('OSM'), 'osm');
});
