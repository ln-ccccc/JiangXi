<template>
  <footer class="platform-footer">
    <div>
      <strong>江西省矿山生态修复智能监测平台</strong>
      <span>解译与指数分析</span>
    </div>
    <p>江西矿区本地部署 · 同步 CPU 分析 · 成果独立归档</p>
  </footer>
</template>

<script>
export default {
  name: "Bottominfor",
};
</script>

<style scoped>
.platform-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-top: 28px;
  padding: 18px 4px 6px;
  border-top: 1px solid var(--jx-border);
  color: var(--jx-text-muted);
  font-size: 13px;
}

.platform-footer div {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
}

.platform-footer strong {
  color: var(--jx-text);
  font-weight: 600;
}

.platform-footer p {
  margin: 0;
  text-align: right;
}

@media (max-width: 768px) {
  .platform-footer {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .platform-footer p {
    text-align: left;
  }
}
</style>
