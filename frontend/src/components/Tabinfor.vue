<template>
  <div class="tab-information">
    <div class="tab-information__left">
      <slot name="left" />
    </div>
    <div v-if="$slots.mid" class="tab-information__mid">
      <slot name="mid" />
    </div>
    <div v-if="$slots.right" class="tab-information__right">
      <slot name="right" />
    </div>
  </div>
</template>

<script>
export default {
  name: "Tabinfor",
};
</script>

<style scoped>
.tab-information {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 22px;
  min-width: 0;
}

.tab-information__left,
.tab-information__mid,
.tab-information__right {
  min-width: 0;
}

.tab-information__mid {
  text-align: center;
}

.tab-information__right {
  justify-self: end;
  text-align: right;
}

@media (max-width: 768px) {
  .tab-information {
    grid-template-columns: 1fr;
    align-items: start;
    gap: 14px;
  }

  .tab-information__mid,
  .tab-information__right {
    justify-self: stretch;
    text-align: left;
  }
}

@media (max-width: 480px) {
  .tab-information {
    gap: 10px;
  }
}
</style>
