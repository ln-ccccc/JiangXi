<template>
  <main class="login-page">
    <div class="login-contours" aria-hidden="true" />

    <section class="login-atlas" aria-labelledby="login-atlas-title">
      <div class="specimen-rule" aria-hidden="true" />
      <p class="atlas-kicker data-label">JIANGXI · FIELD ATLAS</p>
      <h1 id="login-atlas-title" class="atlas-title">江西生态图册</h1>
      <p class="atlas-purpose">面向江西矿山遥感解译人员的地物分类与光谱指数工作台。</p>
      <div class="access-note">
        <span class="access-note__index data-label">ACCESS 01</span>
        <strong>一次登录可访问江西地图与解译平台</strong>
        <span>使用同一后端会话，无需重复认证。</span>
      </div>
      <dl class="atlas-meta">
        <div>
          <dt class="data-label">样区</dt>
          <dd>江西</dd>
        </div>
        <div>
          <dt class="data-label">任务</dt>
          <dd>解译与指数分析</dd>
        </div>
      </dl>
    </section>

    <section class="login-card" aria-labelledby="login-title">
      <p class="login-record data-label">江西样区档案 · 用户认证</p>
      <h2 id="login-title" class="login-title atlas-title">登录工作台</h2>
      <p class="login-subtitle">输入平台账号，登录后继续选择地物分类或光谱指数。</p>
      <el-form label-position="top" @submit.prevent="submitLogin">
        <el-form-item label="账号">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            autocomplete="current-password"
            show-password
            type="password"
            @keyup.enter="submitLogin"
          />
        </el-form-item>
        <div v-if="errorMessage" class="error-text" role="alert">
          {{ errorMessage }}
        </div>
        <el-button
          :loading="loading"
          class="submit-btn"
          type="primary"
          native-type="submit"
          @click="submitLogin"
        >
          登录并进入图册
        </el-button>
      </el-form>
    </section>
  </main>
</template>

<script>
import { ElMessage } from "element-plus";

import { legacyLogin } from "@/api/auth";

export default {
  name: "LegacyLogin",
  data() {
    return {
      loading: false,
      errorMessage: "",
      form: {
        username: "admin",
        password: "",
      },
    };
  },
  methods: {
    async submitLogin() {
      if (this.loading) return;
      if (!this.form.username.trim() || !this.form.password) {
        this.errorMessage = "请输入账号和密码后再登录";
        return;
      }

      this.loading = true;
      this.errorMessage = "";
      try {
        await legacyLogin({
          username: this.form.username.trim(),
          password: this.form.password,
        });
        ElMessage.success("登录成功");
        this.$router.replace(this.$route.query.redirect || "/segmentation");
      } catch (error) {
        this.errorMessage =
          error?.response?.data?.msg ||
          error?.message ||
          "登录失败，请检查账号和密码后重试";
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.login-page {
  position: relative;
  display: grid;
  min-height: 100vh;
  padding: clamp(28px, 6vw, 84px);
  overflow: hidden;
  grid-template-columns: minmax(0, 1.1fr) minmax(340px, 460px);
  align-items: center;
  gap: clamp(42px, 8vw, 120px);
  background: linear-gradient(110deg, var(--jx-bg-elevated) 0 48%, var(--jx-bg) 48%);
}

.login-contours {
  position: absolute;
  inset: 0 45% 0 0;
  pointer-events: none;
  opacity: 0.18;
  background: repeating-radial-gradient(
    ellipse at 22% 50%,
    transparent 0 27px,
    var(--jx-border) 28px 29px,
    transparent 30px 48px
  );
  mask-image: linear-gradient(90deg, black, transparent);
}

.login-atlas,
.login-card {
  position: relative;
  z-index: 1;
}

.login-atlas {
  width: min(660px, 100%);
}

.specimen-rule {
  width: min(420px, 90%);
  height: 9px;
  margin-bottom: 28px;
  border-top: 1px solid var(--jx-border-strong);
  background: repeating-linear-gradient(
    90deg,
    var(--jx-border-strong) 0 1px,
    transparent 1px 12px
  );
}

.atlas-kicker {
  margin: 0 0 12px;
  color: var(--jx-primary);
  font-size: 10px;
}

.login-atlas h1 {
  margin: 0;
  color: var(--jx-text);
  font-size: clamp(42px, 6vw, 76px);
  font-weight: 600;
  letter-spacing: 0.04em;
  line-height: 1.08;
}

.atlas-purpose {
  max-width: 540px;
  margin: 22px 0 34px;
  color: var(--jx-text-muted);
  font-size: 16px;
  line-height: 1.8;
}

.access-note {
  display: grid;
  max-width: 520px;
  padding: 18px 20px;
  gap: 5px;
  border: 1px solid var(--jx-border);
  border-left: 3px solid var(--jx-sand);
  border-radius: 0 var(--jx-radius) var(--jx-radius) 0;
  background: var(--jx-surface-muted);
}

.access-note__index {
  color: var(--jx-sand);
  font-size: 9px;
}

.access-note strong {
  color: var(--jx-text);
  font-size: 15px;
  font-weight: 600;
}

.access-note span:last-child {
  color: var(--jx-text-muted);
  font-size: 12px;
}

.atlas-meta {
  display: flex;
  margin: 28px 0 0;
  gap: 42px;
}

.atlas-meta div {
  display: grid;
  gap: 3px;
}

.atlas-meta dt {
  color: var(--jx-text-muted);
  font-size: 9px;
}

.atlas-meta dd {
  margin: 0;
  color: var(--jx-text);
  font-size: 13px;
}

.login-card {
  width: 100%;
  padding: 34px 32px 32px;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius-large);
  background: var(--jx-surface);
  box-shadow: var(--shadow-xl);
}

.login-record {
  margin: 0 0 14px;
  color: var(--jx-sand);
  font-size: 9px;
}

.login-title {
  margin: 0;
  color: var(--jx-text);
  font-size: 30px;
  font-weight: 600;
}

.login-subtitle {
  margin: 9px 0 26px;
  color: var(--jx-text-muted);
  font-size: 13px;
  line-height: 1.7;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}

.error-text {
  margin: -2px 0 12px;
  padding: 9px 10px;
  border-left: 2px solid var(--jx-danger);
  background: var(--jx-surface-muted);
  color: var(--jx-danger);
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 1100px) {
  .login-page {
    grid-template-columns: minmax(0, 1fr) minmax(340px, 420px);
    gap: 42px;
  }
}

@media (max-width: 768px) {
  .login-page {
    padding: 36px 24px;
    grid-template-columns: 1fr;
    gap: 32px;
    background: var(--jx-bg);
  }

  .login-contours {
    inset: 0;
    opacity: 0.1;
  }

  .login-atlas h1 {
    font-size: 44px;
  }

  .atlas-purpose {
    margin-bottom: 20px;
  }

  .atlas-meta {
    display: none;
  }

  .login-card {
    justify-self: center;
  }
}

@media (max-width: 480px) {
  .login-page {
    padding: 24px 14px;
    align-content: center;
    gap: 24px;
  }

  .specimen-rule {
    margin-bottom: 18px;
  }

  .login-atlas h1 {
    font-size: 36px;
  }

  .atlas-purpose {
    margin: 14px 0 18px;
    font-size: 14px;
  }

  .access-note {
    padding: 13px 14px;
  }

  .login-card {
    padding: 26px 20px 22px;
  }
}
</style>
