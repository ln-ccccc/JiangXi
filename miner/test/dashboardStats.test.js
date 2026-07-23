import assert from 'node:assert/strict';
import test from 'node:test';

import { buildDashboardStats } from '../services/dashboardStats.js';

test('buildDashboardStats returns Jiangxi overview metrics with area-based status ratio', () => {
  const stats = buildDashboardStats({
    minesData: [
      {
        type: 'Feature',
        properties: {
          FID_1: 1,
          SHI: '赣州市',
          area: 100,
          HFZLQK: '完全修复',
          status_normalized: 'treated',
          NXFFS: '自然恢复',
          STWT: '无主废弃矿山',
          KCFS: '露天开采',
        },
        geometry: { type: 'Polygon', coordinates: [] },
      },
      {
        type: 'Feature',
        properties: {
          FID_1: 2,
          SHI: '上饶市',
          area: 300,
          HFZLQK: '未治理',
          status_normalized: 'untreated',
          NXFFS: '工程修复',
          STWT: '历史遗留矿山',
          KCFS: '地下开采',
        },
        geometry: { type: 'Polygon', coordinates: [] },
      },
    ],
  });

  assert.equal(stats.overview.plot_total, 2);
  assert.equal(stats.overview.area_total, 400);
  assert.equal(stats.overview.treated_area, 100);
  assert.equal(stats.overview.untreated_area, 300);
  assert.equal(stats.overview.treated_area_ratio, 0.25);
  assert.equal(stats.overview.untreated_area_ratio, 0.75);
  assert.deepEqual(stats.city_distribution, [
    { name: '赣州市', value: 1 },
    { name: '上饶市', value: 1 },
  ]);
  assert.deepEqual(stats.damage_type_distribution, [
    { name: '历史遗留矿山', value: 1 },
    { name: '无主废弃矿山', value: 1 },
  ]);
  assert.deepEqual(stats.restoration_method_distribution, [
    { name: '工程修复', value: 1 },
    { name: '自然恢复', value: 1 },
  ]);
  assert.deepEqual(stats.mining_method_distribution, [
    { name: '地下开采', value: 1 },
    { name: '露天开采', value: 1 },
  ]);
  assert.deepEqual(stats.city_area_distribution, [
    { name: '上饶市', value: 0.03 },
    { name: '赣州市', value: 0.01 },
  ]);
  assert.deepEqual(stats.recommended_panels.map((item) => item.key), [
    'city_distribution',
    'damage_type_distribution',
    'restoration_method_area_distribution',
    'city_area_distribution',
    'mining_method_distribution',
  ]);
});

test('buildDashboardStats keeps unknown buckets explicit and never returns fake land type stats', () => {
  const stats = buildDashboardStats({
    minesData: [
      {
        type: 'Feature',
        properties: {
          FID_1: 10,
          area: 0,
          HFZLQK: '',
          status_normalized: 'unknown',
          SHI: '',
          STWT: '',
          NXFFS: '',
          KCFS: '',
        },
        geometry: { type: 'Polygon', coordinates: [] },
      },
    ],
  });

  assert.equal(stats.overview.plot_total, 1);
  assert.equal(stats.overview.area_total, 0);
  assert.equal(stats.overview.treated_area_ratio, 0);
  assert.equal(stats.overview.untreated_area_ratio, 0);
  assert.deepEqual(stats.city_distribution, [{ name: '未标注地市', value: 1 }]);
  assert.deepEqual(stats.damage_type_distribution, [{ name: '未知图斑类型', value: 1 }]);
  assert.deepEqual(stats.restoration_method_distribution, [{ name: '未知修复方式', value: 1 }]);
  assert.deepEqual(stats.mining_method_distribution, [{ name: '未知开采方式', value: 1 }]);
  assert.deepEqual(stats.recommended_panels, []);
  assert.equal('landTypeList' in stats, false);
  assert.equal('changeAreaStats' in stats, false);
});

test('buildDashboardStats hides low-information mining panels when unknown buckets dominate', () => {
  const stats = buildDashboardStats({
    minesData: [
      {
        type: 'Feature',
        properties: {
          FID_1: 1,
          SHI: '赣州市',
          area: 100,
          status_normalized: 'treated',
          NXFFS: '自然恢复',
          STWT: '历史遗留矿山',
          KCFS: '',
        },
        geometry: { type: 'Polygon', coordinates: [] },
      },
      {
        type: 'Feature',
        properties: {
          FID_1: 2,
          SHI: '上饶市',
          area: 200,
          status_normalized: 'untreated',
          NXFFS: '工程修复',
          STWT: '无主废弃矿山',
          KCFS: '',
        },
        geometry: { type: 'Polygon', coordinates: [] },
      },
      {
        type: 'Feature',
        properties: {
          FID_1: 3,
          SHI: '上饶市',
          area: 300,
          status_normalized: 'untreated',
          NXFFS: '工程修复',
          STWT: '无主废弃矿山',
          KCFS: '露天开采',
        },
        geometry: { type: 'Polygon', coordinates: [] },
      },
    ],
  });

  assert.deepEqual(stats.mining_method_distribution, [
    { name: '未知开采方式', value: 2 },
    { name: '露天开采', value: 1 },
  ]);
  assert.equal(
    stats.recommended_panels.some((item) => item.key === 'mining_method_distribution'),
    false,
  );
});

test('buildDashboardStats output shape matches dashboard contract expected by Vue panels', () => {
  const stats = buildDashboardStats({ minesData: [] });

  assert.deepEqual(Object.keys(stats), [
    'overview',
    'city_distribution',
    'damage_type_distribution',
    'restoration_method_distribution',
    'mining_method_distribution',
    'city_area_distribution',
    'damage_type_area_distribution',
    'restoration_method_area_distribution',
    'mining_method_area_distribution',
    'recommended_panels',
  ]);

  assert.deepEqual(Object.keys(stats.overview), [
    'plot_total',
    'area_total',
    'treated_area',
    'untreated_area',
    'treated_area_ratio',
    'untreated_area_ratio',
  ]);
});
