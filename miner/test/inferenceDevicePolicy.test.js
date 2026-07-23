import assert from 'node:assert/strict';
import test from 'node:test';

import { normalizeInferenceDevice } from '../services/inferenceDevicePolicy.js';

test('Jiangxi inference device is fixed to CPU', () => {
  assert.equal(normalizeInferenceDevice(), 'cpu');
  assert.equal(normalizeInferenceDevice('cpu'), 'cpu');
  assert.throws(() => normalizeInferenceDevice('auto'), /江西项目仅支持 CPU/);
  assert.throws(() => normalizeInferenceDevice('cuda:0'), /江西项目仅支持 CPU/);
  assert.throws(() => normalizeInferenceDevice('cuda:1'), /仅支持/);
});
