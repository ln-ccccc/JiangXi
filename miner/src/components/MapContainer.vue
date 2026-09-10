<template>
  <div class="map-container" ref="mapContainer">
    <div id="map" ref="mapElement"></div>

    <div v-if="mapStatusMessage" class="map-status-banner" :class="mapStatusKind">
      {{ mapStatusMessage }}
    </div>

    <div class="map-legend glass-panel" :class="{ 'shifted-left': leftCollapsed }">
      <div class="legend-item"><span class="dot treated"></span> 已治理</div>
      <div class="legend-item"><span class="dot untreated"></span> 未治理</div>
      <div class="legend-item"><span class="dot unknown"></span> 未知/其他</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { createTileFallbackState, noteTileError, noteTileLoad } from '../map/tileFallbackPolicy.js';
import {
  JIANGXI_CITY_BOUNDARY_URL,
  JIANGXI_MAP_MAX_ZOOM,
  JIANGXI_MAP_MIN_ZOOM,
  JIANGXI_PROVINCE_BOUNDARY_URL,
  createJiangxiMapOptions,
} from '../map/jiangxiMapPolicy.js';
import {
  DEFAULT_MAP_LAYER,
  JIANGXI_FALLBACK_CENTER,
  JIANGXI_FALLBACK_ZOOM,
  normalizeMapProvider,
} from '../config/minerDefaults.js';

const props = defineProps({
  minesData: Array,
  dataLoadError: {
    type: String,
    default: '',
  },
  leftCollapsed: Boolean,
  rightCollapsed: Boolean,
});

const emit = defineEmits(['select-mine']);

const mapProvider = normalizeMapProvider(import.meta.env.VITE_MINER_MAP_PROVIDER);
const map = ref(null);
const mineLayer = ref(null);
const provinceBoundaryLayer = ref(null);
const cityBoundaryLayer = ref(null);
const basemapMaskLayer = ref(null);
let provinceGeoJsonCache = null;
const currentLayer = ref(DEFAULT_MAP_LAYER);
const activeMapProvider = ref(mapProvider);
const mapContainer = ref(null);
const mapElement = ref(null);

// 离线形态：底图瓦片只显示江西矢量边界内，边界外以背景色遮罩（世界矩形外环 + 省界内孔）
const WORLD_MASK_RING = [
  [-85, -180],
  [-85, 180],
  [85, 180],
  [85, -180],
];
const BASEMAP_MASK_COLOR = '#071923';
let baseMaps = {};
let providerMaps = {};
let resizeObserver = null;
let hasFitInitialBounds = false;
let tileFallbackState = createTileFallbackState();
const mapStatusMessage = ref('');
const mapStatusKind = ref('info');
const tdtKey = String(import.meta.env.VITE_TDT_KEY || '').trim();
const localTileUrl = String(import.meta.env.VITE_MINER_LOCAL_TILE_URL || '').trim();
const localTileUrlBase = String(import.meta.env.VITE_MINER_LOCAL_TILE_URL_BASE || '').trim();
const localTileUrlSat = String(import.meta.env.VITE_MINER_LOCAL_TILE_URL_SAT || '').trim();
const localTileUrlTer = String(import.meta.env.VITE_MINER_LOCAL_TILE_URL_TER || '').trim();
const localTileTms = String(import.meta.env.VITE_MINER_LOCAL_TMS || '').trim() === '1';
const rawLocalTileMaxNativeZoom = Number(import.meta.env.VITE_MINER_LOCAL_MAX_NATIVE_ZOOM || 13);
const localTileMaxNativeZoom = Number.isFinite(rawLocalTileMaxNativeZoom)
  ? rawLocalTileMaxNativeZoom
  : 13;
// 离线瓦片最高 z13：显示上限钉在数据覆盖层级，避免放大到无影像级别
const localTileDisplayMaxZoom = localTileMaxNativeZoom;
// 已烘焙瓦片的最低层级：缩小到该层级以下时 Leaflet 复用该级瓦片降采样，保证任何视野都有影像
const rawLocalTileMinNativeZoom = Number(import.meta.env.VITE_MINER_LOCAL_MIN_NATIVE_ZOOM || 8);
const localTileMinNativeZoom = Number.isFinite(rawLocalTileMinNativeZoom)
  ? rawLocalTileMinNativeZoom
  : 8;

const makeTdtLayer = (kind) => {
  const kindMap = {
    vec: 'vec_w',
    cva: 'cva_w',
    img: 'img_w',
    cia: 'cia_w',
    ter: 'ter_w',
    cta: 'cta_w',
  };
  const layerCode = kindMap[kind];
  if (!layerCode || !tdtKey) return null;
  return L.tileLayer(
    `https://t{s}.tianditu.gov.cn/DataServer?T=${layerCode}&x={x}&y={y}&l={z}&tk=${tdtKey}`,
    { subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'], maxZoom: 18 }
  );
};

const makeGaodeLayer = (kind) => {
  const kindMap = {
    base: 'https://webrd0{s}.is.autonavi.com/appmaptile?style=7&x={x}&y={y}&z={z}',
    satellite: 'https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}',
    terrain: 'https://webrd0{s}.is.autonavi.com/appmaptile?style=7&x={x}&y={y}&z={z}',
  };
  const url = kindMap[kind];
  if (!url) return null;
  return L.tileLayer(url, { subdomains: ['1', '2', '3', '4'], maxZoom: 19 });
};

const makeLocalLayer = (url) => {
  const value = String(url || '').trim();
  if (!value) return null;
  return L.tileLayer(value, {
    // 不设图层 minZoom（会在低层级直接隐藏整层）；minNativeZoom 让低层级复用 z8 瓦片降采样
    minNativeZoom: localTileMinNativeZoom,
    maxZoom: localTileDisplayMaxZoom,
    maxNativeZoom: localTileMaxNativeZoom,
    crossOrigin: true,
    tms: localTileTms,
  });
};

const makeOfflineLayer = (label) =>
  L.gridLayer({
    tileSize: 256,
    minZoom: 0,
    maxZoom: 19,
    createTile: (coords, done) => {
      const tile = document.createElement('canvas');
      tile.width = 256;
      tile.height = 256;
      const ctx = tile.getContext('2d');
      if (ctx) {
        ctx.fillStyle = '#f5f7fb';
        ctx.fillRect(0, 0, 256, 256);

        ctx.strokeStyle = 'rgba(31,45,61,0.10)';
        ctx.lineWidth = 1;
        ctx.strokeRect(0.5, 0.5, 255, 255);

        ctx.fillStyle = 'rgba(31,45,61,0.55)';
        ctx.font = '12px sans-serif';
        ctx.fillText(label, 10, 18);

        ctx.fillStyle = 'rgba(31,45,61,0.35)';
        ctx.font = '11px monospace';
        ctx.fillText(`z:${coords.z} x:${coords.x} y:${coords.y}`, 10, 36);
      }
      done(null, tile);
      return tile;
    },
  });

const bindTileErrorFallback = (layer, onTileError) => {
  if (!layer || typeof layer.on !== 'function') return;
  if (layer instanceof L.TileLayer) {
    layer.on('tileload', () => noteTileLoad(tileFallbackState));
    layer.on('tileerror', onTileError);
  }
  if (typeof layer.eachLayer === 'function') {
    layer.eachLayer((child) => bindTileErrorFallback(child, onTileError));
  }
};

const providerFallbackOrder = {
  // local 为离线部署形态：缺瓦片只落 offline 占位，绝不回退在线底图（2026-09-09 产品决策）
  local: ['offline'],
  tianditu: ['gaode', 'osm', 'offline'],
  gaode: ['osm', 'offline'],
  osm: ['offline'],
  offline: [],
};

const setTileWarningMessage = () => {
  const count = Array.isArray(props.minesData) ? props.minesData.length : 0;
  mapStatusKind.value = 'warning';
  mapStatusMessage.value =
    count > 0 ? `底图源切换中，当前已保留 ${count} 个江西图斑` : '底图源切换中，请稍候';
};

const buildProviderMaps = () => {
  const tdtBase = makeTdtLayer('vec');
  const tdtLabel = makeTdtLayer('cva');
  const tdtSat = makeTdtLayer('img');
  const tdtSatLabel = makeTdtLayer('cia');
  const tdtTer = makeTdtLayer('ter');
  const tdtTerLabel = makeTdtLayer('cta');

  const offlineMaps = {
    base: makeOfflineLayer('离线底图-标准'),
    satellite: makeOfflineLayer('离线底图-影像'),
    terrain: makeOfflineLayer('离线底图-地形'),
  };

  return {
    tianditu:
      tdtBase && tdtSat && tdtTer
        ? {
            base: L.layerGroup([tdtBase, tdtLabel].filter(Boolean)),
            satellite: L.layerGroup([tdtSat, tdtSatLabel].filter(Boolean)),
            terrain: L.layerGroup([tdtTer, tdtTerLabel].filter(Boolean)),
          }
        : null,
    gaode: {
      base: makeGaodeLayer('base'),
      satellite: makeGaodeLayer('satellite'),
      terrain: makeGaodeLayer('terrain'),
    },
    osm: {
      base: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }),
      satellite: L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        { maxZoom: 19 }
      ),
      terrain: L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', { maxZoom: 17 }),
    },
    local: (() => {
      const fallback = localTileUrl || '/tiles/{z}/{x}/{y}.png';
      return {
        base: makeLocalLayer(localTileUrlBase || fallback),
        satellite: makeLocalLayer(localTileUrlSat || fallback),
        terrain: makeLocalLayer(localTileUrlTer || fallback),
      };
    })(),
    offline: offlineMaps,
  };
};

const hasRenderableProvider = (providerName) => {
  const maps = providerMaps[providerName];
  if (!maps) return false;
  return Boolean(maps.base || maps.satellite || maps.terrain);
};

const clearBaseLayers = () => {
  if (!map.value) return;
  Object.values(baseMaps).forEach((layer) => {
    if (layer && map.value.hasLayer(layer)) {
      map.value.removeLayer(layer);
    }
  });
};

const buildFallbackStatusMessage = (fromProvider, toProvider) => {
  const count = Array.isArray(props.minesData) ? props.minesData.length : 0;
  if (toProvider === 'gaode') {
    return count > 0
      ? `本地底图不可用，已切换到在线卫星底图，并保留 ${count} 个江西图斑`
      : '本地底图不可用，已切换到在线卫星底图';
  }
  if (toProvider === 'osm') {
    return count > 0
      ? `${fromProvider === 'gaode' ? '在线卫星底图' : '当前底图源'}不可用，已切换到备用在线底图，并保留 ${count} 个江西图斑`
      : '当前底图源不可用，已切换到备用在线底图';
  }
  return count > 0
    ? `底图服务均不可用，已切换为离线占位底图，并保留 ${count} 个江西图斑`
    : '底图服务均不可用，已切换为离线占位底图';
};

const basemapMaskPane = 'basemapMask';
let basemapMaskRenderer = null;

const buildMaskRings = (provinceGeoJson) => {
  const features = provinceGeoJson?.features?.length
    ? provinceGeoJson.features
    : provinceGeoJson?.geometry
      ? [provinceGeoJson]
      : [];
  const rings = [];
  for (const feature of features) {
    const coords = feature?.geometry?.coordinates;
    if (!coords) continue;
    const polys =
      feature.geometry.type === 'MultiPolygon'
        ? feature.geometry.coordinates
        : [feature.geometry.coordinates];
    for (const poly of polys) {
      if (poly[0]?.length) {
        // GeoJSON 是 [lng,lat]，Leaflet 要 [lat,lng]，必须轴序翻转（不翻会被投影到视口外，
        // 孔洞环在渲染裁剪后整个丢失，遮罩变成盖满全球的实心块）；
        // 同时反绕向，兼容 canvas nonzero 填充规则
        rings.push(poly[0].map(([lng, lat]) => [lat, lng]).reverse());
      }
    }
  }
  return rings;
};

const removeBasemapMask = () => {
  if (basemapMaskLayer.value) {
    map.value?.removeLayer(basemapMaskLayer.value);
    basemapMaskLayer.value = null;
  }
};

const applyBasemapMask = () => {
  if (!map.value || !provinceGeoJsonCache) return;
  removeBasemapMask();
  if (!basemapMaskRenderer) return;
  const rings = buildMaskRings(provinceGeoJsonCache);
  if (!rings.length) return;
  basemapMaskLayer.value = L.polygon([WORLD_MASK_RING, ...rings], {
    color: BASEMAP_MASK_COLOR,
    weight: 0,
    fillColor: BASEMAP_MASK_COLOR,
    fillOpacity: 1,
    interactive: false,
    pane: basemapMaskPane,
    renderer: basemapMaskRenderer,
  }).addTo(map.value);
};

// —— 瓦片级裁剪（tile bleeding 的构造级修复）——
// overlay 遮罩多边形依赖 Leaflet Renderer 的投影/变换内部状态，连续缩放后会与瓦片层
// 失步（实测 1.9.4：renderer 停在旧层级投影，省界外瓦片裸露）。改为把省界多边形做成
// SVG clipPath 直接挂在瓦片 level 容器上：clip-path 属于元素自身的用户坐标系，随容器
// 的 transform 一起动，与瓦片几何天然同步，不存在生命周期错位。
const JX_CLIP_NS = 'http://www.w3.org/2000/svg';
let basemapClipDefsSvg = null;
let clippedTileLayers = [];
let tileClipSeq = 0;

const ensureTileClipDefsSvg = () => {
  if (basemapClipDefsSvg) return basemapClipDefsSvg;
  basemapClipDefsSvg = document.createElementNS(JX_CLIP_NS, 'svg');
  basemapClipDefsSvg.setAttribute('width', '0');
  basemapClipDefsSvg.setAttribute('height', '0');
  basemapClipDefsSvg.style.position = 'absolute';
  document.body.appendChild(basemapClipDefsSvg);
  return basemapClipDefsSvg;
};

const updateTileClips = () => {
  if (!clippedTileLayers.length) return;
  if (!map.value || !provinceGeoJsonCache) return;
  const defs = ensureTileClipDefsSvg();
  const rings = buildMaskRings(provinceGeoJsonCache);
  if (!rings.length) return;
  for (const layer of clippedTileLayers) {
    // _levels/_origin 为 Leaflet 1.9.4 GridLayer 内部结构（版本锁定，升级需回归本逻辑）。
    // 每个 level 实例一个专属 clipPath：d 直接以 level 局部坐标（worldPx - origin）表达，
    // 不依赖 clipPath transform 的浏览器兼容语义；origin 在 level 生命周期内不变，一次成型。
    const levels = layer._levels || {};
    for (const key of Object.keys(levels)) {
      const level = levels[key];
      if (!level?.el) continue;
      if (level.el.dataset.jxClipId) continue;
      const origin = level.origin;
      if (!origin) continue;
      const clipId = `jx-tile-clip-${(tileClipSeq += 1)}`;
      const clipPath = document.createElementNS(JX_CLIP_NS, 'clipPath');
      clipPath.setAttribute('id', clipId);
      clipPath.setAttribute('clipPathUnits', 'userSpaceOnUse');
      const d = rings
        .map((ring) =>
          ring
            .map((latlng) => {
              const p = map.value.project(latlng, level.zoom);
              return `${(p.x - origin.x).toFixed(1)},${(p.y - origin.y).toFixed(1)}`;
            })
            .join(' L ')
        )
        .map((seg) => `M${seg} Z`)
        .join(' ');
      const path = document.createElementNS(JX_CLIP_NS, 'path');
      path.setAttribute('d', d);
      clipPath.appendChild(path);
      defs.appendChild(clipPath);
      level.el.dataset.jxClipId = clipId;
      level.el.style.clipPath = `url(#${clipId})`;
    }
  }
};

const applyBaseProvider = (providerName, { fallback = false, fromProvider = '' } = {}) => {
  if (!map.value || !hasRenderableProvider(providerName)) return false;

  tileFallbackState = createTileFallbackState();
  clearBaseLayers();

  baseMaps = providerMaps[providerName];
  activeMapProvider.value = providerName;

  if (providerName === 'local') {
    map.value.setMaxZoom(localTileDisplayMaxZoom);
  } else {
    map.value.setMaxZoom(19);
  }

  const onTileError = () => {
    if (!noteTileError(tileFallbackState, { initialErrorThreshold: 4 })) return;
    const nextProvider = (providerFallbackOrder[activeMapProvider.value] || []).find((candidate) =>
      hasRenderableProvider(candidate)
    );

    if (!nextProvider) return;

    setTileWarningMessage();
    applyBaseProvider(nextProvider, {
      fallback: true,
      fromProvider: activeMapProvider.value,
    });
  };

  // local 为离线部署形态：缺瓦片是常态（视野边缘/无影像区），不得因 tileerror
  // 触发换源回退；offline 占位层同理。仅在线源（gaode/osm/tianditu）保留回退绑定。
  if (providerName !== 'offline' && providerName !== 'local') {
    Object.values(baseMaps).forEach((layer) => bindTileErrorFallback(layer, onTileError));
  }

  const firstLayer = baseMaps[currentLayer.value] || baseMaps.base;
  if (firstLayer) {
    firstLayer.addTo(map.value);
  }

  // local 瓦片层走 clipPath 级裁剪（见 updateTileClips 注释）；level 容器在 addTo 时已创建
  clippedTileLayers = providerName === 'local' ? Object.values(baseMaps).filter(Boolean) : [];
  if (clippedTileLayers.length) {
    updateTileClips();
  }

  if (providerName === 'local' || providerName === 'offline') {
    applyBasemapMask();
  } else {
    removeBasemapMask();
  }

  // 地图级缩放钳制：图层 maxZoom/minZoom 的 Leaflet 语义是"越界隐藏整层"（黑屏），
  // 不是限制缩放。local 的层级上下限必须落在地图上，放大才真正停在瓦片覆盖上限。
  const mapMaxZoom = providerName === 'local' ? localTileDisplayMaxZoom : JIANGXI_MAP_MAX_ZOOM;
  map.value.setMinZoom(JIANGXI_MAP_MIN_ZOOM);
  map.value.setMaxZoom(mapMaxZoom);
  if (map.value.getZoom() > mapMaxZoom) map.value.setZoom(mapMaxZoom);

  if (fallback) {
    mapStatusKind.value = 'warning';
    mapStatusMessage.value = buildFallbackStatusMessage(fromProvider, providerName);
  }

  return true;
};

const initMap = () => {
  if (!mapElement.value) return;
  map.value = L.map(mapElement.value, {
    zoomControl: false,
    attributionControl: false,
    ...createJiangxiMapOptions(),
  }).setView(JIANGXI_FALLBACK_CENTER, JIANGXI_FALLBACK_ZOOM);
  L.control.zoom({ position: 'bottomright' }).addTo(map.value);

  // 底图遮罩专用 pane：位于瓦片层(200)之上、矢量边界/图斑层(400)之下
  map.value.createPane(basemapMaskPane);
  map.value.getPane(basemapMaskPane).style.zIndex = 350;

  // 遮罩走独立 renderer：与默认渲染器的 viewBox/节流互不干扰，便于按 pane 定位问题
  basemapMaskRenderer = L.svg({ pane: basemapMaskPane, padding: 1 });

  // tile bleeding 防御（2026-09-10 实测复现）：连续多级滚轮缩放时，Renderer._update()
  // 在 _animatingZoom 期间被跳过，动画结束后无人补跑，遮罩停留在旧层级投影
  // （transform 缺少层级间缩放，孔洞跑偏 → 省界外瓦片持续裸露）。
  // zoomend 时 _animatingZoom 已复位，强制重挂遮罩逼迫 renderer 完整重投影，
  // 使遮罩与瓦片层收敛到同一视图状态。
  map.value.on('zoomend', () => {
    applyBasemapMask();
  });
  // 缩放后 GridLayer 可能新建/裁剪 level 容器，重刷 clip 归属与原点平移
  map.value.on('zoomend viewreset', () => {
    updateTileClips();
  });

  // 调试句柄：仅 dev 构建存在（import.meta.env.DEV 静态替换，生产包整段消除），
  // 供自动化测试/控制台直取地图实例做确定性缩放验证
  if (import.meta.env.DEV) {
    window.__jxMap = map.value;
  }

  providerMaps = buildProviderMaps();

  const preferredProvider = hasRenderableProvider(mapProvider) ? mapProvider : 'gaode';
  if (!applyBaseProvider(preferredProvider)) {
    applyBaseProvider('offline');
  }
};

const addBoundaryLayer = (geoJson, style, { labelCities = false } = {}) => {
  if (!map.value) return null;
  const boundaryLayer = L.geoJSON(geoJson, {
    interactive: false,
    style,
    onEachFeature: (feature, layer) => {
      if (!labelCities || !feature.properties?.name) return;
      layer.bindTooltip(feature.properties.name, {
        className: 'city-boundary-label',
        direction: 'center',
        permanent: true,
        opacity: 0.9,
      });
    },
  }).addTo(map.value);
  boundaryLayer.bringToBack?.();
  return boundaryLayer;
};

const loadJiangxiBoundaries = async () => {
  try {
    const [provinceResponse, citiesResponse] = await Promise.all([
      fetch(JIANGXI_PROVINCE_BOUNDARY_URL),
      fetch(JIANGXI_CITY_BOUNDARY_URL),
    ]);
    if (!provinceResponse.ok || !citiesResponse.ok) {
      throw new Error('行政边界文件不可用');
    }

    const [province, cities] = await Promise.all([provinceResponse.json(), citiesResponse.json()]);
    provinceBoundaryLayer.value = addBoundaryLayer(province, {
      color: '#8fc6c8',
      weight: 2.4,
      opacity: 0.95,
      fill: false,
    });
    cityBoundaryLayer.value = addBoundaryLayer(
      cities,
      {
        color: '#9ce7bd',
        dashArray: '5 5',
        opacity: 0.72,
        weight: 1.1,
        fill: false,
      },
      { labelCities: true }
    );
    // 边界数据就绪后，为离线底图补上边界外遮罩
    provinceGeoJsonCache = province;
    if (activeMapProvider.value === 'local' || activeMapProvider.value === 'offline') {
      applyBasemapMask();
      // 省界到位晚于瓦片层挂载，此时才有坐标可建 clipPath，补触发一次
      updateTileClips();
    }
  } catch (error) {
    console.warn('江西行政边界加载失败，已保留卫星影像和矿山图斑。', error);
  }
};

const getMineColor = (feature) => {
  const status = feature.properties.status_normalized || 'unknown';
  if (status === 'treated') return '#82d7a7';
  if (status === 'untreated') return '#d96b6b';
  return '#e6c98c';
};

const fitMineLayerBounds = () => {
  if (!map.value || !mineLayer.value) return;
  const bounds = mineLayer.value.getBounds();
  if (!bounds || !bounds.isValid()) return;
  map.value.fitBounds(bounds, {
    paddingTopLeft: [24, 30],
    paddingBottomRight: [24, 30],
    maxZoom: 12,
  });
};

const renderMapMarkers = () => {
  if (!map.value) return;
  if (mineLayer.value) map.value.removeLayer(mineLayer.value);

  if (props.dataLoadError) {
    mapStatusKind.value = 'error';
    mapStatusMessage.value = '江西图斑加载失败，请检查 /api/geojson 与默认数据源';
    return;
  }

  if (!props.minesData || props.minesData.length === 0) {
    mapStatusKind.value = 'error';
    mapStatusMessage.value = '当前筛选条件下无匹配图斑，请调整筛选或重置条件';
    return;
  }

  const geoJsonData = { type: 'FeatureCollection', features: props.minesData };

  mineLayer.value = L.geoJSON(geoJsonData, {
    style: (feature) => {
      const color = getMineColor(feature);
      return {
        color,
        weight: 1.5,
        opacity: 0.95,
        fillColor: color,
        fillOpacity: 0.52,
      };
    },
    onEachFeature: (feature, layer) => {
      const name =
        feature.properties.mine_name ||
        feature.properties.name ||
        `TBBH: ${feature.properties.tbbh}`;
      layer.bindTooltip(name, { direction: 'top', className: 'map-tooltip' });

      layer.on('click', () => {
        const bounds = layer.getBounds();
        const center = bounds.getCenter();
        emit('select-mine', { feature, center, bounds });
      });

      layer.on('mouseover', (event) => {
        event.target.setStyle({ weight: 3, fillOpacity: 0.7 });
      });
      layer.on('mouseout', (event) => {
        mineLayer.value.resetStyle(event.target);
      });
    },
  }).addTo(map.value);
  mineLayer.value.bringToFront?.();

  if (!hasFitInitialBounds && props.minesData.length > 0) {
    fitMineLayerBounds();
    hasFitInitialBounds = true;
  }

  if (mapStatusKind.value !== 'warning') {
    mapStatusKind.value = 'success';
    mapStatusMessage.value = `江西图斑已加载，共 ${props.minesData.length} 个`;
  } else {
    setTileWarningMessage();
  }
};

const flyToMine = (tbbh) => {
  if (!map.value || !mineLayer.value) return;
  let targetLayer = null;
  mineLayer.value.eachLayer((layer) => {
    if (String(layer.feature.properties.tbbh) === String(tbbh)) {
      targetLayer = layer;
    }
  });

  if (targetLayer) {
    map.value.fitBounds(targetLayer.getBounds(), { maxZoom: 15 });
    targetLayer.openTooltip();
    const bounds = targetLayer.getBounds();
    const center = bounds.getCenter();
    emit('select-mine', { feature: targetLayer.feature, center, bounds });
  }
};

const invalidateSize = () => {
  if (map.value) map.value.invalidateSize();
};

watch(
  () => [props.minesData, props.dataLoadError],
  () => {
    renderMapMarkers();
  },
  { deep: true }
);

onMounted(() => {
  initMap();
  loadJiangxiBoundaries();

  if (mapContainer.value && typeof window.ResizeObserver === 'function') {
    resizeObserver = new window.ResizeObserver(() => {
      invalidateSize();
    });
    resizeObserver.observe(mapContainer.value);
  }
});

onUnmounted(() => {
  resizeObserver?.disconnect();
});

defineExpose({
  flyToMine,
  invalidateSize,
});
</script>

<style scoped>
.map-container {
  flex: 1 1 auto;
  position: relative;
  min-width: 0;
  min-height: 0;
  background: var(--jx-bg);
  width: 100%;
  height: 100%;
  overflow: hidden;
}

#map {
  width: 100%;
  height: 100%;
  z-index: 1;
  background: transparent;
}

.map-legend {
  position: absolute;
  bottom: 20px;
  left: 16px;
  z-index: 10;
  padding: 6px 9px;
  display: flex;
  gap: 8px;
  transition: left 0.2s ease;
}

.map-status-banner {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 12;
  max-width: min(72vw, 680px);
  padding: 7px 18px;
  border: 1px solid var(--jx-border);
  border-radius: 999px;
  background: var(--jx-surface-glass);
  backdrop-filter: var(--jx-blur);
  -webkit-backdrop-filter: var(--jx-blur);
  color: var(--jx-text-muted);
  font-size: 12px;
  line-height: 1.45;
  text-align: center;
  pointer-events: none;
  box-shadow: none;
}

.map-status-banner.info {
  color: var(--jx-text-muted);
}

.map-status-banner.success {
  color: var(--jx-primary);
  border-color: rgba(127, 216, 166, 0.32);
}

.map-status-banner.warning {
  color: var(--jx-warning);
  border-color: rgba(226, 194, 133, 0.32);
}

.map-status-banner.error {
  color: var(--jx-danger);
  border-color: rgba(224, 138, 128, 0.32);
}

.map-legend.shifted-left {
  left: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--jx-text-muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
  letter-spacing: 0.03em;
  line-height: 1.35;
  white-space: nowrap;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot.treated {
  background: var(--jx-success);
}

.dot.untreated {
  background: var(--jx-danger);
}

.dot.unknown {
  background: var(--jx-sand);
}

.glass-panel {
  background: var(--jx-surface);
  border: 1px solid var(--jx-border);
  border-radius: 5px;
  box-shadow: none;
  padding: 8px;
  backdrop-filter: blur(8px);
}

:global(.city-boundary-label) {
  background: rgba(7, 19, 31, 0.62);
  border: 1px solid rgba(156, 231, 189, 0.38);
  border-radius: 4px;
  box-shadow: none;
  color: var(--jx-text);
  font-size: 11px;
  padding: 1px 4px;
}

:global(.city-boundary-label::before) {
  display: none;
}

@media (max-width: 900px) {
  .map-container {
    flex: 0 0 auto;
    height: clamp(420px, 62vh, 680px);
    min-height: 420px;
  }

  .map-status-banner {
    top: 10px;
    right: 12px;
    left: 12px;
    max-width: none;
    transform: none;
  }

  .map-legend,
  .map-legend.shifted-left {
    right: 12px;
    bottom: 12px;
    left: 12px;
    flex-wrap: wrap;
  }
}
</style>
