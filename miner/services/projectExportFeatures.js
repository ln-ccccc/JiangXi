export function buildProjectExportFeatures({ projectDetail, minesData }) {
  const summary = projectDetail?.summary || {};
  const mines = Array.isArray(projectDetail?.mines) ? projectDetail.mines : [];
  const datasets = Array.isArray(projectDetail?.datasets) ? projectDetail.datasets : [];
  const mineFeatureMap = new Map(
    (Array.isArray(minesData) ? minesData : []).map((feature) => [
      String(feature?.properties?.tbbh || '').trim(),
      feature,
    ])
  );

  return mines
    .map((mine) => {
      const tbbh = String(mine?.tbbh || '').trim();
      const feature = mineFeatureMap.get(tbbh);
      if (!feature?.geometry) return null;
      const dataset = datasets.find((item) => String(item?.tbbh || '').trim() === tbbh) || null;
      return {
        type: 'Feature',
        geometry: feature.geometry,
        properties: {
          project_id: Number(summary.id || 0),
          tbbh,
          map_fid: Number(feature.properties?.map_fid),
          mine_name:
            mine.mine_name_snapshot ||
            feature?.properties?.mine_name ||
            feature?.properties?.name ||
            '',
          dataset_id: dataset?.id ?? null,
          result_type: dataset?.dataset_kind || null,
          year_start: dataset?.year_start ?? null,
          year_end: dataset?.year_end ?? null,
        },
      };
    })
    .filter(Boolean);
}
