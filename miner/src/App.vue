<template>
  <div v-if="initializing" class="loading-shell">正在检查登录状态...</div>
  <LoginPage
    v-else-if="currentView === 'login'"
    :submitting="authLoading"
    :error="authError"
    @login="handleLogin"
  />
  <div v-else class="app-shell">
    <div class="map-shell">
      <MapDashboard :username="sessionState.username" @logout="handleLogout" />
    </div>
  </div>
</template>

<script setup>
import axios from 'axios';
import { onMounted, onUnmounted, ref } from 'vue';

import {
  fetchSession,
  login as loginRequest,
  logout as logoutRequest,
} from './auth/sessionClient.js';
import LoginPage from './components/LoginPage.vue';
import MapDashboard from './components/MapDashboard.vue';
import { VIEW_HASH } from './navigation/viewNavigation.js';

const currentView = ref('login');
const initializing = ref(true);
const authLoading = ref(false);
const authError = ref('');
const sessionState = ref({ authenticated: false, username: '' });

let responseInterceptorId = null;

const navigateToLogin = (message = '') => {
  sessionState.value = { authenticated: false, username: '' };
  currentView.value = 'login';
  authError.value = message;
  if (window.location.hash !== VIEW_HASH.map) {
    window.history.replaceState(null, '', VIEW_HASH.map);
  }
};

const syncMapHash = () => {
  if (window.location.hash !== VIEW_HASH.map) {
    window.location.hash = VIEW_HASH.map;
  }
};

const handleHashChange = () => {
  if (sessionState.value.authenticated) {
    currentView.value = 'map';
    syncMapHash();
  }
};

const handleLogin = async ({ username, password }) => {
  authLoading.value = true;
  authError.value = '';
  try {
    sessionState.value = await loginRequest(username, password);
    if (!sessionState.value.authenticated) {
      navigateToLogin('登录状态未建立，请重新登录');
      return;
    }
    currentView.value = 'map';
    syncMapHash();
  } catch (error) {
    authError.value = error?.response?.data?.msg || error?.message || '登录失败';
  } finally {
    authLoading.value = false;
  }
};

const handleLogout = async () => {
  try {
    await logoutRequest();
  } catch (_) {
    // Ignore logout transport errors and clear the local session shell.
  }
  navigateToLogin('');
};

onMounted(async () => {
  if (!window.location.hash) {
    window.history.replaceState(null, '', VIEW_HASH.map);
  }
  responseInterceptorId = axios.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error?.response?.status === 401) {
        navigateToLogin('登录已失效，请重新登录');
      }
      return Promise.reject(error);
    }
  );
  try {
    sessionState.value = await fetchSession();
    currentView.value = sessionState.value.authenticated ? 'map' : 'login';
    if (sessionState.value.authenticated) syncMapHash();
  } catch (_) {
    navigateToLogin('会话检查失败，请重新登录');
  } finally {
    initializing.value = false;
  }
  window.addEventListener('hashchange', handleHashChange);
});

onUnmounted(() => {
  window.removeEventListener('hashchange', handleHashChange);
  if (responseInterceptorId !== null) {
    axios.interceptors.response.eject(responseInterceptorId);
  }
});
</script>

<style scoped>
.app-shell,
.map-shell {
  width: 100vw;
  height: 100vh;
}

.loading-shell {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at top left, rgba(78, 205, 196, 0.13), transparent 32%),
    linear-gradient(180deg, var(--jx-bg) 0%, var(--jx-bg-elevated) 100%);
  color: var(--jx-text);
  font-size: 16px;
}
</style>
