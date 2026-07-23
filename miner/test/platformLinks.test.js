import test from 'node:test';
import assert from 'node:assert/strict';

import { buildGeoViewUrl, buildMinerMapUrl } from '../src/navigation/platformLinks.js';

const intranetLocation = {
  protocol: 'http:',
  hostname: '192.168.1.20',
};

test('platform links retain the current host and use the dedicated frontend ports', () => {
  assert.equal(buildGeoViewUrl(intranetLocation), 'http://192.168.1.20:3000/#/segmentation');
  assert.equal(buildMinerMapUrl(intranetLocation), 'http://192.168.1.20:4000/#/map');
});

test('configured platform root overrides the generated host', () => {
  assert.equal(
    buildGeoViewUrl(intranetLocation, 'https://geoview.example/'),
    'https://geoview.example/#/segmentation'
  );
});
