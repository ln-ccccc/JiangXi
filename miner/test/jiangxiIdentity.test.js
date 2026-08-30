import assert from 'node:assert/strict';
import test from 'node:test';

import { buildMineIdentityIndex, normalizeTbbh } from '../services/jiangxiIdentity.js';

test('normalizeTbbh trims only the boundary and preserves case', () => {
  assert.equal(normalizeTbbh('  Zj3607  '), 'Zj3607');
  assert.throws(() => normalizeTbbh('   '), /TBBH/);
  assert.throws(() => normalizeTbbh('x'.repeat(129)), /128/);
});

test('buildMineIdentityIndex rejects missing and duplicate TBBH', () => {
  assert.throws(() => buildMineIdentityIndex([{ properties: { map_fid: 1 } }]), /TBBH/);
  assert.throws(
    () =>
      buildMineIdentityIndex([
        { properties: { tbbh: 'A', map_fid: 1 } },
        { properties: { tbbh: 'A', map_fid: 2 } },
      ]),
    /duplicate.*TBBH/i
  );
});

test('buildMineIdentityIndex rejects duplicate map_fid and indexes both identities', () => {
  const features = [
    { properties: { tbbh: 'A', map_fid: 23 } },
    { properties: { tbbh: 'B', map_fid: 22 } },
  ];
  const index = buildMineIdentityIndex(features);
  assert.equal(index.byTbbh.get('A'), features[0]);
  assert.equal(index.byMapFid.get(23), features[0]);
  assert.throws(
    () =>
      buildMineIdentityIndex([
        { properties: { tbbh: 'A', map_fid: 23 } },
        { properties: { tbbh: 'B', map_fid: 23 } },
      ]),
    /map_fid/i
  );
});
