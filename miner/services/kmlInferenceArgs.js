import { normalizeInferenceDevice } from './inferenceDevicePolicy.js';

export function buildKmlRoiArgs({
  scriptPath,
  oldTifPath,
  newTifPath,
  kmlPath,
  outputRoot,
  manifestPath,
  limit = 0,
  year = '',
  oldYear = '',
  newYear = '',
  device = process.env.JIANGXI_INFERENCE_DEVICE || 'cpu',
}) {
  const effectiveDevice = normalizeInferenceDevice(device);
  const args = [
    scriptPath,
    '--old_tif',
    oldTifPath,
    '--new_tif',
    newTifPath,
    '--kml',
    kmlPath,
    '--output_root',
    outputRoot,
    '--device',
    effectiveDevice,
  ];
  if (manifestPath) args.push('--manifest', manifestPath);

  const limitNum = Number(limit || 0);
  if (Number.isFinite(limitNum) && limitNum > 0) {
    args.push('--limit', String(Math.floor(limitNum)));
  }

  const yearText = String(year || '').trim();
  if (yearText) {
    args.push('--year', yearText);
    return args;
  }

  const oldYearText = String(oldYear || '').trim();
  const newYearText = String(newYear || '').trim();
  if (oldYearText) args.push('--old_year', oldYearText);
  if (newYearText) args.push('--new_year', newYearText);
  return args;
}
