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
