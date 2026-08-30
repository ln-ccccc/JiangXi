import assert from 'node:assert/strict';
import test from 'node:test';

import { VIEW_HASH, resolveViewFromHash } from '../src/navigation/viewNavigation.js';

test('resolveViewFromHash supports the map and project workspace views', () => {
  assert.equal(resolveViewFromHash('#/map'), 'map');
  assert.equal(resolveViewFromHash('#/projects'), 'projects');
  assert.equal(resolveViewFromHash(''), 'map');
  assert.equal(resolveViewFromHash('#/unknown'), 'map');
});

test('VIEW_HASH exposes the map and project workspace hashes', () => {
  assert.deepEqual(VIEW_HASH, {
    map: '#/map',
    projects: '#/projects',
  });
});
