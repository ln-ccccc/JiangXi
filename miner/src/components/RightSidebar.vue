<template>
  <aside class="sidebar right-sidebar">
    <div class="sidebar-header">
      <h2>分析统计</h2>
    </div>

    <div ref="sidebarContentRef" class="sidebar-content">
      <div v-if="dataLoadError" class="error-panel">
        {{ dataLoadError }}
      </div>

      <div v-else-if="!visiblePanels.length" class="empty-panel glass-panel">
        当前可用统计维度较少，已自动隐藏低信息量图表。
      </div>

      <div v-for="panel in visiblePanels" :key="panel.key" class="chart-panel glass-panel">
        <div class="panel-header">
          <h3>{{ panel.title }}</h3>
          <span class="panel-unit">{{ panel.metric === 'area' ? '按面积' : '按数量' }}</span>
        </div>
        <div :ref="(el) => setChartRef(panel.key, el)" class="chart-box"></div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  recommendedPanels: {
    type: Array,
    default: () => [],
  },
  dataLoadError: {
    type: String,
    default: '',
  },
});

const sidebarContentRef = ref(null);
let chartResizeObserver = null;
const chartRefs = new Map();
const chartInstances = new Map();

const visiblePanels = computed(() =>
  (props.recommendedPanels || []).filter(
    (panel) => Array.isArray(panel?.data) && panel.data.length > 0
  )
);

const formatPanelValue = (panel, value) => {
  const num = Number(value);
  if (!Number.isFinite(num)) return '--';
  if (panel.metric === 'area') return `${num.toFixed(2)} ${panel.unit}`;
  return `${num} ${panel.unit}`;
};

const setChartRef = (key, el) => {
  if (el) {
    chartRefs.set(key, el);
  } else {
    chartRefs.delete(key);
  }
};

const makeBarOption = (panel) => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'axis',
    // confine: 侧栏图表宽度有限，tooltip 必须限制在图表容器内，
    // 否则跟随鼠标溢出到面板外/压住相邻条目标签（悬浮框遮挡缺陷）
    confine: true,
    backgroundColor: 'rgba(9, 23, 34, 0.96)',
    borderColor: 'rgba(112, 160, 151, 0.3)',
    borderWidth: 1,
    padding: [8, 10],
    textStyle: { color: '#d3e1dd', fontSize: 11 },
    axisPointer: {
      type: 'shadow',
      shadowStyle: { color: 'rgba(91, 151, 142, 0.08)' },
    },
    formatter: (params) => {
      const item = params?.[0];
      if (!item) return '';
      return `${item.name}<br/>${formatPanelValue(panel, item.value)}`;
    },
  },
  grid: { left: '4%', right: '5%', bottom: '7%', top: '5%', containLabel: true },
  xAxis: {
    type: 'value',
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: {
      show: true,
      lineStyle: { color: 'rgba(136, 169, 162, 0.12)', type: 'dashed' },
    },
    axisLabel: {
      color: '#78918f',
      fontSize: 10,
      margin: 8,
      formatter: (value) => (panel.metric === 'area' ? Number(value).toFixed(0) : value),
    },
  },
  yAxis: {
    type: 'category',
    data: panel.data.map((item) => item.name),
    axisLine: { show: false },
    axisTick: { show: false },
    // 长类目名换行展示（break）而非截断：截断会迫使读者悬停读 tooltip，
    // 而 tooltip 又容易遮挡相邻内容；直接可读是更好的信息设计
    axisLabel: {
      color: '#a2b8b3',
      fontSize: 11,
      margin: 10,
      width: 96,
      overflow: 'break',
      lineHeight: 14,
    },
  },
  series: [
    {
      type: 'bar',
      data: panel.data.map((item) => item.value),
      barWidth: '60%',
      itemStyle: {
        color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
          { offset: 0, color: '#7fd8a6' },
          { offset: 0.62, color: '#54997a' },
          { offset: 1, color: '#e2c285' },
        ]),
      },
    },
  ],
});

const resizeCharts = () => {
  chartInstances.forEach((instance) => instance.resize());
};

const syncCharts = () => {
  const activeKeys = new Set(visiblePanels.value.map((panel) => panel.key));

  chartInstances.forEach((instance, key) => {
    if (!activeKeys.has(key)) {
      instance.dispose();
      chartInstances.delete(key);
    }
  });

  visiblePanels.value.forEach((panel) => {
    const el = chartRefs.get(panel.key);
    if (!el) return;

    let instance = chartInstances.get(panel.key);
    if (!instance) {
      instance = echarts.init(el);
      chartInstances.set(panel.key, instance);
    }

    instance.setOption(makeBarOption(panel), true);
  });

  nextTick(() => {
    resizeCharts();
  });
};

watch(
  visiblePanels,
  () => {
    nextTick(() => {
      syncCharts();
    });
  },
  { deep: true }
);

onMounted(() => {
  nextTick(() => {
    syncCharts();
    resizeCharts();
  });

  window.addEventListener('resize', resizeCharts);

  if (typeof ResizeObserver !== 'undefined') {
    chartResizeObserver = new ResizeObserver(() => {
      resizeCharts();
    });
    if (sidebarContentRef.value) {
      chartResizeObserver.observe(sidebarContentRef.value);
    }
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts);
  chartResizeObserver?.disconnect();
  chartInstances.forEach((instance) => instance.dispose());
  chartInstances.clear();
});
</script>

<style scoped>
.sidebar {
  width: 286px;
  max-width: 100%;
  min-width: 0;
  min-height: 0;
  background: var(--jx-bg-elevated);
  border-left: 1px solid var(--jx-border);
  display: flex;
  flex-direction: column;
  z-index: 100;
  overflow: hidden;
}

.sidebar-header {
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  white-space: nowrap;
}

.sidebar-header h2 {
  font-size: 16px;
  margin: 0;
  color: var(--jx-primary);
  flex: 1;
  text-align: center;
}

.sidebar-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  padding: 14px 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: opacity 0.2s;
}

.glass-panel {
  background: var(--jx-surface);
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius);
  padding: 14px 14px 10px;
}

.error-panel {
  padding: 8px 10px;
  color: var(--jx-danger);
  background: color-mix(in srgb, var(--jx-danger) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--jx-danger) 28%, transparent);
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.panel-header h3 {
  min-width: 0;
  font-size: 13px;
  line-height: 1.4;
  color: var(--jx-text);
  margin: 0;
  border-left: 2px solid var(--jx-info);
  padding-left: 8px;
}

.panel-unit {
  flex: 0 0 auto;
  color: var(--jx-text-muted);
  font-size: 11px;
}

.chart-box {
  width: 100%;
  height: 184px;
}

.empty-panel {
  display: flex;
  align-items: center;
  min-height: 128px;
  padding: 16px;
  color: var(--jx-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 720px) {
  .sidebar {
    width: min(286px, 34vw);
    min-width: 210px;
  }

  .chart-box {
    height: 168px;
  }
}
</style>
