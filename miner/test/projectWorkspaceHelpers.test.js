import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildMineSelectionSet,
  filterProjects,
  groupPlotsByMineFid,
} from '../src/projectWorkspace/projectWorkspaceHelpers.js';

test('filterProjects matches by name, region, year and status', () => {
  const items = [
    { id: 1, name: '赣州一期', region: '赣州市', status: 'active', monitor_start_year: 2024, monitor_end_year: 2025 },
    { id: 2, name: '宜春归档', region: '宜春市', status: 'archived', monitor_start_year: 2022, monitor_end_year: 2023 },
  ];
  const filtered = filterProjects(items, {
    name: '赣州',
    region: '赣州',
    status: 'active',
    monitorYear: '2024',
  });

  assert.deepEqual(filtered.map((item) => item.id), [1]);
});

test('buildMineSelectionSet returns bound mine fid values as strings', () => {
  const detail = {
    mines: [
      { mine_fid: 101 },
      { mine_fid: 102 },
    ],
  };

  const selected = buildMineSelectionSet(detail);

  assert.deepEqual(Array.from(selected.values()), ['101', '102']);
});

test('groupPlotsByMineFid groups jiangxi plot rows under one subject', () => {
  const grouped = groupPlotsByMineFid([
    { mine_fid: 1, plot_code: 'PLOT-1', repair_status: '完全修复' },
    { mine_fid: 1, plot_code: 'PLOT-2', repair_status: '部分修复' },
    { mine_fid: 2, plot_code: 'PLOT-3', repair_status: '完全修复' },
  ]);

  assert.equal(grouped.get(1).length, 2);
  assert.equal(grouped.get(2).length, 1);
});
