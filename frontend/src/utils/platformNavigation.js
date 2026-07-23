function normalizeRoot(configuredRoot, locationLike, port) {
  const configured = String(configuredRoot || "").trim();
  if (configured) {
    return `${configured.split("#")[0].replace(/\/+$/, "")}/`;
  }

  const protocol = locationLike?.protocol || "http:";
  const hostname = locationLike?.hostname || "localhost";
  return `${protocol}//${hostname}:${port}/`;
}

export function buildMinerMapUrl(locationLike, configuredRoot = "") {
  return `${normalizeRoot(configuredRoot, locationLike, 4000)}#/map`;
}
