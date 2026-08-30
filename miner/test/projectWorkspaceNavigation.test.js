import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const read = (relativePath) => readFile(new URL(relativePath, import.meta.url), 'utf8');

test('Miner exposes a browser entry point for the project workspace', async () => {
  const appSource = await read('../src/App.vue');
  const dashboardSource = await read('../src/components/MapDashboard.vue');
  const headerSource = await read('../src/components/TheHeader.vue');

  assert.match(
    appSource,
    /import\s+ProjectWorkspace\s+from\s+['"]\.\/components\/ProjectWorkspace\.vue['"]/u
  );
  assert.match(appSource, /currentView\s*===\s*['"]projects['"]/u);
  assert.match(appSource, /@open-workspace=['"]handleOpenWorkspace['"]/u);
  assert.match(dashboardSource, /@open-workspace=['"]emit\(['"]open-workspace['"]\)['"]/u);
  assert.match(headerSource, /项目工作台/u);
  assert.match(headerSource, /\$emit\(['"]open-workspace['"]\)/u);
});
