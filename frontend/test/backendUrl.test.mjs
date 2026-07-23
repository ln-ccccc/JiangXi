import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const globalVueUrl = new URL("../src/global.vue", import.meta.url);
const helperUrl = new URL("../src/utils/backendUrl.mjs", import.meta.url);

test("global.vue uses VUE_APP_BACKEND_URL through the backend URL helper", async () => {
  const source = await readFile(globalVueUrl, "utf8");
  const helperSource = await readFile(helperUrl, "utf8");

  assert.match(source, /buildBackendUrl\(process\.env\.VUE_APP_BACKEND_URL/);
  assert.doesNotMatch(source, /VUE_APP_BACKEND_(?:IP|PORT)/);
  assert.doesNotMatch(`${source}\n${helperSource}`, /\b(?:5008|3000|4000)\b/);
});

test("configured complete backend URL takes priority", async () => {
  const { buildBackendUrl } = await import(helperUrl.href);

  assert.equal(
    buildBackendUrl("http://127.0.0.1:5178/", {
      protocol: "https:",
      hostname: "jiangxi.example",
    }),
    "http://127.0.0.1:5178/",
  );
});

test("missing backend URL falls back to current hostname on Jiangxi port", async () => {
  const { buildBackendUrl } = await import(helperUrl.href);

  assert.equal(
    buildBackendUrl("", { protocol: "https:", hostname: "jiangxi.example" }),
    "https://jiangxi.example:5178/",
  );
});

test("partial backend URL uses the Jiangxi development fallback", async () => {
  const { buildBackendUrl } = await import(helperUrl.href);

  assert.equal(
    buildBackendUrl("/api", { protocol: "http:", hostname: "127.0.0.1" }),
    "http://127.0.0.1:5178/",
  );
});
