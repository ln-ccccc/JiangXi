<template>
  <div class="header-content">
    <div class="sample-record" aria-label="江西样区档案">
      <span class="sample-record__label data-label">江西样区档案</span>
      <strong class="sample-record__title atlas-title">生态图册</strong>
      <span class="sample-record__id data-label">JX · INTERPRET</span>
    </div>

    <div class="header-right">
      <span v-if="authenticated" class="user-pill">
        <span class="user-caption data-label">用户</span>
        <span>{{ username || "admin" }}</span>
      </span>
      <el-button
        v-if="authenticated"
        plain
        class="logout-btn"
        title="退出登录"
        aria-label="退出登录"
        @click="logout"
      >
        退出
      </el-button>
      <el-button
        v-if="authenticated"
        type="primary"
        class="miner-btn"
        :disabled="!minerUrl"
        :title="minerButtonLabel"
        :aria-label="minerButtonLabel"
        @click="goToMiner"
      >
        <i class="icon-map" aria-hidden="true" />
        <span>{{ minerButtonLabel }}</span>
      </el-button>
    </div>
  </div>
</template>

<script>
import { legacyLogout, legacySession } from "@/api/auth";
import { buildMinerMapUrl } from "@/utils/platformNavigation";

export default {
  name: "HeaderComponent",
  data() {
    return {
      authenticated: false,
      username: "",
    };
  },
  computed: {
    minerUrl() {
      return buildMinerMapUrl(window.location, process.env.VUE_APP_MINER_URL);
    },
    minerButtonLabel() {
      return this.minerUrl ? "返回矿山地图" : "矿山地图地址未配置";
    },
  },
  async mounted() {
    await this.refreshSession();
  },
  methods: {
    async refreshSession() {
      try {
        const response = await legacySession();
        const auth = response?.data?.data || {};
        this.authenticated = Boolean(auth.authenticated);
        this.username = auth.username || "";
      } catch (_) {
        this.authenticated = false;
        this.username = "";
      }
    },
    async logout() {
      try {
        await legacyLogout();
      } finally {
        window.location.assign("/#/login");
      }
    },
    goToMiner() {
      if (!this.minerUrl) return;
      window.location.assign(this.minerUrl);
    },
  },
};
</script>

<style scoped>
.header-content {
  display: flex;
  min-width: 0;
  flex: 1;
  height: 68px;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  font-family: var(--jx-font-body);
  line-height: normal;
}

.sample-record {
  position: relative;
  display: grid;
  min-width: 230px;
  padding: 6px 18px 6px 16px;
  grid-template-columns: auto 1fr;
  align-items: baseline;
  gap: 1px 10px;
  border-left: 2px solid var(--jx-sand);
  background-image: repeating-linear-gradient(
    90deg,
    transparent 0 9px,
    var(--jx-border) 9px 10px
  );
  background-position: left bottom;
  background-repeat: repeat-x;
  background-size: auto 4px;
}

.sample-record__label {
  color: var(--jx-primary);
  font-size: 9px;
  grid-column: 1 / -1;
}

.sample-record__title {
  color: var(--jx-text);
  font-size: 17px;
  font-weight: 600;
}

.sample-record__id {
  color: var(--jx-text-muted);
  font-size: 9px;
  white-space: nowrap;
}

.header-right {
  display: flex;
  min-width: 0;
  flex-shrink: 0;
  align-items: center;
  gap: 9px;
}

.user-pill {
  display: inline-flex;
  min-width: 0;
  height: 36px;
  padding: 0 12px;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius);
  background: var(--jx-surface-muted);
  color: var(--jx-text);
  font-size: 12px;
}

.user-caption {
  color: var(--jx-text-muted);
  font-size: 8px;
}

.logout-btn,
.miner-btn {
  height: 36px;
}

.miner-btn {
  font-size: 12px;
  white-space: nowrap;
}

.miner-btn .icon-map {
  margin-right: 5px;
}

@media (max-width: 1100px) {
  .sample-record {
    min-width: 190px;
  }

  .sample-record__id,
  .user-caption {
    display: none;
  }

  .sample-record__title {
    grid-column: 1 / -1;
  }
}

@media (max-width: 768px) {
  .header-content {
    gap: 8px;
  }

  .sample-record {
    min-width: 108px;
    padding-right: 8px;
    padding-left: 10px;
  }

  .sample-record__label {
    font-size: 8px;
  }

  .sample-record__title {
    font-size: 15px;
  }

  .user-pill {
    display: none;
  }

  .logout-btn,
  .miner-btn {
    padding-right: 9px;
    padding-left: 9px;
    font-size: 11px;
  }
}

@media (max-width: 480px) {
  .sample-record {
    min-width: 56px;
    padding-left: 7px;
  }

  .sample-record__label {
    white-space: nowrap;
  }

  .sample-record__title {
    display: none;
  }

  .logout-btn {
    min-width: 44px;
    padding-right: 7px;
    padding-left: 7px;
  }

  .miner-btn {
    max-width: 146px;
    padding-right: 7px;
    padding-left: 7px;
    white-space: normal;
    line-height: 1.2;
  }

  .miner-btn .icon-map {
    display: none;
  }
}
</style>
