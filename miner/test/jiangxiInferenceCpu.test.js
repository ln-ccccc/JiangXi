import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const read = (relativePath) => fs.readFileSync(new URL(relativePath, import.meta.url), 'utf8');

test('Jiangxi Miner uses the configured inference device without automatic fallback', () => {
  const modal = read('../src/components/InferenceModal.vue');
  const dashboard = read('../src/components/MapDashboard.vue');
  const mineData = read('../src/composables/useMineData.js');
  const geoviewRoute = read('../routes/geoview.js');
  const server = read('../server.js');

  assert.match(modal, /当前容器设备/);
  assert.match(modal, /INFERENCE_DEVICE/);
  assert.match(dashboard, /device:\s*INFERENCE_DEVICE/);
  assert.doesNotMatch(dashboard, /formData\.device\s*\|\|\s*'auto'/);
  assert.match(mineData, /device\s*=\s*INFERENCE_DEVICE/);
  assert.doesNotMatch(geoviewRoute, /gpu_capability|fetchGpuCapability/);
  assert.match(server, /model_device:\s*normalizeInferenceDevice\(\)/);
});
