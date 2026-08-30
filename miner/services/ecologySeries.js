export const ECOLOGY_METRICS = {
  ndvi: { label: 'NDVI', unit: '无量纲', prefixes: ['NDVI'] },
  fcv: { label: '植被覆盖度', unit: '比例（0-1）', prefixes: ['FCV'] },
  lai: { label: '叶面积指数', unit: 'm²/m²', prefixes: ['LAI'] },
  npp: { label: '净初级生产力', unit: 'gC/m²', prefixes: ['NPP'] },
  lst: { label: '地表温度', unit: '°C', prefixes: ['LST'] },
  sm_proxy: { label: '土壤湿度代理', unit: '比例（0-1）', prefixes: ['SM_proxy'] },
  tvdi_proxy: { label: '干旱指数代理', unit: '比例（0-1）', prefixes: ['TVDI_proxy'] },
  mean_temp_c: { label: '年均气温', unit: '°C', prefixes: ['mean_temp_C'] },
  total_precip_mm: { label: '年降水量', unit: 'mm', prefixes: ['total_precip_mm'] },
};

import { normalizeTbbh } from './jiangxiIdentity.js';

const BUSINESS_FIELDS = {
  province: '省市',
  city: '地市',
  county: '区县',
  mine_location: '矿山位置_',
  mine_code: '主体编号',
  plot_code: '图斑编号',
  restoration_plot_code: '修复图斑编',
  area: '面积',
  verified_area: '图斑核定面',
  plot_category: '图斑小类',
  restoration_status: '修复状态',
  restoration_mode: '修复模式',
  completion_date: '完成时间',
  project_name: '工程项目名',
  project_type: '工程项目类',
  actual_restoration_area: '实际修复面',
  untreated_area: '未治理面积',
  reporting_organization: '填报单位',
  reporter: '填报人',
  report_date: '填报日期',
  remark: '备注',
};

const CONTEXT_FIELDS = {
  longitude: '中心经度_',
  latitude: '中心纬度_',
  elevation: 'elevation',
  slope: 'slope',
  aspect: 'aspect',
  land_use_type: '土地利用类型',
  lithology: '岩性',
};

const PREDICTION_FIELDS = {
  predicted_restoration_type: '预测修复类型',
  engineering_probability: '工程修复概率',
  natural_recovery_probability: '自然恢复概率',
  confidence: '预测置信度',
  confidence_level: '置信度等级',
  recovery_tendency_level: '恢复倾向等级',
  matches_original_restoration_mode: '是否与原始修复模式一致',
  decision_threshold: '模型判别阈值',
  review_recommendation: '复核建议',
};

function normalizeValue(rawValue) {
  if (rawValue === null || rawValue === undefined || String(rawValue).trim() === '') return null;
  const numericValue = Number(rawValue);
  if (String(rawValue).trim() !== '' && Number.isFinite(numericValue)) {
    return numericValue === -9999 ? null : numericValue;
  }
  return typeof rawValue === 'string' ? rawValue.trim() : null;
}

function pickFields(row, fieldMap) {
  return Object.fromEntries(
    Object.entries(fieldMap).map(([key, column]) => [key, normalizeValue(row?.[column])])
  );
}

export function calculateSeriesStats(data = []) {
  const validData = data.filter(
    (item) => Number.isFinite(Number(item?.year)) && Number.isFinite(Number(item?.value))
  );
  const values = validData.map((item) => Number(item.value));
  if (!values.length) {
    return { mean: null, trend: null, mk_trend: '暂无' };
  }

  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  if (validData.length < 2) {
    return { mean: Number(mean.toFixed(3)), trend: 0, mk_trend: 'stable' };
  }

  const years = validData.map((item) => Number(item.year));
  const sumX = years.reduce((a, b) => a + b, 0);
  const sumY = values.reduce((a, b) => a + b, 0);
  const sumXY = years.reduce((acc, year, index) => acc + year * values[index], 0);
  const sumXX = years.reduce((acc, year) => acc + year * year, 0);
  const denom = validData.length * sumXX - sumX * sumX;
  const slope = denom !== 0 ? (validData.length * sumXY - sumX * sumY) / denom : 0;

  return {
    mean: Number(mean.toFixed(3)),
    trend: Number(slope.toFixed(5)),
    mk_trend: slope > 0.0005 ? 'upward' : slope < -0.0005 ? 'downward' : 'stable',
  };
}

function matchMetricByColumnName(columnName) {
  const normalized = String(columnName || '').trim();
  if (!normalized) return null;

  for (const [metricKey, config] of Object.entries(ECOLOGY_METRICS)) {
    const matched = config.prefixes.find((prefix) =>
      new RegExp(`^${prefix}_(19|20)\\d{2}$`, 'i').test(normalized)
    );
    if (matched) return metricKey;
  }
  return null;
}

function extractYear(columnName) {
  const match = String(columnName || '').match(/(19|20)\d{2}$/);
  if (!match) return null;
  const value = Number(match[0]);
  return Number.isFinite(value) ? value : null;
}

function createEmptyMetricGroup() {
  return Object.fromEntries(Object.keys(ECOLOGY_METRICS).map((key) => [key, { data: [] }]));
}

export function parseEcologyWorkbookRows(rows = []) {
  const result = {};

  for (const row of rows) {
    const fid = Number(row?.FID ?? row?.fid ?? row?.FID_1);
    if (!Number.isInteger(fid) || fid < 0) continue;
    let tbbh;
    try {
      tbbh = normalizeTbbh(row?.TBBH);
    } catch (_) {
      continue;
    }

    if (!result[tbbh]) {
      result[tbbh] = {
        tbbh,
        excel_fid: fid,
        ...createEmptyMetricGroup(),
        business: pickFields(row, BUSINESS_FIELDS),
        context: pickFields(row, CONTEXT_FIELDS),
        prediction: pickFields(row, PREDICTION_FIELDS),
      };
    }

    for (const [column, rawValue] of Object.entries(row || {})) {
      const metricKey = matchMetricByColumnName(column);
      if (!metricKey) continue;

      const year = extractYear(column);
      const value = normalizeValue(rawValue);
      if (!Number.isFinite(year) || !Number.isFinite(value)) continue;

      result[tbbh][metricKey].data.push({ year, value });
    }
  }

  for (const metricGroup of Object.values(result)) {
    Object.keys(ECOLOGY_METRICS).forEach((key) => {
      metricGroup[key].data.sort((a, b) => a.year - b.year);
    });
  }

  return result;
}

export function buildEcologySeriesPayload({ tbbh, dataMap = {} }) {
  let normalizedTbbh = null;
  try {
    normalizedTbbh = normalizeTbbh(tbbh);
  } catch (_) {
    // Keep the payload shape stable for a missing/invalid query.
  }
  const current = dataMap[normalizedTbbh] || {};
  const payload = { tbbh: normalizedTbbh || null };

  for (const [metricKey, config] of Object.entries(ECOLOGY_METRICS)) {
    const data = current[metricKey]?.data || [];
    const stats = calculateSeriesStats(data);
    payload[metricKey] = {
      label: config.label,
      unit: config.unit,
      data,
      ...stats,
      available: data.length > 0,
      message: data.length > 0 ? '' : '暂无该图斑年度数据',
    };
  }

  return payload;
}

function getYearRange(current) {
  const years = Object.keys(ECOLOGY_METRICS).flatMap((key) =>
    (current[key]?.data || []).map((item) => item.year)
  );
  if (!years.length) return { start: null, end: null };
  return { start: Math.min(...years), end: Math.max(...years) };
}

function buildMetricProfile({ config, data, expectedYears }) {
  const stats = calculateSeriesStats(data);
  const first = data[0] || null;
  const latest = data.at(-1) || null;
  const missingYears = expectedYears.filter((year) => !data.some((item) => item.year === year));
  const delta = first && latest ? Number((latest.value - first.value).toFixed(6)) : null;

  return {
    label: config.label,
    unit: config.unit,
    data,
    first,
    latest,
    delta,
    ...stats,
    available: data.length > 0,
    completeness: {
      available_years: data.length,
      expected_years: expectedYears.length,
      missing_years: missingYears,
      coverage: expectedYears.length ? Number((data.length / expectedYears.length).toFixed(3)) : 0,
    },
  };
}

export function buildEcologyProfilePayload({ tbbh, dataMap = {} }) {
  const normalizedTbbh = parseEcologyProfileTbbh(tbbh);
  const current = normalizedTbbh ? dataMap[normalizedTbbh] : null;
  if (!current) return null;

  const yearRange = getYearRange(current);
  const expectedYears =
    yearRange.start === null
      ? []
      : Array.from(
          { length: yearRange.end - yearRange.start + 1 },
          (_, index) => yearRange.start + index
        );
  const metrics = Object.fromEntries(
    Object.entries(ECOLOGY_METRICS).map(([key, config]) => [
      key,
      buildMetricProfile({ config, data: current[key]?.data || [], expectedYears }),
    ])
  );
  const availableMetrics = Object.entries(metrics)
    .filter(([, metric]) => metric.available)
    .map(([key]) => key);

  return {
    tbbh: normalizedTbbh,
    excel_fid: current.excel_fid,
    metrics,
    business: current.business || {},
    context: current.context || {},
    prediction: current.prediction || {},
    data_quality: {
      year_range: yearRange,
      available_metrics: availableMetrics,
      metric_count: availableMetrics.length,
    },
  };
}

export function parseEcologyProfileFid(value) {
  if (typeof value !== 'string' || !/^(0|[1-9]\d*)$/.test(value)) return null;
  const fid = Number(value);
  return Number.isSafeInteger(fid) ? fid : null;
}

export function parseEcologyProfileTbbh(value) {
  if (typeof value !== 'string') return null;
  try {
    return normalizeTbbh(value);
  } catch (_) {
    return null;
  }
}

export function resolveEcologyWorkbookPath({
  environmentPath,
  defaultPath,
  fallbackPath,
  fileExists,
}) {
  if (environmentPath) {
    return { path: environmentPath, source: 'environment' };
  }
  if (fileExists(defaultPath)) {
    return { path: defaultPath, source: 'default' };
  }
  if (fallbackPath && fileExists(fallbackPath)) {
    return { path: fallbackPath, source: 'fallback' };
  }
  return { path: defaultPath, source: 'default' };
}

export function hasEcologyAnnualData(dataMap = {}) {
  return Object.entries(dataMap).some(
    ([tbbh, profile]) =>
      Boolean(String(tbbh).trim()) &&
      Object.keys(ECOLOGY_METRICS).some((key) => profile?.[key]?.data?.length > 0)
  );
}
