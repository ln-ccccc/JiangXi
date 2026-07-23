const geoviewBackendUrl = (process.env.GEOVIEW_BACKEND_URL || 'http://localhost:5008').replace(/\/$/, '');

export async function fetchSpectralLive(fidRaw) {
  const fid = encodeURIComponent(fidRaw || '');
  const upstream = await fetch(`${geoviewBackendUrl}/api/analysis/spectral_live/${fid}`);
  const text = await upstream.text();
  return {
    status: upstream.status,
    contentType: upstream.headers.get('content-type') || 'application/json',
    body: text,
  };
}

export async function fetchGpuCapability(cookie = '') {
  const upstream = await fetch(`${geoviewBackendUrl}/api/analysis/gpu_capability`, {
    headers: cookie ? { cookie } : {},
  });
  const text = await upstream.text();
  return {
    status: upstream.status,
    contentType: upstream.headers.get('content-type') || 'application/json',
    body: text,
  };
}
