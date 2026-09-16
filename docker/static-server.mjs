import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(process.argv[2] || '.');
const port = Number(process.argv[3] || 3000);
const fallback = process.argv[4] || '/index.html';
const proxies = [
  { prefix: '/api/', target: process.env.PROXY_API_TARGET || '' },
  { prefix: '/tiles/', target: process.env.PROXY_TILES_TARGET || process.env.PROXY_API_TARGET || '' },
  { prefix: '/change-matrix-outputs/', target: process.env.PROXY_CHANGE_MATRIX_TARGET || process.env.PROXY_API_TARGET || '' },
].filter((item) => item.target);

const types = new Map([
  ['.css', 'text/css; charset=utf-8'],
  ['.html', 'text/html; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.map', 'application/json; charset=utf-8'],
  ['.png', 'image/png'],
  ['.jpg', 'image/jpeg'],
  ['.jpeg', 'image/jpeg'],
  ['.svg', 'image/svg+xml'],
  ['.ico', 'image/x-icon'],
]);

function sendFile(response, filePath) {
  fs.readFile(filePath, (error, data) => {
    if (error) {
      response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
      response.end('Not found');
      return;
    }
    response.writeHead(200, {
      'content-type': types.get(path.extname(filePath).toLowerCase()) || 'application/octet-stream',
    });
    response.end(data);
  });
}

function proxyRequest(request, response, proxy) {
  // 上游配置损坏（非 URL）时按上游不可用收口为 502，异常不得逃逸杀死主进程
  let upstream;
  try {
    upstream = new URL(proxy.target);
  } catch (error) {
    response.writeHead(502, { 'content-type': 'application/json; charset=utf-8' });
    response.end(JSON.stringify({ error: 'Proxy target is misconfigured' }));
    return;
  }
  // request.url 携带绝对 URL（http://169.254.169.254/...）或协议相对 URL
  // （//evil.example/...）时会整体覆盖 base，把本服务变成任意主机中继（SSRF）。
  // 重组后的目标必须与配置的上游同源，否则固定 400、不回显请求内容
  let target;
  try {
    target = new URL(request.url, upstream);
  } catch (error) {
    response.writeHead(400, { 'content-type': 'text/plain; charset=utf-8' });
    response.end('Bad Request');
    return;
  }
  if (target.origin !== upstream.origin) {
    response.writeHead(400, { 'content-type': 'text/plain; charset=utf-8' });
    response.end('Bad Request');
    return;
  }
  const proxied = http.request(target, {
    method: request.method,
    headers: { ...request.headers, host: target.host },
  }, (proxyResponse) => {
    response.writeHead(proxyResponse.statusCode || 502, proxyResponse.headers);
    proxyResponse.pipe(response);
  });
  proxied.on('error', (error) => {
    response.writeHead(502, { 'content-type': 'application/json; charset=utf-8' });
    response.end(JSON.stringify({ error: `Proxy failed: ${error.message}` }));
  });
  request.pipe(proxied);
}

http.createServer((request, response) => {
  // 请求目标收口（P1-4 SSRF）：origin-form（RFC 9112 §3.2）必须以单个 "/" 开头。
  // 绝对 URL（http://169.254.169.254/...）与协议相对 URL（//evil.example/...）
  // 自带 authority：交给代理分支会被 new URL(request.url, target) 整体覆盖 base
  // 变成任意主机中继，落到静态分支则被回退页静默吞成 200 —— 一律固定 400
  if (!request.url.startsWith('/') || request.url.startsWith('//')) {
    response.writeHead(400, { 'content-type': 'text/plain; charset=utf-8' });
    response.end('Bad Request');
    return;
  }

  const proxy = proxies.find((item) => request.url.startsWith(item.prefix));
  if (proxy) {
    proxyRequest(request, response, proxy);
    return;
  }

  // 畸形 URL（如 /%E0%A4%A）会让 new URL/decodeURIComponent 抛 URIError，
  // 直接杀死 4173/4174 的主进程；这里必须就地兜底为 400，保住进程
  let requestPath;
  try {
    requestPath = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
  } catch (error) {
    response.writeHead(400, { 'content-type': 'text/plain; charset=utf-8' });
    response.end('Bad Request');
    return;
  }
  const safePath = path.normalize(requestPath).replace(/^(\.\.[/\\])+/, '');
  let filePath = path.join(root, safePath);
  if (fs.existsSync(filePath) && fs.statSync(filePath).isDirectory()) {
    filePath = path.join(filePath, 'index.html');
  }
  if (!fs.existsSync(filePath)) {
    filePath = path.join(root, fallback);
  }
  sendFile(response, filePath);
}).listen(port, '0.0.0.0', () => {
  console.log(`[static-server] ${root} -> http://0.0.0.0:${port}`);
});
