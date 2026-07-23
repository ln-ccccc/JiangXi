import assert from 'node:assert/strict';
import test from 'node:test';

import { normalizeInferenceDevice } from '../services/inferenceDevicePolicy.js';

test('inference device defaults to auto and permits only the supported values', () => {
  assert.equal(normalizeInferenceDevice(), 'auto');
  assert.equal(normalizeInferenceDevice(' CUDA:0 '), 'cuda:0');
  assert.equal(normalizeInferenceDevice('cpu'), 'cpu');
  assert.throws(() => normalizeInferenceDevice('cuda:1'), /仅支持/);
});
