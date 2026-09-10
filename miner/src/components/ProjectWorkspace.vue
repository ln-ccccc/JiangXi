<template>
  <div class="workspace-page">
    <header class="workspace-header">
      <div>
        <p class="workspace-kicker">{{ APP_KICKER }}</p>
        <h1>项目工作台</h1>
        <p class="workspace-subtitle">{{ WORKSPACE_SUBTITLE }}</p>
      </div>
      <div class="workspace-header-actions">
        <button v-if="username" class="ghost-btn" @click="$emit('logout')">
          {{ username }} 退出登录
        </button>
        <button class="secondary-btn" @click="$emit('open-map', null)">打开矿山地图</button>
        <button class="primary-btn" @click="startCreateProject">新建项目</button>
      </div>
    </header>

    <section class="workspace-filters panel">
      <input v-model.trim="filters.name" placeholder="项目名称" />
      <input v-model.trim="filters.region" placeholder="区域" />
      <input v-model.trim="filters.monitorYear" placeholder="监测年份" />
      <select v-model="filters.status">
        <option value="">全部状态</option>
        <option v-for="status in projectStatuses" :key="status" :value="status">
          {{ formatProjectStatus(status) }}
        </option>
      </select>
      <button class="secondary-btn" @click="resetFilters">重置筛选</button>
    </section>

    <section class="workspace-layout">
      <aside class="panel project-list-panel">
        <div class="panel-title-row">
          <h2>项目列表</h2>
          <span>{{
            loadingProjects ? '加载中...' : `${visibleProjects.length} / ${projects.length}`
          }}</span>
        </div>
        <p v-if="listError" class="error-text">{{ listError }}</p>
        <button class="ghost-btn" @click="loadProjects(currentProjectId)">刷新列表</button>
        <div class="project-card-list">
          <div v-if="loadingProjects && !projects.length" class="empty-block">
            项目列表加载中...
          </div>
          <template v-else>
            <button
              v-for="item in visibleProjects"
              :key="item.id"
              class="project-card"
              :class="{ active: item.id === currentProjectId }"
              @click="selectProject(item.id)"
            >
              <div class="project-card-top">
                <strong>{{ item.name }}</strong>
                <span class="status-pill" :data-status="item.status">{{
                  formatProjectStatus(item.status)
                }}</span>
              </div>
              <p>{{ item.region || '未填写区域' }}</p>
              <p>监测期：{{ formatYearRange(item.monitor_start_year, item.monitor_end_year) }}</p>
              <p>矿山 {{ item.mine_count || 0 }} 座，数据 {{ item.dataset_count || 0 }} 份</p>
            </button>
            <div v-if="!visibleProjects.length" class="empty-block">暂无匹配项目</div>
          </template>
        </div>
      </aside>

      <main class="project-main">
        <section class="panel" v-if="showProjectForm">
          <div class="panel-title-row">
            <h2>{{ editingProjectId ? '编辑项目' : '新建项目' }}</h2>
            <button class="ghost-btn" @click="cancelProjectForm">关闭</button>
          </div>
          <form class="project-form" @submit.prevent="submitProjectForm">
            <input v-model.trim="projectForm.name" placeholder="项目名称" required />
            <input v-model.trim="projectForm.region" placeholder="区域" />
            <input v-model.trim="projectForm.manager" placeholder="负责人" />
            <select v-model="projectForm.status">
              <option v-for="status in projectStatuses" :key="status" :value="status">
                {{ formatProjectStatus(status) }}
              </option>
            </select>
            <input
              v-model.number="projectForm.monitor_start_year"
              type="number"
              placeholder="开始年份"
            />
            <input
              v-model.number="projectForm.monitor_end_year"
              type="number"
              placeholder="结束年份"
            />
            <textarea v-model.trim="projectForm.remark" placeholder="备注"></textarea>
            <div class="form-actions">
              <button class="primary-btn" type="submit" :disabled="savingProject">
                {{ savingProject ? '保存中...' : '保存项目' }}
              </button>
            </div>
          </form>
          <p v-if="formError" class="error-text">{{ formError }}</p>
        </section>

        <section v-if="currentProjectDetail" class="project-detail-stack">
          <section class="panel">
            <div class="panel-title-row">
              <div>
                <h2>{{ currentProjectDetail.summary?.name }}</h2>
                <p class="muted-text">
                  {{ currentProjectDetail.summary?.region || '未填写区域' }}
                  ·
                  {{
                    formatYearRange(
                      currentProjectDetail.summary?.monitor_start_year,
                      currentProjectDetail.summary?.monitor_end_year
                    )
                  }}
                </p>
              </div>
              <div class="action-row">
                <button class="secondary-btn" @click="startEditCurrentProject">编辑项目</button>
                <button class="secondary-btn" @click="refreshCurrentProject">刷新详情</button>
                <button
                  v-if="currentProjectDetail.summary?.status !== 'archived'"
                  class="ghost-btn"
                  @click="archiveCurrentProject"
                >
                  归档
                </button>
                <button v-else class="ghost-btn" @click="restoreCurrentProject">恢复</button>
              </div>
            </div>
            <div class="summary-grid">
              <div class="summary-card">
                <span>状态</span>
                <strong>{{ formatProjectStatus(currentProjectDetail.summary?.status) }}</strong>
              </div>
              <div class="summary-card">
                <span>负责人</span>
                <strong>{{ currentProjectDetail.summary?.manager || '未填写' }}</strong>
              </div>
              <div class="summary-card">
                <span>矿山数量</span>
                <strong>{{ currentProjectDetail.summary?.mine_count || 0 }}</strong>
              </div>
              <div class="summary-card">
                <span>数据集数量</span>
                <strong>{{ currentProjectDetail.summary?.dataset_count || 0 }}</strong>
              </div>
            </div>
            <p class="muted-text">{{ currentProjectDetail.summary?.remark || '暂无备注' }}</p>
          </section>

          <section class="panel">
            <div class="panel-title-row">
              <h2>江西矿山图斑</h2>
              <span>{{ currentProjectDetail.mines?.length || 0 }} 个图斑</span>
            </div>
            <div v-if="!(currentProjectDetail.mines || []).length" class="empty-block">
              暂无矿山图斑数据
            </div>
            <div v-else class="mine-list">
              <label
                v-for="item in projectMinesPaged.pageItems"
                :key="item.id"
                class="mine-item mine-item-radio"
                :class="{ active: String(item.tbbh) === String(selectedMineTbbh) }"
              >
                <input v-model="selectedMineTbbh" type="radio" :value="String(item.tbbh)" />
                <div class="mine-item-main">
                  <strong>{{ item.mine_name_snapshot || `图斑 ${item.tbbh}` }}</strong>
                  <small class="mine-item-meta">
                    {{ item.city_snapshot || '未标注区域' }}
                    · {{ item.status_snapshot || '状态待补充' }} · TBBH {{ item.tbbh || '--' }}
                  </small>
                </div>
              </label>
            </div>
            <div v-if="projectMinesPaged.totalPages > 1" class="pagination-bar">
              <button
                class="link-btn"
                type="button"
                :disabled="mineListPage <= 1"
                @click="mineListPage -= 1"
              >
                上一页
              </button>
              <span>第 {{ mineListPage }} / {{ projectMinesPaged.totalPages }} 页</span>
              <button
                class="link-btn"
                type="button"
                :disabled="mineListPage >= projectMinesPaged.totalPages"
                @click="mineListPage += 1"
              >
                下一页
              </button>
            </div>
          </section>

          <section class="panel">
            <div class="panel-title-row">
              <h2>图斑明细</h2>
              <span>{{ selectedMinePlots.length }} 条</span>
            </div>
            <div v-if="!selectedMinePlots.length" class="empty-block">当前主体暂无图斑明细</div>
            <div v-else class="table-list">
              <div
                v-for="item in selectedMinePlots"
                :key="`${item.tbbh}-${item.plot_code}`"
                class="table-row table-row-multi"
              >
                <strong>{{ item.plot_code || '--' }}</strong>
                <span>{{ item.plot_category || '--' }}</span>
                <span>{{ item.repair_status || '--' }}</span>
                <span>{{ item.repair_mode || '--' }}</span>
                <span>面积 {{ formatAreaValue(item.area) }}</span>
                <span>未治理 {{ formatAreaValue(item.untreated_area) }}</span>
                <small class="table-row-subline">
                  {{ item.city || '未标注地市' }} / {{ item.county || '未标注区县' }} · 主体
                  {{ item.tbbh || '--' }}
                </small>
              </div>
            </div>
          </section>

          <section class="panel">
            <div class="panel-title-row">
              <h2>绑定矿山</h2>
              <button class="primary-btn" @click="saveMineBindings" :disabled="savingMineBindings">
                保存绑定
              </button>
            </div>
            <div class="mine-list">
              <label v-for="item in mineOptionsPaged.pageItems" :key="item.tbbh" class="mine-item">
                <input v-model="selectedMineTbbhs" type="checkbox" :value="item.tbbh" />
                <span>{{ item.name }}</span>
                <small>{{ item.city || '未标注区域' }}</small>
                <button class="link-btn" type="button" @click.stop="$emit('open-map', item.tbbh)">
                  定位地图
                </button>
              </label>
            </div>
            <div v-if="mineOptionsPaged.totalPages > 1" class="pagination-bar">
              <button
                class="link-btn"
                type="button"
                :disabled="bindMinePage <= 1"
                @click="bindMinePage -= 1"
              >
                上一页
              </button>
              <span>第 {{ bindMinePage }} / {{ mineOptionsPaged.totalPages }} 页</span>
              <button
                class="link-btn"
                type="button"
                :disabled="bindMinePage >= mineOptionsPaged.totalPages"
                @click="bindMinePage += 1"
              >
                下一页
              </button>
            </div>
          </section>

          <section class="panel">
            <div class="panel-title-row">
              <h2>项目数据集</h2>
              <span>{{ currentProjectDetail.datasets?.length || 0 }} 条</span>
            </div>
            <form class="dataset-form" @submit.prevent="submitDatasetForm">
              <input v-model.trim="datasetForm.display_name" placeholder="显示名称" required />
              <select v-model="datasetForm.dataset_kind">
                <option v-for="item in datasetKinds" :key="item" :value="item">
                  {{ formatDatasetKind(item) }}
                </option>
              </select>
              <input v-model.trim="datasetForm.file_path" placeholder="文件路径" required />
              <input
                v-model.trim="datasetForm.source_format"
                placeholder="源格式，例如 tif / xlsx"
              />
              <select v-model="datasetForm.tbbh">
                <option value="">关联全部矿山/不指定</option>
                <option v-for="item in boundMineOptions" :key="item.tbbh" :value="item.tbbh">
                  {{ item.name }}
                </option>
              </select>
              <input v-model.number="datasetForm.year_start" type="number" placeholder="开始年份" />
              <input v-model.number="datasetForm.year_end" type="number" placeholder="结束年份" />
              <textarea
                v-model.trim="datasetForm.slice_config_text"
                placeholder='切片参数 JSON，例如 {"slice_size":1024,"padding":64}'
              ></textarea>
              <div class="form-actions">
                <button class="primary-btn" type="submit" :disabled="savingDataset">
                  {{ savingDataset ? '登记中...' : '登记数据集' }}
                </button>
              </div>
            </form>
            <p v-if="datasetError" class="error-text">{{ datasetError }}</p>
            <div class="table-list">
              <div
                v-for="dataset in currentProjectDetail.datasets || []"
                :key="dataset.id"
                class="table-row"
              >
                <strong>{{ dataset.display_name }}</strong>
                <span>{{ formatDatasetKind(dataset.dataset_kind) }}</span>
                <span>{{ dataset.year_start || '--' }} - {{ dataset.year_end || '--' }}</span>
                <span class="truncate-text">{{ dataset.file_path }}</span>
              </div>
            </div>
          </section>

          <section class="panel">
            <div class="panel-title-row">
              <h2>项目时间线</h2>
              <span>{{ currentProjectDetail.timeline?.length || 0 }} 条</span>
            </div>
            <div class="timeline-list">
              <div
                v-for="item in currentProjectDetail.timeline || []"
                :key="item.id"
                class="timeline-item"
              >
                <strong>{{ formatTimelineType(item.event_type) }}</strong>
                <span>{{ item.actor || 'system' }}</span>
                <small>{{ item.timestamp }}</small>
              </div>
            </div>
          </section>

          <section class="panel">
            <div class="panel-title-row">
              <h2>导出与备份</h2>
              <div class="action-row">
                <button class="secondary-btn" @click="createExport('geojson')">导出 GeoJSON</button>
                <button class="secondary-btn" @click="createExport('csv')">导出 CSV</button>
                <button class="secondary-btn" @click="createExport('shp')">导出 SHP</button>
                <button class="primary-btn" @click="createBackup">生成备份</button>
              </div>
            </div>
            <div class="sub-panel">
              <h3>导出记录</h3>
              <div class="table-list">
                <div
                  v-for="item in currentProjectDetail.exports || []"
                  :key="item.id"
                  class="table-row"
                >
                  <strong>{{ String(item.format || '').toUpperCase() }}</strong>
                  <span>{{ item.status }}</span>
                  <span class="truncate-text">{{ item.file_path || '--' }}</span>
                </div>
              </div>
            </div>
            <div class="sub-panel">
              <h3>备份记录</h3>
              <div class="table-list">
                <div
                  v-for="item in currentProjectDetail.backups || []"
                  :key="item.id"
                  class="table-row"
                >
                  <strong>{{ item.scope }}</strong>
                  <span>{{ item.status }}</span>
                  <span class="truncate-text">{{ item.manifest_path || '--' }}</span>
                  <button class="link-btn" @click="restoreBackup(item.id)">恢复</button>
                </div>
              </div>
            </div>
          </section>
        </section>

        <section v-else-if="loadingProjects" class="panel empty-detail">
          <h2>项目加载中</h2>
          <p>正在读取项目列表和详情...</p>
        </section>
        <section v-else class="panel empty-detail">
          <h2>暂无项目详情</h2>
          <p>先创建项目，或者从左侧选择一个已有项目。</p>
        </section>
      </main>
    </section>
  </div>
</template>

<script setup>
import axios from 'axios';
import { computed, onMounted, ref, watch } from 'vue';

import { APP_KICKER, WORKSPACE_SUBTITLE } from '../config/minerDefaults.js';
import {
  buildMineSelectionSet,
  filterProjects,
  groupPlotsByTbbh,
  paginateList,
} from '../projectWorkspace/projectWorkspaceHelpers.js';

const MINE_PAGE_SIZE = 10;

defineProps({
  username: {
    type: String,
    default: '',
  },
});

defineEmits(['open-map', 'logout']);

const rawMinerApiBase = import.meta.env.VITE_MINER_API_BASE_URL;
const MINER_API_BASE_URL = rawMinerApiBase ? String(rawMinerApiBase).replace(/\/$/, '') : '';
const apiUrl = (path) => `${MINER_API_BASE_URL}${path}`;

const projectStatuses = ['draft', 'active', 'completed', 'archived'];
const datasetKinds = ['imagery', 'inference_result', 'report', 'export_package'];
const projectStatusLabels = {
  draft: '草稿',
  active: '进行中',
  completed: '已完成',
  archived: '已归档',
};
const datasetKindLabels = {
  imagery: '影像',
  inference_result: '解译结果',
  report: '报告',
  export_package: '导出包',
};
const timelineTypeLabels = {
  create: '创建项目',
  update: '更新项目',
  bind_mines: '绑定矿山',
  import_dataset: '登记数据集',
  run_inference: '运行解译',
  create_export: '创建导出',
  create_backup: '生成备份',
  archive: '项目归档',
  restore: '项目恢复',
  restore_backup: '恢复备份',
};

const filters = ref({
  name: '',
  region: '',
  status: '',
  monitorYear: '',
});

const projects = ref([]);
const currentProjectId = ref(null);
const currentProjectDetail = ref(null);
const loadingProjects = ref(false);
const mineOptions = ref([]);
const selectedMineTbbhs = ref([]);
const selectedMineTbbh = ref(null);

// 图斑较多（348 条）时全量渲染过长：两个列表各自分页，每页 10 条
const mineListPage = ref(1);
const bindMinePage = ref(1);
const projectMinesPaged = computed(() =>
  paginateList(currentProjectDetail.value?.mines || [], mineListPage.value, MINE_PAGE_SIZE)
);
const mineOptionsPaged = computed(() =>
  paginateList(mineOptions.value, bindMinePage.value, MINE_PAGE_SIZE)
);
watch(currentProjectDetail, () => {
  mineListPage.value = 1;
  bindMinePage.value = 1;
});

const showProjectForm = ref(false);
const editingProjectId = ref(null);
const savingProject = ref(false);
const savingMineBindings = ref(false);
const savingDataset = ref(false);

const listError = ref('');
const formError = ref('');
const datasetError = ref('');

const projectForm = ref(createDefaultProjectForm());
const datasetForm = ref(createDefaultDatasetForm());

function createDefaultProjectForm() {
  return {
    name: '',
    region: '',
    manager: '',
    remark: '',
    status: 'draft',
    monitor_start_year: '',
    monitor_end_year: '',
  };
}

function createDefaultDatasetForm() {
  return {
    display_name: '',
    dataset_kind: 'imagery',
    file_path: '',
    source_format: '',
    tbbh: '',
    year_start: '',
    year_end: '',
    slice_config_text: '',
  };
}

function unwrapPayload(response) {
  return response?.data?.data ?? response?.data ?? null;
}

function formatYearRange(startYear, endYear) {
  if (!startYear && !endYear) return '未设置';
  return `${startYear || '--'} - ${endYear || '--'}`;
}

function formatProjectStatus(status) {
  return projectStatusLabels[status] || status || '--';
}

function formatDatasetKind(kind) {
  return datasetKindLabels[kind] || kind || '--';
}

function formatTimelineType(type) {
  return timelineTypeLabels[type] || type || '--';
}

function formatAreaValue(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number.toFixed(2) : '0.00';
}

const visibleProjects = computed(() => filterProjects(projects.value, filters.value));
const plotGroups = computed(() => groupPlotsByTbbh(currentProjectDetail.value?.plots || []));
const selectedMinePlots = computed(() => {
  if (!selectedMineTbbh.value) return [];
  return plotGroups.value.get(String(selectedMineTbbh.value)) || [];
});

const boundMineOptions = computed(() => {
  const mines = Array.isArray(currentProjectDetail.value?.mines)
    ? currentProjectDetail.value.mines
    : [];
  return mines.map((item) => ({
    tbbh: String(item.tbbh),
    name: item.mine_name_snapshot || `矿山 ${item.tbbh}`,
  }));
});

async function loadMineOptions() {
  const data = unwrapPayload(await axios.get(apiUrl('/api/geojson')));
  const features = Array.isArray(data?.features) ? data.features : [];
  mineOptions.value = features.map((feature) => {
    const properties = feature.properties || {};
    return {
      tbbh: String(properties.tbbh || ''),
      map_fid: Number(properties.map_fid),
      name: properties.mine_name || properties.name || `矿山 ${properties.tbbh || ''}`,
      city: properties.SHI || '',
      area: properties.area || properties.TBTYMJ || null,
      status: properties.status_normalized || '',
    };
  });
}

async function loadProjects(preferredProjectId = null) {
  listError.value = '';
  loadingProjects.value = true;
  try {
    const data = unwrapPayload(await axios.get(apiUrl('/api/projects')));
    projects.value = Array.isArray(data?.items) ? data.items : [];
    const nextProjectId =
      preferredProjectId || currentProjectId.value || projects.value[0]?.id || null;
    if (nextProjectId) {
      await selectProject(nextProjectId);
    } else {
      currentProjectId.value = null;
      currentProjectDetail.value = null;
    }
  } catch (error) {
    listError.value = error?.response?.data?.msg || error?.message || '项目列表加载失败';
  } finally {
    loadingProjects.value = false;
  }
}

async function selectProject(projectId) {
  if (!projectId) return;
  currentProjectId.value = Number(projectId);
  const requests = await Promise.allSettled([
    axios.get(apiUrl(`/api/projects/${projectId}`)),
    axios.get(apiUrl(`/api/projects/${projectId}/timeline`)),
    axios.get(apiUrl(`/api/projects/${projectId}/exports`)),
    axios.get(apiUrl(`/api/projects/${projectId}/backups`)),
  ]);

  const detail = requests[0].status === 'fulfilled' ? unwrapPayload(requests[0].value) : null;
  if (!detail) {
    currentProjectDetail.value = null;
    return;
  }

  const timeline =
    requests[1].status === 'fulfilled'
      ? unwrapPayload(requests[1].value)?.items || []
      : detail.timeline || [];
  const exportsList =
    requests[2].status === 'fulfilled'
      ? unwrapPayload(requests[2].value)?.items || []
      : detail.exports || [];
  const backupsList =
    requests[3].status === 'fulfilled'
      ? unwrapPayload(requests[3].value)?.items || []
      : detail.backups || [];

  currentProjectDetail.value = {
    ...detail,
    timeline,
    exports: exportsList,
    backups: backupsList,
  };
  selectedMineTbbhs.value = Array.from(buildMineSelectionSet(currentProjectDetail.value));
  datasetError.value = '';
}

function resetFilters() {
  filters.value = {
    name: '',
    region: '',
    status: '',
    monitorYear: '',
  };
}

function startCreateProject() {
  editingProjectId.value = null;
  projectForm.value = createDefaultProjectForm();
  showProjectForm.value = true;
  formError.value = '';
}

function startEditCurrentProject() {
  if (!currentProjectDetail.value?.summary) return;
  editingProjectId.value = currentProjectDetail.value.summary.id;
  projectForm.value = {
    name: currentProjectDetail.value.summary.name || '',
    region: currentProjectDetail.value.summary.region || '',
    manager: currentProjectDetail.value.summary.manager || '',
    remark: currentProjectDetail.value.summary.remark || '',
    status: currentProjectDetail.value.summary.status || 'draft',
    monitor_start_year: currentProjectDetail.value.summary.monitor_start_year || '',
    monitor_end_year: currentProjectDetail.value.summary.monitor_end_year || '',
  };
  showProjectForm.value = true;
  formError.value = '';
}

function cancelProjectForm() {
  showProjectForm.value = false;
  editingProjectId.value = null;
  formError.value = '';
}

async function submitProjectForm() {
  savingProject.value = true;
  formError.value = '';
  try {
    const payload = {
      ...projectForm.value,
      monitor_start_year: projectForm.value.monitor_start_year || null,
      monitor_end_year: projectForm.value.monitor_end_year || null,
    };
    const response = editingProjectId.value
      ? await axios.patch(apiUrl(`/api/projects/${editingProjectId.value}`), payload)
      : await axios.post(apiUrl('/api/projects'), payload);
    const project = unwrapPayload(response);
    showProjectForm.value = false;
    await loadProjects(project?.id || editingProjectId.value);
  } catch (error) {
    formError.value = error?.response?.data?.msg || error?.message || '项目保存失败';
  } finally {
    savingProject.value = false;
  }
}

async function saveMineBindings() {
  if (!currentProjectId.value) return;
  savingMineBindings.value = true;
  try {
    const mineMap = new Map(mineOptions.value.map((item) => [item.tbbh, item]));
    const mines = selectedMineTbbhs.value.map((tbbh, index) => {
      const mine = mineMap.get(String(tbbh)) || {};
      return {
        tbbh: String(tbbh),
        mine_name_snapshot: mine.name || `矿山 ${tbbh}`,
        city_snapshot: mine.city || '',
        area_snapshot: mine.area,
        status_snapshot: mine.status || '',
        sort_order: index + 1,
      };
    });
    await axios.put(apiUrl(`/api/projects/${currentProjectId.value}/mines`), { mines });
    await refreshCurrentProject();
  } catch (error) {
    alert(error?.response?.data?.msg || error?.message || '矿山绑定保存失败');
  } finally {
    savingMineBindings.value = false;
  }
}

async function submitDatasetForm() {
  if (!currentProjectId.value) return;
  savingDataset.value = true;
  datasetError.value = '';
  try {
    let sliceConfigJson = {};
    if (datasetForm.value.slice_config_text) {
      sliceConfigJson = JSON.parse(datasetForm.value.slice_config_text);
    }
    const payload = {
      display_name: datasetForm.value.display_name,
      dataset_kind: datasetForm.value.dataset_kind,
      file_path: datasetForm.value.file_path,
      source_format: datasetForm.value.source_format || null,
      tbbh: datasetForm.value.tbbh || null,
      year_start: datasetForm.value.year_start || null,
      year_end: datasetForm.value.year_end || null,
      slice_config_json: sliceConfigJson,
    };
    await axios.post(apiUrl(`/api/projects/${currentProjectId.value}/datasets`), payload);
    datasetForm.value = createDefaultDatasetForm();
    await refreshCurrentProject();
  } catch (error) {
    datasetError.value = error?.response?.data?.msg || error?.message || '数据集登记失败';
  } finally {
    savingDataset.value = false;
  }
}

async function refreshCurrentProject() {
  if (!currentProjectId.value) return;
  await selectProject(currentProjectId.value);
  await loadProjects(currentProjectId.value);
}

async function archiveCurrentProject() {
  if (!currentProjectId.value) return;
  await axios.post(apiUrl(`/api/projects/${currentProjectId.value}/archive`), {});
  await refreshCurrentProject();
}

async function restoreCurrentProject() {
  if (!currentProjectId.value) return;
  await axios.post(apiUrl(`/api/projects/${currentProjectId.value}/restore`), {});
  await refreshCurrentProject();
}

async function createExport(format) {
  if (!currentProjectId.value) return;
  await axios.post(apiUrl(`/api/projects/${currentProjectId.value}/exports`), {
    format,
  });
  await refreshCurrentProject();
}

async function createBackup() {
  if (!currentProjectId.value) return;
  await axios.post(apiUrl(`/api/projects/${currentProjectId.value}/backups`), {
    scope: 'metadata_index',
  });
  await refreshCurrentProject();
}

async function restoreBackup(backupId) {
  if (!currentProjectId.value || !backupId) return;
  if (!window.confirm(`确认从备份 ${backupId} 恢复项目索引吗？`)) return;
  await axios.post(
    apiUrl(`/api/projects/${currentProjectId.value}/backups/${backupId}/restore`),
    {}
  );
  await refreshCurrentProject();
}

watch(
  () => currentProjectDetail.value?.mines,
  (items) => {
    const mines = Array.isArray(items) ? items : [];
    if (!mines.length) {
      selectedMineTbbh.value = null;
      return;
    }
    const current = String(selectedMineTbbh.value || '');
    const exists = mines.some((item) => String(item.tbbh) === current);
    if (!exists) {
      selectedMineTbbh.value = String(mines[0].tbbh);
    }
  },
  { immediate: true }
);

onMounted(async () => {
  await Promise.allSettled([loadMineOptions(), loadProjects()]);
});
</script>

<style scoped>
.workspace-page {
  /* index.html 对 html/body/#app 设置了 height:100% + overflow:hidden（为地图全屏设计），
     工作台内容超过一屏时无法滚动，因此本页自带滚动容器 */
  height: 100vh;
  overflow-y: auto;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(78, 205, 196, 0.13), transparent 32%),
    linear-gradient(180deg, var(--jx-bg) 0%, var(--jx-bg-elevated) 100%);
  color: var(--jx-text);
  box-sizing: border-box;
}

.workspace-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.workspace-header h1,
.panel h2,
.sub-panel h3 {
  margin: 0;
}

.workspace-kicker {
  margin: 0 0 8px;
  color: var(--jx-primary);
  font-size: 13px;
  letter-spacing: 0.02em;
}

.workspace-subtitle,
.muted-text {
  color: var(--jx-text-muted);
}

.workspace-header-actions,
.action-row,
.form-actions,
.panel-title-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.workspace-filters,
.workspace-layout {
  display: flex;
  gap: 16px;
}

.workspace-filters {
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.workspace-layout {
  align-items: flex-start;
}

.panel {
  background: var(--jx-surface);
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius-large);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
  padding: 18px;
  box-sizing: border-box;
}

.project-list-panel {
  width: 320px;
  flex-shrink: 0;
}

.project-main,
.project-detail-stack {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.project-card-list,
.timeline-list,
.table-list,
.mine-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-top: 12px;
  font-size: 13px;
  color: var(--jx-text-muted, #8fa8b8);
}

.pagination-bar .link-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.project-card {
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius);
  padding: 14px;
  background: var(--jx-surface-muted);
  color: var(--jx-text);
  text-align: left;
  cursor: pointer;
}

.project-card.active {
  border-color: var(--jx-primary);
  background: rgba(78, 205, 196, 0.12);
}

.project-card p,
.empty-block {
  margin: 6px 0 0;
}

.project-card-top,
.summary-grid {
  display: flex;
  gap: 10px;
}

.project-card-top {
  justify-content: space-between;
  align-items: center;
}

.summary-grid {
  flex-wrap: wrap;
  margin: 16px 0;
}

.summary-card {
  min-width: 150px;
  flex: 1;
  border-radius: var(--jx-radius);
  background: var(--jx-surface-muted);
  border: 1px solid var(--jx-border);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.project-form,
.dataset-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.project-form textarea,
.dataset-form textarea,
.project-form .form-actions,
.dataset-form .form-actions {
  grid-column: 1 / -1;
}

.mine-item,
.timeline-item,
.table-row {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border-radius: var(--jx-radius);
  background: var(--jx-surface-muted);
  border: 1px solid var(--jx-border);
}

.mine-item.active {
  border-color: var(--jx-border-strong);
  background: rgba(78, 205, 196, 0.12);
}

.mine-item-radio {
  grid-template-columns: auto 1fr;
}

.mine-item-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mine-item-meta {
  color: var(--jx-text-muted);
}

.timeline-item {
  grid-template-columns: 1.3fr 0.7fr 1fr;
}

.table-row {
  grid-template-columns: 1fr auto auto 1.3fr auto;
}

.table-row-multi {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.table-row-subline {
  grid-column: 1 / -1;
  color: #5d6f6d;
}

.sub-panel + .sub-panel {
  margin-top: 14px;
}

input,
select,
textarea,
button {
  font: inherit;
}

input,
select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius);
  padding: 10px 12px;
  background: rgba(7, 19, 31, 0.72);
  color: var(--jx-text);
}

input:focus,
select:focus,
textarea:focus {
  border-color: var(--jx-primary);
  outline: 2px solid rgba(78, 205, 196, 0.18);
}

textarea {
  min-height: 92px;
  resize: vertical;
}

button {
  border-radius: var(--jx-radius);
  padding: 10px 14px;
  cursor: pointer;
}

.primary-btn {
  border: none;
  background: var(--jx-primary);
  color: #06211f;
  font-weight: 600;
}

.primary-btn:hover {
  background: var(--jx-primary-hover);
}

.secondary-btn {
  border: 1px solid var(--jx-border);
  background: var(--jx-surface-muted);
  color: var(--jx-primary);
}

.ghost-btn,
.link-btn {
  border: none;
  background: transparent;
  color: var(--jx-primary);
  padding: 0;
}

.status-pill {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: rgba(0, 184, 148, 0.16);
  color: #5ce3bd;
}

.status-pill[data-status='draft'] {
  background: rgba(244, 201, 93, 0.16);
  color: var(--jx-warning);
}

.status-pill[data-status='archived'] {
  background: rgba(141, 163, 182, 0.14);
  color: var(--jx-text-muted);
}

.status-pill[data-status='completed'] {
  background: rgba(87, 183, 255, 0.16);
  color: var(--jx-info);
}

.error-text {
  color: var(--jx-danger);
  margin: 12px 0 0;
}

.truncate-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-detail {
  min-height: 300px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

@media (max-width: 1100px) {
  .workspace-header,
  .workspace-layout {
    flex-direction: column;
  }

  .project-list-panel {
    width: 100%;
  }

  .project-form,
  .dataset-form {
    grid-template-columns: 1fr;
  }

  .mine-item,
  .table-row,
  .timeline-item {
    grid-template-columns: 1fr;
  }
}
</style>
