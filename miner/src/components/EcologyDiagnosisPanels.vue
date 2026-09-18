<template>
  <section v-if="loading" class="state-panel">正在加载生态诊断资料…</section>
  <section v-else-if="error" class="state-panel error">{{ error }}</section>
  <section v-else-if="tab === '修复诊断'" class="panel-stack">
    <div class="official-summary">
      <div>
        <span>台账治理状态</span><strong>{{ mineData.status_raw || '暂无' }}</strong>
      </div>
      <div>
        <span>台账修复方式</span><strong>{{ mineData.restoration_method || '暂无' }}</strong>
      </div>
      <div>
        <span>AI 辅助研判</span
        ><strong>{{ prediction.predicted_restoration_type || '暂无' }}</strong>
      </div>
      <div>
        <span>预测置信度</span><strong>{{ formatPercent(prediction.confidence) }}</strong>
      </div>
    </div>
    <p class="notice">AI 辅助研判不替代台账中的正式治理状态与修复方式。</p>
    <div class="metric-grid">
      <article v-for="card in diagnosisCards" :key="card.key" class="metric-card">
        <span>{{ card.label }}</span>
        <strong>{{ card.available ? formatMetric(card.latest, card.unit) : '暂无数据' }}</strong>
        <small v-if="card.available"
          >{{ card.latestYear }} 年 · 较 {{ card.firstYear }} 年
          {{ formatDelta(card.delta, card.unit) }}</small
        >
        <small v-if="card.available">趋势：{{ formatTrend(card.trend) }}</small>
        <small v-else>不插值、不补值</small>
      </article>
    </div>
    <div class="review-box">
      <span>复核建议</span><strong>{{ prediction.review_recommendation || '暂无' }}</strong>
    </div>
  </section>
  <section v-else-if="ecologyMetricKey" class="panel-stack">
    <p class="source-note">数据源：348 图斑 TableMERNet 无图像预测结果工作簿。</p>
    <div class="chart-sampling" aria-label="趋势图采样间隔">
      <span>趋势采样</span>
      <button :class="{ active: chartSamplingInterval === 2 }" @click="chartSamplingInterval = 2">
        每 2 年
      </button>
      <button :class="{ active: chartSamplingInterval === 1 }" @click="chartSamplingInterval = 1">
        逐年
      </button>
    </div>
    <TrendChart :metric="activeMetric" :sampling-interval="chartSamplingInterval" />
    <AnnualDataTable :metric="activeMetric" />
  </section>
  <section v-else-if="tab === '地物分类'" class="panel-stack">
    <div v-if="classificationState.loading" class="state-panel">正在加载地物分类推理结果…</div>
    <div v-else-if="classificationState.error" class="state-panel error">
      {{ classificationState.error }}
    </div>
    <template v-else-if="classificationState.data">
      <div class="source-badge">Source: 同步分析推理产物</div>
      <div v-if="classificationItems.length" class="classification-container">
        <div v-for="item in classificationItems" :key="item.key" class="class-image-box">
          <div class="class-title">{{ item.title }}（{{ item.year ?? '未知年份' }}）</div>
          <div class="class-image-wrapper">
            <img
              :src="item.url"
              :alt="`${item.title}分类结果`"
              class="class-image"
              loading="lazy"
            />
            <div class="class-year-label">{{ item.year ?? '未知' }}</div>
          </div>
        </div>
        <div v-if="classificationItems.length === 1" class="no-data">暂无可比较的前期分类结果</div>
      </div>
      <p v-else class="no-data">暂无地物分类结果</p>
      <div v-if="classificationMatrix" class="matrix-container">
        <table class="confusion-matrix">
          <thead>
            <tr>
              <th class="corner-cell">
                <div class="corner-old">{{ matrixYearLabels.old }}</div>
                <div class="corner-new">{{ matrixYearLabels.new }}</div>
              </th>
              <th v-for="h in classificationMatrix.col_labels" :key="h">{{ classZh(h) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in classificationMatrix.rows" :key="rowIndex">
              <td class="row-label">{{ classZh(classificationMatrix.row_labels[rowIndex]) }}</td>
              <td
                v-for="(val, colIndex) in row"
                :key="colIndex"
                class="matrix-cell"
                :style="{ backgroundColor: getHeatmapColor(Number(val)) }"
              >
                {{ Number(val).toFixed(1) }}%
              </td>
            </tr>
          </tbody>
        </table>
        <div class="matrix-legend">
          <span>0%</span>
          <div class="legend-bar"></div>
          <span>100%</span>
        </div>
      </div>
      <p v-else class="no-data">暂无混淆矩阵数据（需要至少两期分类结果）。</p>
    </template>
  </section>
  <section v-else-if="environmentMetricKey" class="panel-stack">
    <p class="source-note">
      数据源：TableMERNet；土壤湿度与 TVDI 为代理指标，用于辅助判断环境背景。
    </p>
    <ClimateChart
      v-if="environmentMetricKey === 'climate'"
      :temperature="metrics.mean_temp_c"
      :precipitation="metrics.total_precip_mm"
    />
    <template v-else>
      <div class="chart-sampling" aria-label="趋势图采样间隔">
        <span>趋势采样</span>
        <button :class="{ active: chartSamplingInterval === 2 }" @click="chartSamplingInterval = 2">
          每 2 年
        </button>
        <button :class="{ active: chartSamplingInterval === 1 }" @click="chartSamplingInterval = 1">
          逐年
        </button>
      </div>
      <TrendChart :metric="activeMetric" :sampling-interval="chartSamplingInterval" />
    </template>
    <div class="context-grid">
      <div v-for="item in contextItems" :key="item.label">
        <span>{{ item.label }}</span
        ><strong>{{ item.value || '暂无' }}</strong>
      </div>
    </div>
    <template v-if="environmentMetricKey === 'climate'">
      <AnnualDataTable :metric="metrics.mean_temp_c || {}" />
      <AnnualDataTable :metric="metrics.total_precip_mm || {}" />
    </template>
    <AnnualDataTable v-else :metric="activeMetric" />
  </section>
  <section v-else class="panel-stack">
    <p class="notice">以下结果为 AI 辅助研判，不替代台账核定信息。</p>
    <div class="prediction-grid">
      <div v-for="item in predictionItems" :key="item.label">
        <span>{{ item.label }}</span
        ><strong>{{ item.value || '暂无' }}</strong>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import * as echarts from 'echarts';
import axios from 'axios';
import { buildDiagnosisCards, selectEcologyChartPoints } from '../utils/ecologyProfile.js';

const props = defineProps({
  tab: { type: String, required: true },
  mineData: { type: Object, default: () => ({}) },
  profile: { type: Object, default: () => ({}) },
  loading: Boolean,
  error: { type: String, default: '' },
});

const CLASSIFICATION_ZH = {
  grassland: '草地',
  forest: '林地',
  building: '建筑',
  road: '道路',
  bareground: '裸地',
  water: '水体',
};
const classZh = (name) => CLASSIFICATION_ZH[String(name || '').trim()] || name;

const classificationState = ref({ loading: false, error: '', data: null });
const classificationApiBase = import.meta.env.VITE_MINER_API_BASE_URL
  ? String(import.meta.env.VITE_MINER_API_BASE_URL).replace(/\/$/, '')
  : '';

const loadClassification = async () => {
  const tbbh = props.mineData?.tbbh;
  if (!tbbh) return;
  const requestTbbh = String(tbbh);
  classificationState.value = { loading: true, error: '', data: null };
  try {
    const res = await axios.get(
      `${classificationApiBase}/api/inference/classification/${encodeURIComponent(requestTbbh)}`
    );
    // 过期响应守卫：快速切换图斑时，慢响应不得覆盖新图斑的数据
    if (String(props.mineData?.tbbh) !== requestTbbh) return;
    classificationState.value = { loading: false, error: '', data: res?.data?.data || null };
  } catch (err) {
    classificationState.value = {
      loading: false,
      error: err?.response?.data?.error || '地物分类推理结果加载失败',
      data: null,
    };
  }
};

const classificationItems = computed(() => {
  const data = classificationState.value.data;
  if (!data) return [];
  const years = data.years || [];
  // 无年份推理产物只有 pair（_old/_new）没有 +YYYY 掩膜：年份缺省显示「未知年份」
  if (data.pair.old_url && (years.length >= 2 || !years.length)) {
    const oldYear = years[0].year;
    const newYear = years[years.length - 1].year;
    return [
      { key: 'old', title: '前期地物分类', year: oldYear, url: data.pair.old_url },
      {
        key: 'new',
        title: '当前地物分类',
        year: newYear,
        url: data.pair.new_url || years[years.length - 1].result_url,
      },
    ];
  }
  return years.map((item) => ({
    key: String(item.year),
    title: '地物分类',
    year: item.year,
    url: item.result_url,
  }));
});

const classificationMatrix = computed(() => {
  const data = classificationState.value.data;
  if (!data) return null;
  const matrix = data.confusion_matrix?.percent_rownorm || null;
  if (!matrix || matrix.rows.length < 2) return null;
  return matrix;
});

const matrixYearLabels = computed(() => {
  const years = classificationState.value.data?.years || [];
  if (years.length >= 2) {
    return { old: `${years[0].year}（基准期）`, new: `${years[years.length - 1].year}（最新期）` };
  }
  return { old: '前期', new: '当前' };
});

const getHeatmapColor = (val) => {
  const opacity = Math.min(Math.max(val, 0) / 100, 1);
  return `rgba(78, 205, 196, ${opacity * 0.8})`;
};

watch(
  () => [props.tab, props.mineData?.tbbh],
  ([tab]) => {
    if (tab === '地物分类') loadClassification();
  },
  { immediate: true }
);

const metrics = computed(() => props.profile?.metrics || {});
const ecologyMetricKey = computed(
  () => ({ NDVI: 'ndvi', FCV: 'fcv', LAI: 'lai', NPP: 'npp' }[props.tab] || '')
);
const environmentMetricKey = computed(
  () =>
    ({ LST: 'lst', 土壤湿度: 'sm_proxy', TVDI: 'tvdi_proxy', 气候背景: 'climate' }[props.tab] || '')
);
const prediction = computed(() => props.profile?.prediction || {});
const diagnosisCards = computed(() => buildDiagnosisCards(metrics.value));
const chartSamplingInterval = ref(2);
const activeMetric = computed(() => {
  const key = ecologyMetricKey.value || environmentMetricKey.value;
  return metrics.value[key] || { label: key, data: [] };
});
const contextItems = computed(() => {
  const context = props.profile?.context || {};
  return [
    ['海拔', context.elevation],
    ['坡度', context.slope],
    ['坡向', context.aspect],
    ['土地利用类型', context.land_use_type],
    ['岩性', context.lithology],
  ].map(([label, value]) => ({ label, value }));
});
const predictionItems = computed(() =>
  [
    ['预测修复类型', prediction.value.predicted_restoration_type],
    ['工程修复概率', formatPercent(prediction.value.engineering_probability)],
    ['自然恢复概率', formatPercent(prediction.value.natural_recovery_probability)],
    ['预测置信度', formatPercent(prediction.value.confidence)],
    ['置信度等级', prediction.value.confidence_level],
    ['恢复倾向等级', prediction.value.recovery_tendency_level],
    ['与台账修复方式一致', prediction.value.matches_original_restoration_mode],
    ['模型判别阈值', prediction.value.decision_threshold],
    ['复核建议', prediction.value.review_recommendation],
  ].map(([label, value]) => ({ label, value }))
);

const formatMetric = (value, unit = '') => `${Number(value).toFixed(3)}${unit ? ` ${unit}` : ''}`;
const formatDelta = (value, unit = '') => `${value >= 0 ? '+' : ''}${formatMetric(value, unit)}`;
const formatPercent = (value) =>
  Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : '暂无';
const formatTrend = (value) =>
  ({ upward: '上升', downward: '下降', stable: '稳定' }[value] || '暂无');

const TrendChart = defineComponent({
  props: {
    metric: { type: Object, required: true },
    samplingInterval: { type: Number, default: 2 },
  },
  setup(chartProps) {
    const element = ref(null);
    let instance = null;
    const render = () => {
      instance?.dispose();
      instance = null;
      const points = selectEcologyChartPoints(
        chartProps.metric.data || [],
        chartProps.samplingInterval
      );
      if (!element.value || !points.length) return;
      instance = echarts.init(element.value);
      instance.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        grid: { top: 28, right: 18, bottom: 28, left: 44 },
        xAxis: {
          type: 'category',
          data: points.map((point) => point.year),
          axisLine: { lineStyle: { color: '#607d8b' } },
        },
        yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,.1)' } } },
        series: [
          {
            type: 'line',
            smooth: true,
            data: points.map((point) => point.value),
            lineStyle: { color: '#4ecdc4', width: 3 },
            itemStyle: { color: '#4ecdc4' },
          },
        ],
      });
    };
    onMounted(render);
    onBeforeUnmount(() => instance?.dispose());
    watch(
      () => [chartProps.metric, chartProps.samplingInterval],
      () => setTimeout(render),
      {
        deep: true,
      }
    );
    return () =>
      h('div', [
        h(
          'h4',
          { class: 'chart-title' },
          `${chartProps.metric.label || '年度趋势'}${
            chartProps.metric.unit ? `（${chartProps.metric.unit}）` : ''
          }`
        ),
        h('div', { ref: element, class: 'eco-chart', style: { height: '230px' } }),
        !(chartProps.metric.data || []).length && h('p', { class: 'empty' }, '暂无该指标年度数据'),
      ]);
  },
});

const ClimateChart = defineComponent({
  props: {
    temperature: { type: Object, default: () => ({}) },
    precipitation: { type: Object, default: () => ({}) },
  },
  setup(chartProps) {
    const element = ref(null);
    let instance = null;
    const render = () => {
      instance?.dispose();
      instance = null;
      const temperature = chartProps.temperature?.data || [];
      const precipitation = chartProps.precipitation?.data || [];
      const years = [
        ...new Set([...temperature, ...precipitation].map((item) => item.year)),
      ].sort();
      if (!element.value || !years.length) return;
      instance = echarts.init(element.value);
      instance.setOption({
        tooltip: { trigger: 'axis' },
        grid: { top: 34, right: 52, bottom: 28, left: 44 },
        xAxis: { type: 'category', data: years },
        yAxis: [
          { type: 'value', name: '°C' },
          { type: 'value', name: 'mm' },
        ],
        series: [
          {
            name: '年均气温',
            type: 'line',
            data: years.map(
              (year) => temperature.find((item) => item.year === year)?.value ?? null
            ),
            lineStyle: { color: '#fdcb6e' },
          },
          {
            name: '年降水量',
            type: 'bar',
            yAxisIndex: 1,
            data: years.map(
              (year) => precipitation.find((item) => item.year === year)?.value ?? null
            ),
            itemStyle: { color: '#0984e3' },
          },
        ],
      });
    };
    onMounted(render);
    onBeforeUnmount(() => instance?.dispose());
    watch(
      () => [chartProps.temperature, chartProps.precipitation],
      () => setTimeout(render),
      {
        deep: true,
      }
    );
    return () =>
      h('div', [
        h('h4', { class: 'chart-title' }, '气候背景（年均气温 / 年降水量）'),
        h('div', { ref: element, class: 'eco-chart', style: { height: '230px' } }),
      ]);
  },
});

const AnnualDataTable = defineComponent({
  props: { metric: { type: Object, required: true } },
  setup(tableProps) {
    return () =>
      h('details', { class: 'annual-data' }, [
        h('summary', '查看原始年度数据'),
        h('table', [
          h(
            'tbody',
            (tableProps.metric.data || []).map((point) =>
              h('tr', [h('td', `${point.year} 年`), h('td', String(point.value))])
            )
          ),
        ]),
        tableProps.metric.completeness?.missing_years?.length
          ? h(
              'p',
              { class: 'missing-years' },
              `缺失年份：${tableProps.metric.completeness.missing_years.join('、')}（不插值）`
            )
          : null,
      ]);
  },
});
</script>

<style scoped>
.panel-stack {
  display: grid;
  gap: 12px;
}
.source-note {
  margin: 0;
  color: #8da3b6;
  font-size: 12px;
}
.chart-sampling {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #8da3b6;
  font-size: 12px;
}
.chart-sampling button {
  border: 1px solid rgba(78, 205, 196, 0.22);
  background: rgba(78, 205, 196, 0.06);
  color: #cfe8f3;
  cursor: pointer;
  padding: 4px 8px;
}
.chart-sampling button.active {
  border-color: rgba(78, 205, 196, 0.7);
  background: rgba(78, 205, 196, 0.22);
  color: #fff;
}
.chart-title {
  margin: 0;
  color: #cfe8f3;
  font-size: 13px;
  font-weight: normal;
}
.missing-years {
  color: #f7d794;
  font-size: 12px;
}
.state-panel {
  padding: 32px;
  text-align: center;
  color: #cfe8f3;
}
.state-panel.error {
  color: #ff9a9a;
}
.official-summary,
.metric-grid,
.context-grid,
.prediction-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.official-summary > div,
.context-grid > div,
.prediction-grid > div,
.review-box,
.metric-card {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 10px;
}
.official-summary span,
.context-grid span,
.prediction-grid span,
.review-box span,
.metric-card span {
  display: block;
  color: #8da3b6;
  font-size: 12px;
  margin-bottom: 4px;
}
.metric-card strong {
  color: #4ecdc4;
  font-size: 18px;
}
.metric-card small {
  display: block;
  color: #8da3b6;
  margin-top: 5px;
}
.notice {
  margin: 0;
  color: #f7d794;
  font-size: 12px;
}
.metric-switch {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.metric-switch button {
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  padding: 6px 10px;
  cursor: pointer;
}
.metric-switch button.active {
  background: #4ecdc4;
  color: #06202b;
  border-color: #4ecdc4;
}
.eco-chart {
  height: 230px;
}
.empty {
  color: #8da3b6;
  text-align: center;
}
.annual-data {
  color: #cfe8f3;
  font-size: 13px;
}
.annual-data summary {
  cursor: pointer;
}
.annual-data table {
  width: 100%;
  margin-top: 8px;
  border-collapse: collapse;
}
.annual-data td {
  padding: 5px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.matrix-container {
  margin-top: 10px;
  background: rgba(0, 0, 0, 0.2);
  padding: 15px;
  border-radius: 8px;
  overflow-x: auto;
}

.confusion-matrix {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  table-layout: fixed;
}

.confusion-matrix th,
.confusion-matrix td {
  padding: 8px 4px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.confusion-matrix th {
  color: var(--jx-text-muted);
  font-weight: normal;
  background: rgba(255, 255, 255, 0.03);
}

.corner-cell {
  position: relative;
  min-width: 80px;
  height: 56px;
  background: rgba(255, 255, 255, 0.03);
  overflow: hidden;
}

.corner-cell::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    135deg,
    transparent 48%,
    rgba(255, 255, 255, 0.35) 50%,
    transparent 52%
  );
  pointer-events: none;
}

.corner-old,
.corner-new {
  position: absolute;
  font-size: 11px;
  color: var(--jx-text-muted);
}

.corner-old {
  top: 4px;
  left: 6px;
  text-align: left;
}

.corner-new {
  bottom: 4px;
  right: 6px;
  text-align: right;
}

.row-label {
  color: var(--jx-text-muted);
  text-align: left !important;
  width: 60px;
}

.matrix-cell {
  transition: transform 0.2s;
  cursor: default;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.matrix-cell:hover {
  transform: scale(1.05);
  z-index: 1;
}

.matrix-legend {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 15px;
  font-size: 12px;
  color: var(--jx-text-muted);
  justify-content: center;
}

.legend-bar {
  width: 200px;
  height: 10px;
  background: linear-gradient(to right, rgba(78, 205, 196, 0), rgba(78, 205, 196, 0.8));
  border-radius: 5px;
}

.no-data {
  text-align: center;
  padding: 40px;
  color: var(--jx-text-muted);
}

.classification-container {
  margin-top: 10px;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.class-image-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  padding: 10px;
}

.class-title {
  font-size: 13px;
  margin-bottom: 6px;
  color: var(--jx-text-muted);
}

.class-image-wrapper {
  position: relative;
  width: 100%;
}

.class-image {
  width: 100%;
  border-radius: 6px;
  object-fit: cover;
}

.class-year-label {
  position: absolute;
  left: 10px;
  bottom: 10px;
  padding: 2px 8px;
  font-size: 12px;
  color: #000;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 4px;
}
</style>
