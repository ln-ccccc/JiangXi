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
import { buildDiagnosisCards, selectEcologyChartPoints } from '../utils/ecologyProfile.js';

const props = defineProps({
  tab: { type: String, required: true },
  mineData: { type: Object, default: () => ({}) },
  profile: { type: Object, default: () => ({}) },
  loading: Boolean,
  error: { type: String, default: '' },
});

const metrics = computed(() => props.profile?.metrics || {});
const ecologyMetricKey = computed(
  () => ({ NDVI: 'ndvi', FCV: 'fcv', LAI: 'lai', NPP: 'npp' })[props.tab] || ''
);
const environmentMetricKey = computed(
  () =>
    ({ LST: 'lst', 土壤湿度: 'sm_proxy', TVDI: 'tvdi_proxy', 气候背景: 'climate' })[props.tab] || ''
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
    ['恢复倾向等级', prediction.value.recovery_tendency],
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
  ({ upward: '上升', downward: '下降', stable: '稳定' })[value] || '暂无';

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
          `${chartProps.metric.label || '年度趋势'}${chartProps.metric.unit ? `（${chartProps.metric.unit}）` : ''}`
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
</style>
