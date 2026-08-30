import assert from 'node:assert/strict';
import test from 'node:test';

import { normalizeInferenceDevice } from '../services/inferenceDevicePolicy.js';

test('Jiangxi inference device defaults to CPU and accepts explicit CUDA profiles', () => {
  assert.equal(normalizeInferenceDevice(), 'cpu');
  assert.equal(normalizeInferenceDevice('cpu'), 'cpu');
  assert.equal(normalizeInferenceDevice('cuda'), 'cuda:0');
  assert.equal(normalizeInferenceDevice('cuda:0'), 'cuda:0');
  assert.throws(() => normalizeInferenceDevice('auto'), /仅支持/);
  assert.throws(() => normalizeInferenceDevice('cuda:1'), /仅支持/);
});

test('Jiangxi inference device uses the container environment when omitted', () => {
  const previous = process.env.JIANGXI_INFERENCE_DEVICE;
  process.env.JIANGXI_INFERENCE_DEVICE = 'cuda:0';
  try {
    assert.equal(normalizeInferenceDevice(), 'cuda:0');
  } finally {
    if (previous === undefined) delete process.env.JIANGXI_INFERENCE_DEVICE;
    else process.env.JIANGXI_INFERENCE_DEVICE = previous;
  }
});
