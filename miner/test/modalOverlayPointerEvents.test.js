import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const modalComponents = [
  '../src/components/MineDetailModal.vue',
  '../src/components/InferenceModal.vue',
  '../src/components/TrendReportModal.vue',
];

for (const component of modalComponents) {
  test(`modal leave transition must not intercept clicks: ${component}`, async () => {
    const source = await readFile(new URL(component, import.meta.url), 'utf8');
    assert.match(
      source,
      /\.modal-overlay\.fade-leave-active\s*\{[^}]*pointer-events:\s*none\s*;[^}]*\}/,
      'fading modal overlay must set pointer-events: none while leaving'
    );
  });
}
