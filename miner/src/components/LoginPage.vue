<template>
  <div class="login-page">
    <div class="login-card">
      <p class="login-kicker">{{ APP_KICKER }}</p>
      <h1>管理员登录</h1>
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
          {{ submitting ? '登录中...' : '登录' }}
        </button>
      </form>
      <p v-if="error" class="error-text">{{ error }}</p>
    </div>
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
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at top left, rgba(78, 205, 196, 0.16), transparent 30%),
    radial-gradient(circle at bottom right, rgba(87, 183, 255, 0.1), transparent 28%),
    linear-gradient(180deg, var(--jx-bg) 0%, var(--jx-bg-elevated) 100%);
  padding: 24px;
  box-sizing: border-box;
}

.login-card {
  width: min(100%, 420px);
  background: var(--jx-surface);
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius-large);
  padding: 28px;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.32);
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
  font-size: 14px;
  letter-spacing: 0.02em;
}

.login-card h1 {
  margin: 10px 0 8px;
  font-size: 28px;
  font-weight: 600;
}

.login-subtitle {
  color: var(--jx-text-muted);
  line-height: 1.6;
}

.login-form {
  display: grid;
  gap: 14px;
  margin-top: 22px;
}

.login-form label {
  display: grid;
  gap: 8px;
}

.login-form input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius);
  padding: 12px 14px;
  background: rgba(7, 19, 31, 0.76);
  color: var(--jx-text);
  font: inherit;
}

.login-form input:focus {
  border-color: var(--jx-primary);
  outline: 2px solid rgba(78, 205, 196, 0.18);
}

.login-btn {
  border: none;
  border-radius: var(--jx-radius);
  padding: 12px 14px;
  background: var(--jx-primary);
  color: #06211f;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.login-btn:not(:disabled):hover {
  background: var(--jx-primary-hover);
}

.login-btn:disabled {
  cursor: wait;
  opacity: 0.72;
}

.error-text {
  margin-top: 14px;
  color: var(--jx-danger);
}
</style>
