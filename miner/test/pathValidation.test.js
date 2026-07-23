import assert from 'node:assert/strict';
import test from 'node:test';

import { parsePositiveIdentifier, parseTileCoordinate } from '../services/pathValidation.js';

test('parsePositiveIdentifier accepts positive numeric identifiers', () => {
  assert.equal(parsePositiveIdentifier('101', 'FID'), '101');
});

test('parsePositiveIdentifier rejects traversal and zero', () => {
  assert.throws(() => parsePositiveIdentifier('../101', 'FID'), /FID/);
  assert.throws(() => parsePositiveIdentifier('0', 'FID'), /FID/);
});

test('parseTileCoordinate accepts zero and rejects traversal', () => {
  assert.equal(parseTileCoordinate('0', 'z'), '0');
  assert.throws(() => parseTileCoordinate('../0', 'z'), /z/);
});
