import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFile as execFileCb, spawnSync } from 'node:child_process';
import { promisify } from 'node:util';

import { DOMParser } from '@xmldom/xmldom';
import tj from '@mapbox/togeojson';

const execFile = promisify(execFileCb);

function normalizeStatus(value) {
  const text = String(value || '').trim();
  if (!text) return 'unknown';
  if (text.includes('未')) return 'untreated';
  if (text.includes('完全') || text.includes('治理') || text.includes('修复') || text.includes('恢复')) {
    return 'treated';
  }
  return 'unknown';
}

function pickFirstProperty(properties, keys) {
  for (const key of keys) {
    const value = properties?.[key];
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      return value;
    }
  }
  return null;
}

function toNumber(value) {
  const text = String(value ?? '').trim().replace(/,/g, '');
  if (!text) return null;
  const result = Number(text);
  return Number.isFinite(result) ? result : null;
}

function normalizeText(value) {
  if (value === undefined || value === null) return '';
  const text = String(value).trim();
  if (!text || text.toLowerCase() === 'nan' || text.toLowerCase() === 'null') return '';
  return text;
}

function findFirstKmlFile(rootDir) {
  const entries = fs.readdirSync(rootDir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(rootDir, entry.name);
    if (entry.isDirectory()) {
      const nested = findFirstKmlFile(fullPath);
      if (nested) return nested;
      continue;
    }
    if (entry.isFile() && entry.name.toLowerCase().endsWith('.kml')) {
      return fullPath;
    }
  }
  return null;
}

function extractKmlTextFromKmz(kmzPath) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'jiangxi-kmz-unzip-'));
  try {
    const zipPath = path.join(tempDir, 'archive.zip');
    fs.copyFileSync(kmzPath, zipPath);
    const archiveCommand = [
      'Expand-Archive',
      `-LiteralPath '${zipPath.replace(/'/g, "''")}'`,
      `-DestinationPath '${tempDir.replace(/'/g, "''")}'`,
      '-Force',
    ].join(' ');
    const probe = spawnSync(
      'powershell.exe',
      ['-NoProfile', '-Command', archiveCommand],
      { encoding: 'utf8' }
    );
    if (probe.status !== 0) {
      throw new Error(`Expand-Archive failed: ${probe.stderr || probe.stdout}`.trim());
    }

    const kmlPath = findFirstKmlFile(tempDir);
    if (!kmlPath) {
      throw new Error(`No KML found in ${kmzPath}`);
    }
    return fs.readFileSync(kmlPath, 'utf8');
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

function normalizeFeature(feature, index) {
  const properties = { ...(feature.properties || {}) };
  const fid = toNumber(pickFirstProperty(properties, ['FID_1', 'FID', 'No', 'OBJECTID', '序号'])) ?? (index + 1);
  const mineName = String(
    pickFirstProperty(properties, ['mine_name', 'name', '名称', '矿山名称', '矿山位置', '矿山位置_', '图斑编号', 'TBBH']) || `矿山 ${fid}`
  );
  const city = String(pickFirstProperty(properties, ['SHI', '地市', '市']) || '');
  const area = toNumber(pickFirstProperty(properties, ['area', 'TBTYMJ', 'TBTYMJ_1', 'Area', 'SHAPE_Area', '面积', '图斑核定面', '实际修复面']));
  const rawStatus = normalizeText(pickFirstProperty(properties, ['HFZLQK', '修复状态', 'status']));
  const miningMethod = normalizeText(pickFirstProperty(properties, ['KCFS', '开采方式', '开采方']));
  const completionYear = normalizeText(pickFirstProperty(properties, ['GBND', '关闭年', '完成时间']));
  const restorationMethod = normalizeText(pickFirstProperty(properties, ['NXFFS', '修复模式']));
  const damageType = normalizeText(pickFirstProperty(properties, ['STWT', '图斑小类']));
  const landType = normalizeText(pickFirstProperty(properties, ['NXFFX', '工程项目类']));

  return {
    ...feature,
    properties: {
      ...properties,
      FID_1: fid,
      name: normalizeText(properties.name) || mineName,
      mine_name: mineName,
      SHI: city,
      area,
      TBTYMJ: toNumber(properties.TBTYMJ) ?? area,
      HFZLQK: rawStatus,
      KCFS: miningMethod,
      GBND: completionYear,
      NXFFS: restorationMethod,
      STWT: damageType,
      NXFFX: landType,
      status_normalized: normalizeStatus(rawStatus),
    },
  };
}

function resolvePythonRunner(options = {}) {
  const pythonCmd = normalizeText(options.pythonCmd || options.cmd || '');
  const preArgs = Array.isArray(options.preArgs) ? options.preArgs : [];
  if (pythonCmd) {
    return { cmd: pythonCmd, preArgs };
  }
  return { cmd: 'python', preArgs: [] };
}

async function loadGeoJsonFromShp(shpPath, options = {}) {
  const pythonRunner = resolvePythonRunner(options);
  const script = `
import json
import sys

path = sys.argv[1]
try:
    import geopandas as gpd
except ModuleNotFoundError:
    from osgeo import ogr, osr

    ogr.DontUseExceptions()
    dataset = ogr.Open(path)
    if dataset is None:
        raise RuntimeError(f"failed to open shapefile: {path}")

    layer = dataset.GetLayer(0)
    layer_defn = layer.GetLayerDefn()
    source_srs = layer.GetSpatialRef()
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(4326)
    transform = None

    if source_srs is not None and not source_srs.IsSame(target_srs):
        transform = osr.CoordinateTransformation(source_srs, target_srs)

    features = []
    for feature in layer:
        geometry_ref = feature.GetGeometryRef()
        if geometry_ref is None:
            continue

        geometry = geometry_ref.Clone()
        if transform is not None:
            geometry.Transform(transform)

        properties = {}
        for index in range(layer_defn.GetFieldCount()):
            field_name = layer_defn.GetFieldDefn(index).GetName()
            properties[field_name] = feature.GetField(index)

        features.append({
            "type": "Feature",
            "properties": properties,
            "geometry": json.loads(geometry.ExportToJson()),
        })

    geojson = {"type": "FeatureCollection", "features": features}
else:
    gdf = gpd.read_file(path)
    if gdf.crs is not None and str(gdf.crs).upper() != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)
    geojson = json.loads(gdf.to_json())

print(json.dumps(geojson, ensure_ascii=False))
  `.trim();
  const { stdout } = await execFile(
    pythonRunner.cmd,
    [...pythonRunner.preArgs, '-c', script, path.resolve(shpPath)],
    { encoding: 'utf8', maxBuffer: 100 * 1024 * 1024 }
  );
  return JSON.parse(stdout);
}

export async function loadJiangxiGeoJsonFromKmz(kmzPath) {
  const kmlText = extractKmlTextFromKmz(path.resolve(kmzPath));
  const xml = new DOMParser().parseFromString(kmlText, 'text/xml');
  const geojson = tj.kml(xml);

  return {
    type: 'FeatureCollection',
    features: (geojson.features || [])
      .filter((feature) => feature?.geometry?.type === 'Polygon' || feature?.geometry?.type === 'MultiPolygon')
      .map((feature, index) => normalizeFeature(feature, index)),
  };
}

export async function loadJiangxiGeoJsonFromShp(shpPath, options = {}) {
  const geojson = await loadGeoJsonFromShp(path.resolve(shpPath), options);
  return {
    type: 'FeatureCollection',
    features: (geojson.features || [])
      .filter((feature) => feature?.geometry?.type === 'Polygon' || feature?.geometry?.type === 'MultiPolygon')
      .map((feature, index) => normalizeFeature(feature, index)),
  };
}

export async function loadJiangxiGeoJsonFromSource(sourcePath, options = {}) {
  const fullPath = path.resolve(sourcePath);
  const ext = path.extname(fullPath).toLowerCase();
  if (ext === '.kmz') {
    return loadJiangxiGeoJsonFromKmz(fullPath);
  }
  if (ext === '.shp') {
    return loadJiangxiGeoJsonFromShp(fullPath, options);
  }
  throw new Error(`Unsupported jiangxi geo source: ${fullPath}`);
}
