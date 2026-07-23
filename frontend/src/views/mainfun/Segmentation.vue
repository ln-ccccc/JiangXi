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
          <section class="workflow-panel" data-step="01">
            <header class="workflow-panel__header">
              <div>
                <span class="workflow-panel__index data-label">01 / SOURCE</span>
                <h2 class="atlas-title">数据源</h2>
              </div>
              <p>选择包含江西矿区影像的文件夹，或直接选择一个或多个 tif / tiff 文件。</p>
            </header>
          <div
            v-if="fileList.length"
            class="clear-queue"
          >
            <el-button
              type="primary"
              class="btn-animate2 btn-animate__surround"
              @click="clearQueue"
            >
              清空图片
            </el-button>
          </div>
          <div
            class="upload-card upload-dropzone"
            role="button"
            tabindex="0"
            aria-label="选择 tif 或 tiff 遥感影像文件夹"
            @click="fileClick"
            @keydown.enter="fileClick"
            @keydown.space.prevent="fileClick"
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
              @click="fileClick"
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
              <p>填写成果年份，并按影像情况选择裁剪、增强或降噪预处理。</p>
            </header>
          <el-row justify="center">
            <p>
              <label class="prehandle-label container">
                <input
                  ref="cut"
                  type="checkbox"
                  @change="select()"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">上传时编辑图片</span><i
                  class="iconfont icon-crop-full"
                />
              </label>
            </p>
          </el-row>
          <div style="text-align: center; margin-bottom: 20px;">
            <el-input
              v-model="roiYear"
              style="width: 240px;"
              maxlength="4"
              placeholder="年份（YYYY，用于KML ROI命名）"
              clearable
            />
          </div>
          <el-row
            justify="center"
            align="middle"
          >
            <i
              class="iconfont icon-tuxingtuxiangchuli"
            />
            <p>图像增强：</p>
            <p>
              <label class="prehandle-label container">
                <input
                  ref="clahe"
                  type="checkbox"

                  @change="selectClahe(4)"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">CLAHE</span>
              </label>
            </p>
            <p>
              <label class="prehandle-label container">
                <input
                  ref="sharpen"
                  type="checkbox"

                  @change="selectSharpen(4)"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">锐化</span>
              </label>
            </p>
          </el-row>
          <el-row
            justify="center"
            align="middle"
          >
            <i
              class="iconfont icon-agora_AIjiangzao"
            />
            <p>降噪处理：</p>
            <p>
              <label class="prehandle-label container">
                <input
                  ref="smooth"
                  type="checkbox"

                  @change="selectSmooth()"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">平滑</span>
              </label>
              <label class="prehandle-label container">
                <input
                  ref="filter"
                  type="checkbox"

                  @change="selectFilter()"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">滤波</span>
              </label>
            </p>
          </el-row>
          </section>

          <section class="workflow-panel workflow-panel--execute" data-step="03">
            <header class="workflow-panel__header">
              <div>
                <span class="workflow-panel__index data-label">03 / RUN</span>
                <h2 class="atlas-title">执行分析</h2>
              </div>
              <p>使用江西固定 CPU 配置同步分析；页面会等待本批次完成后再刷新成果。</p>
            </header>
          <div class="handle-button execution-action">
            <el-button
              type="primary"
              class="btn-animate btn-animate__shiny"
              :disabled="fileList.length === 0"
              @click="upload('地物分类','semantic_segmentation')"
            >
              开始地物分类
            </el-button>
          </div>
          <div class="run-status" aria-live="polite">
            <p :data-state="analysisRunState">
              {{ analysisRunMessage }}
            </p>
          </div>
          <el-divider v-if="!uploadSrc.prehandle" />
          <div v-if="uploadSrc.prehandle">
            <div v-if="uploadSrc.prehandle===2">
              <div
                id="sub-title"
              >
                CLAHE处理结果预览<i
                  class="iconfont icon-dianji"
                />
              </div>
            </div>
            <div v-else-if="uploadSrc.prehandle===4">
              <div
                id="sub-title"
              >
                锐化处理结果预览<i
                  class="iconfont icon-dianji"
                />
              </div>
            </div>
            <el-divider />
            <el-row
              justify="center"
              :gutter="20"
            >
              <el-col
                :xs="24"
                :sm="24"
                :md="6"
                :lg="6"
                :xl="6"
              >
                <div
                  v-for="(item,index) in before"
                  :key="index"
                >
                  <el-image
                    :src="item"
                    :preview-src-list="[item]"
                    :preview-teleported="true"
                  />
                  <div class="handle-words">
                    原图
                  </div>
                </div>
              </el-col>
              <el-col
                :md="2"
                :lg="2"
                :xl="2"
              />
              <el-col
                v-if="uploadSrc.prehandle===2"
                :xs="24"
                :sm="24"
                :md="6"
                :lg="6"
                :xl="6"
              >
                <div
                  v-for="(item,index) in claheImg"
                  :key="index"
                >
                  <el-image
                    :src="item"
                    :preview-src-list="[item]"
                    :preview-teleported="true"
                  />
                  <div class="handle-words">
                    CLAHE处理后 <span
                      @click="
                        downloadimgWithWords(
                          -1,
                          item,
                          `CLAHE处理图.png`
                        )
                      "
                    ><i class="iconfont icon-xiazai" /></span>
                  </div>
                </div>
              </el-col>
              <el-col
                v-if="uploadSrc.prehandle===4"
                :xs="24"
                :sm="24"
                :md="6"
                :lg="6"
                :xl="6"
              >
                <div
                  v-for="(item,index) in sharpenImg"
                  :key="index"
                >
                  <el-image
                    :src="item"
                    :preview-src-list="[item]"
                    :preview-teleported="true"
                  />
                  <div class="handle-words">
                    锐化处理后 <span
                      @click="
                        downloadimgWithWords(
                          -1,
                          item,
                          `锐化处理图.png`
                        )
                      "
                    ><i class="iconfont icon-xiazai" /></span>
                  </div>
                </div>
              </el-col>
            </el-row>
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
              <p>查看原始影像、分类成果与类别图例；选择图片可放大检查。</p>
            </div>
          </div>
        </template>
        <template #right>
          <div class="history-tools">
          <el-button
            size="mini"
            type="danger"
            plain
            @click="clearCurrentHistory"
          >
            一键清空历史
          </el-button>
          <i
            class="iconfont icon-shuaxin"
            role="button"
            tabindex="0"
            @click="getMore"
            @keydown.enter="getMore"
          ><span
            class="hidden-sm-and-down"
          >点击刷新</span></i>
        </div>
        </template>
      </Tabinfor>
    <el-dialog
      v-model="cutVisible"
      :modal="false"
      title="编辑"
      width="75%"
      top="0"
    >
      <MyVueCropper
        :fileimg="fileimg"
        :funtype="funtype"
        :file="file"
        :child-prehandle="uploadSrc.prehandle"
        :child-denoise="uploadSrc.denoise"
        @cut-changed="notvisible"
        @child-refresh="getMore"
      />
    </el-dialog>
    <ImgShow
      :img-arr="imgArr"
      @delete-item="deleteHistoryItem"
    />
    </section>
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
import { selectClahe, selectFilter, selectSharpen, selectSmooth, } from "@/utils/preHandle";
import ImgShow from "@/components/ImgShow";
import Tabinfor from "@/components/Tabinfor";
import Bottominfor from "@/components/Bottominfor";
import MyVueCropper from "@/components/MyVueCropper";

export default {
  name: "Segmentation",
  components: {
    ImgShow,
    Tabinfor,
    Bottominfor,
    MyVueCropper,
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      document.querySelector(".el-main").scrollTop = 0;
    });
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
      roiYear: ''
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
      if (this.$refs.folderInput) this.$refs.folderInput.value = "";
      if (this.$refs.fileInput) this.$refs.fileInput.value = "";
      this.$message.success("清除成功");
    },
    notvisible() {
      this.cutVisible = false;
      this.fileList = [];
      this.analysisRunState = "idle";
      this.analysisRunMessage = "请先选择 tif / tiff 影像。";
      if (this.$refs.folderInput) this.$refs.folderInput.value = "";
      if (this.$refs.fileInput) this.$refs.fileInput.value = "";
    },
    getMore() {
      this.getUploadImg("地物分类");
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
      if (this.$refs.folderInput) {
        this.$refs.folderInput.value = "";
        this.$refs.folderInput.click();
      }
    },
    openFilePicker() {
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = "";
        this.$refs.fileInput.click();
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
      this.cutVisible = !!this.$refs.cut?.checked;
      this.canUpload = true;
      this.fileimg = window.URL.createObjectURL(file);
    },
    disableCutForBatchUpload() {
      if (this.$refs.cut?.checked) {
        this.$refs.cut.checked = false;
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
      this.isNotCut = this.$refs.cut.checked;
    },
  },
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

</style>
