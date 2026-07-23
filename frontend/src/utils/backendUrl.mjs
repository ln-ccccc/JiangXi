const JIANGXI_BACKEND_PORT = "5178";

function configuredHttpUrl(value) {
  try {
    const url = new URL(String(value || "").trim());
    if (!["http:", "https:"].includes(url.protocol) || !url.hostname) {
      return null;
    }
    return url.href.endsWith("/") ? url.href : `${url.href}/`;
  } catch {
    return null;
  }
}

export function buildBackendUrl(configuredUrl, currentLocation) {
  const completeUrl = configuredHttpUrl(configuredUrl);
  if (completeUrl) {
    return completeUrl;
  }

  return `${currentLocation.protocol}//${currentLocation.hostname}:${JIANGXI_BACKEND_PORT}/`;
}
