const backendBaseUrl = (process.env.GEOVIEW_BACKEND_URL || 'http://localhost:5008').replace(
  /\/$/,
  ''
);

// 认证操作（login/logout/session）均为轻量请求，统一 15s 超时；
// 慢操作分级（导出/备份恢复 120s）见 projectBackend.js 的 SLOW_OP_TIMEOUT_MS。
const AUTH_TIMEOUT_MS = 15000;

export async function requestBackendAuth(method, path, { body, cookie } = {}) {
  const response = await fetch(`${backendBaseUrl}${path}`, {
    method,
    headers: {
      ...(body ? { 'content-type': 'application/json' } : {}),
      ...(cookie ? { cookie } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(AUTH_TIMEOUT_MS),
  });

  const text = await response.text();
  let parsed;
  try {
    parsed = text ? JSON.parse(text) : {};
  } catch (_) {
    parsed = { success: false, code: 1, msg: text || 'Invalid JSON response' };
  }

  return {
    status: response.status,
    body: parsed,
    setCookies:
      typeof response.headers.getSetCookie === 'function'
        ? response.headers.getSetCookie()
        : response.headers.get('set-cookie')
          ? [response.headers.get('set-cookie')]
          : [],
  };
}

export const authBackend = {
  login(payload) {
    return requestBackendAuth('POST', '/api/auth/login', { body: payload });
  },
  logout(cookie = '') {
    return requestBackendAuth('POST', '/api/auth/logout', { cookie });
  },
  session(cookie = '') {
    return requestBackendAuth('GET', '/api/auth/session', { cookie });
  },
};
