<template>
  <el-container
    class="atlas-shell"
    :class="{ 'sidebar-is-collapsed': isCollapse }"
  >
    <el-aside class="atlas-sidebar-region" width="auto">
      <AsideVue
        :is-collapse="isCollapse"
        :active-index="activeIndex"
        @navigate="closeSidebarOnMobile"
      />
    </el-aside>

    <button
      v-if="!isCollapse"
      class="shell-scrim"
      type="button"
      aria-label="收起图册索引"
      @click="goCollapse"
    />

    <el-container class="atlas-workspace">
      <el-header class="platform-header" height="68px">
        <div class="header-layout">
          <button
            class="sidebar-toggle"
            type="button"
            :aria-expanded="!isCollapse"
            aria-controls="jiangxi-atlas-index"
            :title="isCollapse ? '展开图册索引' : '收起图册索引'"
            @click="goCollapse"
          >
            <i class="icon-menu" aria-hidden="true" />
            <span class="sr-only">{{ isCollapse ? "展开图册索引" : "收起图册索引" }}</span>
          </button>
          <Tablogin />
        </div>
      </el-header>

      <el-main class="main-ctx">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
        <el-backtop
          target=".main-ctx"
          :bottom="40"
          :visibility-height="50"
          :right="27"
        />
      </el-main>
    </el-container>
  </el-container>
</template>

<script>
import "@/assets/css/app.css";
import AsideVue from "@/components/AsideVue";
import Tablogin from "@/components/Tablogin";

export default {
  name: "Home",
  components: {
    AsideVue,
    Tablogin,
  },
  data() {
    return {
      isCollapse: false,
      activeIndex: this.$route.path,
    };
  },
  watch: {
    "$route.path"(path) {
      this.activeIndex = path;
      this.closeSidebarOnMobile();
    },
  },
  mounted() {
    this.syncCollapse();
    window.addEventListener("resize", this.syncCollapse);
    document.body.style.overflow = "hidden";
  },
  beforeUnmount() {
    window.removeEventListener("resize", this.syncCollapse);
    document.body.style.overflow = "";
  },
  methods: {
    syncCollapse() {
      this.isCollapse = document.documentElement.clientWidth <= 1100;
    },
    goCollapse() {
      this.isCollapse = !this.isCollapse;
    },
    closeSidebarOnMobile() {
      if (document.documentElement.clientWidth <= 768) {
        this.isCollapse = true;
      }
    },
  },
};
</script>

<style scoped>
.atlas-shell {
  position: relative;
  width: 100%;
  min-width: 0;
  min-height: 100vh;
  overflow: hidden;
  background: var(--jx-bg);
}

.atlas-sidebar-region {
  flex: 0 0 auto;
  height: 100vh;
  overflow: hidden;
  transition: width var(--transition-normal), transform var(--transition-normal);
}

.atlas-workspace {
  min-width: 0;
  height: 100vh;
}

.platform-header {
  position: relative;
  z-index: 5;
  flex: 0 0 68px;
  min-width: 0;
  width: 100%;
  height: 68px;
  padding: 0 22px;
  line-height: normal;
  background: var(--jx-bg-elevated);
  border-bottom: 1px solid var(--jx-border);
}

.header-layout {
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 0;
  height: 100%;
  gap: 16px;
}

.sidebar-toggle {
  display: inline-grid;
  flex: 0 0 40px;
  width: 40px;
  height: 40px;
  padding: 0;
  place-items: center;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius);
  background: var(--jx-surface-muted);
  color: var(--jx-text-muted);
  cursor: pointer;
  transition: border-color var(--transition-fast), color var(--transition-fast);
}

.sidebar-toggle:hover {
  border-color: var(--jx-border-strong);
  color: var(--jx-primary);
}

.sidebar-toggle .icon-menu {
  font-size: 19px;
}

.main-ctx {
  --el-main-padding: 22px;
  width: 100%;
  min-width: 0;
  height: calc(100vh - 68px);
  overflow-x: hidden;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.shell-scrim {
  display: none;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 1100px) {
  .platform-header {
    padding: 0 18px;
  }
}

@media (max-width: 768px) {
  .atlas-sidebar-region {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 30;
    width: 280px !important;
    transform: translateX(0);
  }

  .sidebar-is-collapsed .atlas-sidebar-region {
    transform: translateX(-100%);
    pointer-events: none;
  }

  .shell-scrim {
    position: fixed;
    inset: 0;
    z-index: 20;
    display: block;
    padding: 0;
    border: 0;
    background: rgba(0, 0, 0, 0.56);
    cursor: pointer;
  }

  .platform-header {
    padding: 0 12px;
  }

  .header-layout {
    gap: 10px;
  }

  .main-ctx {
    --el-main-padding: 14px 10px;
  }
}

@media (max-width: 480px) {
  .platform-header {
    padding: 0 8px;
  }

  .header-layout {
    gap: 7px;
  }

  .sidebar-toggle {
    flex-basis: 36px;
    width: 36px;
    height: 36px;
  }
}
</style>
