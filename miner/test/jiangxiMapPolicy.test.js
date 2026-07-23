import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import {
  JIANGXI_CITY_BOUNDARY_URL,
  JIANGXI_MAP_MAX_BOUNDS,
  JIANGXI_PROVINCE_BOUNDARY_URL,
  createJiangxiMapOptions,
} from '../src/map/jiangxiMapPolicy.js';

test('locks the satellite map to the Jiangxi operating extent', () => {
  assert.deepEqual(JIANGXI_MAP_MAX_BOUNDS, [
    [24.0, 113.2],
    [30.2, 118.8],
  ]);
  assert.deepEqual(createJiangxiMapOptions(), {
    maxBounds: JIANGXI_MAP_MAX_BOUNDS,
    maxBoundsViscosity: 1,
    minZoom: 7,
    maxZoom: 15,
    worldCopyJump: false,
  });
});

test('ships province and 11 city boundary layers with the Miner build', () => {
  assert.equal(JIANGXI_PROVINCE_BOUNDARY_URL, '/boundaries/jiangxi-province.geojson');
  assert.equal(JIANGXI_CITY_BOUNDARY_URL, '/boundaries/jiangxi-cities.geojson');

  const citiesPath = new URL('../public/boundaries/jiangxi-cities.geojson', import.meta.url);
  const cities = JSON.parse(fs.readFileSync(citiesPath, 'utf8'));
  assert.equal(cities.type, 'FeatureCollection');
  assert.equal(cities.features.length, 11);
  assert.ok(cities.features.every((feature) => feature.properties?.name && feature.geometry));
});
