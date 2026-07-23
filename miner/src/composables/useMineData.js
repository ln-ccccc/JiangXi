import { ref } from 'vue';
import axios from 'axios';

const rawMinerApiBase = import.meta.env.VITE_MINER_API_BASE_URL;
const MINER_API_BASE_URL = rawMinerApiBase ? String(rawMinerApiBase).replace(/\/$/, '') : '';
const apiUrl = (path) => `${MINER_API_BASE_URL}${path}`;
const buildEmptyIndexEntry = () => ({
  mean: null,
  trend: null,
  mk_trend: '暂无',
  data: [],
  available: true,
  message: '',
  reason: null,
  source_file: '',
});

const buildEmptyEcologyEntry = (label = '') => ({
  label,
  mean: null,
  trend: null,
  mk_trend: '暂无',
  data: [],
  available: false,
  message: '暂无该图斑年度数据',
});

const buildEmptyEcologySeries = () => ({
  ndvi: buildEmptyEcologyEntry('NDVI'),
  fcv: buildEmptyEcologyEntry('FCV'),
  lai: buildEmptyEcologyEntry('LAI'),
  npp: buildEmptyEcologyEntry('NPP'),
  lst: buildEmptyEcologyEntry('LST'),
  sm_proxy: buildEmptyEcologyEntry('土壤湿度代理'),
  tvdi_proxy: buildEmptyEcologyEntry('干旱指数代理'),
});

const buildEmptyEcologyProfile = () => ({
  metrics: {},
  context: {},
  prediction: {},
  data_quality: {},
});

const sortZhText = (values) =>
  Array.from(values)
    .filter(Boolean)
    .sort((a, b) => String(a).localeCompare(String(b), 'zh-CN'));

export function useMineData() {
  const allMinesData = ref([]);
  const filteredMinesData = ref([]);

  const filterCity = ref('');
  const filterStatus = ref('');
  const filterMethod = ref('');
  const searchMineId = ref('');

  const cityOptions = ref([]);
  const miningMethodOptions = ref([]);

  const plotTotal = ref(0);
  const plotAreaTotal = ref(0);
  const treatedArea = ref(0);
  const untreatedArea = ref(0);
  const treatedAreaRatio = ref(0);
  const untreatedAreaRatio = ref(0);

  const cityDistribution = ref([]);
  const damageTypeDistribution = ref([]);
  const restorationMethodDistribution = ref([]);
  const miningMethodDistribution = ref([]);
  const recommendedPanels = ref([]);

  const mineIndices = ref({
    ndvi: buildEmptyIndexEntry(),
    ndbi: buildEmptyIndexEntry(),
    ndwi: buildEmptyIndexEntry(),
    ndsi: buildEmptyIndexEntry(),
  });

  const mineEcologySeries = ref(buildEmptyEcologySeries());
  const mineEcologyProfile = ref(buildEmptyEcologyProfile());
  const ecologyProfileLoading = ref(false);
  const ecologyProfileError = ref('');
  const mineChangeDetails = ref(null);
  const inferenceRunning = ref(false);
  const inferenceResult = ref(null);
  const inferenceError = ref('');
  const dataLoadError = ref('');
  const trendReportLoading = ref(false);
  const trendReportError = ref('');
  const trendReport = ref(null);

  const loadData = async () => {
    dataLoadError.value = '';
    try {
      const statsRes = await axios.get(apiUrl('/api/stats'));
      const stats = statsRes.data || {};
      const overview = stats.overview || {};

      plotTotal.value = Number(overview.plot_total || 0);
      plotAreaTotal.value = Number(overview.area_total || 0);
      treatedArea.value = Number(overview.treated_area || 0);
      untreatedArea.value = Number(overview.untreated_area || 0);
      treatedAreaRatio.value = Number(overview.treated_area_ratio || 0);
      untreatedAreaRatio.value = Number(overview.untreated_area_ratio || 0);

      cityDistribution.value = stats.city_distribution || [];
      damageTypeDistribution.value = stats.damage_type_distribution || [];
      restorationMethodDistribution.value = stats.restoration_method_distribution || [];
      miningMethodDistribution.value = stats.mining_method_distribution || [];
      recommendedPanels.value = stats.recommended_panels || [];

      const geoRes = await axios.get(apiUrl('/api/geojson'));
      if (geoRes.data && geoRes.data.features) {
        allMinesData.value = geoRes.data.features;

        const cities = new Set();
        const methods = new Set();
        allMinesData.value.forEach((f) => {
          const p = f.properties || {};
          const city = p.SHI || p.city || p['地市'] || '';
          const method = p.KCFS || p['开采方式'] || '';
          if (city) cities.add(city);
          if (method) methods.add(method);
        });
        cityOptions.value = sortZhText(cities);
        miningMethodOptions.value = sortZhText(methods);

        applyFilters();
      }
    } catch (e) {
      console.error('Data load error:', e);
      dataLoadError.value =
        e?.response?.data?.error || e?.message || '矿山数据加载失败，请检查 Miner API 服务';
    }
  };

  const applyFilters = () => {
    filteredMinesData.value = allMinesData.value.filter((f) => {
      const p = f.properties || {};
      const cityMatch =
        !filterCity.value || (p.SHI || p.city || p['地市'] || '') === filterCity.value;
      const methodMatch =
        !filterMethod.value || (p.KCFS || p['开采方式'] || '') === filterMethod.value;

      let statusMatch = true;
      if (filterStatus.value) {
        const norm = p.status_normalized || 'unknown';
        statusMatch = norm === filterStatus.value;
      }

      let searchMatch = true;
      if (searchMineId.value) {
        const q = searchMineId.value.toLowerCase();
        const idMatch = String(p.FID_1) === q;
        const nameText = String(p.mine_name || p.name || '').toLowerCase();
        const nameMatch = nameText.includes(q);
        searchMatch = idMatch || nameMatch;
      }

      return cityMatch && methodMatch && statusMatch && (searchMineId.value ? searchMatch : true);
    });
  };

  const resetFilters = () => {
    filterCity.value = '';
    filterStatus.value = '';
    filterMethod.value = '';
    searchMineId.value = '';
    applyFilters();
  };

  const fetchIndices = async (fid) => {
    try {
      const res = await axios.get(apiUrl(`/api/mines/indices?fid=${fid}`));
      const merged = res.data || {};

      try {
        const liveRes = await axios.get(apiUrl(`/api/geoview/spectral_live/${fid}`));
        const live = (liveRes.data && liveRes.data.data && liveRes.data.data.indices) || {};
        ['ndvi', 'ndbi', 'ndwi', 'ndsi'].forEach((key) => {
          if (!Array.isArray(live[key]) || live[key].length === 0) return;
          const base = merged[key] && Array.isArray(merged[key].data) ? [...merged[key].data] : [];
          const yearToItem = new Map(
            base.map((item) => [Number(item.year), { ...item, source: item.source || 'xlsx' }])
          );
          live[key].forEach((item) => {
            const y = Number(item.year);
            const v = Number(item.value);
            if (Number.isFinite(y) && Number.isFinite(v)) {
              yearToItem.set(y, {
                year: y,
                value: v,
                source: 'live',
                computed_at: item.computed_at || null,
              });
            }
          });
          const data = Array.from(yearToItem.values()).sort((a, b) => a.year - b.year);
          const values = data.map((d) => Number(d.value)).filter((v) => Number.isFinite(v));
          const mean = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
          let trend = 0;
          if (data.length >= 2) {
            const n = data.length;
            const years = data.map((d) => Number(d.year));
            const vals = data.map((d) => Number(d.value));
            const sumX = years.reduce((a, b) => a + b, 0);
            const sumY = vals.reduce((a, b) => a + b, 0);
            const sumXY = years.reduce((acc, x, i) => acc + x * vals[i], 0);
            const sumXX = years.reduce((acc, x) => acc + x * x, 0);
            const denom = n * sumXX - sumX * sumX;
            trend = denom !== 0 ? (n * sumXY - sumX * sumY) / denom : 0;
          }
          merged[key] = {
            ...(merged[key] || {}),
            data,
            mean: Number(mean.toFixed(3)),
            trend: Number(trend.toFixed(5)),
            mk_trend: trend > 0.0005 ? 'upward' : trend < -0.0005 ? 'downward' : 'stable',
            available: true,
            reason: null,
            message: '',
          };
        });
      } catch (_) {
        // live overlay 不可用时保留 miner 基线数据。
      }

      mineIndices.value = merged;
    } catch (e) {
      console.warn('No indices data for FID:', fid);
      mineIndices.value = {
        ndvi: buildEmptyIndexEntry(),
        ndbi: buildEmptyIndexEntry(),
        ndwi: buildEmptyIndexEntry(),
        ndsi: buildEmptyIndexEntry(),
      };
    }
  };

  const fetchEcologySeries = async (fid) => {
    try {
      const res = await axios.get(apiUrl(`/api/mines/ecology-series?fid=${fid}`));
      const payload = res.data || {};
      mineEcologySeries.value = {
        ndvi: payload.ndvi || buildEmptyEcologyEntry('NDVI'),
        fcv: payload.fcv || buildEmptyEcologyEntry('FCV'),
        lai: payload.lai || buildEmptyEcologyEntry('LAI'),
        npp: payload.npp || buildEmptyEcologyEntry('NPP'),
        lst: payload.lst || buildEmptyEcologyEntry('LST'),
        sm_proxy: payload.sm_proxy || buildEmptyEcologyEntry('土壤湿度代理'),
        tvdi_proxy: payload.tvdi_proxy || buildEmptyEcologyEntry('干旱指数代理'),
      };
    } catch (_) {
      mineEcologySeries.value = buildEmptyEcologySeries();
    }
  };

  const fetchEcologyProfile = async (tbbh) => {
    ecologyProfileLoading.value = true;
    ecologyProfileError.value = '';
    mineEcologyProfile.value = buildEmptyEcologyProfile();
    try {
      const normalizedTbbh = String(tbbh || '').trim();
      if (!normalizedTbbh) throw new Error('该图斑缺少 TBBH，无法关联生态资料');
      const response = await axios.get(
        apiUrl(`/api/mines/ecology-profile?tbbh=${encodeURIComponent(normalizedTbbh)}`)
      );
      mineEcologyProfile.value = {
        ...buildEmptyEcologyProfile(),
        ...(response.data || {}),
      };
    } catch (error) {
      const message = error?.response?.data?.error || error.message || '生态诊断资料加载失败';
      ecologyProfileError.value = message;
    } finally {
      ecologyProfileLoading.value = false;
    }
  };

  const fetchTrendReport = async (filters = {}) => {
    trendReportLoading.value = true;
    trendReportError.value = '';
    try {
      const class_name = filters.class_name || 'bareground';
      const direction = filters.direction || 'all';
      const res = await axios.get(apiUrl('/api/mines/trend-report'), {
        params: { class_name, direction },
      });
      trendReport.value = res.data || null;
      return trendReport.value;
    } catch (e) {
      trendReportError.value = e?.response?.data?.error || e?.message || '趋势统计加载失败';
      throw e;
    } finally {
      trendReportLoading.value = false;
    }
  };

  const exportTrendReport = async () => {
    const rows = trendReport.value?.tables?.selected_class_rows || [];
    const header = [
      'FID',
      'MineName',
      'StartYear',
      'EndYear',
      'StartPercent',
      'EndPercent',
      'DeltaPercent',
      'StartAreaKm2',
      'EndAreaKm2',
      'DeltaAreaKm2',
    ];
    const lines = [header.join(',')];
    rows.forEach((r) => {
      lines.push(
        [
          r.fid ?? '',
          `"${(r.mine_name || '').replace(/"/g, '""')}"`,
          r.start_year ?? '',
          r.end_year ?? '',
          r.start_percent ?? '',
          r.end_percent ?? '',
          r.delta_percent ?? '',
          r.start_area_km2 ?? '',
          r.end_area_km2 ?? '',
          r.delta_area_km2 ?? '',
        ].join(',')
      );
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trend_report_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const deleteMines = async () => {
    throw new Error('当前 miner 后端不支持删除矿山');
  };

  const runKmlRoiInference = async ({
    oldTifPath,
    newTifPath,
    kmlPath = '',
    device = 'auto',
    limit = 0,
    year = '',
    oldYear = '',
    newYear = '',
  } = {}) => {
    inferenceRunning.value = true;
    inferenceError.value = '';
    inferenceResult.value = null;
    try {
      const payload = {
        old_tif_path: oldTifPath,
        new_tif_path: newTifPath || oldTifPath,
        device,
        limit,
      };
      if (kmlPath) payload.kml_path = kmlPath;
      if (year) payload.year = year;
      if (oldYear) payload.old_year = oldYear;
      if (newYear) payload.new_year = newYear;
      const res = await axios.post(apiUrl('/api/inference/kml-roi'), payload);
      inferenceResult.value = res.data;
      return res.data;
    } catch (e) {
      inferenceError.value = e?.response?.data?.error || e?.message || '推理任务执行失败';
      throw e;
    } finally {
      inferenceRunning.value = false;
    }
  };

  const formatMaybeNumber = (v, d = 2) => {
    const n = Number(v);
    return Number.isFinite(n) ? n.toFixed(d) : '--';
  };

  const formatTrend = (v) => {
    const n = Number(v);
    if (!Number.isFinite(n)) return '--';
    return n > 0 ? `+${n.toFixed(4)}` : `${n.toFixed(4)}`;
  };

  const getTrendClass = (v) => {
    const n = Number(v);
    if (!Number.isFinite(n)) return '';
    return n > 0 ? 'text-green' : n < 0 ? 'text-red' : '';
  };

  return {
    allMinesData,
    filteredMinesData,
    filterCity,
    filterStatus,
    filterMethod,
    searchMineId,
    cityOptions,
    miningMethodOptions,
    plotTotal,
    plotAreaTotal,
    treatedArea,
    untreatedArea,
    treatedAreaRatio,
    untreatedAreaRatio,
    cityDistribution,
    damageTypeDistribution,
    restorationMethodDistribution,
    miningMethodDistribution,
    recommendedPanels,
    mineIndices,
    mineEcologySeries,
    mineEcologyProfile,
    ecologyProfileLoading,
    ecologyProfileError,
    mineChangeDetails,
    dataLoadError,
    inferenceRunning,
    inferenceResult,
    inferenceError,
    trendReportLoading,
    trendReportError,
    trendReport,
    loadData,
    applyFilters,
    resetFilters,
    fetchIndices,
    fetchEcologySeries,
    fetchEcologyProfile,
    runKmlRoiInference,
    fetchTrendReport,
    exportTrendReport,
    deleteMines,
    formatMaybeNumber,
    formatTrend,
    getTrendClass,
  };
}
