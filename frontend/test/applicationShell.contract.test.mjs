import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const homeUrl = new URL("../src/views/Home.vue", import.meta.url);
const asideUrl = new URL("../src/components/AsideVue.vue", import.meta.url);

test("Home removes only the closed mobile drawer from interaction and accessibility", async () => {
  const source = await readFile(homeUrl, "utf8");

  assert.match(source, /:inert="isMobileDrawerClosed"/);
  assert.match(
    source,
    /:aria-hidden="isMobileDrawerClosed \? 'true' : undefined"/,
  );
  assert.match(
    source,
    /isMobileDrawerClosed\(\)\s*{\s*return this\.isMobileViewport && this\.isCollapse;\s*}/s,
  );
  assert.match(source, /this\.isMobileViewport = viewportWidth <= 768;/);
});

test("Home restores focus to the menu button after closing the mobile drawer", async () => {
  const source = await readFile(homeUrl, "utf8");

  assert.match(source, /ref="sidebarToggle"/);
  assert.match(
    source,
    /focusMenuButton\(\)\s*{[\s\S]*this\.\$refs\.sidebarToggle\?\.focus\(\);[\s\S]*}/,
  );
  assert.match(
    source,
    /const closesMobileDrawer = this\.isMobileViewport && !this\.isCollapse;/,
  );
  assert.match(source, /if \(closesMobileDrawer\) this\.focusMenuButton\(\);/);
  assert.match(
    source,
    /closeSidebarOnMobile\(\)\s*{[\s\S]*this\.isCollapse = true;[\s\S]*this\.focusMenuButton\(\);[\s\S]*}/,
  );
});

test("Aside atlas mark preserves routing and always emits the drawer close event", async () => {
  const source = await readFile(asideUrl, "utf8");

  assert.match(
    source,
    /class="atlas-mark atlas-title"[\s\S]*?@click="handleAtlasMarkClick"/,
  );
  assert.match(
    source,
    /handleAtlasMarkClick\(\)\s*{\s*goSegmentation\.call\(this\);\s*this\.\$emit\("navigate"\);\s*}/,
  );
  assert.match(source, /methods:\s*{\s*goSegmentation,/);
});
