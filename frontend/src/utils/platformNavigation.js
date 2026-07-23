function configuredHttpRoot(value) {
  const configured = String(value || "").trim();
  if (!configured) return "";

  try {
    const url = new URL(configured);
    const isHttp = url.protocol === "http:" || url.protocol === "https:";
    const isRoot = url.pathname === "/" && !url.search && !url.hash;
    if (!isHttp || !url.hostname || !isRoot || url.username || url.password) {
      return "";
    }
    return `${url.origin}/`;
  } catch (_) {
    return "";
  }
}

export function buildMinerMapUrl(_locationLike, configuredRoot = "") {
  const root = configuredHttpRoot(configuredRoot);
  return root ? `${root}#/map` : "";
}
