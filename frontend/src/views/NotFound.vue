<template>
  <main class="not-found-page">
    <div class="not-found-contours" aria-hidden="true" />
    <section class="not-found-record" aria-labelledby="not-found-title">
      <p class="record-label data-label">江西生态图册 · 档案校验</p>
      <div class="error-index data-label">404</div>
      <div class="specimen-scale" aria-hidden="true" />
      <h1 id="not-found-title" class="atlas-title">未找到这份样区档案</h1>
      <p>当前地址没有对应工作流。返回地物分类重新开始，或回到上一页检查路径。</p>
      <div class="not-found-actions">
        <el-button type="primary" @click="goHome">返回地物分类</el-button>
        <el-button plain @click="goBack">返回上一页</el-button>
      </div>
    </section>
  </main>
</template>

<script>
export default {
  name: "NotFound",
  methods: {
    goBack() {
      this.$router.go(-1);
    },
    goHome() {
      this.$router.push("/segmentation");
    },
  },
};
</script>

<style scoped>
.not-found-page {
  position: relative;
  display: grid;
  min-height: 100vh;
  padding: 32px;
  overflow: hidden;
  place-items: center;
  background: var(--jx-bg);
}

.not-found-contours {
  position: absolute;
  inset: 0;
  opacity: 0.14;
  background: repeating-radial-gradient(
    ellipse at 70% 45%,
    transparent 0 30px,
    var(--jx-border) 31px 32px,
    transparent 33px 52px
  );
  mask-image: linear-gradient(90deg, transparent, black);
}

.not-found-record {
  position: relative;
  z-index: 1;
  width: min(620px, 100%);
  padding: clamp(30px, 6vw, 60px);
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius-large);
  background: var(--jx-surface);
  box-shadow: var(--shadow-xl);
}

.record-label {
  margin: 0 0 22px;
  color: var(--jx-sand);
  font-size: 9px;
}

.error-index {
  color: var(--jx-primary);
  font-size: clamp(60px, 12vw, 112px);
  font-weight: 600;
  line-height: 1;
}

.specimen-scale {
  width: 100%;
  height: 9px;
  margin: 18px 0 28px;
  border-top: 1px solid var(--jx-border-strong);
  background: repeating-linear-gradient(
    90deg,
    var(--jx-border-strong) 0 1px,
    transparent 1px 12px
  );
}

.not-found-record h1 {
  margin: 0 0 12px;
  color: var(--jx-text);
  font-size: clamp(28px, 5vw, 42px);
  font-weight: 600;
}

.not-found-record > p:not(.record-label) {
  margin: 0;
  color: var(--jx-text-muted);
  line-height: 1.8;
}

.not-found-actions {
  display: flex;
  margin-top: 30px;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 768px) {
  .not-found-page {
    padding: 20px;
  }
}

@media (max-width: 480px) {
  .not-found-page {
    padding: 12px;
  }

  .not-found-record {
    padding: 28px 20px;
  }

  .not-found-actions {
    display: grid;
  }
}
</style>
