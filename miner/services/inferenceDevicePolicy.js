export const INFERENCE_DEVICES = new Set(['auto', 'cpu', 'cuda:0']);

export function normalizeInferenceDevice(value) {
  const device = String(value || 'auto').trim().toLowerCase();
  if (!INFERENCE_DEVICES.has(device)) {
    throw new Error('device 仅支持 auto、cpu 或 cuda:0');
  }
  return device;
}
