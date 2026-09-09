export const APP_TITLE = '江西省矿山生态修复智能监测平台';
export const APP_KICKER = APP_TITLE;
export const LOGIN_SUBTITLE =
  '输入管理员账号和密码后，直接进入江西矿山在线地图；可按需进入解译与指数分析。';
export const WORKSPACE_SUBTITLE = '江西版默认入口，承接项目建档、矿山绑定、数据登记和只读溯源。';

export const JIANGXI_FALLBACK_CENTER = [27.61, 115.95];
export const JIANGXI_FALLBACK_ZOOM = 8; // 离线瓦片从 z8 起步，初始视野直接落在原生层级
export const DEFAULT_MAP_LAYER = 'satellite';
export const DEFAULT_MAP_PROVIDER = 'gaode';
export const INFERENCE_DEVICE = String(import.meta.env?.VITE_JIANGXI_INFERENCE_DEVICE || 'cpu')
  .trim()
  .toLowerCase();

const SUPPORTED_MAP_PROVIDERS = new Set(['tianditu', 'gaode', 'osm', 'local', 'offline']);

export function normalizeMapProvider(provider) {
  const normalized = String(provider || '')
    .trim()
    .toLowerCase();
  if (SUPPORTED_MAP_PROVIDERS.has(normalized)) {
    return normalized;
  }
  return DEFAULT_MAP_PROVIDER;
}
