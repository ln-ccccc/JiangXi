export const INFERENCE_DEVICES = new Set(['cpu', 'cuda:0']);

export function normalizeInferenceDevice(value) {
  const configured =
    value == null || String(value).trim() === ''
      ? process.env.JIANGXI_INFERENCE_DEVICE || 'cpu'
      : value;
  let device = String(configured).trim().toLowerCase();
  if (device === 'cuda') device = 'cuda:0';
  if (!INFERENCE_DEVICES.has(device)) {
    throw new Error('江西项目 device 仅支持 cpu、cuda:0');
  }
  return device;
}
