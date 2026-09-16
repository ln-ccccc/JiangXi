const backendBaseUrl = (process.env.GEOVIEW_BACKEND_URL || 'http://localhost:5008').replace(
  /\/$/,
  ''
);

// 超时分级：普通 CRUD 15s；导出/备份恢复类慢操作放宽到 120s——
// 后端打包/恢复远超 15s 时，过短超时会让用户看到 502 而后端任务实际成功，诱导重复提交。
const DEFAULT_TIMEOUT_MS = 15000;
const SLOW_OP_TIMEOUT_MS = 120000;

async function requestJson(
  method,
  path,
  { query, body, cookie, timeoutMs = DEFAULT_TIMEOUT_MS } = {}
) {
  const url = new URL(`${backendBaseUrl}${path}`);
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      url.searchParams.set(key, String(value));
    }
  });

  const response = await fetch(url, {
    method,
    headers: {
      ...(body ? { 'content-type': 'application/json' } : {}),
      ...(cookie ? { cookie } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await response.text();
  let parsed;
  try {
    parsed = text ? JSON.parse(text) : {};
  } catch (_) {
    parsed = { success: false, code: 1, msg: text || 'Invalid JSON response' };
  }
  return { status: response.status, body: parsed };
}

export const projectApi = {
  listProjects(query, cookie) {
    return requestJson('GET', '/api/projects', { query, cookie });
  },
  createProject(payload, cookie) {
    return requestJson('POST', '/api/projects', { body: payload, cookie });
  },
  getProjectDetail(projectId, cookie) {
    return requestJson('GET', `/api/projects/${projectId}`, { cookie });
  },
  updateProject(projectId, payload, cookie) {
    return requestJson('PATCH', `/api/projects/${projectId}`, { body: payload, cookie });
  },
  replaceProjectMines(projectId, payload, cookie) {
    return requestJson('PUT', `/api/projects/${projectId}/mines`, { body: payload, cookie });
  },
  createProjectDataset(projectId, payload, cookie) {
    return requestJson('POST', `/api/projects/${projectId}/datasets`, { body: payload, cookie });
  },
  getProjectTimeline(projectId, cookie) {
    return requestJson('GET', `/api/projects/${projectId}/timeline`, { cookie });
  },
  archiveProject(projectId, payload = {}, cookie) {
    return requestJson('POST', `/api/projects/${projectId}/archive`, { body: payload, cookie });
  },
  restoreProject(projectId, payload = {}, cookie) {
    return requestJson('POST', `/api/projects/${projectId}/restore`, { body: payload, cookie });
  },
  createProjectExport(projectId, payload, cookie) {
    return requestJson('POST', `/api/projects/${projectId}/exports`, {
      body: payload,
      cookie,
      timeoutMs: SLOW_OP_TIMEOUT_MS,
    });
  },
  listProjectExports(projectId, cookie) {
    return requestJson('GET', `/api/projects/${projectId}/exports`, { cookie });
  },
  createProjectBackup(projectId, payload, cookie) {
    return requestJson('POST', `/api/projects/${projectId}/backups`, {
      body: payload,
      cookie,
      timeoutMs: SLOW_OP_TIMEOUT_MS,
    });
  },
  listProjectBackups(projectId, cookie) {
    return requestJson('GET', `/api/projects/${projectId}/backups`, { cookie });
  },
  restoreProjectBackup(projectId, backupId, payload = {}, cookie) {
    return requestJson('POST', `/api/projects/${projectId}/backups/${backupId}/restore`, {
      body: payload,
      cookie,
      timeoutMs: SLOW_OP_TIMEOUT_MS,
    });
  },
};
