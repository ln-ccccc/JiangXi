import fs from 'node:fs';
import path from 'node:path';

import { parseTileCoordinate } from './pathValidation.js';

const EMPTY_TILE_PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAAAGklEQVR4nO3BMQEAAADCoPdPbQ8HFAAAAAAAAAAA8G4wQAABiwCo9wAAAABJRU5ErkJggg==';

export function buildEmptyTilePng() {
  return Buffer.from(EMPTY_TILE_PNG_BASE64, 'base64');
}

export function resolveLocalTilePath(tileRoot, z, x, y) {
  let coordinates;
  try {
    coordinates = [
      parseTileCoordinate(z, 'z'),
      parseTileCoordinate(x, 'x'),
      parseTileCoordinate(y, 'y'),
    ];
  } catch (_) {
    return null;
  }

  const root = path.resolve(tileRoot);
  const candidate = path.resolve(root, coordinates[0], coordinates[1], `${coordinates[2]}.png`);
  if (!candidate.startsWith(`${root}${path.sep}`)) return null;
  return fs.existsSync(candidate) ? candidate : null;
}
