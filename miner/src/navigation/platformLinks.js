export function buildGeoViewUrl(configuredRoot = '') {
  const configured = String(configuredRoot || '').trim();
  if (!configured) {
    return '';
  }

  let root;
  try {
    root = new URL(configured);
  } catch {
    return '';
  }

  const isHttpRoot =
    (root.protocol === 'http:' || root.protocol === 'https:') &&
    !root.username &&
    !root.password &&
    root.pathname === '/' &&
    !root.search &&
    !root.hash;

  return isHttpRoot ? `${root.origin}/#/segmentation` : '';
}
