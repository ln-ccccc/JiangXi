<template>
  <main class="login-page">
    <div class="login-backdrop" aria-hidden="true" />
    <div class="login-veil" aria-hidden="true" />

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
/* 背景：本机 z13 卫星瓦片拼合底图（与 Miner 登录页同源），深潭色罩保证表单可读 */
.login-page {
  position: relative;
  display: flex;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
  padding: clamp(24px, 5vw, 72px);
  overflow: hidden;
  background: var(--jx-bg);
}

.login-backdrop {
  position: absolute;
  inset: 0;
  background-image: url("~@/assets/image/login-backdrop.jpg");
  background-size: cover;
  background-position: center 32%;
  filter: saturate(0.88) brightness(0.94);
}

.login-veil {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(
      120% 90% at 50% 82%,
      rgba(6, 20, 28, 0.92) 0%,
      rgba(6, 20, 28, 0.58) 54%,
      rgba(6, 20, 28, 0.24) 100%
    ),
    linear-gradient(180deg, rgba(6, 20, 28, 0.38) 0%, rgba(6, 20, 28, 0.6) 100%);
}

.login-card {
  position: relative;
  z-index: 1;
  width: min(100%, 400px);
  padding: 34px 32px 32px;
  border: 1px solid var(--jx-border);
  border-radius: var(--jx-radius-large);
  background: var(--jx-surface-glass, rgba(7, 24, 33, 0.72));
  backdrop-filter: saturate(150%) blur(18px);
  -webkit-backdrop-filter: saturate(150%) blur(18px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    0 14px 44px rgba(2, 10, 14, 0.45);
}

.login-record {
  margin: 0 0 14px;
  color: var(--jx-sand);
  font-size: 9px;
}

.login-title {
  margin: 0;
  color: var(--jx-text);
  font-size: 26px;
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

@media (max-width: 480px) {
  .login-page {
    padding: 24px 14px;
  }

  .login-card {
    padding: 26px 20px 22px;
  }
}
</style>
