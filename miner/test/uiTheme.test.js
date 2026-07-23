import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const baseCss = await readFile(new URL('../src/assets/base.css', import.meta.url), 'utf8');

test('defines the ecology atlas theme tokens and reduced-motion rule', () => {
  assert.match(baseCss, /--jx-bg:\s*#071923\s*;/);
  assert.match(baseCss, /--jx-primary:\s*#9ce7bd\s*;/);
  assert.match(baseCss, /--jx-warning:\s*#d68058\s*;/);
  assert.match(baseCss, /--jx-sand:\s*#e6c98c\s*;/);

  const reducedMotionBlock = baseCss.match(
    /@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{[\s\S]*?transition-duration:\s*0\.01ms\s*!important;/
  );
  assert.ok(reducedMotionBlock, 'reduced-motion block should disable transitions');

  const focusVisibleRule = baseCss.match(/:focus-visible\s*\{([\s\S]*?)\}/);
  assert.ok(focusVisibleRule, 'focus-visible rule should exist');
  assert.match(focusVisibleRule[1], /outline:\s*2px\s+solid\s+var\(--jx-primary\)/);

  assert.match(baseCss, /--border-color:\s*var\(--jx-border\)\s*;/);
  assert.match(baseCss, /--color-background:\s*var\(--jx-bg\)\s*;/);
  assert.match(baseCss, /--color-text:\s*var\(--jx-text\)\s*;/);
});
