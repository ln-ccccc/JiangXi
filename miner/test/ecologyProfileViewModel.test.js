import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildDiagnosisCards,
  MINE_ECOLOGY_TABS,
  selectEcologyChartPoints,
  summarizeEcologyMetric,
} from '../src/utils/ecologyProfile.js';

test('summarizeEcologyMetric uses the earliest and latest valid annual value', () => {
  const summary = summarizeEcologyMetric({
    data: [
      { year: 2025, value: 0.58 },
      { year: 2013, value: 0.21 },
      { year: 2018, value: null },
    ],
  });

  assert.deepEqual(summary, {
    available: true,
    first: 0.21,
    firstYear: 2013,
    latest: 0.58,
    latestYear: 2025,
    delta: 0.37,
  });
});

test('buildDiagnosisCards keeps missing metrics visible without inventing values', () => {
  const cards = buildDiagnosisCards({
    ndvi: {
      label: 'NDVI',
      unit: '',
      data: [
        { year: 2013, value: 0.21 },
        { year: 2025, value: 0.58 },
      ],
      mk_trend: 'upward',
    },
    fcv: {
      label: 'FCV',
      unit: '%',
      data: [],
      mk_trend: null,
    },
  });

  assert.equal(cards.length, 4);
  assert.deepEqual(cards[0], {
    key: 'ndvi',
    label: 'NDVI',
    unit: '',
    available: true,
    first: 0.21,
    firstYear: 2013,
    latest: 0.58,
    latestYear: 2025,
    delta: 0.37,
    trend: 'upward',
  });
  assert.deepEqual(cards[1], {
    key: 'fcv',
    label: 'FCV',
    unit: '%',
    available: false,
    first: null,
    firstYear: null,
    latest: null,
    latestYear: null,
    delta: null,
    trend: null,
  });
});

test('selectEcologyChartPoints shows a two-year sample beginning with the first valid year', () => {
  const points = Array.from({ length: 13 }, (_, index) => ({
    year: 2013 + index,
    value: index / 10,
  }));

  assert.deepEqual(
    selectEcologyChartPoints(points, 2).map((point) => point.year),
    [2013, 2015, 2017, 2019, 2021, 2023, 2025]
  );
});

test('selectEcologyChartPoints keeps every valid annual observation for an interval of one', () => {
  const points = [
    { year: 2015, value: 0.2 },
    { year: 2013, value: 0.1 },
    { year: 2014, value: null },
  ];

  assert.deepEqual(selectEcologyChartPoints(points, 1), [
    { year: 2013, value: 0.1 },
    { year: 2015, value: 0.2 },
  ]);
});

test('MINE_ECOLOGY_TABS keeps Jiangxi workbook indicators and excludes Yunnan legacy indices', () => {
  assert.ok(MINE_ECOLOGY_TABS.includes('TVDI'));
  assert.equal(MINE_ECOLOGY_TABS.includes('NDBI'), false);
  assert.equal(MINE_ECOLOGY_TABS.includes('NDWI'), false);
  assert.equal(MINE_ECOLOGY_TABS.includes('NDSI'), false);
});
