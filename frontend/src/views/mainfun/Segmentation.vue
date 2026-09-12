<template>
  <main class="analysis-workflow segmentation-workflow">
    <Tabinfor>
      <template #left>
        <div class="workflow-heading">
          <span class="workflow-heading__eyebrow data-label">JIANGXI · LAND RECORD</span>
          <h1 class="atlas-title">地物分类</h1>
          <p>对江西矿区 tif / tiff 遥感影像执行多要素地物解译，并按矿区边界归档成果。</p>
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

    <el-row
      type="flex"
      justify="space-evenly"
    >
      <el-col :span="24">
        <el-card class="workflow-sheet">
    <SourcePanel ref="sourcePanel" />
    <ParamsPanel ref="paramsPanel" />
    <RunPanel />
      </el-card>
      </el-col>
    </el-row>
    <ResultsPanel />
    <Bottominfor />
  </main>
</template>

<script>
import { atchDownload, downloadimgWithWords, getImgArrayBuffer } from "@/utils/download.js";
import { imgUpload, createSrc } from "@/api/upload";
import {
  flashHistoryClear,
  flashHistoryDeleteOne,
  historyGetPage
} from "@/api/history";
import { getUploadImg, goCompress, upload } from "@/utils/getUploadImg";
import { legacySession } from "@/api/auth";
import { redirectToLegacyLogin } from "@/utils/authRedirect";
import { selectClahe, selectFilter, selectSharpen, selectSmooth, } from "@/utils/preHandle";
import ImgShow from "@/components/ImgShow";
import Tabinfor from "@/components/Tabinfor";
import Bottominfor from "@/components/Bottominfor";
import SourcePanel from "./segmentation/SourcePanel.vue";
import ParamsPanel from "./segmentation/ParamsPanel.vue";
import RunPanel from "./segmentation/RunPanel.vue";
import ResultsPanel from "./segmentation/ResultsPanel.vue";
import MyVueCropper from "@/components/MyVueCropper";

export default {
  name: "Segmentation",
  components: {
    ImgShow,
    Tabinfor,
    Bottominfor,
    MyVueCropper,
    SourcePanel,
    ParamsPanel,
    RunPanel,
    ResultsPanel,
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      document.querySelector(".el-main").scrollTop = 0;
    });
  },
  provide() {
    // 步骤子组件通过 inject seg 直接读写本实例状态与方法（拆分不改变状态归属）
    return { seg: this };
  },

  data() {
    return {
      isUpload: true,
      canUpload: true,
      claheImg: [],
      sharpenImg: [],
      before: [],
      fileimg: "",
      file: {},
      isNotCut: true,
      cutVisible: false,
      fileList: [],
      analysisRunState: "idle",
      analysisRunMessage: "请先选择 tif / tiff 影像。",
      funtype: "地物分类",
      scrollTop: "",
      fit: "fill",

      uploadSrc: { list: [], prehandle: 0, denoise: 0 },

      prePhoto: {
        list: [],
        prehandle: 0,
        type: 4
      },
      imgArr:[],
      roiYear: '',
      sessionRefreshTimer: null,
      inferenceDevice: String(process.env.VUE_APP_JIANGXI_INFERENCE_DEVICE || 'cpu')
        .trim()
        .toLowerCase()
    };
  },
  watch: {
    uploadSrc: {
      handler(newVal, oldVal) {
        this.uploadSrc = newVal
      },
      deep: true,
      immediate: true
    }
  },
  created() {
    this.getUploadImg("地物分类");
    this.sessionRefreshTimer = window.setInterval(() => {
      legacySession().then((res) => {
        if (!res?.data?.data?.authenticated) redirectToLegacyLogin("expired");
      }).catch(() => { });
    }, 10 * 60 * 1000);
  },
  beforeUnmount() {
    if (this.sessionRefreshTimer !== null) {
      window.clearInterval(this.sessionRefreshTimer);
      this.sessionRefreshTimer = null;
    }
  },
  methods: {
    getImgArrayBuffer,
    atchDownload,
    imgUpload,
    historyGetPage,
    createSrc,
    getUploadImg,
    upload,
    goCompress,
    selectSharpen,
    selectFilter,
    selectSmooth,
    selectClahe,
    downloadimgWithWords,
    flashHistoryDeleteOne,
    flashHistoryClear,
    checkUpload() {
      this.isUpload = this.afterImg.length !== 0;
    },
    clearQueue() {
      this.fileList = [];
      this.analysisRunState = "idle";
      this.analysisRunMessage = "请先选择 tif / tiff 影像。";
      const folderInput = this.getSourceInput("folderInput");
      const fileInput = this.getSourceInput("fileInput");
      if (folderInput) folderInput.value = "";
      if (fileInput) fileInput.value = "";
      this.$message.success("清除成功");
    },
    notvisible() {
      this.cutVisible = false;
      this.fileList = [];
      this.analysisRunState = "idle";
      this.analysisRunMessage = "请先选择 tif / tiff 影像。";
      const folderInput = this.getSourceInput("folderInput");
      const fileInput = this.getSourceInput("fileInput");
      if (folderInput) folderInput.value = "";
      if (fileInput) fileInput.value = "";
    },
    getMore() {
      return this.getUploadImg("地物分类");
    },
    // 拆分后文件 input 在 SourcePanel、编辑复选框在 ParamsPanel，父组件经子组件取 ref
    getSourceInput(kind) {
      const panel = this.$refs.sourcePanel;
      return panel && panel.$refs ? panel.$refs[kind] : null;
    },
    getCutCheckbox() {
      const panel = this.$refs.paramsPanel;
      return panel && panel.$refs ? panel.$refs.cut : null;
    },
    deleteHistoryItem(item) {
      this.$confirm("删除该条历史？", "提示", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }).then(() => {
        return this.flashHistoryDeleteOne(item.record_id);
      }).then(() => {
        this.$message.success("删除成功");
        this.getMore();
      }).catch(() => {});
    },
    clearCurrentHistory() {
      this.$confirm("确认清空全部历史？", "提示", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }).then(() => {
        return this.flashHistoryClear();
      }).then(() => {
        this.$message.success("清理完成");
        this.getMore();
      }).catch(() => {});
    },
    fileClick() {
      const folderInput = this.getSourceInput("folderInput");
      if (folderInput) {
        folderInput.value = "";
        folderInput.click();
      }
    },
    openFilePicker() {
      const fileInput = this.getSourceInput("fileInput");
      if (fileInput) {
        fileInput.value = "";
        fileInput.click();
      }
    },
    isValidTiff(fileLike) {
      const raw = fileLike?.raw || fileLike?.file || fileLike;
      const name = String(fileLike?.relativePath || raw?.webkitRelativePath || raw?.name || "");
      const fileSuffix = name.substring(name.lastIndexOf(".") + 1);
      return ["tif", "tiff", "TIF", "TIFF"].includes(fileSuffix);
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
      }});
    },
    setPreviewFile(fileLike) {
      const file = fileLike?.raw || fileLike?.file || fileLike;
      this.cutVisible = !!this.getCutCheckbox()?.checked;
      this.canUpload = true;
      this.fileimg = window.URL.createObjectURL(file);
    },
    disableCutForBatchUpload() {
      const cutCheckbox = this.getCutCheckbox();
      if (cutCheckbox?.checked) {
        cutCheckbox.checked = false;
        this.cutVisible = false;
        this.isNotCut = true;
        this.$message.warning("整文件夹/批量上传不支持上传时编辑，已自动关闭编辑模式");
      }
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
        this.cutVisible = false;
        this.canUpload = false;
        this.analysisRunState = "error";
        this.analysisRunMessage = "没有可用的 tif / tiff 影像，请重新选择。";
        this.$message.error("只允许上传 tif / tiff 格式,请重新上传");
        return;
      }
      if (validFiles.length > 1) {
        this.disableCutForBatchUpload();
      }
      this.fileList = this.createUploadItems(validFiles);
      this.analysisRunState = "ready";
      this.analysisRunMessage = `已就绪 ${validFiles.length} 个文件；请确认四位年份后开始同步分析。`;
      this.setPreviewFile(validFiles[validFiles.length - 1]);
    },
    handleUploadChange(file, uploadFiles) {
      const rawFiles = (uploadFiles || [])
        .map((item) => item?.raw || item)
        .filter(Boolean);
      this.replaceFileList(rawFiles);
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
      this.disableCutForBatchUpload();
      this.replaceFileList(rawFiles);
      event.target.value = "";
    },
    async handleNativeDrop(event) {
      const items = Array.from(event?.dataTransfer?.items || []);
      const filesFromDrop = await this.readDroppedItems(items);
      if (filesFromDrop.length > 0) {
        this.disableCutForBatchUpload();
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
        .map((item) => item.webkitGetAsEntry ? item.webkitGetAsEntry() : null)
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
    select() {
      this.isNotCut = !!this.getCutCheckbox()?.checked;
    },
  },
};
</script>
<style lang="less">
.segmentation-workflow {

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
  min-height: 132px;
  padding: 18px 16px 14px;
  text-align: center;
  cursor: pointer;
}

.upload-dropzone:focus-visible {
  outline: 2px solid var(--jx-primary);
  outline-offset: 3px;
}

.upload-dropzone .iconfont {
  display: block;
  font-size: 38px;
  line-height: 1;
  margin-bottom: 8px;
  color: var(--jx-primary);
}

.upload-dropzone .el-upload__text {
  font-size: 15px;
  line-height: 1.5;
}

.upload-dropzone .el-upload__tip {
  margin-top: 4px;
  line-height: 1.4;
}

.upload-dropzone :deep(.el-button) {
  margin-top: 8px !important;
}

.upload-dropzone > .el-row {
  margin-top: 8px;
}

.upload-dropzone > .el-row p {
  margin: 4px 0;
}

.upload-dropzone :deep(.el-input) {
  margin: 2px 0 6px;
}

.upload-dropzone + .el-row,
.upload-dropzone ~ .el-row {
  margin-top: 8px;
}

.upload-guidance {
  margin-top: 8px;
  color: var(--jx-text-muted);
  font-size: 12px;
}

.selected-files {
  margin-top: 10px;
  text-align: left;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 10px;
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

.el-radio {
  height: auto !important;
  margin-bottom: 8px;
  margin-right: 20px;
  display: inline-flex;
  align-items: center;
}

.el-radio /deep/ .el-radio__label {
  display: flex;
  align-items: center;
  padding-left: 10px;
}

.el-radio /deep/ .el-radio__input {
  margin-top: 0;
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

.workflow-panel--execute {
  padding-bottom: 8px;
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
  margin: 0;
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

.run-status__guide {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 18px;
  margin-top: 8px;
  font-size: 12px;
}

.run-status [data-state="partial"] {
  color: var(--jx-warning);
}

.run-status [data-state="error"] {
  color: var(--jx-danger);
}

.history-tools {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}

.history-tools .icon-shuaxin {
  color: var(--jx-primary);
  cursor: pointer;
}

.history-tools .icon-shuaxin:focus-visible {
  outline: 2px solid var(--jx-primary);
  outline-offset: 3px;
}

@media (max-width: 1100px) {
  .workflow-panel__header {
    gap: 18px;
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

  .run-status__guide {
    grid-template-columns: 1fr;
  }

  .execution-action :deep(.el-button) {
    width: 100%;
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

  .history-tools {
    align-items: stretch;
    flex-direction: column;
  }
}


}
</style>
