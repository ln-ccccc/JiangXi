import fs from 'node:fs';

export const DEFAULT_JIANGXI_RUNTIME_DIR = '/app/runtime_data';
export const DEFAULT_JIANGXI_RUNTIME_GEO_SOURCE_PATH = `${DEFAULT_JIANGXI_RUNTIME_DIR}/348个图斑.shp`;
export const DEFAULT_JIANGXI_RUNTIME_KMZ_PATH = `${DEFAULT_JIANGXI_RUNTIME_DIR}/Jiangxi_NaturalMine.kmz`;
export const DEFAULT_JIANGXI_GEO_SOURCE_PATH = 'D:/项目/江西数据/348个图斑.shp';
export const DEFAULT_JIANGXI_GEO_SOURCE_CANDIDATES = [
  DEFAULT_JIANGXI_RUNTIME_GEO_SOURCE_PATH,
  DEFAULT_JIANGXI_GEO_SOURCE_PATH,
];
export const DEFAULT_JIANGXI_KMZ_PATH = 'D:/项目/江西数据/Jiangxi_NaturalMine.kmz';
export const DEFAULT_JIANGXI_KMZ_FALLBACK_PATH = 'D:/项目/江西数据/Jiangxi/Jiangxi_NaturalMine.kmz';
export const DEFAULT_JIANGXI_KMZ_CANDIDATES = [
  DEFAULT_JIANGXI_RUNTIME_KMZ_PATH,
  DEFAULT_JIANGXI_KMZ_PATH,
  DEFAULT_JIANGXI_KMZ_FALLBACK_PATH,
];

export function resolveDefaultJiangxiGeoSourcePath(value = '', existsSyncImpl = fs.existsSync) {
  const text = String(value || '').trim();
  if (text) return text;
  const existingCandidate = DEFAULT_JIANGXI_GEO_SOURCE_CANDIDATES.find((candidate) => existsSyncImpl(candidate));
  return existingCandidate || DEFAULT_JIANGXI_GEO_SOURCE_PATH;
}

export function resolveDefaultJiangxiKmzPath(value = '', existsSyncImpl = fs.existsSync) {
  const text = String(value || '').trim();
  if (text) return text;
  const existingCandidate = DEFAULT_JIANGXI_KMZ_CANDIDATES.find((candidate) => existsSyncImpl(candidate));
  return existingCandidate || DEFAULT_JIANGXI_KMZ_PATH;
}
