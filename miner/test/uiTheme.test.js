import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const baseCss = await readFile(new URL('../src/assets/base.css', import.meta.url), 'utf8');

test('defines the ecology atlas theme tokens and reduced-motion rule', () => {
  // 2026-09-10「山地制图台」重设计：深潭基底 + 植被薄荷主色 + 矿砂警示
  assert.match(baseCss, /--jx-bg:\s*#06141c\s*;/);
  assert.match(baseCss, /--jx-primary:\s*#7fd8a6\s*;/);
  assert.match(baseCss, /--jx-warning:\s*#e2c285\s*;/);
  assert.match(baseCss, /--jx-sand:\s*#e2c285\s*;/);
  assert.match(baseCss, /--jx-surface-glass:\s*rgba\(7,\s*24,\s*33,\s*0\.72\)\s*;/);
  assert.match(baseCss, /--jx-blur:\s*saturate\(150%\)\s*blur\(18px\)\s*;/);

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
