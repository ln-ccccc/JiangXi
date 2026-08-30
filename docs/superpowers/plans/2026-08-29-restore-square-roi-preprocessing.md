# Restore Square ROI Preprocessing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the legacy fixed `512×512` PNG input used by the MMSeg model for every cropped Jiangxi ROI, without changing model weights, GPU runtime, TBBH mapping, or the white ROI boundary overlay.

**Architecture:** `tif_to_png()` resumes using `UI_SEGMENT_SIZE` as its default. `prepare_tiles()` uses that default instead of overriding it with `None`. The explicit `resize_to=None` API remains available for callers that intentionally need a native-size preview.

**Tech Stack:** Python, rasterio, OpenCV, unittest, MMSeg GPU Worker.

---

### Task 1: Lock the legacy input contract with tests

**Files:**
- Modify: `backend/test_kml_roi_raster_ops.py`

- [ ] **Step 1: Write failing expectations**

Change the default-conversion test to expect a `512×512×3` BGR image, add a native-size test that calls `resize_to=None`, and require `prepare_tiles()` to call `tif_to_png()` without an override.

- [ ] **Step 2: Verify RED**

Run:

```powershell
docker run --rm --network none -v "${PWD}:/source:ro" --entrypoint /bin/bash geoview-jiangxi:jiangxi-gpu -lc "cd /source/backend && PYTHONPATH=/source/backend /opt/conda/envs/MMSeg310/bin/python -m unittest test_kml_roi_raster_ops -v"
```

Expected: the two restored legacy-contract tests fail because production code still keeps the source size and passes `resize_to=None`.

### Task 2: Restore the old preprocessing behavior

**Files:**
- Modify: `backend/applications/kml_roi/raster_ops.py`
- Modify: `backend/applications/kml_roi/tiles.py`
- Test: `backend/test_kml_roi_raster_ops.py`

- [ ] **Step 1: Restore the default size**

Set the default `resize_to` value in `tif_to_png()` back to `UI_SEGMENT_SIZE`; retain explicit `None` behavior.

- [ ] **Step 2: Restore pipeline use of the default**

Remove the `resize_to=None` override from `prepare_tiles()`.

- [ ] **Step 3: Verify GREEN**

Run the Task 1 unittest command again. Expected: all raster-ops tests pass, including the white boundary regression.

### Task 3: Verify real GPU behavior without changing persisted data

**Files:**
- No repository files changed.

- [ ] **Step 1: Build the GPU image from `F:\images\jiangxi` cache-backed Docker storage**

Build an immutable validation tag using `docker/standalone/Dockerfile.jiangxi`.

- [ ] **Step 2: Run the existing map-fid 22 sample through the rebuilt GPU Worker**

Use `D:\项目\jiangxi_data\影像文件\001_201108.tif`; crop its authoritative `map_fid=22` ROI and verify its temporary inference input is `512×512`.

- [ ] **Step 3: Check health and cleanup**

Confirm the validation container reports a ready GPU Worker and remove only its known temporary test files. Do not modify the formal runtime database, persistent volume, or model assets.
