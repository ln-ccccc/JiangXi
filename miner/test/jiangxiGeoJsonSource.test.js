import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

import {
  loadJiangxiGeoJsonFromKmz,
  loadJiangxiGeoJsonFromShp,
  loadJiangxiGeoJsonFromSource,
} from '../services/jiangxiGeoJsonSource.js';

function writeFakeKmz(kmlText) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'jiangxi-kmz-'));
  const kmlPath = path.join(tempDir, 'doc.kml');
  const zipPath = path.join(tempDir, 'sample.zip');
  const kmzPath = path.join(tempDir, 'sample.kmz');
  fs.writeFileSync(kmlPath, kmlText, 'utf8');

  const archiveCommand = [
    'Compress-Archive',
    `-LiteralPath '${kmlPath.replace(/'/g, "''")}'`,
    `-DestinationPath '${zipPath.replace(/'/g, "''")}'`,
    '-Force',
  ].join(' ');
  const result = spawnSync('powershell.exe', ['-NoProfile', '-Command', archiveCommand], {
    encoding: 'utf8',
  });
  if (result.status !== 0) {
    throw new Error(`Compress-Archive failed: ${result.stderr || result.stdout}`.trim());
  }
  fs.renameSync(zipPath, kmzPath);

  return { tempDir, kmzPath };
}

function writeFakeShp(records) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'jiangxi-shp-'));
  const specPath = path.join(tempDir, 'records.json');
  const shpPath = path.join(tempDir, 'sample.shp');
  fs.writeFileSync(specPath, JSON.stringify(records), 'utf8');

  const script = `
import json
import sys
import geopandas as gpd
from shapely.geometry import shape

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    records = json.load(f)
props = [item.get('properties', {}) for item in records]
geometries = [shape(item['geometry']) for item in records]
gdf = gpd.GeoDataFrame(props, geometry=geometries, crs='EPSG:4326')
gdf.to_file(sys.argv[2], encoding='utf-8')
  `.trim();
  const result = spawnSync('python', ['-c', script, specPath, shpPath], { encoding: 'utf8' });
  if (result.status !== 0) {
    throw new Error(`create fake shp failed: ${result.stderr || result.stdout}`.trim());
  }
  return { tempDir, shpPath };
}

test('loadJiangxiGeoJsonFromKmz normalizes polygon properties', async (t) => {
  const { tempDir, kmzPath } = writeFakeKmz(`<?xml version="1.0" encoding="UTF-8"?>
  <kml xmlns="http://www.opengis.net/kml/2.2">
    <Document>
      <Placemark>
        <name>江西省宜春市高安市示例矿山</name>
        <ExtendedData>
          <Data name="FID_1"><value>101</value></Data>
          <Data name="TBBH"><value>TBBH-101</value></Data>
          <Data name="SHI"><value>宜春市</value></Data>
          <Data name="TBTYMJ"><value>15391.28</value></Data>
          <Data name="HFZLQK"><value>完全修复</value></Data>
        </ExtendedData>
        <Polygon>
          <outerBoundaryIs>
            <LinearRing>
              <coordinates>
                115.1,28.1,0 115.2,28.1,0 115.2,28.2,0 115.1,28.2,0 115.1,28.1,0
              </coordinates>
            </LinearRing>
          </outerBoundaryIs>
        </Polygon>
      </Placemark>
    </Document>
  </kml>`);
  t.after(() => fs.rmSync(tempDir, { recursive: true, force: true }));

  const result = await loadJiangxiGeoJsonFromKmz(kmzPath);

  assert.equal(result.type, 'FeatureCollection');
  assert.equal(result.features.length, 1);
  assert.equal(result.features[0].geometry.type, 'Polygon');
  assert.equal(result.features[0].properties.FID_1, 101);
  assert.equal(result.features[0].properties.map_fid, 101);
  assert.equal(result.features[0].properties.tbbh, 'TBBH-101');
  assert.equal(result.features[0].properties.mine_name, '江西省宜春市高安市示例矿山');
  assert.equal(result.features[0].properties.SHI, '宜春市');
  assert.equal(result.features[0].properties.area, 15391.28);
  assert.equal(result.features[0].properties.status_normalized, 'treated');
});

test('loadJiangxiGeoJsonFromKmz keeps polygon features and legacy properties', async (t) => {
  const { tempDir, kmzPath } = writeFakeKmz(`<?xml version="1.0" encoding="UTF-8"?>
  <kml xmlns="http://www.opengis.net/kml/2.2">
    <Document>
      <Placemark>
        <name>江西矿山A</name>
        <ExtendedData>
          <Data name="FID"><value>7</value></Data>
          <Data name="TBBH"><value>TBBH-7</value></Data>
          <Data name="地市"><value>南昌市</value></Data>
          <Data name="Area"><value>2345</value></Data>
          <Data name="KCFS"><value>A</value></Data>
          <Data name="HFZLQK"><value>未治理</value></Data>
        </ExtendedData>
        <Polygon>
          <outerBoundaryIs>
            <LinearRing>
              <coordinates>
                116.1,28.6,0 116.2,28.6,0 116.2,28.7,0 116.1,28.7,0 116.1,28.6,0
              </coordinates>
            </LinearRing>
          </outerBoundaryIs>
        </Polygon>
      </Placemark>
      <Placemark>
        <name>忽略点位</name>
        <Point>
          <coordinates>116.3,28.8,0</coordinates>
        </Point>
      </Placemark>
    </Document>
  </kml>`);
  t.after(() => fs.rmSync(tempDir, { recursive: true, force: true }));

  const result = await loadJiangxiGeoJsonFromKmz(kmzPath);
  const properties = result.features[0].properties;

  assert.equal(result.features.length, 1);
  assert.equal(properties.FID_1, 7);
  assert.equal(properties.mine_name, '江西矿山A');
  assert.equal(properties.SHI, '南昌市');
  assert.equal(properties.area, 2345);
  assert.equal(properties.KCFS, 'A');
  assert.equal(properties.status_normalized, 'untreated');
});

test('loadJiangxiGeoJsonFromKmz rejects a polygon without map_fid', async (t) => {
  const { tempDir, kmzPath } = writeFakeKmz(`<?xml version="1.0" encoding="UTF-8"?>
  <kml xmlns="http://www.opengis.net/kml/2.2">
    <Document>
      <Placemark>
        <name>江西矿山缺少地图编号</name>
        <ExtendedData><Data name="TBBH"><value>TBBH-MISSING-MAP-ID</value></Data></ExtendedData>
        <Polygon>
          <outerBoundaryIs><LinearRing><coordinates>
            116.1,28.6,0 116.2,28.6,0 116.2,28.7,0 116.1,28.7,0 116.1,28.6,0
          </coordinates></LinearRing></outerBoundaryIs>
        </Polygon>
      </Placemark>
    </Document>
  </kml>`);
  t.after(() => fs.rmSync(tempDir, { recursive: true, force: true }));

  await assert.rejects(() => loadJiangxiGeoJsonFromKmz(kmzPath), /map_fid/);
});

test('loadJiangxiGeoJsonFromShp normalizes polygon properties and keeps legacy fields', async (t) => {
  const { tempDir, shpPath } = writeFakeShp([
    {
      properties: {
        FID_1: 23,
        TBBH: 'TBBH-23',
        SHI: '赣州市',
        TBTYMJ: '51149.365963476',
        mine_name: '江西省赣州市大余县左拔镇大江村',
        HFZLQK: '完全修复',
        NXFFS: '工程修复',
        STWT: '无主废弃矿山',
        NXFFX: '地方财政支持的项目',
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [114.44, 25.52],
            [114.45, 25.52],
            [114.45, 25.53],
            [114.44, 25.53],
            [114.44, 25.52],
          ],
        ],
      },
    },
    {
      properties: {
        FID_1: 24,
        TBBH: 'TBBH-24',
        SHI: '赣州市',
        mine_name: '江西矿山B',
        HFZLQK: '未治理',
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [114.46, 25.54],
            [114.47, 25.54],
            [114.47, 25.55],
            [114.46, 25.55],
            [114.46, 25.54],
          ],
        ],
      },
    },
  ]);
  t.after(() => fs.rmSync(tempDir, { recursive: true, force: true }));

  const result = await loadJiangxiGeoJsonFromShp(shpPath);
  const sourceResult = await loadJiangxiGeoJsonFromSource(shpPath);
  const properties = result.features[0].properties;

  assert.equal(result.type, 'FeatureCollection');
  assert.equal(result.features.length, 2);
  assert.equal(sourceResult.features.length, 2);
  assert.equal(result.features[0].geometry.type, 'Polygon');
  assert.equal(properties.FID_1, 23);
  assert.equal(properties.map_fid, 23);
  assert.equal(properties.tbbh, 'TBBH-23');
  assert.equal(properties.mine_name, '江西省赣州市大余县左拔镇大江村');
  assert.equal(properties.name, '江西省赣州市大余县左拔镇大江村');
  assert.equal(properties.SHI, '赣州市');
  assert.equal(properties.area, 51149.365963476);
  assert.equal(properties.TBTYMJ, 51149.365963476);
  assert.equal(properties.HFZLQK, '完全修复');
  assert.equal(properties.NXFFS, '工程修复');
  assert.equal(properties.STWT, '无主废弃矿山');
  assert.equal(properties.NXFFX, '地方财政支持的项目');
  assert.equal(properties.status_normalized, 'treated');
});
