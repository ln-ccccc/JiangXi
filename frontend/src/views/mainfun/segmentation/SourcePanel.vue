<template>
          <section class="workflow-panel" data-step="01">
            <header class="workflow-panel__header">
              <div>
                <span class="workflow-panel__index data-label">01 / SOURCE</span>
                <h2 class="atlas-title">数据源</h2>
              </div>
              <p>选择包含江西矿区影像的文件夹，或直接选择一个或多个 tif / tiff 文件。</p>
            </header>
          <div
            v-if="seg.fileList.length"
            class="clear-queue"
          >
            <el-button
              type="primary"
              class="btn-animate2 btn-animate__surround"
              @click="seg.clearQueue"
            >
              清空图片
            </el-button>
          </div>
          <div
            class="upload-card upload-dropzone"
            role="button"
            tabindex="0"
            aria-label="选择 tif 或 tiff 遥感影像文件夹"
            @click="seg.fileClick"
            @keydown.enter="seg.fileClick"
            @keydown.space.prevent="seg.fileClick"
            @dragover.prevent
            @dragenter.prevent
            @drop.prevent="seg.handleNativeDrop"
          >
            <i class="iconfont icon-yunduanshangchuan" />
            <div class="el-upload__text">
              将文件夹拖到此处，或<em>点击上传整个文件夹</em>
            </div>
            <div class="el-upload__tip">
              递归读取文件夹内容，仅上传 tif / tiff
            </div>
            <div
              v-if="seg.fileList.length"
              class="selected-files"
              @click.stop
            >
              <div class="selected-files__title">
                已选择 {{ seg.fileList.length }} 个 tif/tiff 文件
              </div>
              <div
                v-for="item in seg.fileList.slice(0, 8)"
                :key="item.uid"
                class="selected-files__item"
              >
                {{ item.name }}
              </div>
              <div
                v-if="seg.fileList.length > 8"
                class="selected-files__item"
              >
                其余 {{ seg.fileList.length - 8 }} 个文件待上传
              </div>
            </div>
          </div>
          <el-row justify="center">
            <el-button
              plain
              size="small"
              style="margin-top: 8px;"
              @click="seg.fileClick"
            >
              选择整个文件夹
            </el-button>
            <el-button
              plain
              size="small"
              style="margin-top: 8px; margin-left: 8px;"
              @click="seg.openFilePicker"
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
            @change="seg.handleFolderSelect"
          >
          <input
            ref="fileInput"
            type="file"
            accept=".tif,.tiff,.TIF,.TIFF"
            multiple
            style="display: none;"
            @change="seg.handleFileSelect"
          >
          <el-row justify="center">
            <div class="upload-guidance">
              支持拖拽文件夹、点击选择整个文件夹，自动递归过滤非 tif / tiff 文件
            </div>
          </el-row>
          </section>
  </template>

<script>


export default {
  name: 'SourcePanel',
  inject: ['seg'],
};
</script>
