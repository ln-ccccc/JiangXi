export const INFERENCE_DEVICES = new Set(['cpu']);

export function normalizeInferenceDevice(value) {
  const device = String(value || 'cpu')
    .trim()
    .toLowerCase();
  if (!INFERENCE_DEVICES.has(device)) {
    throw new Error('江西项目仅支持 CPU 推理，device 仅支持 cpu');
  }
  return device;
}
