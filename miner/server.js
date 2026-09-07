import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import dotenv from 'dotenv';
import { promisify } from 'util';
import { execFile as execFileCb, spawnSync } from 'child_process';
import xlsx from 'xlsx';
import geoviewRoutes from './routes/geoview.js';
import { createProjectRoutes } from './routes/projects.js';
import { authBackend } from './services/authBackend.js';
import { relayBackendResponse, requireMinerAuth } from './services/authProxy.js';
import { buildChangeMatrixAssetPath } from './services/changeMatrixAssets.js';
import { buildDashboardStats } from './services/dashboardStats.js';
import {
  buildEcologyProfilePayload,
  buildEcologySeriesPayload,
  hasEcologyAnnualData,
  parseEcologyProfileTbbh,
  parseEcologyWorkbookRows,
  resolveEcologyWorkbookPath,
} from './services/ecologySeries.js';
import {
  resolveDefaultJiangxiGeoSourcePath,
  resolveDefaultJiangxiKmzPath,
} from './services/defaultJiangxiSource.js';
import { buildKmlRoiArgs } from './services/kmlInferenceArgs.js';
import { normalizeInferenceDevice } from './services/inferenceDevicePolicy.js';
import {
  buildIndicesPayload,
  calculateStats,
  INDEX_SOURCE_FILES,
  resolveIndexSourcePath,
} from './services/indexSeries.js';
import { loadJiangxiGeoJsonFromSource } from './services/jiangxiGeoJsonSource.js';
import { buildMineIdentityIndex, normalizeTbbh } from './services/jiangxiIdentity.js';
import { saveKmlUpload } from './services/kmlUpload.js';
import { resolveLocalTilePath } from './services/localTileService.js';
import { ManagedPathError, resolvePathInRoots } from './services/inferencePathPolicy.js';
import { parsePositiveIdentifier } from './services/pathValidation.js';
import { buildTrendReport } from './services/trendReport.js';

dotenv.config();

const app = express();
const port = process.env.PORT ? Number(process.env.PORT) : 8000;
const execFile = promisify(execFileCb);
let kmlInferenceActive = false;

// Enable CORS and JSON parsing
app.use(cors());
app.use(express.json({ limit: '20mb' }));
const authGuard = requireMinerAuth({ sessionApi: authBackend.session });
app.use('/api/geoview', authGuard, geoviewRoutes);

app.post('/api/auth/login', async (req, res) => {
  relayBackendResponse(res, await authBackend.login(req.body || {}));
});

app.get('/api/auth/session', async (req, res) => {
  relayBackendResponse(res, await authBackend.session(req.headers.cookie || ''));
});

app.post('/api/auth/logout', async (req, res) => {
  relayBackendResponse(res, await authBackend.logout(req.headers.cookie || ''));
});

app.use('/api/projects', authGuard, createProjectRoutes({ getMinesData: () => minesData }));

const tileStaticDir = path.resolve(process.cwd(), 'public', 'tiles');
app.get('/tiles/:z/:x/:y.png', (req, res) => {
  const tilePath = resolveLocalTilePath(tileStaticDir, req.params.z, req.params.x, req.params.y);
  if (tilePath) {
    return res.sendFile(tilePath);
  }
  return res.status(404).json({ error: 'local tile not found', code: 'tile_not_found' });
});
app.use('/tiles', express.static(tileStaticDir));

const changeMatrixStaticDir = path.resolve(
  process.env.MINER_CHANGE_OUTPUT_ROOT || path.join(process.cwd(), 'change_matrix_outputs')
);
app.use('/change-matrix-outputs', authGuard, express.static(changeMatrixStaticDir));

const repoRoot = path.resolve(process.cwd(), '..');
const backendRoot = path.resolve(repoRoot, 'backend');
const runtimeDataRoot = path.resolve(
  process.env.RUNTIME_DATA_DIR || path.join(repoRoot, 'docker', 'standalone', 'runtime_data')
);
const configuredMineSourcePath = normalizePathInput(
  process.env.MINER_DEFAULT_GEO_SOURCE_PATH || ''
);
const configuredKmlPath = normalizePathInput(process.env.MINER_DEFAULT_KMZ_PATH || '');
const defaultMineSourcePath = path.resolve(
  configuredMineSourcePath ||
    (fs.existsSync(path.join(runtimeDataRoot, '348个图斑.shp'))
      ? path.join(runtimeDataRoot, '348个图斑.shp')
      : resolveDefaultJiangxiGeoSourcePath(''))
);
const defaultKmlPath = path.resolve(
  configuredKmlPath ||
    (fs.existsSync(path.join(runtimeDataRoot, 'Jiangxi_NaturalMine.kmz'))
      ? path.join(runtimeDataRoot, 'Jiangxi_NaturalMine.kmz')
      : resolveDefaultJiangxiKmzPath(''))
);
const assetManifestPath = path.resolve(
  normalizePathInput(
    process.env.JIANGXI_ASSET_MANIFEST_PATH ||
      path.join(runtimeDataRoot, 'Jiangxi_asset_manifest.json')
  )
);
const defaultOutputRoot = changeMatrixStaticDir;
const defaultKmlUploadRoot = path.resolve(process.cwd(), 'uploads', 'kml');
const kmlRoiScriptPath = path.resolve(backendRoot, 'kml_roi_infer.py');
const configuredPythonExe = normalizePathInput(process.env.PYTHON_EXE || '');
const configuredInferenceRoots = String(process.env.MINER_INFERENCE_DATA_ROOTS || '')
  .split(',')
  .map((item) => item.trim())
  .filter(Boolean);
const inferenceDataRoots = configuredInferenceRoots.length
  ? configuredInferenceRoots.map((item) => path.resolve(item))
  : [
      path.resolve(
        process.env.MINER_INFERENCE_DATA_ROOT || path.join(backendRoot, 'bianhua_2years')
      ),
    ];
const inferenceKmlRoots = [
  defaultKmlUploadRoot,
  path.dirname(defaultKmlPath),
  ...inferenceDataRoots,
];

function getLandTypeList(value) {
  const raw = String(value || '').trim();
  if (!raw) return ['未知'];
  const types = raw
    .split(/[,\uFF0C;；/、]+/)
    .map((item) => item.trim())
    .filter(Boolean);
  return Array.from(new Set(types.length ? types : ['未知']));
}

function commandExists(cmd) {
  try {
    const probe =
      process.platform === 'win32'
        ? spawnSync('where', [cmd], { encoding: 'utf-8' })
        : spawnSync('which', [cmd], { encoding: 'utf-8' });
    return probe.status === 0;
  } catch (_) {
    return false;
  }
}

function pythonRunnable(cmd, preArgs = []) {
  try {
    const probe = spawnSync(cmd, [...preArgs, '-c', 'import sys; print(sys.executable)'], {
      encoding: 'utf-8',
    });
    return probe.status === 0;
  } catch (_) {
    return false;
  }
}

function resolvePythonRunner() {
  if (
    configuredPythonExe &&
    fs.existsSync(configuredPythonExe) &&
    pythonRunnable(configuredPythonExe)
  ) {
    return { cmd: configuredPythonExe, preArgs: [], source: 'env:PYTHON_EXE' };
  }
  if (commandExists('python') && pythonRunnable('python')) {
    return { cmd: 'python', preArgs: [], source: 'PATH:python' };
  }
  if (commandExists('py') && pythonRunnable('py', ['-3'])) {
    return { cmd: 'py', preArgs: ['-3'], source: 'PATH:py -3' };
  }
  return { cmd: 'python', preArgs: [], source: 'fallback:python' };
}

const pythonRunner = resolvePythonRunner();
console.log(
  `[Startup] python runner=${pythonRunner.source} cmd=${pythonRunner.cmd} preArgs=${pythonRunner.preArgs.join(' ')}`
);

function normalizePathInput(v) {
  if (!v) return '';
  return String(v)
    .trim()
    .replace(/^["']|["']$/g, '');
}

function sha256File(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function resolveManifestFilePath(entry) {
  const declaredPath = normalizePathInput(entry?.path || '');
  const candidates = [
    declaredPath,
    path.join(runtimeDataRoot, path.basename(declaredPath)),
    path.join(repoRoot, 'miner', 'data', path.basename(declaredPath)),
  ].filter(Boolean);
  return candidates
    .map((candidate) => path.resolve(candidate))
    .find((candidate) => fs.existsSync(candidate));
}

function loadJiangxiAssetManifest() {
  const required =
    process.env.STANDALONE_MODE === '1' || process.env.JIANGXI_REQUIRE_ASSET_MANIFEST === '1';
  if (!fs.existsSync(assetManifestPath)) {
    if (required) throw new Error(`江西资产 manifest 不存在: ${assetManifestPath}`);
    console.warn(`[Startup] Jiangxi asset manifest not found: ${assetManifestPath}`);
    return { path: null, sha256: null, mapping: null };
  }

  let manifest;
  try {
    manifest = JSON.parse(fs.readFileSync(assetManifestPath, 'utf8'));
  } catch (error) {
    throw new Error(`江西资产 manifest 损坏: ${assetManifestPath}: ${error.message}`);
  }
  if (manifest.status !== 'ok') throw new Error('江西资产 manifest 状态不是 ok，禁止启动');

  const mapping = {};
  const reverse = new Map();
  for (const [rawTbbh, rawMapFid] of Object.entries(manifest.mapping?.tbbh_to_map_fid || {})) {
    const tbbh = normalizeTbbh(rawTbbh);
    const mapFid = Number(rawMapFid);
    if (!Number.isSafeInteger(mapFid) || mapFid <= 0 || mapping[tbbh] || reverse.has(mapFid)) {
      throw new Error(`江西资产 manifest TBBH/map_fid 映射无效: ${rawTbbh}/${rawMapFid}`);
    }
    mapping[tbbh] = mapFid;
    reverse.set(mapFid, tbbh);
  }
  const expectedCount = Number(process.env.JIANGXI_EXPECTED_COUNT || 348);
  if (Object.keys(mapping).length !== expectedCount) {
    throw new Error(
      `江西资产 manifest 映射数量错误: ${Object.keys(mapping).length}，期望 ${expectedCount}`
    );
  }

  for (const [name, entry] of Object.entries(manifest.files || {})) {
    const filePath = resolveManifestFilePath(entry);
    if (!filePath) throw new Error(`江西资产文件缺失: ${name}`);
    if (entry.sha256 && sha256File(filePath) !== entry.sha256) {
      throw new Error(`江西资产文件哈希不匹配: ${name} (${filePath})`);
    }
  }
  return {
    path: assetManifestPath,
    sha256: sha256File(assetManifestPath),
    mapping: { tbbhToMapFid: mapping, mapFidToTbbh: Object.fromEntries(reverse) },
  };
}

function parseJsonFromStdout(stdoutText) {
  const lines = String(stdoutText || '')
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i];
    if (!line.startsWith('{')) continue;
    try {
      return JSON.parse(line);
    } catch (_) {
      // Keep scanning upwards.
    }
  }
  return null;
}

function parseChangedAreaKm2FromMatrixCsv(csvPath) {
  if (!fs.existsSync(csvPath)) {
    return { has_change_matrix: false, changed_area_km2: 0 };
  }
  const content = fs.readFileSync(csvPath, 'utf-8').trim();
  if (!content) {
    return { has_change_matrix: false, changed_area_km2: 0 };
  }
  const lines = content
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length < 2) {
    return { has_change_matrix: false, changed_area_km2: 0 };
  }

  let changedArea = 0;
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(',');
    const rowValues = parts.slice(1).map((v) => Number(v));
    for (let j = 0; j < rowValues.length; j++) {
      const val = rowValues[j];
      if (!Number.isFinite(val)) continue;
      if (j !== i - 1) changedArea += val;
    }
  }
  return { has_change_matrix: true, changed_area_km2: changedArea };
}

function parseOffDiagonalFromMatrixCsv(csvPath) {
  if (!fs.existsSync(csvPath)) {
    return { exists: false, off_diagonal_sum: 0 };
  }
  const content = fs.readFileSync(csvPath, 'utf-8').trim();
  if (!content) {
    return { exists: false, off_diagonal_sum: 0 };
  }
  const lines = content
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length < 2) {
    return { exists: false, off_diagonal_sum: 0 };
  }
  let offDiag = 0;
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(',');
    const rowValues = parts.slice(1).map((v) => Number(v));
    for (let j = 0; j < rowValues.length; j++) {
      const val = rowValues[j];
      if (!Number.isFinite(val)) continue;
      if (j !== i - 1) offDiag += val;
    }
  }
  return { exists: true, off_diagonal_sum: offDiag };
}

function readResolutionFromOutputDir(outputDir) {
  const metaCandidates = ['resolution.json', 'meta.json', 'inference_meta.json'];
  for (const f of metaCandidates) {
    const fp = path.join(outputDir, f);
    if (!fs.existsSync(fp)) continue;
    try {
      const obj = JSON.parse(fs.readFileSync(fp, 'utf-8'));
      const rx = Number(
        obj?.resolution?.x ??
          obj?.resolution_x ??
          obj?.res_x ??
          obj?.pixel_size_x ??
          obj?.pixelSizeX
      );
      const ry = Number(
        obj?.resolution?.y ??
          obj?.resolution_y ??
          obj?.res_y ??
          obj?.pixel_size_y ??
          obj?.pixelSizeY
      );
      if (Number.isFinite(rx) && Number.isFinite(ry) && rx !== 0 && ry !== 0) {
        return { res_x: rx, res_y: ry };
      }
    } catch (_) {}
  }
  return null;
}

function computeMineChangedArea(fidRaw) {
  const fid = String(fidRaw);
  const outputDir = path.resolve(defaultOutputRoot, fid);
  const km2CsvPath = path.join(outputDir, 'change_matrix_km2.csv');
  const pxCsvPath = path.join(outputDir, 'change_matrix_pixels.csv');

  const km2Res = parseOffDiagonalFromMatrixCsv(km2CsvPath);
  if (km2Res.exists) {
    return {
      changed_area_km2: Number(km2Res.off_diagonal_sum.toFixed(6)),
      area_source: 'km2_matrix',
      has_inference_output: true,
      has_change_matrix: true,
    };
  }

  const pxRes = parseOffDiagonalFromMatrixCsv(pxCsvPath);
  if (!pxRes.exists) {
    return {
      changed_area_km2: null,
      area_source: 'none',
      has_inference_output: false,
      has_change_matrix: false,
    };
  }

  const resolution = readResolutionFromOutputDir(outputDir);
  const fallbackRes = Number(process.env.DEFAULT_PIXEL_RES_METERS || 1);
  const hasFallbackRes = Number.isFinite(fallbackRes) && fallbackRes > 0;
  if (!resolution && !hasFallbackRes) {
    return {
      changed_area_km2: null,
      area_source: 'none',
      has_inference_output: true,
      has_change_matrix: true,
    };
  }

  const resX = resolution ? resolution.res_x : fallbackRes;
  const resY = resolution ? resolution.res_y : fallbackRes;
  const pixelAreaM2 = Math.abs(resX * resY);
  const changedKm2 = (pxRes.off_diagonal_sum * pixelAreaM2) / 1e6;
  return {
    changed_area_km2: Number(changedKm2.toFixed(6)),
    area_source: resolution ? 'pixel_resolution' : 'pixel_resolution_assumed_1m',
    has_inference_output: true,
    has_change_matrix: true,
  };
}

// In-memory data storage
let minesData = []; // Array of GeoJSON features
let mineIdentityIndex = { byTbbh: new Map(), byMapFid: new Map() };
let assetManifestInfo = { path: null, sha256: null, mapping: null };
let ndviData = {}; // Object mapping FID -> Array of {year, value}
let ndbiData = {};
let ndwiData = {};
let ndsiData = {};
let ecologySeriesData = {};
let indexAvailability = {
  ndvi: { available: false, source_file: INDEX_SOURCE_FILES.ndvi, reason: 'not_loaded' },
  ndbi: { available: false, source_file: INDEX_SOURCE_FILES.ndbi, reason: 'not_loaded' },
  ndwi: { available: false, source_file: INDEX_SOURCE_FILES.ndwi, reason: 'not_loaded' },
  ndsi: { available: false, source_file: INDEX_SOURCE_FILES.ndsi, reason: 'not_loaded' },
};

// --- Helper functions for Excel parsing ---
function detectColumns(headerRow, valueRegex) {
  const header = headerRow.map((h) => String(h || '').trim());
  const fidCol = header.find((h) => /^(fid|fid_1)$/i.test(h));
  const yearCol = header.find((h) => /^year$/i.test(h));
  const valCol = header.find((h) => valueRegex.test(h));
  const yearHeaders = header.filter((h) => /(19|20)\d{2}/.test(h));
  return { fidCol, yearCol, valCol, yearHeaders, header };
}

function rowsFromSheet(sheet, valueRegex) {
  const aoa = xlsx.utils.sheet_to_json(sheet, { header: 1, defval: null });
  if (!aoa.length) return [];
  const headerRow = aoa[0];
  const { fidCol, yearCol, valCol, yearHeaders, header } = detectColumns(headerRow, valueRegex);
  const dataRows = aoa.slice(1);

  const rows = [];
  if (fidCol && yearCol && valCol) {
    // tidy format
    const idxFID = header.indexOf(fidCol);
    const idxYear = header.indexOf(yearCol);
    const idxVal = header.indexOf(valCol);
    for (const r of dataRows) {
      const fid = Number(r[idxFID]);
      const year = Number(r[idxYear]);
      const val = r[idxVal] != null ? Number(r[idxVal]) : null;
      if (!Number.isFinite(fid) || !Number.isFinite(year) || !Number.isFinite(val)) continue;
      rows.push({ fid, year, value: val });
    }
  } else if (fidCol && yearHeaders.length) {
    // wide format
    const idxFID = header.indexOf(fidCol);
    const yearIdxMap = yearHeaders.reduce((acc, y) => {
      acc[y] = header.indexOf(y);
      return acc;
    }, {});
    for (const r of dataRows) {
      const fid = Number(r[idxFID]);
      if (!Number.isFinite(fid)) continue;
      for (const yStr of yearHeaders) {
        // Extract year from header like "2023" or "NDVI_2023"
        const yMatch = yStr.match(/(19|20)\d{2}/);
        const year = yMatch ? Number(yMatch[0]) : null;
        if (!year) continue;
        const val = r[yearIdxMap[yStr]] != null ? Number(r[yearIdxMap[yStr]]) : null;
        if (Number.isFinite(val)) {
          rows.push({ fid, year, value: val });
        }
      }
    }
  }
  return rows;
}

async function loadIndexData(filePath, valueRegex) {
  const fullPath = resolveIndexSourcePath(filePath);
  const result = {
    dataMap: {},
    available: false,
    source_file: path.basename(filePath),
    reason: 'missing_source_file',
  };
  if (fs.existsSync(fullPath)) {
    try {
      const workbook = xlsx.readFile(fullPath);
      const sheetName = workbook.SheetNames[0];
      const sheet = workbook.Sheets[sheetName];
      const rows = rowsFromSheet(sheet, valueRegex);

      // Group by FID
      for (const r of rows) {
        if (!result.dataMap[r.fid]) result.dataMap[r.fid] = [];
        result.dataMap[r.fid].push({ year: r.year, value: r.value });
      }

      // Sort by year for each FID
      for (const fid in result.dataMap) {
        result.dataMap[fid].sort((a, b) => a.year - b.year);
      }
      result.available = true;
      result.reason = null;
      console.log(
        `Loaded data from ${path.basename(filePath)} for ${Object.keys(result.dataMap).length} mines.`
      );
    } catch (e) {
      result.reason = 'load_failed';
      console.error(`Failed to load ${filePath}:`, e);
    }
  } else {
    console.warn(`File not found: ${filePath}`);
  }
  return result;
}

function loadEcologySeriesWorkbook(filePath, source) {
  const fullPath = path.resolve(filePath);
  if (!fs.existsSync(fullPath)) {
    throw new Error(
      `生态诊断工作簿不存在：${fullPath}。请检查 MINER_ECOLOGY_WORKBOOK_PATH 或受控文件目录。`
    );
  }

  try {
    const workbook = xlsx.readFile(fullPath);
    const sheet = workbook.Sheets[workbook.SheetNames[0]];
    if (!sheet) {
      throw new Error('工作簿不包含可读取的工作表');
    }
    const rows = xlsx.utils.sheet_to_json(sheet, { defval: null });
    const parsed = parseEcologyWorkbookRows(rows);
    const expectedCount = Number(process.env.JIANGXI_EXPECTED_COUNT || 348);
    if (Object.keys(parsed).length !== expectedCount) {
      throw new Error(`工作簿 TBBH 数量为 ${Object.keys(parsed).length}，期望 ${expectedCount}`);
    }
    if (!hasEcologyAnnualData(parsed)) {
      throw new Error('工作簿未包含有效 TBBH 与年度生态指标列');
    }
    for (const tbbh of Object.keys(parsed)) {
      if (!mineIdentityIndex.byTbbh.has(tbbh)) {
        throw new Error(`生态工作簿 TBBH 不在权威图斑中: ${tbbh}`);
      }
    }
    console.log(
      `Loaded ecology workbook for ${Object.keys(parsed).length} mines from ${path.basename(fullPath)} (${source}).`
    );
    return parsed;
  } catch (error) {
    throw new Error(
      `生态诊断工作簿加载失败：${fullPath}。请检查 MINER_ECOLOGY_WORKBOOK_PATH 或受控文件目录。原因：${error.message}`
    );
  }
}

async function loadMinesData() {
  if (!fs.existsSync(defaultMineSourcePath)) {
    throw new Error(`江西权威 SHP 不存在: ${defaultMineSourcePath}`);
  }

  const geojson = await loadJiangxiGeoJsonFromSource(defaultMineSourcePath, pythonRunner);
  minesData = Array.isArray(geojson?.features) ? geojson.features : [];
  const expectedCount = Number(process.env.JIANGXI_EXPECTED_COUNT || 348);
  if (minesData.length !== expectedCount) {
    throw new Error(`江西权威 SHP 图斑数量错误: ${minesData.length}，期望 ${expectedCount}`);
  }
  mineIdentityIndex = buildMineIdentityIndex(minesData);
  if (assetManifestInfo.mapping) {
    for (const feature of minesData) {
      const { tbbh, map_fid: mapFid } = feature.properties;
      if (assetManifestInfo.mapping.tbbhToMapFid[tbbh] !== mapFid) {
        throw new Error(`SHP 与资产 manifest 的映射不一致: ${tbbh}/${mapFid}`);
      }
    }
  }
  console.log(
    `[Startup] loaded jiangxi geojson features=${minesData.length} source=${defaultMineSourcePath}`
  );
  if (minesData.length > 0) {
    console.log('Sample properties:', minesData[0].properties);
  }
}

// --- Initialization function ---
async function initData() {
  // 1. Validate immutable Jiangxi assets before loading dependent data.
  assetManifestInfo = loadJiangxiAssetManifest();
  await loadMinesData();

  // 2. Load Indices Data
  const ndviResult = await loadIndexData(INDEX_SOURCE_FILES.ndvi, /^(ndvi|ndvi_value)$/i);
  const ndbiResult = await loadIndexData(
    INDEX_SOURCE_FILES.ndbi,
    /^(ndbi|ndbi_value|mean_ndbi|mean)$/i
  );
  const ndwiResult = await loadIndexData(
    INDEX_SOURCE_FILES.ndwi,
    /^(ndwi|ndwi_value|mean_ndwi|mean)$/i
  );
  const ndsiResult = await loadIndexData(
    INDEX_SOURCE_FILES.ndsi,
    /^(ndsi|ndsi_value|mean_ndsi|mean)$/i
  );

  ndviData = ndviResult.dataMap;
  ndbiData = ndbiResult.dataMap;
  ndwiData = ndwiResult.dataMap;
  ndsiData = ndsiResult.dataMap;
  indexAvailability = {
    ndvi: {
      available: ndviResult.available,
      source_file: ndviResult.source_file,
      reason: ndviResult.reason,
    },
    ndbi: {
      available: ndbiResult.available,
      source_file: ndbiResult.source_file,
      reason: ndbiResult.reason,
    },
    ndwi: {
      available: ndwiResult.available,
      source_file: ndwiResult.source_file,
      reason: ndwiResult.reason,
    },
    ndsi: {
      available: ndsiResult.available,
      source_file: ndsiResult.source_file,
      reason: ndsiResult.reason,
    },
  };

  const ecologyWorkbookName = '348图斑_TableMERNet无图像预测结果.xlsx';
  const ecologyWorkbook = resolveEcologyWorkbookPath({
    environmentPath: process.env.MINER_ECOLOGY_WORKBOOK_PATH
      ? path.resolve(process.env.MINER_ECOLOGY_WORKBOOK_PATH)
      : null,
    defaultPath: path.resolve(process.cwd(), 'data', ecologyWorkbookName),
    fallbackPath: path.resolve(repoRoot, 'data', ecologyWorkbookName),
    fileExists: fs.existsSync,
  });
  ecologySeriesData = loadEcologySeriesWorkbook(ecologyWorkbook.path, ecologyWorkbook.source);
}

await initData();

function getFeatureByTbbh(rawTbbh) {
  let tbbh;
  try {
    tbbh = normalizeTbbh(rawTbbh);
  } catch (_) {
    return { error: 'TBBH 不能为空或无效', code: 'invalid_tbbh' };
  }
  const feature = mineIdentityIndex.byTbbh.get(tbbh);
  if (!feature) return { error: `TBBH 不存在: ${tbbh}`, code: 'tbbh_not_found' };
  return { tbbh, feature, mapFid: Number(feature.properties.map_fid) };
}

app.get('/api/health/jiangxi', (req, res) => {
  res.json({
    status: 'ok',
    mine_count: minesData.length,
    geojson_count: minesData.length,
    unique_tbbh_count: mineIdentityIndex.byTbbh.size,
    tbbh_duplicate_count: minesData.length - mineIdentityIndex.byTbbh.size,
    manifest_sha256: assetManifestInfo.sha256,
    asset_manifest: Boolean(assetManifestInfo.path),
    model_device: normalizeInferenceDevice(),
  });
});

// --- API Endpoints ---

// Get Global Statistics
app.get('/api/stats', authGuard, (req, res) => {
  const stats = buildDashboardStats({ minesData });
  res.json(stats);
});

// Get all mines as GeoJSON
app.get('/api/geojson', authGuard, (req, res) => {
  res.json({
    type: 'FeatureCollection',
    features: minesData,
  });
});

// Search mines
app.use('/api/mines', authGuard);
app.get('/api/mines/search', (req, res) => {
  const q = req.query.q;
  if (!q) return res.status(400).json({ error: 'Missing query parameter q' });

  const qStr = String(q).toLowerCase();
  const mapFid = Number(q);

  let found = null;

  // Exact TBBH or technical map_fid match first.
  if (Number.isSafeInteger(mapFid)) {
    found = mineIdentityIndex.byMapFid.get(mapFid) || null;
  }
  if (!found) found = mineIdentityIndex.byTbbh.get(String(q).trim()) || null;

  // If not found, try name match
  if (!found) {
    found = minesData.find((f) => {
      if (!f.properties) return false;
      const name = f.properties.mine_name || f.properties.name || '';
      return name.toLowerCase().includes(qStr);
    });
  }

  if (!found)
    return res.status(404).json({ error: 'TBBH 或地图编号不存在', code: 'mine_not_found' });

  res.json(found);
});

// Get Indices Data (NDVI, NDBI, NDWI)
app.get('/api/mines/indices', (req, res) => {
  const resolved = getFeatureByTbbh(req.query.tbbh);
  if (resolved.error)
    return res.status(resolved.code === 'tbbh_not_found' ? 404 : 400).json(resolved);
  const { tbbh, mapFid } = resolved;

  res.json(
    buildIndicesPayload({
      tbbh,
      map_fid: mapFid,
      sourceData: {
        ndvi: ndviData[mapFid] || [],
        ndbi: ndbiData[mapFid] || [],
        ndwi: ndwiData[mapFid] || [],
        ndsi: ndsiData[mapFid] || [],
      },
      availability: indexAvailability,
    })
  );
});

app.get('/api/mines/ecology-series', (req, res) => {
  const resolved = getFeatureByTbbh(req.query.tbbh);
  if (resolved.error)
    return res.status(resolved.code === 'tbbh_not_found' ? 404 : 400).json(resolved);

  const payload = buildEcologySeriesPayload({ tbbh: resolved.tbbh, dataMap: ecologySeriesData });
  if (!ecologySeriesData[resolved.tbbh]) {
    return res.status(404).json({
      error: `TBBH 存在但无历史生态结果: ${resolved.tbbh}`,
      code: 'tbbh_history_not_found',
      tbbh: resolved.tbbh,
      map_fid: resolved.mapFid,
      data: payload,
    });
  }
  return res.json({ ...payload, map_fid: resolved.mapFid });
});

app.get('/api/mines/ecology-profile', (req, res) => {
  const tbbh = parseEcologyProfileTbbh(req.query.tbbh);
  if (tbbh === null) {
    return res.status(400).json({ error: 'TBBH 不能为空' });
  }

  const profile = buildEcologyProfilePayload({ tbbh, dataMap: ecologySeriesData });
  if (!profile) {
    return res.status(404).json({ error: `未找到 TBBH ${tbbh} 的生态诊断资料` });
  }

  return res.json(profile);
});

// Get Change Matrix Data
app.get('/api/mines/change-matrix', (req, res) => {
  const resolved = getFeatureByTbbh(req.query.tbbh);
  if (resolved.error)
    return res.status(resolved.code === 'tbbh_not_found' ? 404 : 400).json(resolved);
  const fidText = String(resolved.mapFid);

  const csvPath = path.resolve(defaultOutputRoot, fidText, 'change_matrix_percent_rownorm.csv');
  const dirPath = path.resolve(defaultOutputRoot, fidText);

  if (fs.existsSync(csvPath)) {
    try {
      const content = fs.readFileSync(csvPath, 'utf-8');
      // Simple CSV parsing for this specific format
      const lines = content.trim().split('\n');
      if (lines.length === 0) return res.status(404).json({ error: 'Empty matrix' });

      const headers = lines[0].split(',').map((h) => h.trim().replace(/^\uFEFF/, '')); // Remove BOM if present
      const matrix = [];

      for (let i = 1; i < lines.length; i++) {
        const parts = lines[i].split(',');
        const rowLabel = parts[0].trim();
        const rowValues = parts.slice(1).map((v) => Number(v));
        matrix.push({ label: rowLabel, values: rowValues });
      }

      const newImageName = `${fidText}_new.png`;
      const oldImageName = `${fidText}_old.png`;
      const newImage = fs.existsSync(path.join(dirPath, newImageName))
        ? buildChangeMatrixAssetPath(fidText, newImageName)
        : null;
      const oldImage = fs.existsSync(path.join(dirPath, oldImageName))
        ? buildChangeMatrixAssetPath(fidText, oldImageName)
        : null;

      const changeArea = computeMineChangedArea(fidText);
      const matrixSource =
        changeArea.area_source === 'pixel_resolution' ||
        changeArea.area_source === 'pixel_resolution_assumed_1m'
          ? 'pixel_resolution'
          : 'historical_output';

      res.json({
        tbbh: resolved.tbbh,
        map_fid: resolved.mapFid,
        has_change_matrix: true,
        data_source: matrixSource,
        changed_area_km2: changeArea.changed_area_km2,
        area_source: changeArea.area_source,
        has_inference_output: changeArea.has_inference_output,
        headers: headers.slice(1), // First column is empty or row label header
        matrix: matrix,
        images: {
          new: newImage,
          old: oldImage,
        },
      });
    } catch (e) {
      console.error(`Failed to read change matrix for TBBH ${resolved.tbbh}:`, e);
      res.status(500).json({ error: '数据文件损坏，无法读取变化矩阵', code: 'data_file_corrupt' });
    }
  } else {
    const changeArea = computeMineChangedArea(fidText);
    res.status(404).json({
      error: `TBBH 存在但无历史变化矩阵: ${resolved.tbbh}`,
      code: 'tbbh_history_not_found',
      tbbh: resolved.tbbh,
      map_fid: resolved.mapFid,
      has_change_matrix: false,
      data_source: 'none',
      changed_area_km2: changeArea.changed_area_km2,
      area_source: changeArea.area_source,
      has_inference_output: changeArea.has_inference_output,
    });
  }
});

app.get('/api/mines/change-area-summary', (req, res) => {
  const list = minesData.map((f) => {
    const p = f.properties || {};
    const mapFid = p.map_fid;
    const area = computeMineChangedArea(mapFid);
    return {
      tbbh: p.tbbh,
      map_fid: Number(mapFid),
      mine_name: p.mine_name || p.name || `Mine_${mapFid}`,
      changed_area_km2: area.changed_area_km2,
      area_source: area.area_source,
      has_inference_output: area.has_inference_output,
      has_change_matrix: area.has_change_matrix,
    };
  });
  res.json({
    mine_total: list.length,
    valid_mine_count: list.filter((x) => Number.isFinite(x.changed_area_km2)).length,
    list,
  });
});

app.get('/api/mines/trend-report', (req, res) => {
  const className = String(req.query.class_name || 'bareground').trim();
  const direction = String(req.query.direction || 'all').trim();
  const report = buildTrendReport({
    outputRoot: defaultOutputRoot,
    minesData,
    className,
    direction,
  });
  res.json(report);
});

app.use('/api/kml', authGuard);
app.post('/api/kml/upload', (req, res) => {
  try {
    const result = saveKmlUpload({
      uploadRoot: defaultKmlUploadRoot,
      filename: req.body?.filename,
      content: req.body?.content,
    });
    res.json(result);
  } catch (err) {
    res.status(400).json({
      error: err?.message || 'KML 上传失败',
      next: '请确认文件扩展名为 .kml，且文件内容非空',
    });
  }
});

// Get NDVI data and trend (Legacy/Specific)
app.get('/api/mines/ndvi', (req, res) => {
  const resolved = getFeatureByTbbh(req.query.tbbh);
  if (resolved.error)
    return res.status(resolved.code === 'tbbh_not_found' ? 404 : 400).json(resolved);
  const data = ndviData[resolved.mapFid];

  if (!data || data.length === 0) {
    return res.status(404).json({
      error: `TBBH 存在但无 NDVI 历史结果: ${resolved.tbbh}`,
      code: 'tbbh_history_not_found',
      tbbh: resolved.tbbh,
      map_fid: resolved.mapFid,
    });
  }

  const stats = calculateStats(data);

  res.json({
    tbbh: resolved.tbbh,
    map_fid: resolved.mapFid,
    ndvi_data: data, // Keep naming for compatibility if needed, but data has .value now
    ndvi_mean: stats.mean,
    ndvi_trend: stats.trend,
    mk_trend: stats.mk_trend,
  });
});

// KML ROI inference for one image that may contain multiple mines.
app.use('/api/inference', authGuard);
app.post('/api/inference/kml-roi', async (req, res) => {
  if (kmlInferenceActive) {
    return res.status(409).json({ error: '同步分析任务正忙，请等待当前任务完成' });
  }
  kmlInferenceActive = true;
  try {
    if (req.body?.output_root) {
      return res.status(400).json({ error: '不支持自定义输出目录' });
    }
    const oldTifPath = resolvePathInRoots(
      req.body?.old_tif_path,
      inferenceDataRoots,
      'old_tif_path',
      ['.tif', '.tiff']
    );
    const newTifPath = req.body?.new_tif_path
      ? resolvePathInRoots(req.body.new_tif_path, inferenceDataRoots, 'new_tif_path', [
          '.tif',
          '.tiff',
        ])
      : oldTifPath;
    const kmlPath = resolvePathInRoots(
      req.body?.kml_path || path.basename(defaultKmlPath),
      inferenceKmlRoots,
      'kml_path',
      ['.kml', '.kmz']
    );
    const outputRoot = defaultOutputRoot;
    const device = normalizeInferenceDevice(req.body?.device);
    const limitNum = Number(req.body?.limit || 0);
    const year = normalizePathInput(req.body?.year || '');
    const oldYear = normalizePathInput(req.body?.old_year || '');
    const newYear = normalizePathInput(req.body?.new_year || '');

    if (!oldTifPath) return res.status(400).json({ error: 'Missing old_tif_path' });
    if (!fs.existsSync(oldTifPath))
      return res.status(400).json({ error: `old_tif_path not found: ${oldTifPath}` });
    if (!fs.existsSync(newTifPath))
      return res.status(400).json({ error: `new_tif_path not found: ${newTifPath}` });
    if (!fs.existsSync(kmlPath))
      return res.status(400).json({ error: `kml_path not found: ${kmlPath}` });
    if (!fs.existsSync(kmlRoiScriptPath))
      return res.status(500).json({ error: `Script not found: ${kmlRoiScriptPath}` });

    const args = buildKmlRoiArgs({
      scriptPath: kmlRoiScriptPath,
      oldTifPath,
      newTifPath,
      kmlPath,
      outputRoot,
      manifestPath: assetManifestInfo.path,
      limit: limitNum,
      year,
      oldYear,
      newYear,
      device,
    });

    const { stdout, stderr } = await execFile(
      pythonRunner.cmd,
      [...pythonRunner.preArgs, ...args],
      {
        cwd: backendRoot,
        maxBuffer: 20 * 1024 * 1024,
      }
    );

    const parsed = parseJsonFromStdout(stdout);
    const rawMatchedMapFidList = Array.isArray(parsed?.matched_fid_list)
      ? parsed.matched_fid_list.map((fid) => parsePositiveIdentifier(fid, 'map_fid'))
      : [];
    const matchedTbbhList = Array.isArray(parsed?.matched_tbbh_list)
      ? parsed.matched_tbbh_list.map((value) => normalizeTbbh(value))
      : rawMatchedMapFidList.map((mapFid) => {
          const feature = mineIdentityIndex.byMapFid.get(Number(mapFid));
          if (!feature) throw new Error(`推理结果 map_fid 无法映射 TBBH: ${mapFid}`);
          return feature.properties.tbbh;
        });
    const matchedMapFidList = rawMatchedMapFidList.length
      ? rawMatchedMapFidList
      : matchedTbbhList.map((tbbh) => {
          const feature = mineIdentityIndex.byTbbh.get(tbbh);
          if (!feature) throw new Error(`推理结果 TBBH 无法映射 map_fid: ${tbbh}`);
          return Number(feature.properties.map_fid);
        });

    const rawWrittenMapFidList = Array.isArray(parsed?.written_fid_list)
      ? parsed.written_fid_list.map((fid) => parsePositiveIdentifier(fid, 'map_fid'))
      : [];
    const writtenTbbhList = Array.isArray(parsed?.written_tbbh_list)
      ? parsed.written_tbbh_list.map((value) => normalizeTbbh(value))
      : (rawWrittenMapFidList.length ? rawWrittenMapFidList : matchedMapFidList).map((mapFid) => {
          const feature = mineIdentityIndex.byMapFid.get(Number(mapFid));
          if (!feature) throw new Error(`推理结果 map_fid 无法映射 TBBH: ${mapFid}`);
          return feature.properties.tbbh;
        });
    const writtenMapFidList = rawWrittenMapFidList.length
      ? rawWrittenMapFidList
      : writtenTbbhList.map((tbbh) => {
          const feature = mineIdentityIndex.byTbbh.get(tbbh);
          if (!feature) throw new Error(`推理结果 TBBH 无法映射 map_fid: ${tbbh}`);
          return Number(feature.properties.map_fid);
        });

    const results = writtenMapFidList.map((fid, index) => {
      const fidStr = String(fid);
      const dirPath = path.resolve(outputRoot, fidStr);
      const oldName = `${fidStr}_old.png`;
      const newName = `${fidStr}_new.png`;
      return {
        tbbh: writtenTbbhList[index],
        map_fid: Number(fidStr),
        images: {
          old: fs.existsSync(path.join(dirPath, oldName))
            ? buildChangeMatrixAssetPath(fidStr, oldName)
            : null,
          new: fs.existsSync(path.join(dirPath, newName))
            ? buildChangeMatrixAssetPath(fidStr, newName)
            : null,
        },
      };
    });

    return res.json({
      status: parsed?.status || 'completed',
      total_features: parsed?.total_features ?? null,
      matched_tbbhs: matchedTbbhList.length,
      matched_tbbh_list: matchedTbbhList,
      written_tbbhs: writtenTbbhList.length,
      written_tbbh_list: writtenTbbhList,
      failed_tiles: parsed?.failed_tiles || [],
      runtime: parsed?.runtime || null,
      stderr_tail: String(stderr || '')
        .split('\n')
        .slice(-8)
        .join('\n'),
      results,
    });
  } catch (err) {
    if (err instanceof ManagedPathError) {
      return res.status(400).json({ error: err.message });
    }
    const message = err?.message || String(err);
    const status = /device 仅支持|CUDA 不可用|江西项目仅支持 CPU/.test(message) ? 400 : 500;
    return res.status(status).json({
      error: 'Failed to run kml roi inference',
      detail: message,
    });
  } finally {
    kmlInferenceActive = false;
  }
});
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
  console.log('Mode: Local File System (No Database)');
});
