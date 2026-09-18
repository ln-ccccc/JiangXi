import fs from 'node:fs';

// 六类地物契约顺序（AGENTS §6）：与 change_matrix CSV 的列/行一一对应
export const CLASSIFICATION_CLASS_NAMES = [
  'grassland',
  'forest',
  'building',
  'road',
  'bareground',
  'water',
];

/**
 * 解析 kml_roi 推理管线写出的混淆矩阵 CSV（change_matrix_pixels/
 * change_matrix_percent_rownorm/change_matrix_km2）。格式：首列 class 标签 +
 * 六个数值列；行为基准期类别，列为最新期类别。任何缺失/畸形都返回 null，
 * 由调用方降级为「暂无混淆矩阵」提示。
 */
export function parseClassificationMatrixCsv(csvPath) {
  if (!fs.existsSync(csvPath)) return null;
  const content = fs.readFileSync(csvPath, 'utf-8').trim();
  if (!content) return null;
  const lines = content
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length < 2) return null;
  const colLabels = lines[0]
    .split(',')
    .slice(1)
    .map((s) => s.trim());
  if (colLabels.length === 0) return null;
  const rowLabels = [];
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(',');
    rowLabels.push(parts[0].trim());
    rows.push(parts.slice(1).map((v) => Number(String(v).trim())));
  }
  if (rows.some((row) => row.length !== colLabels.length || row.some((v) => !Number.isFinite(v)))) {
    return null;
  }
  return { row_labels: rowLabels, col_labels: colLabels, rows };
}

/**
 * 扫描某图斑目录下可用的推理年份（{fid}+{YYYY}_mask.png 形态），年份升序。
 */
export function listClassificationYears(fidDir, fid) {
  if (!fs.existsSync(fidDir)) return [];
  const yearMask = new RegExp(`^${fid}\\+(\\d{4})_mask\\.png$`);
  return fs
    .readdirSync(fidDir)
    .map((name) => yearMask.exec(name)?.[1])
    .filter(Boolean)
    .sort();
}
