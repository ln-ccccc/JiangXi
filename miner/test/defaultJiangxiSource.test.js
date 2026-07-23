import assert from 'node:assert/strict';
import test from 'node:test';

import {
  DEFAULT_JIANGXI_GEO_SOURCE_CANDIDATES,
  DEFAULT_JIANGXI_GEO_SOURCE_PATH,
  DEFAULT_JIANGXI_RUNTIME_GEO_SOURCE_PATH,
  resolveDefaultJiangxiGeoSourcePath,
} from '../services/defaultJiangxiSource.js';

test('resolveDefaultJiangxiGeoSourcePath returns authoritative SHP path', () => {
  assert.equal(DEFAULT_JIANGXI_GEO_SOURCE_PATH, 'D:/项目/江西数据/348个图斑.shp');
  assert.equal(
    resolveDefaultJiangxiGeoSourcePath('', () => false),
    'D:/项目/江西数据/348个图斑.shp'
  );
});

test('resolveDefaultJiangxiGeoSourcePath picks existing candidate', () => {
  assert.deepEqual(DEFAULT_JIANGXI_GEO_SOURCE_CANDIDATES, [
    DEFAULT_JIANGXI_RUNTIME_GEO_SOURCE_PATH,
    DEFAULT_JIANGXI_GEO_SOURCE_PATH,
  ]);
  assert.equal(
    resolveDefaultJiangxiGeoSourcePath(
      '',
      (candidate) => candidate === DEFAULT_JIANGXI_RUNTIME_GEO_SOURCE_PATH
    ),
    DEFAULT_JIANGXI_RUNTIME_GEO_SOURCE_PATH
  );
  assert.equal(
    resolveDefaultJiangxiGeoSourcePath(
      '',
      (candidate) => candidate === DEFAULT_JIANGXI_GEO_SOURCE_PATH
    ),
    DEFAULT_JIANGXI_GEO_SOURCE_PATH
  );
});

test('resolveDefaultJiangxiGeoSourcePath keeps explicit override untouched', () => {
  assert.equal(
    resolveDefaultJiangxiGeoSourcePath('D:/custom/source.shp', () => false),
    'D:/custom/source.shp'
  );
});
