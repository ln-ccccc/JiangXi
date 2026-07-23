<template>
  <div class="result-gallery">
    <div v-if="childImgArr.length === 0" class="result-empty" data-state="idle">
      <el-empty description="尚无分析结果" :image-size="150" />
      <p>请先在上方选择 tif / tiff 影像并执行分析，完成后结果会自动归档到这里。</p>
    </div>

    <article
      v-for="(item,index) in childImgArr"
      :key="item.record_id || item.id || index"
      class="result-record"
    >
      <header class="result-record__header">
        <div>
          <span class="result-record__eyebrow data-label">RECORD {{ item.display_index || (index + 1) }}</span>
          <h3 class="atlas-title">第 {{ item.display_index || (index + 1) }} 组 · {{ item.type || "分析成果" }}</h3>
        </div>
        <button class="result-delete" type="button" @click="$emit('delete-item', item)">
          删除该组
        </button>
      </header>

      <div v-if="item.type === '场景分类'" class="scene-result">
        <span>分类结果</span>
        <strong>{{ sceneClassification(item) }}</strong>
      </div>

      <div v-else class="result-record__body">
        <figure class="result-figure">
          <el-image
            ref="tableTab"
            class="result-image"
            :src="item.before_img"
            :fit="fit"
            :lazy="true"
            :preview-src-list="[item.before_img]"
            :preview-teleported="true"
          />
          <figcaption>
            <span>原始影像</span>
            <small>选择图片可放大检查</small>
          </figcaption>
        </figure>

        <figure class="result-figure result-figure--analysis">
          <el-image
            ref="tableTab"
            class="result-image"
            :src="item.after_img"
            :fit="fit"
            :lazy="true"
            :preview-src-list="[item.after_img]"
            :preview-teleported="true"
          />
          <figcaption>
            <span>分析结果</span>
            <button
              class="result-download"
              type="button"
              @click="downloadimgWithWords(
                item.display_index || (index + 1),
                item.after_img,
                `${item.type}结果图.png`
              )"
            >
              <i class="iconfont icon-xiazai" aria-hidden="true" />
              下载结果
            </button>
          </figcaption>
        </figure>

        <aside v-if="isLandClassification(item)" class="classification-legend" aria-label="地物分类类别图例">
          <span class="classification-legend__eyebrow data-label">LEGEND</span>
          <h4 class="atlas-title">类别图例</h4>
          <ul>
            <li><i class="legend-swatch legend-swatch--grass" /><span>草地</span><small>Grassland</small></li>
            <li><i class="legend-swatch legend-swatch--forest" /><span>林地</span><small>Forest</small></li>
            <li><i class="legend-swatch legend-swatch--building" /><span>建筑</span><small>Building</small></li>
            <li><i class="legend-swatch legend-swatch--road" /><span>道路</span><small>Road</small></li>
            <li><i class="legend-swatch legend-swatch--bare" /><span>裸地</span><small>Bareground</small></li>
            <li><i class="legend-swatch legend-swatch--water" /><span>水体</span><small>Water</small></li>
          </ul>
        </aside>
      </div>

      <dl v-if="item.data && item.data.index_type" class="spectral-stat">
        <div>
          <dt>指数</dt>
          <dd>{{ item.data.index_type }}</dd>
        </div>
        <div>
          <dt>矿山边界内平均值</dt>
          <dd>{{ formatNumber(item.data.mean) }}</dd>
        </div>
        <div v-if="item.data.valid_pixel_count !== undefined">
          <dt>有效像元</dt>
          <dd>{{ item.data.valid_pixel_count }}</dd>
        </div>
        <div v-if="item.data.boundary_status && item.data.boundary_status !== 'ok'" data-state="error">
          <dt>边界状态</dt>
          <dd>{{ boundaryStatusText(item.data.boundary_status) }}</dd>
        </div>
      </dl>
    </article>
  </div>
</template>

<script>
import { downloadimgWithWords } from "@/utils/download.js";

export default {
  name: "Imgshow",
  emits: ["delete-item"],
  props: {
    imgArr:{
      type:Array,
      default(){
        return []
      }
    },
  },
  data() {
    return {
      fit: "fill",
      childImgArr:[]
    };
  },
  mounted() {
    this.childImgArr = this.imgArr
  },
  updated() {
    this.childImgArr = this.imgArr
  },
  methods: {
    downloadimgWithWords,
    isLandClassification(item) {
      return ["地物分类", "semantic_segmentation"].includes(item?.type);
    },
    sceneClassification(item) {
      const data = item?.data || {};
      const key = Object.keys(data)[0];
      return key ? `${key}：${data[key]}` : "暂无分类信息";
    },
    formatNumber(value) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "暂无";
      }
      return Number(value).toFixed(4);
    },
    boundaryStatusText(status) {
      const statusMap = {
        kml_missing: "未找到KML边界文件",
        no_boundary_overlap: "影像与矿山边界无重叠",
        raster_missing_crs: "影像缺少坐标系",
      };
      return statusMap[status] || status;
    },
  },
};
</script>

<style scoped lang="less">
.result-gallery {
  display: grid;
  gap: 18px;
  margin-top: 22px;
}

.result-empty {
  padding: 20px;
  border: 1px dashed var(--jx-border);
  border-radius: var(--jx-radius-large);
  background: var(--jx-surface-muted);
  text-align: center;
}

.result-empty p {
  max-width: 540px;
  margin: -12px auto 12px;
  color: var(--jx-text-muted);
}

.result-record {
  overflow: hidden;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius-large);
  background: var(--jx-bg-elevated);
}

.result-record__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--jx-border);
  background: var(--jx-surface-muted);
}

.result-record__eyebrow,
.classification-legend__eyebrow {
  color: var(--jx-sand);
  font-size: 10px;
}

.result-record__header h3 {
  margin: 2px 0 0;
  color: var(--jx-text);
  font-size: 19px;
}

.result-delete,
.result-download {
  border: 0;
  background: transparent;
  cursor: pointer;
  font: inherit;
}

.result-delete {
  color: var(--jx-danger);
}

.result-download {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--jx-primary);
}

.result-delete:focus-visible,
.result-download:focus-visible {
  outline: 2px solid var(--jx-primary);
  outline-offset: 3px;
}

.result-record__body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)) minmax(180px, 0.58fr);
  gap: 16px;
  padding: 18px;
}

.result-figure {
  min-width: 0;
  margin: 0;
}

.result-image {
  display: block;
  width: 100%;
  aspect-ratio: 1 / 1;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius);
  background: var(--jx-surface);
}

.result-figure figcaption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 44px;
  color: var(--jx-text);
}

.result-figure figcaption small {
  color: var(--jx-text-muted);
}

.classification-legend {
  align-self: stretch;
  padding: 16px;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius);
  background: var(--jx-surface-muted);
}

.classification-legend h4 {
  margin: 2px 0 14px;
  color: var(--jx-text);
  font-size: 17px;
}

.classification-legend ul {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.classification-legend li {
  display: grid;
  grid-template-columns: 16px minmax(36px, auto) 1fr;
  align-items: center;
  gap: 8px;
  color: var(--jx-text);
}

.classification-legend small {
  color: var(--jx-text-muted);
}

.legend-swatch {
  width: 14px;
  height: 14px;
  border: 1px solid var(--jx-border-strong);
  border-radius: 3px;
}

.legend-swatch--grass { background: rgb(0, 255, 0); }
.legend-swatch--forest { background: rgb(0, 128, 0); }
.legend-swatch--building { background: rgb(255, 0, 0); }
.legend-swatch--road { background: rgb(255, 255, 0); }
.legend-swatch--bare { background: rgb(255, 0, 255); }
.legend-swatch--water { background: rgb(0, 191, 255); }

.spectral-stat {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin: 0;
  padding: 0 18px 18px;
}

.spectral-stat > div {
  padding: 12px;
  border: 1px solid var(--jx-border);
  background: var(--jx-surface-muted);
}

.spectral-stat dt {
  color: var(--jx-text-muted);
  font-size: 12px;
}

.spectral-stat dd {
  margin: 3px 0 0;
  color: var(--jx-text);
  font-family: var(--jx-font-data);
}

.spectral-stat [data-state="error"] dd {
  color: var(--jx-warning);
}

.scene-result {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin: 18px;
  padding: 18px;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius);
  color: var(--jx-text-muted);
}

.scene-result strong {
  color: var(--jx-primary);
}

@media (max-width: 1100px) {
  .result-record__body {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .classification-legend {
    grid-column: 1 / -1;
  }

  .classification-legend ul {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .spectral-stat {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .result-record__body,
  .spectral-stat {
    grid-template-columns: 1fr;
  }

  .classification-legend {
    grid-column: auto;
  }

  .classification-legend ul {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 480px) {
  .result-record__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .result-record__body {
    padding: 12px;
  }

  .result-figure figcaption,
  .classification-legend ul {
    align-items: flex-start;
    grid-template-columns: 1fr;
  }

  .result-figure figcaption {
    flex-direction: column;
    padding: 10px 0;
  }
}
</style>
