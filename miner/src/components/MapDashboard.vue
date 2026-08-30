<template>
  <div class="dashboard">
    <TheHeader
      :weatherIcon="weatherIcon"
      :temperature="temperature"
      :airQuality="airQuality"
      :currentDate="currentDate"
      :currentTime="currentTime"
      :getAqiClass="getAqiClass"
      :username="username"
      @logout="emit('logout')"
      @open-workspace="emit('open-workspace')"
    />

    <main class="main-container">
      <LeftSidebar
        v-model:filterCity="filterCity"
        v-model:filterStatus="filterStatus"
        v-model:filterMethod="filterMethod"
        v-model:searchMineId="searchMineId"
        :plotTotal="plotTotal"
        :plotAreaTotal="plotAreaTotal"
        :treatedAreaRatio="treatedAreaRatio"
        :untreatedAreaRatio="untreatedAreaRatio"
        :restorationMethodDistribution="restorationMethodDistribution"
        :cityOptions="cityOptions"
        :miningMethodOptions="miningMethodOptions"
        :searchFeedbackMessage="searchFeedbackMessage"
        :searchFeedbackKind="searchFeedbackKind"
        :dataLoadError="dataLoadError"
        @apply-filters="handleApplyFilters"
        @reset-filters="handleResetFilters"
        @search="performSearch"
      />

      <MapContainer
        ref="mapContainerRef"
        :minesData="filteredMinesData"
        :dataLoadError="dataLoadError"
        :leftCollapsed="false"
        :rightCollapsed="false"
        @select-mine="handleSelectMine"
      />

      <RightSidebar :recommendedPanels="recommendedPanels" :dataLoadError="dataLoadError" />
    </main>

    <MineDetailModal
      :visible="showMineDetail"
      :mineData="selectedMine"
      :ecologyProfile="mineEcologyProfile"
      :ecologyLoading="ecologyProfileLoading"
      :ecologyError="ecologyProfileError"
      :selectedTab="selectedTab"
      @close="showMineDetail = false"
      @tab-change="selectedTab = $event"
    />

    <InferenceModal
      :visible="showInferenceModal"
      :running="inferenceRunning"
      :error="inferenceError"
      :result="inferenceResult"
      @close="showInferenceModal = false"
      @submit="handleInferenceSubmit"
    />

    <TrendReportModal
      :visible="showTrendReportModal"
      :loading="trendReportLoading"
      :error="trendReportError"
      :report="trendReport"
      @close="showTrendReportModal = false"
      @refresh="refreshTrendReport"
      @export="handleExportTrendReport"
    />
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue';
import 'leaflet/dist/leaflet.css';

import TheHeader from './TheHeader.vue';
import LeftSidebar from './LeftSidebar.vue';
import RightSidebar from './RightSidebar.vue';
import MapContainer from './MapContainer.vue';
import MineDetailModal from './MineDetailModal.vue';
import InferenceModal from './InferenceModal.vue';
import TrendReportModal from './TrendReportModal.vue';
import { INFERENCE_DEVICE, JIANGXI_FALLBACK_CENTER } from '../config/minerDefaults.js';

import { useWeather } from '../composables/useWeather';
import { useMineData } from '../composables/useMineData';

const props = defineProps({
  username: {
    type: String,
    default: '',
  },
  focusTbbh: {
    type: String,
    default: '',
  },
});

const emit = defineEmits(['logout', 'open-workspace']);

const showMineDetail = ref(false);
const showInferenceModal = ref(false);
const showTrendReportModal = ref(false);
const selectedMine = ref({});
const selectedTab = ref('基础信息');
const mapContainerRef = ref(null);
const searchFeedbackMessage = ref('');
const searchFeedbackKind = ref('info');

const {
  currentDate,
  currentTime,
  temperature,
  weatherIcon,
  airQuality,
  getAqiClass,
  fetchRealtimeEnvironmentAt,
} = useWeather();

const {
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
  treatedAreaRatio,
  untreatedAreaRatio,
  restorationMethodDistribution,
  recommendedPanels,
  dataLoadError,
  mineEcologyProfile,
  ecologyProfileLoading,
  ecologyProfileError,
  loadData,
  applyFilters,
  resetFilters,
  fetchEcologyProfile,
  inferenceRunning,
  inferenceResult,
  inferenceError,
  runKmlRoiInference,
  trendReportLoading,
  trendReportError,
  trendReport,
  fetchTrendReport,
  exportTrendReport,
} = useMineData();

let dataLoadPromise = null;

const ensureDataLoaded = () => {
  if (allMinesData.value.length > 0) return Promise.resolve();
  if (!dataLoadPromise) {
    dataLoadPromise = loadData().finally(() => {
      dataLoadPromise = null;
    });
  }
  return dataLoadPromise;
};

const setSearchFeedback = (message = '', kind = 'info') => {
  searchFeedbackMessage.value = message;
  searchFeedbackKind.value = kind;
};

const clearSearchFeedback = () => setSearchFeedback('', 'info');

const handleApplyFilters = () => {
  clearSearchFeedback();
  applyFilters();
};

const handleResetFilters = () => {
  clearSearchFeedback();
  resetFilters();
};

const performSearch = () => {
  const keyword = String(searchMineId.value || '')
    .trim()
    .toLowerCase();
  if (!keyword) {
    setSearchFeedback('请输入 TBBH、地图编号或图斑名称后再定位', 'warning');
    return;
  }

  const target = allMinesData.value.find((feature) => {
    const properties = feature.properties || {};
    return (
      String(properties.tbbh || '').toLowerCase() === keyword ||
      String(properties.map_fid ?? '') === keyword ||
      String(properties.mine_name || '')
        .toLowerCase()
        .includes(keyword) ||
      String(properties.name || '')
        .toLowerCase()
        .includes(keyword)
    );
  });

  if (!target) {
    setSearchFeedback('未找到匹配图斑，请检查名称、编号或筛选条件', 'warning');
    return;
  }

  let filterReset = false;
  if (!filteredMinesData.value.find((item) => item.properties.tbbh === target.properties.tbbh)) {
    filterCity.value = '';
    filterStatus.value = '';
    filterMethod.value = '';
    applyFilters();
    filterReset = true;
  }

  const targetName =
    target.properties.mine_name || target.properties.name || `图斑 ${target.properties.tbbh}`;
  setSearchFeedback(
    filterReset
      ? `目标图斑不在当前筛选结果中，已重置筛选并定位到 ${targetName}`
      : `已定位到 ${targetName}`,
    'success'
  );

  nextTick(() => {
    mapContainerRef.value?.flyToMine?.(target.properties.tbbh);
  });
};

const handleSelectMine = async ({ feature, center }) => {
  const properties = feature.properties || {};
  selectedMine.value = {
    mine_id: properties.tbbh || '',
    tbbh: properties.tbbh || properties.TBBH || '',
    map_fid: properties.map_fid,
    name: properties.mine_name || properties.name || `图斑 ${properties.tbbh}`,
    city: properties.SHI || properties.city || '未标注地市',
    area: properties.area || properties.TBTYMJ || properties.TBTYMJ_1 || 0,
    status_raw: properties.HFZLQK || '未知',
    status_normalized: properties.status_normalized || 'unknown',
    restoration_method: properties.NXFFS || '未知修复方式',
    damage_type: properties.STWT || '未知图斑类型',
    mining_method: properties.KCFS || '未知开采方式',
    center_lat: Number.isFinite(center?.lat) ? center.lat : null,
    center_lng: Number.isFinite(center?.lng) ? center.lng : null,
  };

  clearSearchFeedback();
  showMineDetail.value = true;
  selectedTab.value = '修复诊断';

  await fetchEcologyProfile(properties.tbbh || properties.TBBH);
  fetchRealtimeEnvironmentAt(center.lat, center.lng);
};

const focusByTbbh = (tbbh) => {
  searchMineId.value = String(tbbh);
  performSearch();
};

const focusAfterDataLoad = async (tbbh) => {
  const normalized = String(tbbh || '').trim();
  if (!normalized) return;
  await ensureDataLoaded();
  focusByTbbh(normalized);
};

const handleInferenceSubmit = async (formData) => {
  if (!formData.oldTifPath) return;
  try {
    const result = await runKmlRoiInference({
      oldTifPath: formData.oldTifPath,
      newTifPath: formData.newTifPath || formData.oldTifPath,
      kmlPath: formData.kmlPath,
      year: formData.singleYear,
      oldYear: formData.oldYear,
      newYear: formData.newYear,
      device: INFERENCE_DEVICE,
      limit: 0,
      syncIndices: true,
      indexTypes: ['ndvi', 'ndbi', 'ndwi', 'ndsi'],
    });

    const writtenCount = Array.isArray(result?.written_tbbh_list)
      ? result.written_tbbh_list.length
      : 0;
    const kmlChangedCount =
      Number(result?.kml_update?.updated || 0) + Number(result?.kml_update?.inserted || 0);
    if (writtenCount > 0 || kmlChangedCount > 0) {
      await loadData();
    }
    if (writtenCount > 0) {
      showInferenceModal.value = false;
      focusByTbbh(result.written_tbbh_list[0]);
    } else if (kmlChangedCount > 0) {
      showInferenceModal.value = false;
    }
  } catch (_) {
    // 错误文案通过 useMineData 暴露给弹窗
  }
};

const refreshTrendReport = async (filters = {}) => {
  try {
    await fetchTrendReport(filters);
  } catch (_) {}
};

const handleExportTrendReport = async (filters = {}) => {
  try {
    await exportTrendReport(filters);
  } catch (_) {
    alert('导出失败，请稍后重试');
  }
};

onMounted(() => {
  ensureDataLoaded().then(() => {
    if (props.focusTbbh) focusByTbbh(props.focusTbbh);
  });
  fetchRealtimeEnvironmentAt(JIANGXI_FALLBACK_CENTER[0], JIANGXI_FALLBACK_CENTER[1]);

  window.addEventListener('resize', () => {
    mapContainerRef.value?.invalidateSize?.();
  });
});

watch(
  () => props.focusTbbh,
  (tbbh) => {
    if (tbbh) focusAfterDataLoad(tbbh);
  }
);

defineExpose({
  focusByTbbh,
});
</script>

<style scoped>
.dashboard {
  width: 100vw;
  height: 100vh;
  min-width: 0;
  background:
    repeating-radial-gradient(
      ellipse at 18% 22%,
      transparent 0 28px,
      rgba(156, 231, 189, 0.035) 29px 30px,
      transparent 31px 68px
    ),
    repeating-linear-gradient(
      142deg,
      transparent 0 46px,
      rgba(230, 201, 140, 0.022) 47px 48px,
      transparent 49px 96px
    ),
    radial-gradient(circle at 50% 42%, rgba(156, 231, 189, 0.08), transparent 46%),
    linear-gradient(135deg, var(--jx-bg) 0%, var(--jx-surface) 100%);
  color: var(--jx-text);
  overflow: hidden;
  font-family: inherit;
  display: flex;
  flex-direction: column;
}

.main-container {
  flex: 1 1 auto;
  position: relative;
  display: flex;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
  gap: 0;
}

.main-container :deep(.left-sidebar),
.main-container :deep(.right-sidebar) {
  flex: 0 0 286px;
  width: 286px;
  min-width: 286px;
}

.main-container :deep(.map-container) {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
}

@media (max-width: 900px) {
  .main-container {
    flex-direction: column;
    overflow-x: hidden;
    overflow-y: auto;
  }

  .main-container :deep(.left-sidebar),
  .main-container :deep(.right-sidebar) {
    flex: 0 0 auto;
    width: 100%;
    max-width: none;
    min-width: 0;
    max-height: min(42vh, 360px);
  }

  .main-container :deep(.left-sidebar) {
    border-right: 0;
    border-bottom: 1px solid var(--jx-border);
  }

  .main-container :deep(.right-sidebar) {
    border-top: 1px solid var(--jx-border);
    border-left: 0;
  }

  .main-container :deep(.sidebar-content) {
    min-height: 0;
    overflow-y: auto;
  }

  .main-container :deep(.map-container) {
    flex: 0 0 auto;
    width: 100%;
    min-height: 420px;
  }

  .dashboard :deep(.header) {
    height: auto;
    min-height: 64px;
    padding-block: 10px;
    flex-wrap: wrap;
    align-content: center;
  }

  .dashboard :deep(.header-left),
  .dashboard :deep(.header-right) {
    flex-wrap: wrap;
  }
}
</style>
