import assert from 'node:assert/strict';
import test from 'node:test';

import {
  parseEcologyWorkbookRows,
  buildEcologySeriesPayload,
  buildEcologyProfilePayload,
  parseEcologyProfileFid,
  parseEcologyProfileTbbh,
  hasEcologyAnnualData,
  resolveEcologyWorkbookPath,
} from '../services/ecologySeries.js';

test('parseEcologyWorkbookRows extracts yearly series by metric prefix', () => {
  const rows = [
    { FID: 101, TBBH: 'TBBH-101', NDVI_2013: 0.1, NDVI_2014: 0.2, FCV_2013: 0.3, FCV_2014: 0.5 },
  ];
  const result = parseEcologyWorkbookRows(rows);
  assert.deepEqual(result['TBBH-101'].ndvi.data, [
    { year: 2013, value: 0.1 },
    { year: 2014, value: 0.2 },
  ]);
  assert.deepEqual(result['TBBH-101'].fcv.data, [
    { year: 2013, value: 0.3 },
    { year: 2014, value: 0.5 },
  ]);
});

test('buildEcologySeriesPayload returns missing message when mine has no yearly ecology data', () => {
  const payload = buildEcologySeriesPayload({
    tbbh: 'missing-tbbh',
    dataMap: {},
  });
  assert.equal(payload.tbbh, 'missing-tbbh');
  assert.equal(payload.ndvi.available, false);
  assert.match(payload.ndvi.message, /暂无该图斑年度数据/);
});

test('parseEcologyWorkbookRows preserves diagnostic fields and removes sentinel values', () => {
  const [profile] = Object.values(
    parseEcologyWorkbookRows([
      {
        FID: 0,
        TBBH: 'TBBH-0',
        NDVI_2013: 0.2,
        NDVI_2014: -9999,
        mean_temp_C_2013: 22.5,
        total_precip_mm_2013: 1200,
        elevation: 100,
        slope: 12,
        aspect: 180,
        土地利用类型: '林地',
        岩性: '花岗岩',
        预测修复类型: '工程修复',
        工程修复概率: 0.8,
        自然恢复概率: 0.2,
        预测置信度: 0.8,
        置信度等级: '高置信',
        恢复倾向等级: '强工程修复倾向',
        是否与原始修复模式一致: '一致',
        模型判别阈值: 0.6,
        复核建议: '可直接使用',
      },
    ])
  );

  assert.deepEqual(profile.ndvi.data, [{ year: 2013, value: 0.2 }]);
  assert.deepEqual(profile.mean_temp_c.data, [{ year: 2013, value: 22.5 }]);
  assert.equal(profile.context.elevation, 100);
  assert.equal(profile.context.land_use_type, '林地');
  assert.equal(profile.prediction.predicted_restoration_type, '工程修复');
  assert.equal(profile.prediction.engineering_probability, 0.8);
});

test('buildEcologyProfilePayload returns summary, completeness and stable metric shape', () => {
  const dataMap = parseEcologyWorkbookRows([
    {
      FID: 0,
      TBBH: 'TBBH-0',
      NDVI_2013: 0.2,
      NDVI_2015: 0.5,
      FCV_2013: 0.3,
      预测修复类型: '自然恢复',
    },
  ]);

  const payload = buildEcologyProfilePayload({ tbbh: 'TBBH-0', dataMap });

  assert.equal(payload.tbbh, 'TBBH-0');
  assert.equal(payload.excel_fid, 0);
  assert.deepEqual(payload.metrics.ndvi.first, { year: 2013, value: 0.2 });
  assert.deepEqual(payload.metrics.ndvi.latest, { year: 2015, value: 0.5 });
  assert.equal(payload.metrics.ndvi.delta, 0.3);
  assert.deepEqual(payload.metrics.ndvi.completeness.missing_years, [2014]);
  assert.equal(payload.metrics.ndvi.available, true);
  assert.equal(payload.metrics.lai.available, false);
  assert.equal(payload.prediction.predicted_restoration_type, '自然恢复');
  assert.equal(payload.data_quality.year_range.start, 2013);
  assert.equal(payload.data_quality.year_range.end, 2015);
});

test('parseEcologyProfileFid accepts only non-negative integer FIDs', () => {
  assert.equal(parseEcologyProfileFid('0'), 0);
  assert.equal(parseEcologyProfileFid('262'), 262);
  assert.equal(parseEcologyProfileFid('-1'), null);
  assert.equal(parseEcologyProfileFid('2.5'), null);
  assert.equal(parseEcologyProfileFid('mine-262'), null);
});

test('buildEcologyProfilePayload uses TBBH instead of the Excel FID', () => {
  const dataMap = parseEcologyWorkbookRows([
    { FID: 101, TBBH: 'ZJ3600000001', NDVI_2013: 0.2, NDVI_2025: 0.6 },
  ]);

  const payload = buildEcologyProfilePayload({ tbbh: 'ZJ3600000001', dataMap });

  assert.equal(payload.tbbh, 'ZJ3600000001');
  assert.equal(payload.excel_fid, 101);
  assert.equal(payload.metrics.ndvi.latest.value, 0.6);
  assert.equal(buildEcologyProfilePayload({ tbbh: '101', dataMap }), null);
});

test('parseEcologyProfileTbbh trims valid keys and rejects blank values', () => {
  assert.equal(parseEcologyProfileTbbh(' ZJ3600000001 '), 'ZJ3600000001');
  assert.equal(parseEcologyProfileTbbh(''), null);
  assert.equal(parseEcologyProfileTbbh('   '), null);
});

test('resolveEcologyWorkbookPath prioritizes an explicit environment path', () => {
  const resolved = resolveEcologyWorkbookPath({
    environmentPath: 'D:/mounted/ecology.xlsx',
    defaultPath: '/app/miner/data/default.xlsx',
    fallbackPath: 'D:/repo/data/fallback.xlsx',
    fileExists: () => false,
  });

  assert.deepEqual(resolved, {
    path: 'D:/mounted/ecology.xlsx',
    source: 'environment',
  });
});

test('resolveEcologyWorkbookPath uses a development fallback only when the default file is absent', () => {
  const resolved = resolveEcologyWorkbookPath({
    defaultPath: '/app/miner/data/default.xlsx',
    fallbackPath: 'D:/repo/data/fallback.xlsx',
    fileExists: (filePath) => filePath.endsWith('fallback.xlsx'),
  });

  assert.deepEqual(resolved, {
    path: 'D:/repo/data/fallback.xlsx',
    source: 'fallback',
  });
});

test('hasEcologyAnnualData requires at least one TBBH profile with yearly metric values', () => {
  assert.equal(hasEcologyAnnualData({}), false);
  assert.equal(hasEcologyAnnualData({ TBBH_3: { ndvi: { data: [] } } }), false);
  assert.equal(
    hasEcologyAnnualData({ TBBH_0: { ndvi: { data: [{ year: 2013, value: 0.2 }] } } }),
    true
  );
});
