import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
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
import { buildIndicesPayload, calculateStats, INDEX_SOURCE_FILES } from './services/indexSeries.js';
import { loadJiangxiGeoJsonFromSource } from './services/jiangxiGeoJsonSource.js';
import { saveKmlUpload } from './services/kmlUpload.js';
import { buildEmptyTilePng, resolveLocalTilePath } from './services/localTileService.js';
import { ManagedPathError, resolvePathInRoots } from './services/inferencePathPolicy.js';
import { parsePositiveIdentifier } from './services/pathValidation.js';
import { buildTrendReport } from './services/trendReport.js';

dotenv.config();

const app = express();
const port = process.env.PORT ? Number(process.env.PORT) : 8000;
const execFile = promisify(execFileCb);
let kmlInferenceActive = false;
const startupCwd = process.cwd();
console.log(`[Startup] miner cwd=${startupCwd}`);
if (/wsl|\\\\wsl\\.localhost/i.test(startupCwd)) {
  console.warn('[Startup] Warning: running from WSL path; expected E:\\GeoView\\miner');
}

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
  res.setHeader('Content-Type', 'image/png');
  res.setHeader('Cache-Control', 'public, max-age=120');
  return res.send(buildEmptyTilePng());
});
app.use('/tiles', express.static(tileStaticDir));

const changeMatrixStaticDir = path.resolve(process.cwd(), 'change_matrix_outputs');
app.use('/change-matrix-outputs', authGuard, express.static(changeMatrixStaticDir));

const repoRoot = path.resolve(process.cwd(), '..');
const backendRoot = path.resolve(repoRoot, 'backend');
const defaultMineSourcePath = path.resolve(
  resolveDefaultJiangxiGeoSourcePath(process.env.MINER_DEFAULT_GEO_SOURCE_PATH)
);
const defaultKmlPath = path.resolve(
  resolveDefaultJiangxiKmzPath(process.env.MINER_DEFAULT_KMZ_PATH)
);
const defaultOutputRoot = path.resolve(process.cwd(), 'change_matrix_outputs');
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
  const outputDir = path.resolve(process.cwd(), 'change_matrix_outputs', fid);
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
  const fullPath = path.resolve(process.cwd(), filePath);
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
    if (!hasEcologyAnnualData(parsed)) {
      throw new Error('工作簿未包含有效 FID 与年度生态指标列');
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
    minesData = [];
    console.warn(`Default mine source not found: ${defaultMineSourcePath}`);
    return;
  }

  const geojson = await loadJiangxiGeoJsonFromSource(defaultMineSourcePath, pythonRunner);
  minesData = Array.isArray(geojson?.features) ? geojson.features : [];
  console.log(
    `[Startup] loaded jiangxi geojson features=${minesData.length} source=${defaultMineSourcePath}`
  );
  if (minesData.length > 0) {
    console.log('Sample properties:', minesData[0].properties);
  }
}

// --- Initialization function ---
async function initData() {
  // 1. Load 江西 KMZ polygons via the shared source adapter.
  try {
    await loadMinesData();
  } catch (e) {
    minesData = [];
    console.error(`Failed to parse mine source ${defaultMineSourcePath}:`, e);
  }

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
  const fid = parseInt(q, 10);

  let found = null;

  // Try exact FID match first
  if (!isNaN(fid)) {
    found = minesData.find((f) => f.properties && f.properties.FID_1 === fid);
  }

  // If not found, try name match
  if (!found) {
    found = minesData.find((f) => {
      if (!f.properties) return false;
      const name = f.properties.mine_name || f.properties.name || '';
      return name.toLowerCase().includes(qStr);
    });
  }

  if (!found) return res.status(404).json({ error: 'Mine not found' });

  res.json(found);
});

// Get Indices Data (NDVI, NDBI, NDWI)
app.get('/api/mines/indices', (req, res) => {
  const { fid } = req.query;
  if (!fid) return res.status(400).json({ error: 'Missing FID parameter' });

  const fidNum = Number(fid);

  res.json(
    buildIndicesPayload({
      fid: fidNum,
      sourceData: {
        ndvi: ndviData[fidNum] || [],
        ndbi: ndbiData[fidNum] || [],
        ndwi: ndwiData[fidNum] || [],
        ndsi: ndsiData[fidNum] || [],
      },
      availability: indexAvailability,
    })
  );
});

app.get('/api/mines/ecology-series', (req, res) => {
  const { fid } = req.query;
  if (!fid) return res.status(400).json({ error: 'Missing FID parameter' });

  res.json(
    buildEcologySeriesPayload({
      fid: Number(fid),
      dataMap: ecologySeriesData,
    })
  );
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
  const { fid } = req.query;
  if (!fid) return res.status(400).json({ error: 'Missing FID parameter' });

  let fidText;
  try {
    fidText = parsePositiveIdentifier(fid, 'FID');
  } catch (error) {
    return res.status(400).json({ error: error.message });
  }
  const fidNum = Number(fidText);

  const csvPath = path.resolve(
    process.cwd(),
    'change_matrix_outputs',
    fidText,
    'change_matrix_percent_rownorm.csv'
  );
  const dirPath = path.resolve(process.cwd(), 'change_matrix_outputs', fidText);

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
        fid: fidNum,
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
      console.error(`Failed to read change matrix for FID ${fid}:`, e);
      res.status(500).json({ error: 'Failed to read matrix file' });
    }
  } else {
    const changeArea = computeMineChangedArea(fidText);
    res.status(404).json({
      error: 'Change matrix not found for this FID',
      fid: fidNum,
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
    const fid = p.FID_1;
    const area = computeMineChangedArea(fid);
    return {
      fid: Number(fid),
      mine_name: p.mine_name || p.name || `Mine_${fid}`,
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
  const { fid } = req.query;
  if (!fid) return res.status(400).json({ error: 'Missing FID parameter' });

  const fidNum = Number(fid);
  const data = ndviData[fidNum];

  if (!data || data.length === 0) {
    return res.status(404).json({ error: 'No NDVI data for this FID' });
  }

  const stats = calculateStats(data);

  res.json({
    fid: fidNum,
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
    return res.status(409).json({ error: 'GPU 正忙，请等待当前任务完成' });
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
    normalizeInferenceDevice(req.body?.device);
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
      limit: limitNum,
      year,
      oldYear,
      newYear,
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
    const matchedFidList = Array.isArray(parsed?.matched_fid_list) ? parsed.matched_fid_list : [];
    const writtenFidList = (
      Array.isArray(parsed?.written_fid_list) ? parsed.written_fid_list : matchedFidList
    ).map((fid) => parsePositiveIdentifier(fid, 'FID'));

    const results = writtenFidList.map((fid) => {
      const fidStr = String(fid);
      const dirPath = path.resolve(outputRoot, fidStr);
      const oldName = `${fidStr}_old.png`;
      const newName = `${fidStr}_new.png`;
      return {
        fid: Number(fidStr),
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
      matched_fids: parsed?.matched_fids ?? matchedFidList.length,
      matched_fid_list: matchedFidList,
      written_fids: parsed?.written_fids ?? writtenFidList.length,
      written_fid_list: writtenFidList,
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
    const status = /device 仅支持|江西项目仅支持 CPU/.test(message) ? 400 : 500;
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
