export const MAX_TBBH_LENGTH = 128;

export function normalizeTbbh(value) {
  if (value === undefined || value === null) {
    throw new Error('TBBH is required');
  }
  const tbbh = String(value).trim();
  if (!tbbh) throw new Error('TBBH must not be empty');
  if (tbbh.length > MAX_TBBH_LENGTH) {
    throw new Error(`TBBH exceeds ${MAX_TBBH_LENGTH} characters`);
  }
  return tbbh;
}

function normalizeMapFid(value) {
  const number = Number(value);
  if (!Number.isSafeInteger(number) || number <= 0) {
    throw new Error(`map_fid must be a positive integer: ${value}`);
  }
  return number;
}

export function buildMineIdentityIndex(features = []) {
  const byTbbh = new Map();
  const byMapFid = new Map();
  for (const feature of features) {
    const properties = feature?.properties || {};
    const tbbh = normalizeTbbh(properties.tbbh ?? properties.TBBH);
    const mapFid = normalizeMapFid(properties.map_fid ?? properties.FID_1);
    if (byTbbh.has(tbbh)) throw new Error(`duplicate TBBH: ${tbbh}`);
    if (byMapFid.has(mapFid)) throw new Error(`duplicate map_fid: ${mapFid}`);
    byTbbh.set(tbbh, feature);
    byMapFid.set(mapFid, feature);
    if (!feature.properties) feature.properties = {};
    feature.properties.tbbh = tbbh;
    feature.properties.map_fid = mapFid;
  }
  return { byTbbh, byMapFid };
}

export function buildTbbhMapFidManifest(features = []) {
  const { byTbbh } = buildMineIdentityIndex(features);
  return Object.fromEntries(
    [...byTbbh].map(([tbbh, feature]) => [tbbh, feature.properties.map_fid])
  );
}
