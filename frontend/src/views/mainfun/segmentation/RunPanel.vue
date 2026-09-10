<template>
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
              :disabled="seg.fileList.length === 0"
              @click="seg.upload('地物分类','semantic_segmentation')"
            >
              开始地物分类
            </el-button>
          </div>
          <div class="run-status" aria-live="polite">
            <p :data-state="seg.analysisRunState">
              {{ seg.analysisRunMessage }}
            </p>
          </div>
          <el-divider v-if="!seg.uploadSrc.prehandle" />
          <div v-if="seg.uploadSrc.prehandle">
            <div v-if="seg.uploadSrc.prehandle===2">
              <div
                id="sub-title"
              >
                CLAHE处理结果预览<i
                  class="iconfont icon-dianji"
                />
              </div>
            </div>
            <div v-else-if="seg.uploadSrc.prehandle===4">
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
                  v-for="(item,index) in seg.before"
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
                v-if="seg.uploadSrc.prehandle===2"
                :xs="24"
                :sm="24"
                :md="6"
                :lg="6"
                :xl="6"
              >
                <div
                  v-for="(item,index) in seg.claheImg"
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
                        seg.downloadimgWithWords(
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
                v-if="seg.uploadSrc.prehandle===4"
                :xs="24"
                :sm="24"
                :md="6"
                :lg="6"
                :xl="6"
              >
                <div
                  v-for="(item,index) in seg.sharpenImg"
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
                        seg.downloadimgWithWords(
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
  </template>

<script>


export default {
  name: 'RunPanel',
  inject: ['seg'],
};
</script>
