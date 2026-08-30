export function filterProjects(items, filters = {}) {
  const list = Array.isArray(items) ? items : [];
  const name = String(filters.name || '')
    .trim()
    .toLowerCase();
  const region = String(filters.region || '')
    .trim()
    .toLowerCase();
  const status = String(filters.status || '')
    .trim()
    .toLowerCase();
  const monitorYear = Number(filters.monitorYear || 0);

  return list.filter((item) => {
    const projectName = String(item?.name || '').toLowerCase();
    const projectRegion = String(item?.region || '').toLowerCase();
    const projectStatus = String(item?.status || '').toLowerCase();
    const startYear = Number(item?.monitor_start_year || 0);
    const endYear = Number(item?.monitor_end_year || 0);

    if (name && !projectName.includes(name)) return false;
    if (region && !projectRegion.includes(region)) return false;
    if (status && projectStatus !== status) return false;
    if (monitorYear) {
      const hasStart = Number.isFinite(startYear) && startYear > 0;
      const hasEnd = Number.isFinite(endYear) && endYear > 0;
      if (hasStart && hasEnd) {
        if (monitorYear < startYear || monitorYear > endYear) return false;
      } else if (hasStart && monitorYear !== startYear) {
        return false;
      }
    }
    return true;
  });
}

export function buildMineSelectionSet(projectDetail) {
  const mines = Array.isArray(projectDetail?.mines) ? projectDetail.mines : [];
  return new Set(
    mines
      .map((mine) => mine?.tbbh)
      .filter((tbbh) => tbbh !== null && tbbh !== undefined && String(tbbh).trim())
      .map((tbbh) => String(tbbh).trim())
  );
}

export function groupPlotsByTbbh(plotRows = []) {
  const groups = new Map();
  for (const row of Array.isArray(plotRows) ? plotRows : []) {
    const tbbh = String(row?.tbbh || '').trim();
    if (!tbbh) continue;
    if (!groups.has(tbbh)) {
      groups.set(tbbh, []);
    }
    groups.get(tbbh).push(row);
  }
  return groups;
}
