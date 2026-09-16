import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const testDirectory = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(
  path.join(testDirectory, "..", "src", "utils", "download.js"),
  "utf8",
);

test("跨端口下载必须携带江西会话凭据", () => {
  assert.match(source, /fetch\(src,\s*\{\s*credentials:\s*["']include["']/s);
  assert.match(source, /xmlhttp\.withCredentials\s*=\s*true/);
});

test("fetch 下载链失败时必须给出可见错误而不是静默 unhandled rejection", () => {
  // 此前整条 fetch 链无 catch：断网/非 2xx 时用户点击下载毫无反馈
  const chainStart = source.indexOf("fetch(src");
  const chainEnd = source.indexOf("function getImgArrayBuffer");
  assert.ok(chainStart >= 0 && chainEnd > chainStart, "fetch 下载链必须存在");
  const fetchChain = source.slice(chainStart, chainEnd);
  assert.match(fetchChain, /\.catch\(\(err\) => \{/);
  assert.match(fetchChain, /\$message\?\.\s*error\?\.\(/);
  assert.match(fetchChain, /下载失败/);
});
