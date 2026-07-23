<template>
  <aside class="sidebar left-sidebar">
    <div class="sidebar-header">
      <h2>数据概览</h2>
    </div>

    <div class="sidebar-content">
      <div v-if="dataLoadError" class="error-panel">
        {{ dataLoadError }}
      </div>

      <div class="metric-grid">
        <div class="metric-card">
          <div class="metric-label">图斑总数</div>
          <div class="metric-value text-cyan">{{ plotTotal }}</div>
          <div class="metric-unit">个</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">图斑总面积</div>
          <div class="metric-value text-blue">{{ (plotAreaTotal / 10000).toFixed(2) }}</div>
          <div class="metric-unit">公顷</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">已治理面积占比</div>
          <div class="metric-value text-green">{{ (treatedAreaRatio * 100).toFixed(1) }}</div>
          <div class="metric-unit">%</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">未治理面积占比</div>
          <div class="metric-value text-yellow">{{ (untreatedAreaRatio * 100).toFixed(1) }}</div>
          <div class="metric-unit">%</div>
        </div>
      </div>
      <div class="control-panel glass-panel">
        <div class="panel-header">
          <h3>筛选查询</h3>
          <button class="reset-btn" @click="emitReset">重置</button>
        </div>
        <div class="filter-group">
          <label>所属地市</label>
          <select
            :value="filterCity"
            @change="
              $emit('update:filterCity', $event.target.value);
              emitApply();
            "
          >
            <option value="">全部地市</option>
            <option v-for="city in cityOptions" :key="city" :value="city">{{ city }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>治理状态</label>
          <select
            :value="filterStatus"
            @change="
              $emit('update:filterStatus', $event.target.value);
              emitApply();
            "
          >
            <option value="">全部状态</option>
            <option value="treated">已治理</option>
            <option value="untreated">未治理</option>
          </select>
        </div>
        <div class="filter-group">
          <label>开采方式</label>
          <select
            :value="filterMethod"
            @change="
              $emit('update:filterMethod', $event.target.value);
              emitApply();
            "
          >
            <option value="">全部方式</option>
            <option v-for="method in miningMethodOptions" :key="method" :value="method">
              {{ method }}
            </option>
          </select>
        </div>
        <div class="search-box">
          <input
            type="text"
            :value="searchMineId"
            @input="$emit('update:searchMineId', $event.target.value)"
            placeholder="输入图斑名称或ID..."
            @keyup.enter="emitSearch"
          />
          <button @click="emitSearch">定位</button>
        </div>
        <div v-if="searchFeedbackMessage" class="search-feedback" :class="searchFeedbackKind">
          {{ searchFeedbackMessage }}
        </div>
      </div>
      <div class="ranking-panel glass-panel">
        <div class="panel-header"><h3>修复方式分布</h3></div>
        <div v-if="restorationMethodDistribution?.length" class="ranking-list">
          <div
            class="ranking-item"
            v-for="(item, index) in restorationMethodDistribution"
            :key="item.name"
          >
            <span class="rank-num">{{ index + 1 }}</span>
            <span class="rank-name">{{ item.name }}</span>
            <div class="rank-bar-container">
              <div
                class="rank-bar"
                :style="{
                  width: (item.value / (restorationMethodDistribution[0]?.value || 1)) * 100 + '%',
                }"
              ></div>
            </div>
            <span class="rank-val">{{ item.value }}</span>
          </div>
        </div>
        <div v-else class="panel-empty">当前暂无可展示的修复方式统计。</div>
      </div>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  plotTotal: Number,
  plotAreaTotal: Number,
  treatedAreaRatio: Number,
  untreatedAreaRatio: Number,
  restorationMethodDistribution: Array,
  cityOptions: Array,
  miningMethodOptions: Array,
  filterCity: String,
  filterStatus: String,
  filterMethod: String,
  searchMineId: String,
  searchFeedbackMessage: {
    type: String,
    default: '',
  },
  searchFeedbackKind: {
    type: String,
    default: 'info',
  },
  dataLoadError: String,
});

const emit = defineEmits([
  'update:filterCity',
  'update:filterStatus',
  'update:filterMethod',
  'update:searchMineId',
  'apply-filters',
  'reset-filters',
  'search',
]);

const emitApply = () => emit('apply-filters');
const emitReset = () => emit('reset-filters');
const emitSearch = () => emit('search');
</script>

<style scoped>
.sidebar {
  width: 286px;
  background: var(--jx-bg-elevated);
  backdrop-filter: blur(15px);
  border-right: 1px solid var(--jx-border);
  display: flex;
  flex-direction: column;
  z-index: 100;
  transition: width 0.3s ease;
  overflow: hidden;
}

.sidebar-header {
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 10px;
  border-bottom: 1px solid var(--jx-border);
  white-space: nowrap;
}
.sidebar-header h2 {
  font-size: 15px;
  margin: 0;
  color: var(--jx-primary);
  flex: 1;
  text-align: center;
  letter-spacing: 0.04em;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: opacity 0.2s;
}

.glass-panel {
  background: var(--jx-surface);
  border: 1px solid var(--jx-border);
  border-radius: 6px;
  padding: 10px;
  box-shadow: inset 2px 0 0 rgba(143, 198, 200, 0.26);
}

.error-panel {
  padding: 8px 10px;
  color: #ffe8c7;
  background: rgba(214, 128, 88, 0.16);
  border: 1px solid var(--jx-warning);
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.panel-header h3 {
  font-size: 14px;
  color: var(--jx-text);
  margin: 0;
  border-left: 2px solid var(--jx-primary);
  padding-left: 8px;
}
.reset-btn {
  height: 32px;
  background: transparent;
  border: 1px solid var(--jx-border);
  color: var(--jx-text-muted);
  font-size: 11px;
  padding: 0 9px;
  border-radius: 5px;
  cursor: pointer;
}

.metric-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 7px;
}
.metric-card {
  background: rgba(7, 25, 35, 0.72);
  border: 1px solid rgba(156, 231, 189, 0.12);
  padding: 8px 7px;
  border-radius: 5px;
  text-align: center;
}

.metric-label {
  font-size: 11px;
  color: var(--jx-text-muted);
  line-height: 1.35;
}
.metric-value {
  font-size: 21px;
  font-weight: 700;
  line-height: 1.1;
  margin: 5px 0 3px;
  font-variant-numeric: tabular-nums;
}
.metric-unit {
  font-size: 10px;
  color: var(--jx-text-muted);
  opacity: 0.72;
}
.text-cyan,
.text-blue {
  color: var(--jx-info);
}
.text-green {
  color: var(--jx-primary);
}
.text-yellow {
  color: var(--jx-warning);
}

.filter-group {
  margin-bottom: 10px;
}
.filter-group label {
  display: block;
  font-size: 12px;
  color: var(--jx-text-muted);
  margin-bottom: 4px;
}
.filter-group select {
  width: 100%;
  height: 32px;
  background: rgba(7, 25, 35, 0.82);
  border: 1px solid var(--jx-border);
  color: var(--jx-text);
  padding: 0 8px;
  border-radius: 5px;
}
.search-box {
  display: flex;
  gap: 5px;
  margin-top: 15px;
}
.search-box input {
  flex: 1;
  min-width: 0;
  height: 32px;
  background: rgba(7, 25, 35, 0.82);
  border: 1px solid var(--jx-border);
  color: var(--jx-text);
  padding: 0 8px;
  border-radius: 5px;
}
.search-box button {
  height: 32px;
  background: var(--jx-primary);
  border: 1px solid var(--jx-primary);
  color: var(--jx-bg);
  padding: 0 11px;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 700;
}

.search-feedback {
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
}

.search-feedback.success {
  color: var(--jx-primary);
  background: rgba(156, 231, 189, 0.12);
  border: 1px solid var(--jx-primary);
}

.search-feedback.info {
  color: var(--jx-info);
  background: rgba(143, 198, 200, 0.12);
  border: 1px solid var(--jx-info);
}

.search-feedback.warning {
  color: #ffe8c7;
  background: rgba(214, 128, 88, 0.16);
  border: 1px solid var(--jx-warning);
}

.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ranking-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 24px;
  padding: 3px 4px;
  border: 1px solid transparent;
  border-radius: 4px;
  font-size: 12px;
  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}
.rank-num {
  width: 18px;
  height: 18px;
  background: rgba(7, 25, 35, 0.9);
  border: 1px solid var(--jx-border);
  border-radius: 4px;
  text-align: center;
  line-height: 16px;
  font-size: 10px;
  color: var(--jx-info);
  font-variant-numeric: tabular-nums;
  flex: 0 0 18px;
}
.rank-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rank-bar-container {
  flex: 1;
  height: 6px;
  background: rgba(143, 198, 200, 0.12);
  border: 1px solid rgba(143, 198, 200, 0.16);
  border-radius: 3px;
  overflow: hidden;
}
.rank-bar {
  height: 100%;
  background: var(--jx-primary);
  border-radius: 2px;
}
.rank-val {
  min-width: 24px;
  color: var(--jx-text);
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.panel-empty {
  padding: 12px 8px 5px;
  color: var(--jx-text-muted);
  border-top: 1px solid var(--jx-border);
  font-size: 12px;
  line-height: 1.5;
}

.filter-group select:hover,
.search-box input:hover,
.reset-btn:hover {
  border-color: var(--jx-border-strong);
}

.search-box button:hover {
  background: var(--jx-primary-hover);
  border-color: var(--jx-primary-hover);
}

.ranking-item:hover {
  background: rgba(156, 231, 189, 0.06);
  border-color: var(--jx-border);
}

.filter-group select:focus-visible,
.search-box input:focus-visible,
.search-box button:focus-visible,
.reset-btn:focus-visible {
  outline: 2px solid var(--jx-primary);
  outline-offset: 2px;
}
</style>
