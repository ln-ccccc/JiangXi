<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">江西省矿山生态修复智能监测平台</div>
      <div class="login-title">管理员登录</div>
      <div class="login-subtitle">登录后进入江西矿山地图；可按需进入解译与指数分析。</div>
      <el-form @submit.prevent="submitLogin">
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
        <div v-if="errorMessage" class="error-text">{{ errorMessage }}</div>
        <el-button :loading="loading" class="submit-btn" type="primary" @click="submitLogin">
          登录
        </el-button>
      </el-form>
    </div>
  </div>
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
        this.errorMessage = "请输入账号和密码";
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
        this.errorMessage = error?.response?.data?.msg || error?.message || "登录失败";
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(circle at 18% 12%, rgba(78, 205, 196, 0.18), transparent 34%),
    linear-gradient(155deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
}

.login-card {
  width: min(420px, 100%);
  padding: 32px 28px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-large);
  box-shadow: var(--shadow-xl);
  backdrop-filter: blur(18px);
}

.login-brand {
  margin-bottom: 16px;
  color: var(--primary-color);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.4px;
}

.login-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}

.login-subtitle {
  margin: 10px 0 24px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}

.error-text {
  margin-bottom: 10px;
  color: var(--error-color);
  font-size: 13px;
}
</style>
