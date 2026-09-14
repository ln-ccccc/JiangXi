// 路由是 hash 模式（createWebHashHistory）：真实页面路径在 window.location.hash
// （如 #/segmentation），pathname+search 只是承载 SPA 的外壳。会话过期跳转必须
// 落在 hash 路由 /#/login 上，否则 vue-router 看不到 query，reason 与 redirect
// 都没有消费者（历史缺陷：redirect 恒为 "/"）。
function currentHashRoute() {
  if (typeof window === "undefined") return "";
  const hash = window.location.hash || "";
  return hash.startsWith("#") ? hash.slice(1) : hash;
}

export function redirectToLegacyLogin(reason = "") {
  if (typeof window === "undefined") return;

  const hashRoute = currentHashRoute();

  const params = new URLSearchParams();
  if (hashRoute && !hashRoute.startsWith("/login")) {
    params.set("redirect", hashRoute);
  }
  if (reason) {
    params.set("reason", reason);
  }

  const target = params.toString() ? `/#/login?${params.toString()}` : "/#/login";
  if (currentHashRoute() !== target.slice(target.indexOf("#"))) {
    window.location.assign(target);
  }
}
