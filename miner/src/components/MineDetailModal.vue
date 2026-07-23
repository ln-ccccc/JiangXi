<template>
  <transition name="fade">
    <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-content glass-panel">
        <div class="modal-header">
          <h3>{{ mineData.name }}</h3>
          <button class="close-btn" @click="$emit('close')">×</button>
        </div>
        <div class="modal-body">
          <div class="info-grid">
            <div class="info-item">
              <span class="label">图斑ID:</span> <span class="val">{{ mineData.mine_id }}</span>
            </div>
            <div class="info-item">
              <span class="label">所属地市:</span>
              <span class="val">{{ mineData.city || '暂无' }}</span>
            </div>
            <div class="info-item">
              <span class="label">TBBH:</span>
              <span class="val">{{ mineData.tbbh || '暂无' }}</span>
            </div>
            <div class="info-item">
              <span class="label">面积:</span>
              <span class="val">{{ formatAreaText(mineData.area) }}</span>
            </div>
            <div class="info-item">
              <span class="label">治理状态:</span>
              <span class="status-tag" :class="mineData.status_normalized">
                {{ mineData.status_raw || '未知' }}
              </span>
            </div>
            <div class="info-item">
              <span class="label">修复方式:</span>
              <span class="val">{{ mineData.restoration_method || '暂无' }}</span>
            </div>
            <div class="info-item">
              <span class="label">图斑类型:</span>
              <span class="val">{{ mineData.damage_type || '暂无' }}</span>
            </div>
            <div class="info-item">
              <span class="label">开采方式:</span>
              <span class="val">{{ mineData.mining_method || '暂无' }}</span>
            </div>
            <div class="info-item">
              <span class="label">中心坐标:</span>
              <span class="val">{{
                formatCoordinateText(mineData.center_lat, mineData.center_lng)
              }}</span>
            </div>
          </div>

          <div class="tabs">
            <button
              v-for="tab in MINE_ECOLOGY_TABS"
              :key="tab"
              :class="{ active: selectedTab === tab }"
              @click="$emit('tab-change', tab)"
            >
              {{ tab }}
            </button>
          </div>

          <EcologyDiagnosisPanels
            v-if="selectedTab !== '基础资料'"
            :tab="selectedTab"
            :mine-data="mineData"
            :profile="ecologyProfile"
            :loading="ecologyLoading"
            :error="ecologyError"
          />

          <template v-else>
            <div class="fact-summary">
              当前面板优先展示江西图斑的基础业务事实；分析结果请切换到其他标签页查看。
            </div>
            <details class="business-details">
              <summary>查看工作簿完整台账、项目与填报资料</summary>
              <div class="business-grid">
                <div v-for="item in businessItems" :key="item.label">
                  <span class="label">{{ item.label }}</span>
                  <strong>{{ item.value ?? '暂无' }}</strong>
                </div>
              </div>
            </details>
          </template>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed } from 'vue';
import EcologyDiagnosisPanels from './EcologyDiagnosisPanels.vue';
import { MINE_ECOLOGY_TABS } from '../utils/ecologyProfile.js';

const props = defineProps({
  visible: Boolean,
  mineData: Object,
  ecologyProfile: Object,
  ecologyLoading: Boolean,
  ecologyError: String,
  selectedTab: String,
});

defineEmits(['close', 'tab-change']);

const businessItems = computed(() => {
  const business = props.ecologyProfile?.business || {};
  const labels = {
    province: '省市',
    city: '地市',
    county: '区县',
    mine_location: '矿山位置',
    mine_code: '主体编号',
    plot_code: '图斑编号',
    restoration_plot_code: '修复图斑编号',
    verified_area: '图斑核定面积',
    plot_category: '图斑小类',
    restoration_status: '修复状态',
    restoration_mode: '修复模式',
    completion_date: '完成时间',
    project_name: '工程项目名称',
    project_type: '工程项目类型',
    actual_restoration_area: '实际修复面积',
    untreated_area: '未治理面积',
    reporting_organization: '填报单位',
    reporter: '填报人',
    report_date: '填报日期',
    remark: '备注',
  };
  return Object.entries(labels).map(([key, label]) => ({ key, label, value: business[key] }));
});

const formatAreaText = (value) => {
  const area = Number(value);
  if (!Number.isFinite(area) || area <= 0) return '暂无';
  const hectares = area / 10000;
  return `${hectares.toFixed(2)} 公顷`;
};

const formatCoordinateText = (lat, lng) => {
  const latNum = Number(lat);
  const lngNum = Number(lng);
  if (!Number.isFinite(latNum) || !Number.isFinite(lngNum)) return '暂无';
  return `${latNum.toFixed(4)}, ${lngNum.toFixed(4)}`;
};
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 3000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
  padding: 72px 16px 24px;
  box-sizing: border-box;
}
.modal-content {
  width: min(680px, 100%);
  height: min(760px, calc(100vh - 96px));
  background: rgba(7, 20, 31, 0.94);
  border: 1px solid #4ecdc4;
  box-shadow: 0 0 30px rgba(78, 205, 196, 0.2);
  display: flex;
  flex-direction: column;
  flex: 0 0 auto;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  flex: 0 0 auto;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 10px;
  margin-bottom: 15px;
}
.close-btn {
  background: none;
  border: none;
  color: #fff;
  font-size: 24px;
  cursor: pointer;
}

.glass-panel {
  background: rgba(7, 20, 31, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 12px;
}
.modal-body {
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-color: rgba(78, 205, 196, 0.58) transparent;
  scrollbar-width: thin;
}
.modal-body::-webkit-scrollbar {
  width: 7px;
}
.modal-body::-webkit-scrollbar-track {
  background: transparent;
}
.modal-body::-webkit-scrollbar-thumb {
  background: rgba(78, 205, 196, 0.48);
  border: 2px solid transparent;
  border-radius: 999px;
  background-clip: padding-box;
}
.modal-body::-webkit-scrollbar-thumb:hover {
  background-color: rgba(78, 205, 196, 0.76);
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 20px;
}
.info-item {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.1);
  padding-bottom: 5px;
}
.label {
  color: #8da3b6;
  font-size: 13px;
}
.val {
  font-weight: bold;
}
.status-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.status-tag.treated {
  background: rgba(0, 184, 148, 0.2);
  color: #00b894;
}
.status-tag.untreated {
  background: rgba(255, 118, 117, 0.2);
  color: #ff7675;
}

.fact-summary {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 14px;
  color: #cfe8f3;
  line-height: 1.6;
}

.tabs {
  display: grid;
  grid-auto-columns: minmax(90px, max-content);
  grid-auto-flow: column;
  grid-template-rows: repeat(2, 38px);
  gap: 8px;
  margin-bottom: 15px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-color: rgba(78, 205, 196, 0.58) transparent;
  scrollbar-width: thin;
}
.tabs::-webkit-scrollbar {
  height: 7px;
}
.tabs::-webkit-scrollbar-track {
  background: transparent;
}
.tabs::-webkit-scrollbar-thumb {
  background: rgba(78, 205, 196, 0.48);
  border: 2px solid transparent;
  border-radius: 999px;
  background-clip: padding-box;
}
.tabs::-webkit-scrollbar-thumb:hover {
  background-color: rgba(78, 205, 196, 0.76);
}
.tabs button {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
  padding: 8px;
  cursor: pointer;
}
.tabs button.active {
  background: #4ecdc4;
  color: #000;
  border-color: #4ecdc4;
}
.business-details {
  margin-top: 12px;
  color: #cfe8f3;
}
.business-details summary {
  cursor: pointer;
}
.business-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}
.business-grid > div {
  background: rgba(0, 0, 0, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 8px;
}
.business-grid strong {
  display: block;
  margin-top: 4px;
  word-break: break-word;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
