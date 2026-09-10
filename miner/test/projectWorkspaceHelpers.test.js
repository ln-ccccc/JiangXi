import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildMineSelectionSet,
  filterProjects,
  groupPlotsByTbbh,
  paginateList,
} from '../src/projectWorkspace/projectWorkspaceHelpers.js';

test('filterProjects matches by name, region, year and status', () => {
  const items = [
    {
      id: 1,
      name: '赣州一期',
      region: '赣州市',
      status: 'active',
      monitor_start_year: 2024,
      monitor_end_year: 2025,
    },
    {
      id: 2,
      name: '宜春归档',
      region: '宜春市',
      status: 'archived',
      monitor_start_year: 2022,
      monitor_end_year: 2023,
    },
  ];
  const filtered = filterProjects(items, {
    name: '赣州',
    region: '赣州',
    status: 'active',
    monitorYear: '2024',
  });

  assert.deepEqual(
    filtered.map((item) => item.id),
    [1]
  );
});

test('buildMineSelectionSet returns bound TBBH values as strings', () => {
  const detail = {
    mines: [{ tbbh: 'TBBH-101' }, { tbbh: 'TBBH-102' }],
  };

  const selected = buildMineSelectionSet(detail);

  assert.deepEqual(Array.from(selected.values()), ['TBBH-101', 'TBBH-102']);
});

test('groupPlotsByTbbh groups jiangxi plot rows under one TBBH', () => {
  const grouped = groupPlotsByTbbh([
    { tbbh: 'A', plot_code: 'PLOT-1', repair_status: '完全修复' },
    { tbbh: 'A', plot_code: 'PLOT-2', repair_status: '部分修复' },
    { tbbh: 'B', plot_code: 'PLOT-3', repair_status: '完全修复' },
  ]);

  assert.equal(grouped.get('A').length, 2);
  assert.equal(grouped.get('B').length, 1);
});

test('paginateList slices the requested page and reports total pages', () => {
  const items = Array.from({ length: 23 }, (_, i) => `item-${i + 1}`);

  const page1 = paginateList(items, 1, 10);
  assert.deepEqual(page1.pageItems, items.slice(0, 10));
  assert.equal(page1.totalPages, 3);

  const page3 = paginateList(items, 3, 10);
  assert.deepEqual(page3.pageItems, items.slice(20, 23));
  assert.equal(page3.totalPages, 3);
});

test('paginateList clamps out-of-range pages into valid range', () => {
  const items = Array.from({ length: 12 }, (_, i) => i);

  assert.deepEqual(paginateList(items, 0, 10).pageItems, items.slice(0, 10));
  assert.deepEqual(paginateList(items, 99, 10).pageItems, items.slice(10, 12));
});

test('paginateList handles empty lists and negative page size', () => {
  assert.deepEqual(paginateList([], 1, 10), { pageItems: [], totalPages: 1 });
  const items = [1, 2, 3];
  assert.deepEqual(paginateList(items, 1, 0), { pageItems: items, totalPages: 1 });
});
