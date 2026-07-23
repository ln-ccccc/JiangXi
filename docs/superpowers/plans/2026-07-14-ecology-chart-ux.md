# Ecology Chart UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove unavailable mine-analysis tabs and make workbook ecology charts visible, with a two-year default sampling control.

**Architecture:** `EcologyDiagnosisPanels.vue` owns chart display state and derives sampled points from the immutable annual series. `MapDashboard.vue` stops fetching the unused matrix endpoint, while `MineDetailModal.vue` exposes only tabs backed by delivered data and styles the shared scroll container.

**Tech Stack:** Vue 3 composition API, ECharts 6, Node test runner, ESLint, Prettier, Vite.

---

### Task 1: Add chart sampling regression tests

**Files:**
- Modify: `miner/src/utils/ecologyProfile.js`
- Test: `miner/test/ecologyProfileViewModel.test.js`

- [ ] **Step 1: Write failing tests for two-year and annual sampling**

```js
assert.deepEqual(selectChartPoints(series, 2).map((point) => point.year), [2013, 2015, 2017, 2019, 2021, 2023, 2025]);
assert.deepEqual(selectChartPoints(series, 1).map((point) => point.year), [2013, 2014, 2015]);
```

- [ ] **Step 2: Run `node --test test/ecologyProfileViewModel.test.js` and verify the missing export fails.**
- [ ] **Step 3: Implement `selectChartPoints(series, interval)` as a pure utility that keeps the first valid year and every interval year thereafter.**
- [ ] **Step 4: Re-run the test and verify it passes.**

### Task 2: Render visible, sampled charts

**Files:**
- Modify: `miner/src/components/EcologyDiagnosisPanels.vue`

- [ ] **Step 1: Add the sampling control to individual ecology/environment charts, defaulting to two years.**
- [ ] **Step 2: Pass sampled points to ECharts and give the runtime chart element `height: '230px'`.**
- [ ] **Step 3: Preserve annual raw values and missing-years display.**

### Task 3: Remove unavailable analysis paths

**Files:**
- Modify: `miner/src/components/MapDashboard.vue`
- Modify: `miner/src/components/MineDetailModal.vue`

- [ ] **Step 1: Remove change-matrix fetching and props from the map detail flow.**
- [ ] **Step 2: Remove the two unsupported tabs and their rendering branches.**
- [ ] **Step 3: Style the two-row tab scrollbar with a transparent track and translucent thumb.**

### Task 4: Verify and deploy

**Files:**
- Modify: `docs/user_manual.md`

- [ ] **Step 1: Update the usage manual to describe the two-year default and removed unsupported pages.**
- [ ] **Step 2: Run `npm run format`, `npm run verify`, then build and replace the standalone Docker container after backing up its runtime data.**
