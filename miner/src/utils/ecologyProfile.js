const DIAGNOSIS_METRICS = ['ndvi', 'fcv', 'lai', 'npp'];

export const MINE_ECOLOGY_TABS = [
  '修复诊断',
  'NDVI',
  'FCV',
  'LAI',
  'NPP',
  'LST',
  '土壤湿度',
  'TVDI',
  '气候背景',
  '模型研判',
  '基础资料',
];

export function selectEcologyChartPoints(points = [], interval = 2) {
  const validPoints = points
    .filter(
      (point) =>
        Number.isFinite(Number(point?.year)) &&
        point?.value !== null &&
        point?.value !== undefined &&
        point?.value !== '' &&
        Number.isFinite(Number(point.value))
    )
    .map((point) => ({ year: Number(point.year), value: Number(point.value) }))
    .sort((left, right) => left.year - right.year);

  const normalizedInterval = Number(interval) === 1 ? 1 : 2;
  const firstYear = validPoints[0]?.year;
  if (!Number.isFinite(firstYear)) return [];

  return validPoints.filter((point) => (point.year - firstYear) % normalizedInterval === 0);
}

export function summarizeEcologyMetric(metric = {}) {
  const validPoints = (metric.data || [])
    .filter(
      (point) => Number.isFinite(Number(point?.year)) && Number.isFinite(Number(point?.value))
    )
    .map((point) => ({ year: Number(point.year), value: Number(point.value) }))
    .sort((left, right) => left.year - right.year);

  if (!validPoints.length) {
    return {
      available: false,
      first: null,
      firstYear: null,
      latest: null,
      latestYear: null,
      delta: null,
    };
  }

  const firstPoint = validPoints[0];
  const latestPoint = validPoints[validPoints.length - 1];
  return {
    available: true,
    first: firstPoint.value,
    firstYear: firstPoint.year,
    latest: latestPoint.value,
    latestYear: latestPoint.year,
    delta: Number((latestPoint.value - firstPoint.value).toFixed(4)),
  };
}

export function buildDiagnosisCards(metrics = {}) {
  return DIAGNOSIS_METRICS.map((key) => {
    const metric = metrics[key] || {};
    const summary = summarizeEcologyMetric(metric);
    return {
      key,
      label: metric.label || key.toUpperCase(),
      unit: metric.unit || '',
      ...summary,
      trend: metric.mk_trend || null,
    };
  });
}
