import assert from 'node:assert/strict';
import test from 'node:test';

import { VIEW_HASH, resolveViewFromHash } from '../src/navigation/viewNavigation.js';

test('resolveViewFromHash keeps Miner on the map for default and legacy workspace hashes', () => {
  assert.equal(resolveViewFromHash('#/map'), 'map');
  assert.equal(resolveViewFromHash('#/projects'), 'map');
  assert.equal(resolveViewFromHash(''), 'map');
  assert.equal(resolveViewFromHash('#/unknown'), 'map');
});

test('VIEW_HASH exposes the map hash as the only navigable view', () => {
  assert.deepEqual(VIEW_HASH, {
    map: '#/map',
  });
});
