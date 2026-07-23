import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const helperUrl = new URL("../src/utils/platformNavigation.js", import.meta.url);

async function loadHelper() {
  const source = await readFile(helperUrl, "utf8");
  const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
  return import(moduleUrl);
}

test("explicit HTTP or HTTPS root points exactly to the Miner map", async () => {
  const { buildMinerMapUrl } = await loadHelper();

  assert.equal(
    buildMinerMapUrl(
      { protocol: "https:", hostname: "jiangxi.example" },
      "http://127.0.0.1:4173/",
    ),
    "http://127.0.0.1:4173/#/map",
  );
  assert.equal(
    buildMinerMapUrl(null, "https://miner.example"),
    "https://miner.example/#/map",
  );
});

test("missing Miner root returns an empty URL without guessing a port", async () => {
  const { buildMinerMapUrl } = await loadHelper();

  assert.equal(
    buildMinerMapUrl(
      { protocol: "http:", hostname: "127.0.0.1" },
      "",
    ),
    "",
  );
});

test("invalid or non-root Miner URLs are rejected", async () => {
  const { buildMinerMapUrl } = await loadHelper();

  for (const configuredRoot of [
    "miner.example",
    "/miner",
    "ftp://miner.example/",
    "https://miner.example/workbench",
    "https://miner.example/?tenant=jiangxi",
    "https://miner.example/#/map",
  ]) {
    assert.equal(buildMinerMapUrl({}, configuredRoot), "", configuredRoot);
  }
});

test("navigation helper contains no legacy 4000 fallback", async () => {
  const source = await readFile(helperUrl, "utf8");

  assert.doesNotMatch(source, /\b4000\b/);
});
