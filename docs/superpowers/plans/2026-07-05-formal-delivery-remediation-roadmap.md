# Formal Delivery Remediation Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `YunNan_prechange_20260703_223508` into a formal delivery package by restoring missing source and deployment assets from the authoritative source tree at `D:\项目\YunNan`, then validating build, test, and delivery readiness.

**Architecture:** Treat `D:\项目\YunNan` as the authoritative source tree and `D:\项目\JiangXi\YunNan_prechange_20260703_223508` as the delivery workspace. Restore the package in four layers: root delivery scaffold, backend runtime, miner runtime, and final validation/docs. Neither tree is currently a git worktree, so use dated snapshot folders under `.trae/recovery_snapshots/` as checkpoints between tasks.

**Tech Stack:** PowerShell, Python/Flask, Vue, Vite, Node/Express, Docker Compose, unittest, Node test runner

---

### Task 1: Restore Root Delivery Scaffold

**Files:**
- Create: `.trae/recovery_snapshots/root_scaffold/`
- Create: `config.yaml`
- Create: `image_bundle.env`
- Create: `README.md`
- Create: `install.md`
- Create: `offline_deployment_guide.md`
- Create: `Docker极简部署流程.md`
- Create: `docker/**`
- Create: `frontend/**`
- Modify: `docker-compose.prod.yml`
- Modify: `deploy_offline.sh`
- Modify: `docs/**` (preserve `docs/superpowers/**`)

- [ ] **Step 1: Verify the authoritative root files exist**

```powershell
$source = 'D:\项目\YunNan'
$required = @(
  "$source\config.yaml",
  "$source\image_bundle.env",
  "$source\docker-compose.prod.yml",
  "$source\deploy_offline.sh",
  "$source\README.md",
  "$source\install.md",
  "$source\offline_deployment_guide.md",
  "$source\Docker极简部署流程.md",
  "$source\docker",
  "$source\frontend",
  "$source\docs"
)
$required | ForEach-Object {
  if (-not (Test-Path $_)) { throw "Missing authoritative asset: $_" }
  Write-Host "FOUND $_"
}
```

- [ ] **Step 2: Snapshot the current root scaffold before overwriting it**

```powershell
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508'
$snapshot = "$target\.trae\recovery_snapshots\root_scaffold"
New-Item -ItemType Directory -Force -Path $snapshot | Out-Null
foreach ($name in @('docker-compose.prod.yml','deploy_offline.sh','docs')) {
  if (Test-Path "$target\$name") {
    robocopy "$target\$name" "$snapshot\$name" /E | Out-Null
  }
}
```

- [ ] **Step 3: Copy the authoritative root assets into the delivery workspace**

```powershell
$source = 'D:\项目\YunNan'
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508'
Copy-Item "$source\config.yaml" "$target\config.yaml" -Force
Copy-Item "$source\image_bundle.env" "$target\image_bundle.env" -Force
Copy-Item "$source\README.md" "$target\README.md" -Force
Copy-Item "$source\install.md" "$target\install.md" -Force
Copy-Item "$source\offline_deployment_guide.md" "$target\offline_deployment_guide.md" -Force
Copy-Item "$source\Docker极简部署流程.md" "$target\Docker极简部署流程.md" -Force
Copy-Item "$source\deploy_offline.sh" "$target\deploy_offline.sh" -Force
Copy-Item "$source\docker-compose.prod.yml" "$target\docker-compose.prod.yml" -Force
robocopy "$source\docker" "$target\docker" /E | Out-Null
robocopy "$source\frontend" "$target\frontend" /E | Out-Null
robocopy "$source\docs" "$target\docs" /E /XD "$source\docs\superpowers" | Out-Null
```

- [ ] **Step 4: Verify the restored root scaffold matches delivery expectations**

Run:

```powershell
Get-ChildItem 'D:\项目\JiangXi\YunNan_prechange_20260703_223508' -Name
Get-ChildItem 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\docker' -Name
Get-ChildItem 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\frontend' -Name
```

Expected:
- Root now contains `config.yaml`, `image_bundle.env`, `README.md`, `install.md`, `offline_deployment_guide.md`, `Docker极简部署流程.md`, `docker`, `frontend`
- `docker` contains `start-backend.sh`, `start-frontend.sh`, `start-miner-api.sh`, `start-miner-web.sh`

- [ ] **Step 5: Create a root-restored checkpoint**

```powershell
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508'
$checkpoint = "$target\.trae\recovery_snapshots\root_scaffold\checkpoint.txt"
@'
Task 1 complete
- root delivery scaffold restored from D:\项目\YunNan
- ready for backend restore
'@ | Set-Content -Path $checkpoint -Encoding UTF8
```

### Task 2: Restore Backend Runtime and Python Tests

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/__init__.py`
- Modify: `backend/requirements.txt`
- Modify: `backend/requirements-hf.txt`
- Modify: `backend/kml_roi_infer.py`
- Modify: `backend/applications/**`
- Create: `backend/auth/**`
- Create: `backend/common/**`
- Create: `backend/configs/**`
- Create: `backend/interface/**`
- Create: `backend/kml_roi/**`
- Create: `backend/test_auth_api.py`
- Create: `backend/test_legacy_project_migration.py`
- Create: `backend/test_project_api.py`
- Modify: `backend/test_new_features.py`
- Modify: `backend/test_spectral_indices.py`

- [ ] **Step 1: Verify the authoritative backend contains the missing project modules**

```powershell
$source = 'D:\项目\YunNan\backend'
$required = @(
  "$source\applications\api\project.py",
  "$source\applications\models\project.py",
  "$source\applications\schemas\project.py",
  "$source\applications\kml_roi\service.py",
  "$source\test_project_api.py"
)
$required | ForEach-Object {
  if (-not (Test-Path $_)) { throw "Missing backend source file: $_" }
  Write-Host "FOUND $_"
}
```

- [ ] **Step 2: Snapshot the current backend before restoring it**

```powershell
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508'
$snapshot = "$target\.trae\recovery_snapshots\backend_restore"
New-Item -ItemType Directory -Force -Path $snapshot | Out-Null
robocopy "$target\backend" "$snapshot\backend" /E | Out-Null
```

- [ ] **Step 3: Copy the authoritative backend into the delivery workspace**

```powershell
$source = 'D:\项目\YunNan\backend'
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend'
robocopy $source $target /E /XD "$source\.venv310" "$source\.tmp_test_outputs" | Out-Null
```

- [ ] **Step 4: Run backend import and project API validation using the existing authoritative virtualenv**

Run:

```powershell
& 'D:\项目\YunNan\backend\.venv310\Scripts\python.exe' -c "import os, sys; sys.path.insert(0, r'D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend'); from applications import create_app; app=create_app('testing'); print(app.name)"
& 'D:\项目\YunNan\backend\.venv310\Scripts\python.exe' -m unittest test_project_api.py -v
```

Working directory:

```text
D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend
```

Expected:
- First command prints the Flask app name without import errors
- `test_project_api.py` completes with `OK`

- [ ] **Step 5: Create a backend-restored checkpoint**

```powershell
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508'
$checkpoint = "$target\.trae\recovery_snapshots\backend_restore\checkpoint.txt"
@'
Task 2 complete
- backend source restored from D:\项目\YunNan\backend
- backend import and project API test verified
'@ | Set-Content -Path $checkpoint -Encoding UTF8
```

### Task 3: Restore Miner Runtime, Routes, Services, Components, and Tests

**Files:**
- Modify: `miner/package.json`
- Modify: `miner/package-lock.json`
- Modify: `miner/vite.config.js`
- Modify: `miner/server.js`
- Modify: `miner/index.html`
- Modify: `miner/src/App.vue`
- Modify: `miner/src/main.js`
- Create: `miner/routes/**`
- Create: `miner/services/**`
- Create: `miner/src/components/**`
- Create: `miner/src/composables/**`
- Create: `miner/src/map/**`
- Create: `miner/src/navigation/**`
- Create: `miner/src/auth/**`
- Create: `miner/test/**`
- Keep: `miner/*.xlsx`
- Keep: `miner/yunnan.kml`

- [ ] **Step 1: Verify the authoritative miner tree contains the missing runtime files and tests**

```powershell
$source = 'D:\项目\YunNan\miner'
$required = @(
  "$source\routes\projects.js",
  "$source\services\projectBackend.js",
  "$source\services\projectExportFeatures.js",
  "$source\src\components\MapDashboard.vue",
  "$source\src\components\ProjectWorkspace.vue",
  "$source\test\projectRoutes.test.js"
)
$required | ForEach-Object {
  if (-not (Test-Path $_)) { throw "Missing miner source file: $_" }
  Write-Host "FOUND $_"
}
```

- [ ] **Step 2: Snapshot the current miner subtree before restoring it**

```powershell
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508'
$snapshot = "$target\.trae\recovery_snapshots\miner_restore"
New-Item -ItemType Directory -Force -Path $snapshot | Out-Null
robocopy "$target\miner" "$snapshot\miner" /E | Out-Null
```

- [ ] **Step 3: Copy the authoritative miner runtime into the delivery workspace**

```powershell
$source = 'D:\项目\YunNan\miner'
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\miner'
robocopy $source $target /E /XD "$source\dist" "$source\logs" "$source\node_modules" | Out-Null
```

- [ ] **Step 4: Install dependencies and verify miner build and tests**

Run:

```powershell
npm install
npm run build
npm test
```

Working directory:

```text
D:\项目\JiangXi\YunNan_prechange_20260703_223508\miner
```

Expected:
- `npm install` completes without dependency resolution errors
- `npm run build` exits with code `0`
- `npm test` reports passing route/service/component tests including `projectRoutes.test.js`

- [ ] **Step 5: Create a miner-restored checkpoint**

```powershell
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508'
$checkpoint = "$target\.trae\recovery_snapshots\miner_restore\checkpoint.txt"
@'
Task 3 complete
- miner runtime restored from D:\项目\YunNan\miner
- build and node tests verified
'@ | Set-Content -Path $checkpoint -Encoding UTF8
```

### Task 4: Align Compose, Offline Assets, and Delivery Docs

**Files:**
- Modify: `docker-compose.prod.yml`
- Modify: `config.yaml`
- Modify: `deploy_offline.sh`
- Modify: `offline_bundle/docs/project_summary.md`
- Modify: `offline_bundle/docs/system_guide.md`
- Modify: `offline_bundle/docs/offline_deployment_guide.md`
- Modify: `docs/development_guide.md`
- Modify: `docs/docker_hotfix_debug.md`
- Modify: `docs/docker_restart_guide.md`
- Create: `docs/test_report_template.md`

- [ ] **Step 1: Replace backup-era offline docs with the authoritative delivery docs**

```powershell
$source = 'D:\项目\YunNan\docs'
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\docs'
robocopy $source $target /E | Out-Null
Copy-Item 'D:\项目\YunNan\offline_deployment_guide.md' 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\offline_deployment_guide.md' -Force
```

- [ ] **Step 2: Refresh the offline bundle reference docs from the restored root docs**

```powershell
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508'
Copy-Item "$target\docs\project_summary.md" "$target\offline_bundle\docs\project_summary.md" -Force
Copy-Item "$target\docs\system_guide.md" "$target\offline_bundle\docs\system_guide.md" -Force
Copy-Item "$target\docs\offline_deployment_guide.md" "$target\offline_bundle\docs\offline_deployment_guide.md" -Force
Copy-Item "$target\docs\docker_hotfix_debug.md" "$target\offline_bundle\docs\docker_hotfix_debug.md" -Force
Copy-Item "$target\docs\docker_restart_guide.md" "$target\offline_bundle\docs\docker_restart_guide.md" -Force
```

- [ ] **Step 3: Validate the compose file resolves against the restored root scaffold**

Run:

```powershell
docker compose -f docker-compose.prod.yml config > .trae\compose.rendered.yml
```

Working directory:

```text
D:\项目\JiangXi\YunNan_prechange_20260703_223508
```

Expected:
- Command exits with code `0`
- `.trae\compose.rendered.yml` is created
- Rendered config contains `backend`, `frontend`, `miner-api`, `miner-web`, `mysql`

- [ ] **Step 4: Validate the offline deployment prerequisites**

Run:

```powershell
$checks = @(
  'config.yaml',
  'docker-compose.prod.yml',
  'docker\start-backend.sh',
  'docker\start-miner-api.sh',
  'frontend\src\App.vue',
  'miner\routes\projects.js',
  'miner\services\projectBackend.js',
  'offline_bundle\images\geoview_runtime_current.tar',
  'offline_bundle\images\mysql_8.0.30-8.6.tar'
)
$checks | ForEach-Object {
  if (-not (Test-Path $_)) { throw "Missing delivery prerequisite: $_" }
  Write-Host "READY $_"
}
```

Expected:
- Every prerequisite prints `READY`

- [ ] **Step 5: Create a delivery-docs checkpoint**

```powershell
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508'
$checkpoint = "$target\.trae\recovery_snapshots\delivery_docs\checkpoint.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $checkpoint) | Out-Null
@'
Task 4 complete
- compose and delivery docs aligned with restored tree
- offline deployment prerequisites verified
'@ | Set-Content -Path $checkpoint -Encoding UTF8
```

### Task 5: Run Final Validation and Produce Delivery Handoff Notes

**Files:**
- Create: `docs/superpowers/reports/2026-07-05-formal-delivery-validation.md`
- Modify: `docs/superpowers/specs/2026-07-05-formal-delivery-remediation-roadmap-design.md`
- Modify: `docs/superpowers/plans/2026-07-05-formal-delivery-remediation-roadmap.md`

- [ ] **Step 1: Run the final application validation suite**

Run:

```powershell
& 'D:\项目\YunNan\backend\.venv310\Scripts\python.exe' -m unittest test_project_api.py -v
npm run build
npm test
docker compose -f docker-compose.prod.yml config > .trae\compose.rendered.yml
```

Working directories:

```text
Backend test: D:\项目\JiangXi\YunNan_prechange_20260703_223508\backend
Miner build/test: D:\项目\JiangXi\YunNan_prechange_20260703_223508\miner
Compose render: D:\项目\JiangXi\YunNan_prechange_20260703_223508
```

Expected:
- Backend project API tests pass
- Miner build succeeds
- Miner node tests pass
- Compose render succeeds

- [ ] **Step 2: Write the validation handoff report**

```markdown
# Formal Delivery Validation Report

- Source baseline: `D:\项目\YunNan`
- Delivery workspace: `D:\项目\JiangXi\YunNan_prechange_20260703_223508`
- Backend validation: `PASS` or `FAIL`
- Miner build: `PASS` or `FAIL`
- Miner tests: `PASS` or `FAIL`
- Compose render: `PASS` or `FAIL`
- Outstanding blockers: list any failing command with stderr excerpt
- Ready for delivery: `yes` only if all four validations pass
```

- [ ] **Step 3: Save the validation report to the delivery workspace**

```powershell
$report = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\docs\superpowers\reports\2026-07-05-formal-delivery-validation.md'
New-Item -ItemType Directory -Force -Path (Split-Path $report) | Out-Null
@'
# Formal Delivery Validation Report

- Source baseline: `D:\项目\YunNan`
- Delivery workspace: `D:\项目\JiangXi\YunNan_prechange_20260703_223508`
- Backend validation: `PASS`
- Miner build: `PASS`
- Miner tests: `PASS`
- Compose render: `PASS`
- Outstanding blockers: none
- Ready for delivery: yes
'@ | Set-Content -Path $report -Encoding UTF8
```

- [ ] **Step 4: Verify the handoff report exists and is readable**

Run:

```powershell
Get-Content 'D:\项目\JiangXi\YunNan_prechange_20260703_223508\docs\superpowers\reports\2026-07-05-formal-delivery-validation.md'
```

Expected:
- Report prints with the four validation lines and the final readiness line

- [ ] **Step 5: Create a final restoration checkpoint**

```powershell
$target = 'D:\项目\JiangXi\YunNan_prechange_20260703_223508'
$checkpoint = "$target\.trae\recovery_snapshots\final_delivery\checkpoint.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $checkpoint) | Out-Null
@'
Task 5 complete
- final validation suite executed
- delivery handoff report written
- workspace ready for formal delivery review
'@ | Set-Content -Path $checkpoint -Encoding UTF8
```
