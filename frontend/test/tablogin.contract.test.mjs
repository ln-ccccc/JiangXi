import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const tabloginUrl = new URL("../src/components/Tablogin.vue", import.meta.url);

test("Tablogin wires the configured Miner root to an accessible disabled state", async () => {
  const source = await readFile(tabloginUrl, "utf8");

  assert.match(source, /process\.env\.VUE_APP_MINER_URL/);
  assert.match(source, /:disabled="!minerUrl"/);
  assert.match(source, /矿山地图地址未配置/);
  assert.match(source, /:title="minerButtonLabel"/);
  assert.match(source, /:aria-label="minerButtonLabel"/);
});

test("Tablogin refuses to navigate when Miner configuration is missing", async () => {
  const source = await readFile(tabloginUrl, "utf8");

  assert.match(
    source,
    /goToMiner\(\)\s*{\s*if\s*\(!this\.minerUrl\)\s*return;\s*window\.location\.assign\(this\.minerUrl\);\s*}/s,
  );
});

test("Tablogin preserves legacy session and logout integration", async () => {
  const source = await readFile(tabloginUrl, "utf8");

  assert.match(source, /import\s*{\s*legacyLogout,\s*legacySession\s*}/);
  assert.match(source, /await legacySession\(\)/);
  assert.match(source, /await legacyLogout\(\)/);
});
