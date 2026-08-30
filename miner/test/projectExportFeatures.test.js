import assert from 'node:assert/strict';
import test from 'node:test';

import { buildProjectExportFeatures } from '../services/projectExportFeatures.js';

test('buildProjectExportFeatures joins bound mines with live geometries and dataset metadata', () => {
  const projectDetail = {
    summary: { id: 7 },
    mines: [
      { tbbh: 'A-001', map_fid: 101, mine_name_snapshot: '矿山A' },
      { tbbh: 'B-002', map_fid: 102, mine_name_snapshot: '矿山B' },
    ],
    datasets: [
      {
        id: 9001,
        tbbh: 'A-001',
        dataset_kind: 'imagery',
        year_start: 2024,
        year_end: 2024,
      },
    ],
  };
  const minesData = [
    {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [100, 25],
            [100.1, 25],
            [100.1, 25.1],
            [100, 25.1],
            [100, 25],
          ],
        ],
      },
      properties: { tbbh: 'A-001', map_fid: 23, mine_name: '矿山A' },
    },
    {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [101, 26],
            [101.1, 26],
            [101.1, 26.1],
            [101, 26.1],
            [101, 26],
          ],
        ],
      },
      properties: { tbbh: 'B-002', map_fid: 22, mine_name: '矿山B' },
    },
  ];

  const features = buildProjectExportFeatures({ projectDetail, minesData });

  assert.equal(features.length, 2);
  assert.equal(features[0].properties.project_id, 7);
  assert.equal(features[0].properties.tbbh, 'A-001');
  assert.equal(features[0].properties.map_fid, 23);
  assert.equal(features[0].properties.dataset_id, 9001);
  assert.equal(features[0].properties.result_type, 'imagery');
  assert.equal(features[1].properties.tbbh, 'B-002');
  assert.equal(features[1].properties.map_fid, 22);
  assert.equal(features[1].properties.dataset_id, null);
});
