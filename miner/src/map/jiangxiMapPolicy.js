export const JIANGXI_PROVINCE_BOUNDARY_URL = '/boundaries/jiangxi-province.geojson';
export const JIANGXI_CITY_BOUNDARY_URL = '/boundaries/jiangxi-cities.geojson';
export const JIANGXI_MAP_MAX_BOUNDS = [
  [24.0, 113.2],
  [30.2, 118.8],
];

export const JIANGXI_MAP_MIN_ZOOM = 7;
export const JIANGXI_MAP_MAX_ZOOM = 15;

export function createJiangxiMapOptions() {
  return {
    maxBounds: JIANGXI_MAP_MAX_BOUNDS,
    maxBoundsViscosity: 1,
    minZoom: JIANGXI_MAP_MIN_ZOOM,
    maxZoom: JIANGXI_MAP_MAX_ZOOM,
    worldCopyJump: false,
  };
}
