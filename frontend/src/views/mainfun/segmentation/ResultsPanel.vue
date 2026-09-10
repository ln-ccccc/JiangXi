<template>
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
            @click="seg.clearCurrentHistory"
          >
            一键清空历史
          </el-button>
          <i
            class="iconfont icon-shuaxin"
            role="button"
            tabindex="0"
            @click="seg.getMore"
            @keydown.enter="seg.getMore"
          ><span
            class="hidden-sm-and-down"
          >点击刷新</span></i>
        </div>
        </template>
      </Tabinfor>
    <el-dialog
      v-model="seg.cutVisible"
      :modal="false"
      title="编辑"
      width="75%"
      top="0"
    >
      <MyVueCropper
        :fileimg="seg.fileimg"
        :funtype="seg.funtype"
        :file="seg.file"
        :child-prehandle="seg.uploadSrc.prehandle"
        :child-denoise="seg.uploadSrc.denoise"
        @cut-changed="seg.notvisible"
        @child-refresh="seg.getMore"
      />
    </el-dialog>
    <ImgShow
      :img-arr="seg.imgArr"
      @delete-item="deleteHistoryItem"
    />
    </section>
  </template>

<script>
import Tabinfor from '@/components/Tabinfor';
import MyVueCropper from '@/components/MyVueCropper';
import ImgShow from '@/components/ImgShow';

export default {
  name: 'ResultsPanel',
  components: { Tabinfor, MyVueCropper, ImgShow },
  inject: ['seg'],
};
</script>
