<template>
  <el-menu
    id="jiangxi-atlas-index"
    class="geoview-sidebar"
    :collapse="isCollapse"
    :default-active="activeIndex"
    @select="$emit('navigate')"
  >
    <div class="atlas-contours" aria-hidden="true" />

    <div class="atlas-brand">
      <button
        class="atlas-mark atlas-title"
        type="button"
        aria-label="进入地物分类"
        title="进入地物分类"
        @click="handleAtlasMarkClick"
      >
        赣
      </button>
      <div v-show="!isCollapse" class="atlas-brand-copy">
        <span class="atlas-province data-label">江西</span>
        <button class="atlas-name atlas-title" type="button" @click="goShow">
          生态图册
        </button>
        <p class="atlas-subtitle">解译与指数分析</p>
        <p class="sync-state data-label">
          <span class="sync-dot" aria-hidden="true" />同步 CPU
        </p>
      </div>
    </div>

    <div v-show="!isCollapse" class="section-label data-label">工作流索引</div>

    <el-menu-item
      index="/segmentation"
      title="进入地物分类"
      @click="goSegmentation"
    >
      <i class="iconfont icon-erfenleibianhuajiance16px" aria-hidden="true" />
      <template #title>
        <div class="tool-copy">
          <strong>地物分类</strong>
          <span>识别地表覆盖类型</span>
        </div>
      </template>
    </el-menu-item>

    <el-menu-item
      index="/spectralindices"
      title="进入光谱指数"
      @click="goSpectralIndices"
    >
      <i class="iconfont icon-jishu" aria-hidden="true" />
      <template #title>
        <div class="tool-copy">
          <strong>光谱指数</strong>
          <span>计算并对照指数结果</span>
        </div>
      </template>
    </el-menu-item>

    <section v-show="!isCollapse" class="sidebar-guidance" aria-labelledby="atlas-guidance-title">
      <div class="specimen-scale" aria-hidden="true" />
      <p id="atlas-guidance-title" class="guidance-title data-label">操作提示</p>
      <p class="guidance-lead">先选择工作流，再上传待解译影像。</p>
      <ul>
        <li>分类：准备 tif/tiff 与四位年份。</li>
        <li>指数：上传影像后选择目标指数。</li>
      </ul>
    </section>
  </el-menu>
</template>

<script>
import {
  goSegmentation,
  goSpectralIndices,
} from "@/utils/gosomewhere.js";

export default {
  name: "JiangxiAtlasAside",
  emits: ["navigate"],
  props: {
    isCollapse: {
      type: Boolean,
      default: false,
    },
    activeIndex: {
      type: String,
      default: "/segmentation",
    },
  },
  methods: {
    goSegmentation,
    goSpectralIndices,
    handleAtlasMarkClick() {
      goSegmentation.call(this);
      this.$emit("navigate");
    },
    goShow() {
      this.$message.success("江西生态图册已就绪，请选择地物分类或光谱指数");
    },
  },
};
</script>

<style scoped>
.geoview-sidebar {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 280px;
  height: 100vh;
  padding: 0 12px 18px;
  overflow: hidden;
  background: var(--jx-bg-elevated) !important;
  font-family: var(--jx-font-body);
  transition: width var(--transition-normal);
}

.geoview-sidebar.el-menu--collapse {
  width: 76px;
  padding-right: 6px;
  padding-left: 6px;
}

.atlas-contours {
  position: absolute;
  inset: 0 0 auto;
  height: 220px;
  pointer-events: none;
  opacity: 0.16;
  background:
    repeating-radial-gradient(
      ellipse at 10% 0%,
      transparent 0 16px,
      var(--jx-border) 17px 18px,
      transparent 19px 31px
    );
  mask-image: linear-gradient(to bottom, black, transparent);
}

.atlas-brand {
  position: relative;
  z-index: 1;
  display: flex;
  min-height: 148px;
  padding: 24px 6px 18px;
  align-items: flex-start;
  gap: 13px;
  border-bottom: 1px solid var(--jx-border);
}

.atlas-mark {
  display: grid;
  flex: 0 0 46px;
  width: 46px;
  height: 52px;
  padding: 0;
  place-items: center;
  border: 1px solid var(--jx-border-strong);
  border-radius: 3px 3px var(--jx-radius) 3px;
  background: var(--jx-surface);
  color: var(--jx-sand);
  font-size: 26px;
  cursor: pointer;
}

.atlas-brand-copy {
  min-width: 0;
  text-align: left;
}

.atlas-province {
  display: block;
  margin-bottom: 2px;
  color: var(--jx-primary);
  font-size: 10px;
}

.atlas-name {
  display: block;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--jx-text);
  font-size: 24px;
  line-height: 1.25;
  cursor: pointer;
}

.atlas-subtitle {
  margin: 5px 0 9px;
  color: var(--jx-text-muted);
  font-size: 12px;
}

.sync-state {
  display: flex;
  margin: 0;
  align-items: center;
  gap: 7px;
  color: var(--jx-text-muted);
  font-size: 9px;
}

.sync-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--jx-success);
}

.section-label {
  position: relative;
  z-index: 1;
  margin: 22px 12px 8px;
  color: var(--jx-text-muted);
  font-size: 9px;
  text-align: left;
}

.geoview-sidebar :deep(.el-menu-item) {
  position: relative;
  z-index: 1;
  height: 66px;
  margin: 6px 0;
  padding: 0 14px !important;
  line-height: normal;
}

.geoview-sidebar :deep(.el-menu-item::before) {
  position: absolute;
  top: 14px;
  bottom: 14px;
  left: -1px;
  width: 2px;
  background: var(--jx-sand);
  content: "";
  opacity: 0;
}

.geoview-sidebar :deep(.el-menu-item.is-active::before) {
  opacity: 1;
}

.geoview-sidebar :deep(.el-menu-item .iconfont) {
  width: 28px;
  margin-right: 8px;
  color: var(--jx-text-muted);
  font-size: 19px;
  text-align: center;
}

.geoview-sidebar :deep(.el-menu-item.is-active .iconfont) {
  color: var(--jx-primary);
}

.tool-copy {
  display: grid;
  gap: 5px;
  min-width: 0;
  text-align: left;
}

.tool-copy strong {
  color: inherit;
  font-size: 14px;
  font-weight: 600;
}

.tool-copy span {
  color: var(--jx-text-muted);
  font-size: 11px;
}

.sidebar-guidance {
  position: relative;
  z-index: 1;
  margin: auto 6px 0;
  padding: 18px 2px 0;
  border-top: 1px solid var(--jx-border);
  color: var(--jx-text-muted);
  text-align: left;
}

.specimen-scale {
  width: 100%;
  height: 8px;
  margin-bottom: 14px;
  background: repeating-linear-gradient(
    90deg,
    var(--jx-border-strong) 0 1px,
    transparent 1px 10px
  );
}

.guidance-title {
  margin: 0 0 8px;
  color: var(--jx-sand);
  font-size: 9px;
}

.guidance-lead {
  margin: 0 0 8px;
  color: var(--jx-text);
  font-size: 12px;
}

.sidebar-guidance ul {
  display: grid;
  margin: 0;
  padding: 0;
  gap: 5px;
}

.sidebar-guidance li {
  font-size: 11px;
  line-height: 1.55;
}

.el-menu--collapse .atlas-brand {
  min-height: 94px;
  padding: 20px 8px;
  justify-content: center;
}

.el-menu--collapse .atlas-mark {
  flex-basis: 42px;
  width: 42px;
  height: 48px;
  font-size: 23px;
}

.el-menu--collapse :deep(.el-menu-item) {
  justify-content: center;
  padding: 0 !important;
}

.el-menu--collapse :deep(.el-menu-item .iconfont) {
  margin: 0;
}

@media (max-width: 768px) {
  .geoview-sidebar {
    width: 280px;
    height: 100dvh;
  }
}
</style>
