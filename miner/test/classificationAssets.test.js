import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  CLASSIFICATION_CLASS_NAMES,
  listClassificationYears,
  parseClassificationMatrixCsv,
} from '../services/classificationAssets.js';
import { MINE_ECOLOGY_TABS } from '../src/utils/ecologyProfile.js';

const minerRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const readFile = (...parts) => fs.readFileSync(path.join(minerRoot, ...parts), 'utf-8');

function makeTempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'classification-assets-'));
}

test('parseClassificationMatrixCsv 解析六类像素矩阵', () => {
  const dir = makeTempDir();
  const csvPath = path.join(dir, 'change_matrix_pixels.csv');
  const lines = ['class,grassland,forest,building,road,bareground,water'];
  for (const name of CLASSIFICATION_CLASS_NAMES) {
    lines.push(`${name},1,2,3,4,5,6`);
  }
  fs.writeFileSync(csvPath, lines.join('\n'), 'utf-8');
  const matrix = parseClassificationMatrixCsv(csvPath);
  assert.equal(matrix.row_labels.length, 6);
  assert.deepEqual(matrix.col_labels, CLASSIFICATION_CLASS_NAMES);
  assert.equal(matrix.rows[0][0], 1);
  assert.equal(matrix.rows[5][5], 6);
});

test('parseClassificationMatrixCsv 接受行百分比浮点并拒绝缺失与畸形', () => {
  const dir = makeTempDir();
  const percentPath = path.join(dir, 'change_matrix_percent_rownorm.csv');
  fs.writeFileSync(
    percentPath,
    'class,grassland,forest,building,road,bareground,water\nforest,12.34,0.00,0.00,0.00,0.00,0.00\n',
    'utf-8'
  );
  const matrix = parseClassificationMatrixCsv(percentPath);
  assert.equal(matrix.row_labels[0], 'forest');
  assert.ok(Math.abs(matrix.rows[0][0] - 12.34) < 1e-9);

  const emptyPath = path.join(dir, 'empty.csv');
  fs.writeFileSync(emptyPath, '', 'utf-8');
  assert.equal(parseClassificationMatrixCsv(emptyPath), null);
  assert.equal(parseClassificationMatrixCsv(path.join(dir, 'missing.csv')), null);

  const raggedPath = path.join(dir, 'ragged.csv');
  fs.writeFileSync(raggedPath, 'class,grassland,forest\ngrassland,1,2,3\n', 'utf-8');
  assert.equal(parseClassificationMatrixCsv(raggedPath), null);
});

test('listClassificationYears 只收当前 fid 的年份掩膜并升序', () => {
  const dir = makeTempDir();
  for (const name of [
    '11192+2011_mask.png',
    '11192+2021_mask.png',
    '11192+2021.png',
    '11192+202101_mask.png',
    '99999+2011_mask.png',
  ]) {
    fs.writeFileSync(path.join(dir, name), 'x', 'utf-8');
  }
  assert.deepEqual(listClassificationYears(dir, '11192'), ['2011', '2021']);
  assert.deepEqual(listClassificationYears(path.join(dir, 'nope'), '11192'), []);
});

test('路由与标签接线：classification 路由挂 authGuard，地物分类标签已注册', () => {
  const serverSource = readFile('server.js');
  const routeLine = serverSource
    .split('\n')
    .find((line) => line.includes('/api/inference/classification/:tbbh'));
  assert.ok(routeLine, 'classification 路由未注册');
  assert.match(routeLine, /authGuard/, 'classification 路由必须挂 authGuard');

  const panelSource = readFile('src', 'components', 'EcologyDiagnosisPanels.vue');
  assert.match(panelSource, /confusion_matrix/);
  assert.match(panelSource, /confusion-matrix/);
  assert.match(panelSource, /getHeatmapColor/);
  assert.match(panelSource, /classificationItems/);
  assert.ok(MINE_ECOLOGY_TABS.includes('地物分类'), '地物分类标签未加入 MINE_ECOLOGY_TABS');
});
