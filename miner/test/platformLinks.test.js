import test from 'node:test';
import assert from 'node:assert/strict';

import { buildGeoViewUrl } from '../src/navigation/platformLinks.js';

test('空配置不推断解译平台地址', () => {
  assert.equal(buildGeoViewUrl(''), '');
  assert.equal(buildGeoViewUrl(), '');
});

test('显式 HTTP 或 HTTPS 根地址生成解译平台分割页地址', () => {
  assert.equal(buildGeoViewUrl('http://127.0.0.1:4174/'), 'http://127.0.0.1:4174/#/segmentation');
  assert.equal(
    buildGeoViewUrl('https://geoview.example'),
    'https://geoview.example/#/segmentation'
  );
});

test('无效或非根地址不生成解译平台地址', () => {
  const invalidRoots = [
    'geoview.example',
    '/geoview',
    'ftp://geoview.example/',
    'https://geoview.example/app',
    'https://geoview.example/?mode=test',
    'https://geoview.example/#/map',
    'https://user:secret@geoview.example/',
  ];

  for (const root of invalidRoots) {
    assert.equal(buildGeoViewUrl(root), '', root);
  }
});
