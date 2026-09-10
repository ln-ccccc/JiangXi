<template>
  <header class="header">
    <div class="header-left">
      <div class="logo-area">
        <span class="brand-mark" aria-hidden="true"></span>
        <div class="brand-copy">
          <h1 class="title">{{ APP_TITLE }}</h1>
          <span class="brand-meta">生态监测档案</span>
        </div>
      </div>
      <div class="status-capsule" role="group" aria-label="实时状态">
        <div class="status-item weather-widget">
          <span class="weather-icon">{{ weatherIcon }}</span>
          <div class="weather-info">
            <span class="temp">{{ temperature }}°C</span>
            <span class="aqi" :class="getAqiClass(airQuality)">{{
              airQuality ? `空气${airQuality}` : '空气—'
            }}</span>
          </div>
        </div>
        <span class="status-divider" aria-hidden="true"></span>
        <div class="status-item time-widget">{{ currentDate }} {{ currentTime }}</div>
        <div class="status-item user-profile">
          <span class="role">{{ username || '管理员' }}</span>
        </div>
      </div>
    </div>
    <div class="header-right">
      <button v-if="username" class="secondary-btn" type="button" @click="$emit('logout')">
        <span>退出登录</span>
      </button>
      <button class="secondary-btn" type="button" @click="$emit('open-workspace')">
        <span>项目工作台</span>
      </button>
      <div class="platform-link-control">
        <button
          class="system-btn"
          type="button"
          :disabled="!geoViewUrl"
          :title="geoViewButtonLabel"
          :aria-label="geoViewButtonLabel"
          @click="goToGeoView"
        >
          <span>解译平台</span>
          <svg
            viewBox="0 0 24 24"
            width="16"
            height="16"
            stroke="currentColor"
            stroke-width="2"
            fill="none"
          >
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
        <span v-if="!geoViewUrl" class="platform-link-hint" role="status">
          解译平台地址未配置
        </span>
      </div>
    </div>
  </header>
</template>

<script setup>
import { APP_TITLE } from '../config/minerDefaults.js';
import { buildGeoViewUrl } from '../navigation/platformLinks.js';

defineProps({
  weatherIcon: String,
  temperature: [Number, String],
  airQuality: String,
  currentDate: String,
  currentTime: String,
  getAqiClass: Function,
  username: {
    type: String,
    default: '',
  },
});

defineEmits(['logout', 'open-workspace']);

const geoViewUrl = buildGeoViewUrl(import.meta.env.VITE_GEOVIEW_URL);
const geoViewButtonLabel = geoViewUrl ? '打开解译平台' : '解译平台地址未配置';

const goToGeoView = () => {
  if (!geoViewUrl) {
    return;
  }

  window.location.href = geoViewUrl;
};
</script>

<style scoped>
.header {
  height: 60px;
  min-height: 60px;
  width: 100%;
  background: var(--jx-surface-glass);
  backdrop-filter: var(--jx-blur);
  -webkit-backdrop-filter: var(--jx-blur);
  border-bottom: 1px solid var(--jx-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 0 clamp(12px, 2.4vw, 28px);
  z-index: 2000;
  overflow: hidden;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: clamp(8px, 1.4vw, 18px);
}

.header-left {
  flex: 1 1 auto;
}

.logo-area {
  display: flex;
  align-items: center;
  flex: 0 1 auto;
  min-width: 0;
  gap: 10px;
}

.brand-mark {
  width: 10px;
  height: 26px;
  flex: 0 0 auto;
  border-radius: 3px;
  background: linear-gradient(180deg, var(--jx-primary) 0%, rgba(127, 216, 166, 0.35) 100%);
}

.brand-copy {
  min-width: 0;
}

.title {
  overflow: hidden;
  color: var(--jx-text);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.02em;
  line-height: 1.1;
  margin: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.brand-meta {
  display: block;
  margin-top: 3px;
  color: var(--jx-text-muted);
  font-size: 9px;
  letter-spacing: 0.16em;
  line-height: 1;
}

.status-capsule {
  display: flex;
  align-items: center;
  flex: 0 1 auto;
  min-width: 0;
  max-width: 100%;
  gap: 2px;
  padding: 4px;
  color: var(--jx-text-muted);
  background: rgba(7, 25, 35, 0.36);
  border: 1px solid rgba(156, 231, 189, 0.14);
  border-radius: 999px;
  transition:
    background 0.2s,
    border-color 0.2s,
    box-shadow 0.2s;
}

.status-capsule:hover {
  background: rgba(7, 25, 35, 0.52);
  border-color: var(--jx-border);
  box-shadow: 0 4px 18px rgba(3, 14, 20, 0.2);
}

.status-item {
  display: flex;
  align-items: center;
  min-width: 0;
  padding: 4px 8px;
  border-radius: 999px;
  transition:
    background 0.2s,
    color 0.2s;
}

.status-item:hover {
  color: var(--jx-text);
  background: rgba(255, 255, 255, 0.04);
}

.status-divider {
  width: 1px;
  height: 16px;
  flex: 0 0 auto;
  background: var(--jx-border);
  opacity: 0.7;
}

.weather-widget {
  gap: 8px;
}

.weather-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  font-size: 12px;
  line-height: 1.2;
}

.temp {
  color: var(--jx-sand);
  font-weight: 600;
}

.aqi {
  padding: 1px 4px;
  border-radius: var(--jx-radius);
  font-size: 10px;
  color: #fff;
}

.aqi-1 {
  background: rgba(0, 228, 0, 0.6);
}
.aqi-2 {
  background: rgba(255, 255, 0, 0.6);
  color: #000;
}
.aqi-3 {
  background: rgba(255, 126, 0, 0.6);
}
.aqi-4 {
  background: rgba(255, 0, 0, 0.6);
}
.aqi-5 {
  background: rgba(153, 0, 76, 0.6);
}
.aqi-6 {
  background: rgba(126, 0, 35, 0.6);
}

.time-widget {
  flex: 0 1 auto;
  color: var(--jx-text-muted);
  font-size: 11px;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.user-profile {
  max-width: 120px;
  color: var(--jx-text);
}

.role {
  overflow: hidden;
  color: inherit;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.secondary-btn,
.system-btn {
  display: flex;
  align-items: center;
  min-height: 36px;
  padding: 7px 12px;
  gap: 8px;
  border: 1px solid transparent;
  border-radius: var(--jx-radius);
  cursor: pointer;
  font-weight: 500;
  white-space: nowrap;
  transition:
    transform 0.2s,
    background 0.2s,
    border-color 0.2s,
    box-shadow 0.2s,
    color 0.2s;
}

.secondary-btn {
  color: var(--jx-text-muted);
  background: transparent;
  border-color: var(--jx-border);
}

.system-btn {
  background: var(--jx-primary);
  color: var(--jx-bg);
}

.platform-link-control {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 2px;
}

.platform-link-hint {
  color: var(--jx-sand);
  font-size: 10px;
  line-height: 1;
  text-align: center;
}

.secondary-btn:hover {
  color: var(--jx-text);
  background: var(--jx-surface-muted);
  border-color: var(--jx-border-strong);
  box-shadow: 0 4px 12px rgba(3, 14, 20, 0.2);
  transform: translateY(-1px);
}

.system-btn:hover {
  background: var(--jx-primary-hover);
  box-shadow: 0 4px 12px rgba(156, 231, 189, 0.25);
  transform: translateY(-1px);
}

.system-btn:disabled,
.system-btn:disabled:hover {
  cursor: not-allowed;
  opacity: 0.55;
  background: var(--jx-primary);
  box-shadow: none;
  transform: none;
}

.secondary-btn:focus-visible,
.system-btn:focus-visible {
  outline: 2px solid var(--jx-primary);
  outline-offset: 3px;
}

@media (max-width: 960px) {
  .brand-meta {
    display: none;
  }

  .status-item {
    padding-inline: 6px;
  }

  .secondary-btn,
  .system-btn {
    padding-inline: 10px;
  }
}

@media (max-width: 760px) {
  .header-left,
  .header-right {
    gap: 8px;
  }

  .time-widget,
  .status-divider {
    display: none;
  }

  .user-profile {
    max-width: 88px;
  }

  .system-btn span {
    max-width: 10ch;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

@media (max-width: 560px) {
  .header {
    gap: 6px;
    padding-inline: 10px;
  }

  .title {
    font-size: 16px;
  }

  .weather-info {
    display: none;
  }

  .weather-widget {
    padding-inline: 6px;
  }

  .user-profile {
    max-width: 64px;
  }

  .secondary-btn,
  .system-btn {
    padding-inline: 9px;
  }

  .system-btn span {
    max-width: 8ch;
  }
}
</style>
