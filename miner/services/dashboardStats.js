function normalizeBucket(value, fallback) {
  const text = String(value || '').trim();
  return text || fallback;
}

function toFiniteNumber(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
}

function sortEntries(statsMap, digits = 0) {
  return Object.entries(statsMap)
    .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0], 'zh-CN'))
    .map(([name, value]) => ({
      name,
      value: digits > 0 ? Number(value.toFixed(digits)) : value,
    }));
}

function incrementBucket(statsMap, key, delta = 1) {
  statsMap[key] = (statsMap[key] || 0) + delta;
}

function isUnknownBucket(name) {
  return /未知|未标注|暂无/.test(String(name || '').trim());
}

function isDistributionInformative(list) {
  if (!Array.isArray(list) || list.length < 2) return false;

  const unknownTotal = list
    .filter((item) => isUnknownBucket(item.name))
    .reduce((sum, item) => sum + toFiniteNumber(item.value), 0);

  const knownItems = list.filter((item) => !isUnknownBucket(item.name) && toFiniteNumber(item.value) > 0);
  const knownTotal = knownItems.reduce((sum, item) => sum + toFiniteNumber(item.value), 0);

  if (knownItems.length >= 2) return true;
  if (knownItems.length === 0) return false;
  return knownTotal > unknownTotal;
}

function makePanel({ key, title, unit, metric, data }) {
  return {
    key,
    title,
    unit,
    metric,
    data,
  };
}

export function buildDashboardStats({ minesData = [] } = {}) {
  let areaTotal = 0;
  let treatedArea = 0;
  let untreatedArea = 0;

  const cityCountStats = {};
  const damageTypeCountStats = {};
  const restorationMethodCountStats = {};
  const miningMethodCountStats = {};

  const cityAreaStats = {};
  const damageTypeAreaStats = {};
  const restorationMethodAreaStats = {};
  const miningMethodAreaStats = {};

  for (const feature of minesData) {
    const p = feature?.properties || {};
    const area = toFiniteNumber(p.area || p.TBTYMJ || p.TBTYMJ_1);
    areaTotal += area;

    const status = String(p.status_normalized || '').trim().toLowerCase();
    if (status === 'treated') treatedArea += area;
    if (status === 'untreated') untreatedArea += area;

    const city = normalizeBucket(p.SHI || p.city || p['地市'], '未标注地市');
    const damageType = normalizeBucket(p.STWT, '未知图斑类型');
    const restorationMethod = normalizeBucket(p.NXFFS, '未知修复方式');
    const miningMethod = normalizeBucket(p.KCFS, '未知开采方式');

    incrementBucket(cityCountStats, city, 1);
    incrementBucket(damageTypeCountStats, damageType, 1);
    incrementBucket(restorationMethodCountStats, restorationMethod, 1);
    incrementBucket(miningMethodCountStats, miningMethod, 1);

    incrementBucket(cityAreaStats, city, area);
    incrementBucket(damageTypeAreaStats, damageType, area);
    incrementBucket(restorationMethodAreaStats, restorationMethod, area);
    incrementBucket(miningMethodAreaStats, miningMethod, area);
  }

  const cityDistribution = sortEntries(cityCountStats);
  const damageTypeDistribution = sortEntries(damageTypeCountStats);
  const restorationMethodDistribution = sortEntries(restorationMethodCountStats);
  const miningMethodDistribution = sortEntries(miningMethodCountStats);

  const cityAreaDistribution = sortEntries(cityAreaStats, 2).map((item) => ({
    ...item,
    value: Number((item.value / 10000).toFixed(2)),
  }));
  const damageTypeAreaDistribution = sortEntries(damageTypeAreaStats, 2).map((item) => ({
    ...item,
    value: Number((item.value / 10000).toFixed(2)),
  }));
  const restorationMethodAreaDistribution = sortEntries(restorationMethodAreaStats, 2).map((item) => ({
    ...item,
    value: Number((item.value / 10000).toFixed(2)),
  }));
  const miningMethodAreaDistribution = sortEntries(miningMethodAreaStats, 2).map((item) => ({
    ...item,
    value: Number((item.value / 10000).toFixed(2)),
  }));

  const recommendedPanels = [
    makePanel({
      key: 'city_distribution',
      title: '地市图斑分布',
      unit: '个',
      metric: 'count',
      data: cityDistribution,
    }),
    makePanel({
      key: 'damage_type_distribution',
      title: '图斑类型分布',
      unit: '个',
      metric: 'count',
      data: damageTypeDistribution,
    }),
    makePanel({
      key: 'restoration_method_area_distribution',
      title: '修复方式面积分布',
      unit: '公顷',
      metric: 'area',
      data: restorationMethodAreaDistribution,
    }),
    makePanel({
      key: 'city_area_distribution',
      title: '地市面积分布',
      unit: '公顷',
      metric: 'area',
      data: cityAreaDistribution,
    }),
    makePanel({
      key: 'mining_method_distribution',
      title: '开采方式分布',
      unit: '个',
      metric: 'count',
      data: miningMethodDistribution,
    }),
  ].filter((panel) => isDistributionInformative(panel.data));

  return {
    overview: {
      plot_total: minesData.length,
      area_total: Number(areaTotal.toFixed(2)),
      treated_area: Number(treatedArea.toFixed(2)),
      untreated_area: Number(untreatedArea.toFixed(2)),
      treated_area_ratio: areaTotal > 0 ? Number((treatedArea / areaTotal).toFixed(4)) : 0,
      untreated_area_ratio: areaTotal > 0 ? Number((untreatedArea / areaTotal).toFixed(4)) : 0,
    },
    city_distribution: cityDistribution,
    damage_type_distribution: damageTypeDistribution,
    restoration_method_distribution: restorationMethodDistribution,
    mining_method_distribution: miningMethodDistribution,
    city_area_distribution: cityAreaDistribution,
    damage_type_area_distribution: damageTypeAreaDistribution,
    restoration_method_area_distribution: restorationMethodAreaDistribution,
    mining_method_area_distribution: miningMethodAreaDistribution,
    recommended_panels: recommendedPanels,
  };
}
