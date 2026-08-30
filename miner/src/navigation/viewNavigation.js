export const VIEW_HASH = {
  map: '#/map',
  projects: '#/projects',
};

export function resolveViewFromHash(hash = '') {
  if (String(hash || '').split('?')[0] === VIEW_HASH.projects) {
    return 'projects';
  }
  return 'map';
}
