import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const read = (relativePath) => fs.readFileSync(new URL(relativePath, import.meta.url), 'utf8');

test('Jiangxi Miner exposes a fixed CPU inference contract without GPU probing', () => {
  const modal = read('../src/components/InferenceModal.vue');
  const dashboard = read('../src/components/MapDashboard.vue');
  const mineData = read('../src/composables/useMineData.js');
  const geoviewRoute = read('../routes/geoview.js');
  const server = read('../server.js');

  assert.match(modal, /固定设备：CPU/);
  assert.doesNotMatch(modal, /gpu_capability|CUDA:0|自动模式|gpuCapability/);
  assert.match(dashboard, /device:\s*'cpu'/);
  assert.doesNotMatch(dashboard, /formData\.device\s*\|\|\s*'auto'/);
  assert.match(mineData, /device\s*=\s*'cpu'/);
  assert.doesNotMatch(geoviewRoute, /gpu_capability|fetchGpuCapability/);
  assert.doesNotMatch(server, /GPU|CUDA|cuda:0/);
});
