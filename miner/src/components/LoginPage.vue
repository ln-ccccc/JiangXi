<template>
  <div class="login-page">
    <div class="login-backdrop" aria-hidden="true"></div>
    <div class="login-veil" aria-hidden="true"></div>

    <main class="login-stage">
      <section class="login-lead">
        <p class="lead-region">江西省 · 348 个矿区图斑 · 2013–2025</p>
        <h1 class="lead-title">矿山生态修复，<br />一屏尽读。</h1>
        <p class="lead-desc">卫星影像、图斑档案与两期解译成果在此汇合成一份可溯源的监测台账。</p>
      </section>

      <section class="login-card" aria-label="管理员登录">
        <p class="login-kicker">{{ APP_KICKER }}</p>
        <h2>管理员登录</h2>
        <p class="login-subtitle">{{ LOGIN_SUBTITLE }}</p>
        <form class="login-form" @submit.prevent="submitLogin">
          <label>
            <span>账号</span>
            <input v-model.trim="username" type="text" autocomplete="username" required />
          </label>
          <label>
            <span>密码</span>
            <input v-model="password" type="password" autocomplete="current-password" required />
          </label>
          <button class="login-btn" type="submit" :disabled="submitting">
            {{ submitting ? '登录中...' : '进入监测平台' }}
          </button>
        </form>
        <p v-if="error" class="error-text">{{ error }}</p>
      </section>
    </main>

    <footer class="login-footnote" aria-hidden="true">
      <span>离线影像 · 本机瓦片服务</span>
      <span class="footnote-rule"></span>
      <span>生态监测档案</span>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { APP_KICKER, LOGIN_SUBTITLE } from '../config/minerDefaults.js';

const props = defineProps({
  submitting: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: '',
  },
});

const emit = defineEmits(['login']);
const username = ref('admin');
const password = ref('');

const submitLogin = () => {
  if (props.submitting) {
    return;
  }
  emit('login', { username: username.value, password: password.value });
};
</script>

<style scoped>
.login-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--jx-bg);
  padding: 24px clamp(24px, 6vw, 96px);
  box-sizing: border-box;
}

/* 背景：本机 z8 卫星瓦片 2×2 拼片（离线可用），深潭色罩让影像退成纹理 */
.login-backdrop {
  position: absolute;
  inset: 0;
  background-image: url('/login-backdrop.jpg');
  background-size: cover;
  background-position: center 32%;
  filter: saturate(0.88) brightness(0.94);
}

.login-veil {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(
      120% 90% at 18% 82%,
      rgba(6, 20, 28, 0.94) 0%,
      rgba(6, 20, 28, 0.55) 52%,
      rgba(6, 20, 28, 0.18) 100%
    ),
    linear-gradient(180deg, rgba(6, 20, 28, 0.42) 0%, rgba(6, 20, 28, 0.62) 100%);
}

.login-stage {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: clamp(32px, 6vw, 120px);
}

/* 左侧：编辑排版式主题陈述 */
.login-lead {
  max-width: 520px;
}

.lead-region {
  margin: 0 0 18px;
  font-family: var(--font-num);
  font-size: 13px;
  letter-spacing: 0.08em;
  color: var(--jx-primary);
}

.lead-title {
  margin: 0;
  font-size: clamp(34px, 4.6vw, 56px);
  line-height: 1.22;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: #f2fbf6;
  text-wrap: balance;
}

.lead-desc {
  margin: 22px 0 0;
  max-width: 40em;
  font-size: 15px;
  line-height: 1.9;
  color: rgba(233, 243, 239, 0.78);
}

/* 右侧：玻璃登录卡 */
.login-card {
  width: min(100%, 380px);
  background: var(--jx-surface-glass);
  backdrop-filter: var(--jx-blur);
  -webkit-backdrop-filter: var(--jx-blur);
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius-large);
  padding: 30px 28px;
  box-shadow: var(--jx-shadow-1);
  color: var(--jx-text);
}

.login-kicker,
.login-subtitle,
.error-text,
label span {
  margin: 0;
}

.login-kicker {
  color: var(--jx-primary);
  font-size: 13px;
  letter-spacing: 0.04em;
}

.login-card h2 {
  margin: 10px 0 8px;
  font-size: 22px;
  font-weight: 600;
}

.login-subtitle {
  color: var(--jx-text-muted);
  font-size: 13px;
  line-height: 1.7;
}

.login-form {
  display: grid;
  gap: 16px;
  margin-top: 24px;
}

.login-form label {
  display: grid;
  gap: 8px;
}

.login-form label span {
  font-size: 13px;
  color: var(--jx-text-muted);
}

.login-form input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius);
  padding: 12px 14px;
  background: rgba(4, 15, 21, 0.66);
  color: var(--jx-text);
  font: inherit;
  transition: border-color 0.2s ease;
}

.login-form input:hover {
  border-color: var(--jx-border-strong);
}

.login-form input:focus {
  border-color: var(--jx-primary);
  outline: 2px solid rgba(127, 216, 166, 0.2);
  outline-offset: 0;
}

.login-btn {
  border: none;
  border-radius: var(--jx-radius);
  padding: 13px 16px;
  background: var(--jx-primary);
  color: var(--jx-primary-ink);
  font: inherit;
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition:
    background 0.2s ease,
    transform 0.15s ease;
}

.login-btn:not(:disabled):hover {
  background: var(--jx-primary-hover);
}

.login-btn:not(:disabled):active {
  transform: translateY(1px);
}

.login-btn:disabled {
  cursor: wait;
  opacity: 0.72;
}

.error-text {
  margin-top: 16px;
  font-size: 13px;
  color: var(--jx-danger);
}

/* 页脚注记：制图图签式排布 */
.login-footnote {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding-top: 18px;
  border-top: 1px solid var(--jx-border);
  font-size: 12px;
  letter-spacing: 0.06em;
  color: var(--jx-text-muted);
}

.footnote-rule {
  flex: 1;
  height: 1px;
  background: var(--jx-border);
}

@media (max-width: 960px) {
  .login-stage {
    flex-direction: column;
    align-items: stretch;
    justify-content: center;
    gap: 40px;
  }

  .login-lead {
    max-width: none;
  }

  .login-card {
    width: 100%;
  }
}
</style>
