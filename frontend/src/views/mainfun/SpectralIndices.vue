<template>
  <main class="analysis-workflow spectral-workflow">
    <Tabinfor>
      <template #left>
        <div class="workflow-heading">
          <span class="workflow-heading__eyebrow data-label">JIANGXI · SPECTRAL RECORD</span>
          <h1 class="atlas-title">光谱指数计算</h1>
          <p>以江西矿区多波段影像计算生态光谱指数，并记录矿山边界内统计结果。</p>
        </div>
      </template>
      <template #right>
        <div class="workflow-badges" aria-label="运行配置">
          <span>江西</span>
          <span>同步分析</span>
          <span>CPU</span>
        </div>
      </template>
    </Tabinfor>
    <ol class="workflow-track" aria-label="分析步骤">
      <li><span class="workflow-step__number">01</span><span>数据源</span></li>
      <li><span class="workflow-step__number">02</span><span>参数设置</span></li>
      <li><span class="workflow-step__number">03</span><span>执行分析</span></li>
      <li><span class="workflow-step__number">04</span><span>结果预览</span></li>
    </ol>
    <el-row type="flex" justify="center">
      <el-col :span="24">
        <el-card class="workflow-sheet">
          <section class="workflow-panel" data-step="01">
            <header class="workflow-panel__header">
              <div>
                <span class="workflow-panel__index data-label">01 / SOURCE</span>
                <h2 class="atlas-title">数据源</h2>
              </div>
              <p>选择多波段 tif / tiff 影像；批量文件将按当前指数和波段配置顺序同步处理。</p>
            </header>
          <div v-if="fileList.length" class="clear-queue">
            <el-button type="primary" class="btn-animate2 btn-animate__surround" @click="clearQueue">
              清空影像
            </el-button>
          </div>
          <div
            class="upload-card upload-dropzone"
            role="button"
            tabindex="0"
            aria-label="选择 tif 或 tiff 多波段遥感影像文件夹"
            @click="openFolderPicker"
            @keydown.enter="openFolderPicker"
            @keydown.space.prevent="openFolderPicker"
            @dragover.prevent
            @dragenter.prevent
            @drop.prevent="handleNativeDrop"
          >
            <i class="iconfont icon-yunduanshangchuan" />
            <div class="el-upload__text">
              将文件夹拖到此处，或<em>点击上传整个文件夹</em>
            </div>
            <div class="el-upload__tip">
              递归读取文件夹内容，仅上传 tif / tiff
            </div>
            <div
              v-if="fileList.length"
              class="selected-files"
              @click.stop
            >
              <div class="selected-files__title">
                已选择 {{ fileList.length }} 个 tif/tiff 文件
              </div>
              <div
                v-for="item in fileList.slice(0, 8)"
                :key="item.uid"
                class="selected-files__item"
              >
                {{ item.name }}
              </div>
              <div
                v-if="fileList.length > 8"
                class="selected-files__item"
              >
                其余 {{ fileList.length - 8 }} 个文件待上传
              </div>
            </div>
          </div>
          <el-row justify="center">
            <el-button
              plain
              size="small"
              style="margin-top: 8px;"
              @click="openFolderPicker"
            >
              选择整个文件夹
            </el-button>
            <el-button
              plain
              size="small"
              style="margin-top: 8px; margin-left: 8px;"
              @click="openFilePicker"
            >
              选择文件
            </el-button>
          </el-row>
          <input
            ref="folderInput"
            type="file"
            webkitdirectory
            multiple
            style="display: none;"
            @change="handleFolderSelect"
          >
          <input
            ref="fileInput"
            type="file"
            accept=".tif,.tiff,.TIF,.TIFF"
            multiple
            style="display: none;"
            @change="handleFileSelect"
          >
          <el-row justify="center">
            <div class="upload-guidance">
              支持拖拽文件夹、点击选择整个文件夹，自动递归过滤非 tif / tiff 文件
            </div>
          </el-row>
          </section>

          <section class="workflow-panel" data-step="02">
            <header class="workflow-panel__header">
              <div>
                <span class="workflow-panel__index data-label">02 / PARAMETERS</span>
                <h2 class="atlas-title">参数设置</h2>
              </div>
              <p>选择指数、成果年份与实际影像波段编号；波段编号从 1 开始。</p>
            </header>
          <el-row justify="start" class="option-row">
            <el-form label-width="100px" inline>
              <el-form-item label="指数类型">
                <el-select v-model="indexType" style="width: 180px;">
                  <el-option label="NDVI" value="NDVI" />
                  <el-option label="NDBI" value="NDBI" />
                  <el-option label="NDWI" value="NDWI" />
                  <el-option label="NDSI" value="NDSI" />
                </el-select>
              </el-form-item>
              <el-form-item label="年份">
                <el-input v-model="year" style="width: 180px;" placeholder="例如 2024（可选）" />
              </el-form-item>
              <el-form-item label="NIR波段">
                <el-input-number v-model="bandMap.nir" :min="1" />
              </el-form-item>
              <el-form-item label="RED波段">
                <el-input-number v-model="bandMap.red" :min="1" />
              </el-form-item>
              <el-form-item label="GREEN波段">
                <el-input-number v-model="bandMap.green" :min="1" />
              </el-form-item>
              <el-form-item label="SWIR波段">
                <el-input-number v-model="bandMap.swir" :min="1" />
              </el-form-item>
            </el-form>
          </el-row>
          </section>

          <section class="workflow-panel workflow-panel--execute" data-step="03">
            <header class="workflow-panel__header">
              <div>
                <span class="workflow-panel__index data-label">03 / RUN</span>
                <h2 class="atlas-title">执行分析</h2>
              </div>
              <p>使用江西同步计算链路；本批影像全部返回后才会刷新历史成果。</p>
            </header>
          <div class="handle-button execution-action">
            <el-button
              type="primary"
              class="btn-animate btn-animate__shiny"
              :disabled="fileList.length === 0"
              @click="startCompute"
            >
              开始计算 {{ indexType }}
            </el-button>
          </div>
          <div class="run-status" aria-live="polite">
            <p v-if="runState === 'idle' && !fileList.length" data-state="idle">
              请先选择 tif / tiff 影像，执行按钮将在数据就绪后启用。
            </p>
            <p v-else :data-state="runState">
              {{ runMessage }}
            </p>
            <div class="run-status__guide">
              <span data-state="partial">部分成功：保留成功成果，并显示后端返回的失败说明。</span>
              <span data-state="error">失败：显示计算失败原因，请检查波段、坐标系和矿区边界。</span>
            </div>
          </div>
          </section>
        </el-card>
      </el-col>
    </el-row>

    <section class="workflow-panel workflow-panel--results" data-step="04">
      <Tabinfor>
        <template #left>
          <div class="workflow-panel__header workflow-panel__header--compact">
            <div>
              <span class="workflow-panel__index data-label">04 / RESULTS</span>
              <h2 class="atlas-title">结果预览</h2>
              <p>对照原始影像、指数成果与矿区边界内统计值，选择图片可放大检查。</p>
            </div>
          </div>
        </template>
        <template #right>
          <button class="history-refresh" type="button" @click="getMore">
            <i class="iconfont icon-shuaxin" aria-hidden="true" />
            刷新历史结果
          </button>
        </template>
      </Tabinfor>
    <ImgShow :img-arr="imgArr" @delete-item="deleteHistoryItem" />
    </section>
    <Bottominfor />
  </main>
</template>

<script>
import { createSrc, imgUpload } from "@/api/upload";
import { getUploadImg } from "@/utils/getUploadImg";
import { historyDeleteOne } from "@/api/history";
import Tabinfor from "@/components/Tabinfor";
import Bottominfor from "@/components/Bottominfor";
import ImgShow from "@/components/ImgShow";

export default {
  name: "SpectralIndices",
  components: {
    Tabinfor,
    Bottominfor,
    ImgShow
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      document.querySelector(".el-main").scrollTop = 0;
    });
  },
  data() {
    return {
      fileList: [],
      imgArr: [],
      runState: "idle",
      runMessage: "请先选择 tif / tiff 影像。",
      indexType: "NDVI",
      year: "",
      bandMap: {
        nir: 4,
        red: 3,
        green: 2,
        swir: 5
      }
    };
  },
  created() {
    this.getUploadImg("光谱指数计算");
  },
  methods: {
    createSrc,
    imgUpload,
    getUploadImg,
    historyDeleteOne,
    openFolderPicker() {
      this.$refs.folderInput && this.$refs.folderInput.click();
    },
    openFilePicker() {
      this.$refs.fileInput && this.$refs.fileInput.click();
    },
    isValidTiff(fileLike) {
      const raw = fileLike?.raw || fileLike?.file || fileLike;
      const name = String(fileLike?.relativePath || raw?.webkitRelativePath || raw?.name || "");
      const suffix = name.substring(name.lastIndexOf(".") + 1).toLowerCase();
      return ["tif", "tiff"].includes(suffix);
    },
    normalizeSelectedItems(inputFiles) {
      return inputFiles.map((item) => {
        if (item?.raw) return item;
        if (item?.file) {
          return {
            raw: item.file,
            relativePath: item.relativePath || item.file.webkitRelativePath || item.file.name,
          };
        }
        return {
          raw: item,
          relativePath: item?.webkitRelativePath || item?.name,
        };
      });
    },
    createUploadItems(files) {
      return files.map((item, index) => {
        const raw = item.raw;
        return {
          name: item.relativePath || raw.webkitRelativePath || raw.name,
          size: raw.size,
          status: "ready",
          uid: `${raw.name}-${raw.lastModified}-${index}`,
          raw,
        };
      });
    },
    replaceFileList(inputFiles) {
      const normalizedFiles = this.normalizeSelectedItems(inputFiles);
      const validFiles = normalizedFiles.filter((file) => this.isValidTiff(file));
      const invalidCount = normalizedFiles.length - validFiles.length;
      if (invalidCount > 0) {
        this.$message.warning(`已忽略 ${invalidCount} 个非 tif/tiff 文件`);
      }
      if (validFiles.length === 0) {
        this.fileList = [];
        this.runState = "error";
        this.runMessage = "没有可用的 tif / tiff 影像，请重新选择。";
        this.$message.error("只允许上传 tif / tiff 格式,请重新上传");
        return;
      }
      this.fileList = this.createUploadItems(validFiles);
      this.runState = "ready";
      this.runMessage = `已就绪 ${validFiles.length} 个文件；可开始同步计算 ${this.indexType}。`;
    },
    handleFileSelect(event) {
      const rawFiles = Array.from(event?.target?.files || []);
      if (rawFiles.length === 0) return;
      this.replaceFileList(rawFiles);
      event.target.value = "";
    },
    handleFolderSelect(event) {
      const rawFiles = Array.from(event?.target?.files || []);
      if (rawFiles.length === 0) return;
      this.replaceFileList(rawFiles);
      event.target.value = "";
    },
    async handleNativeDrop(event) {
      const items = Array.from(event?.dataTransfer?.items || []);
      const filesFromDrop = await this.readDroppedItems(items);
      if (filesFromDrop.length > 0) {
        this.replaceFileList(filesFromDrop);
        return;
      }
      const rawFiles = Array.from(event?.dataTransfer?.files || []);
      if (rawFiles.length > 0) {
        this.replaceFileList(rawFiles);
      }
    },
    async readDroppedItems(items) {
      if (!items.length) return [];
      const entries = items
        .map((item) => (item.webkitGetAsEntry ? item.webkitGetAsEntry() : null))
        .filter(Boolean);
      if (!entries.length) return [];
      const files = [];
      for (const entry of entries) {
        const entryFiles = await this.walkFileTree(entry);
        files.push(...entryFiles);
      }
      return files;
    },
    walkFileTree(entry, parentPath = "") {
      if (!entry) return Promise.resolve([]);
      if (entry.isFile) {
        return new Promise((resolve) => {
          entry.file((file) => {
            resolve([{
              file,
              relativePath: parentPath ? `${parentPath}/${file.name}` : file.name,
            }]);
          }, () => resolve([]));
        });
      }
      if (!entry.isDirectory) return Promise.resolve([]);

      const directoryPath = parentPath ? `${parentPath}/${entry.name}` : entry.name;
      const reader = entry.createReader();
      return new Promise((resolve) => {
        const allEntries = [];
        const readBatch = () => {
          reader.readEntries(async (batch) => {
            if (!batch.length) {
              let files = [];
              for (const child of allEntries) {
                const childFiles = await this.walkFileTree(child, directoryPath);
                files = files.concat(childFiles);
              }
              resolve(files);
              return;
            }
            allEntries.push(...batch);
            readBatch();
          }, () => resolve([]));
        };
        readBatch();
      });
    },
    clearQueue() {
      this.fileList = [];
      this.runState = "idle";
      this.runMessage = "请先选择 tif / tiff 影像。";
      this.$message.success("清除成功");
    },
    getMore() {
      this.getUploadImg("光谱指数计算");
    },
    deleteHistoryItem(item) {
      const rid = item?.id;
      if (!rid) {
        this.$message.error("记录ID缺失，无法删除");
        return;
      }
      this.$confirm("此操作将永久删除该组记录, 是否继续?", "提示", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }).then(() => {
        return this.historyDeleteOne(rid);
      }).then(() => {
        this.$message.success("删除成功");
        this.getMore();
      }).catch(() => {});
    },
    startCompute() {
      if (!this.fileList.length) {
        this.runState = "error";
        this.runMessage = "请先选择 tif / tiff 影像。";
        this.$message.error("请先上传tif文件");
        return;
      }
      this.runState = "running";
      this.runMessage = `正在同步计算 ${this.indexType}，请保持当前页面开启。`;
      const formData = new FormData();
      for (const item of this.fileList) {
        formData.append("files", item.raw || item);
      }
      formData.append("type", "光谱指数计算");
      formData.append("keepRawTiff", "true");
      this.createSrc(formData).then((res) => {
        const uploadItems = res.data.data || [];
        const list = uploadItems.map((item) => ({
          src: item.src,
          raw_tiff_path: item.raw_tiff_path || ""
        }));
        return this.imgUpload({
          list,
          index_type: this.indexType,
          year: this.year,
          band_map: this.bandMap
        }, "spectral_indices");
      }).then((res) => {
        const backendMsg = res?.data?.msg || "";
        if (backendMsg.includes("同步部分失败")) {
          this.runState = "partial";
          this.runMessage = backendMsg;
          this.$message.warning(backendMsg);
        } else {
          this.runState = "success";
          this.runMessage = backendMsg || "计算完成，结果已加入历史记录。";
          this.$message.success(backendMsg || "计算完成");
        }
        this.fileList = [];
        this.getMore();
      }).catch((err) => {
        const msg = err?.response?.data?.msg || "计算失败";
        this.runState = "error";
        this.runMessage = msg;
        this.$message.error(msg);
      });
    }
  }
};
</script>

<style lang="less" scoped>
.analysis-workflow {
  width: min(100%, 1480px);
  margin: 0 auto;
  color: var(--jx-text);
}

.clear-queue {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}

.upload-dropzone {
  min-height: 180px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
}

.upload-dropzone:focus-visible {
  outline: 2px solid var(--jx-primary);
  outline-offset: 3px;
}

.upload-dropzone .iconfont {
  display: block;
  margin-bottom: 10px;
  color: var(--jx-primary);
  font-size: 38px;
}

.upload-guidance {
  margin-top: 8px;
  color: var(--jx-text-muted);
  font-size: 12px;
}

.selected-files {
  margin-top: 16px;
  text-align: left;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 12px;
}

.selected-files__title {
  font-weight: 700;
  margin-bottom: 8px;
}

.selected-files__item {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  word-break: break-all;
}

.option-row {
  margin-top: 6px;
}

.option-row :deep(.el-form) {
  display: grid;
  grid-template-columns: repeat(3, minmax(210px, 1fr));
  gap: 10px 16px;
  width: 100%;
}

.option-row :deep(.el-form-item) {
  margin: 0;
}

.option-row :deep(.el-input),
.option-row :deep(.el-select),
.option-row :deep(.el-input-number) {
  width: 100% !important;
}

.workflow-sheet {
  border-color: var(--jx-border) !important;
}

.workflow-panel {
  position: relative;
  padding: 24px 0;
  border-bottom: 1px solid var(--jx-border);
}

.workflow-panel:first-child {
  padding-top: 4px;
}

.workflow-panel:last-child {
  border-bottom: 0;
}

.workflow-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 28px;
  margin-bottom: 20px;
}

.workflow-panel__header h2 {
  margin: 3px 0 0;
  color: var(--jx-text);
  font-size: 24px;
  font-weight: 650;
}

.workflow-panel__header > p {
  max-width: 620px;
  margin: 4px 0 0;
  color: var(--jx-text-muted);
}

.workflow-panel__index {
  color: var(--jx-sand);
  font-size: 11px;
}

.workflow-panel--results {
  margin-top: 22px;
  padding: 24px;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius-large);
  background: var(--jx-surface);
}

.workflow-panel__header--compact {
  margin-bottom: 0;
}

.workflow-panel__header--compact p {
  margin: 6px 0 0;
  color: var(--jx-text-muted);
}

.execution-action {
  display: flex;
  justify-content: flex-start;
}

.execution-action :deep(.el-button) {
  min-width: 210px;
}

.run-status {
  margin-top: 14px;
  padding: 14px 16px;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius);
  background: var(--jx-surface-muted);
  color: var(--jx-text-muted);
}

.run-status p {
  margin: 0;
}

.run-status [data-state="ready"],
.run-status [data-state="success"] {
  color: var(--jx-success);
}

.run-status [data-state="running"] {
  color: var(--jx-info);
}

.run-status [data-state="partial"] {
  color: var(--jx-warning);
}

.run-status [data-state="error"] {
  color: var(--jx-danger);
}

.run-status__guide {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 18px;
  margin-top: 8px;
  font-size: 12px;
}

.history-refresh {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius);
  background: var(--jx-surface-muted);
  color: var(--jx-text);
  cursor: pointer;
}

.history-refresh:hover {
  border-color: var(--jx-border-strong);
  color: var(--jx-primary);
}

.history-refresh:focus-visible {
  outline: 2px solid var(--jx-primary);
  outline-offset: 3px;
}

@media (max-width: 1100px) {
  .option-row :deep(.el-form) {
    grid-template-columns: repeat(2, minmax(210px, 1fr));
  }
}

@media (max-width: 768px) {
  .workflow-panel,
  .workflow-panel--results {
    padding: 18px 14px;
  }

  .workflow-panel__header {
    display: block;
  }

  .workflow-panel__header > p {
    margin-top: 8px;
  }

  .option-row :deep(.el-form),
  .run-status__guide {
    grid-template-columns: 1fr;
  }

  .execution-action :deep(.el-button),
  .history-refresh {
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .workflow-panel,
  .workflow-panel--results {
    padding: 16px 10px;
  }

  .workflow-panel__header h2 {
    font-size: 21px;
  }
}
</style>
