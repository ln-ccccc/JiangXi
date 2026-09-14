<template>
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
                  @change="seg.select()"
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
              v-model="seg.roiYear"
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
                <!-- 受控复选框：勾选态由 seg.uploadSrc.prehandle 驱动，不再走 ref -->
                <input
                  type="checkbox"
                  :checked="seg.uploadSrc.prehandle === 2"
                  @change="seg.selectClahe('地物分类', $event)"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">CLAHE</span>
              </label>
            </p>
            <p>
              <label class="prehandle-label container">
                <input
                  type="checkbox"
                  :checked="seg.uploadSrc.prehandle === 4"
                  @change="seg.selectSharpen('地物分类', $event)"
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
                  type="checkbox"
                  :checked="seg.uploadSrc.denoise === 3"
                  @change="seg.selectSmooth()"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">平滑</span>
              </label>
              <label class="prehandle-label container">
                <input
                  type="checkbox"
                  :checked="seg.uploadSrc.denoise === 5"
                  @change="seg.selectFilter()"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">滤波</span>
              </label>
            </p>
          </el-row>
          </section>
  </template>

<script>


export default {
  name: 'ParamsPanel',
  inject: ['seg'],
};
</script>
