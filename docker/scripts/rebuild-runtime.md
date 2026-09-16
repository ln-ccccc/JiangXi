# 江西运行时底座从源码重建手册

2026-09-15/16 首次执行并验收。目的：让江西 CPU 运行时底座可以**只凭本仓库 + 公网源**
独立重建，摆脱云南血统（旧 `jiangxi-runtime:current` / `jiangxi-runtime:squashed-20260915`
的 conda/node 环境内容源自七月隔离前的云南构建，见 AGENTS.md §4.1）。

## 产物

| 产物 | 定义文件 | 说明 |
| --- | --- | --- |
| `jiangxi-runtime:rebuilt-20260915` | `docker/Dockerfile.jiangxi-runtime` | 江西自有 CPU 运行时底座（ubuntu:20.04 + Miniconda + MMSeg310 + /opt/node20 + miner Linux 原生 npm 依赖） |
| `jiangxi-gpu-compat:shim` | `docker/Dockerfile.jiangxi-gpu-compat-shim` | CPU 构建专用占位镜像，仅提供 `Dockerfile.jiangxi` 无条件 COPY 的 `/opt/venv/.../mmcv` 两条路径 |
| `geoview-jiangxi:cpu-20260915-rebuilt` | `docker/standalone/Dockerfile.jiangxi`（原样，换 ARG） | 以 rebuilt 底座构建的 CPU 验收镜像 |

环境可复现清单入库于 `docker/runtime-env/`：

- `MMSeg310.environment.yml`：conda 依赖（含 channels 与精确 build 串），清洗自 `jiangxi-runtime:squashed-20260915` 的 `conda env export`；
- `MMSeg310.requirements.txt`：75 条 pip 钉子（torch==2.2.2+cpu、mmcv==2.2.0、mmdet==3.3.0、mmsegmentation==1.1.2 等）；
- `MMSeg310.env-export.raw.yml` / `MMSeg310.conda-list.raw.txt` / `MMSeg310.pip-freeze.raw.txt`：2026-09-15 从 squashed 底座导出的原始件（溯源用）。

## 构建命令

前置：Docker Desktop 数据盘在 F 盘（AGENTS.md §4）；记录 C/F 可用空间；网络可达。
全部在仓库根目录执行（Git Bash 下 docker 参数带路径的一律加 `MSYS_NO_PATHCONV=1`）。

```bash
# 1) GPU 兼容 shim（秒级）
MSYS_NO_PATHCONV=1 docker build --progress=plain \
  -f docker/Dockerfile.jiangxi-gpu-compat-shim -t jiangxi-gpu-compat:shim .

# 2) 底座（预计 30-90 分钟；conda 解算/下载与 pip 大轮子下载为主）
MSYS_NO_PATHCONV=1 docker build --progress=plain \
  -f docker/Dockerfile.jiangxi-runtime -t jiangxi-runtime:rebuilt-20260915 .

# 3) CPU 交付镜像（Dockerfile.jiangxi 原样，三个 ARG 全指向 rebuilt 底座 + shim；
#    构建上下文需包含以下 git 忽略的本地资产，从主树拷入 worktree：
#    backend/model/jiangxi（3.5G 模型）、miner/.npm-cache、frontend/.npm-cache、
#    frontend/package-lock.json（npm ci 必需、未跟踪）、backend/static（空 upload 目录）、
#    miner/public/tiles（532M/32,214 张离线瓦片，.dockerignore 未排除、随镜像烘焙））
MSYS_NO_PATHCONV=1 docker build --progress=plain \
  -f docker/standalone/Dockerfile.jiangxi \
  --build-arg JIANGXI_BASE_IMAGE=jiangxi-runtime:rebuilt-20260915 \
  --build-arg JIANGXI_RUNTIME_COMPAT_IMAGE=jiangxi-runtime:rebuilt-20260915 \
  --build-arg JIANGXI_GPU_COMPAT_IMAGE=jiangxi-gpu-compat:shim \
  -t geoview-jiangxi:cpu-20260915-rebuilt .
```

注意：GPU 构建仍按 AGENTS.md §4 的原样参数（`jiangxi-analysis-worker:gpu` 等），
`jiangxi-gpu-compat:shim` 严禁用于 GPU 构建。

## 底座构建脚本下载源

| 内容 | 源 |
| --- | --- |
| Ubuntu 基础层 | `ubuntu:20.04`（Docker Hub） |
| apt 包 | `archive.ubuntu.com`（focal） |
| Miniconda 安装器 | `https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh` |
| conda 包 | 清华 tuna 镜像（conda-forge / pkgs/main / pkgs/r，与原环境 channels 一致，见 environment.yml） |
| pip 常规包 | PyPI（`pypi.org/simple`） |
| `torch==2.2.2+cpu` / `torchvision==0.17.2+cpu` | `--extra-index-url https://download.pytorch.org/whl/cpu` |
| `mmcv==2.2.0`（带编译 ops 的 CPU 轮） | `--find-links https://download.openmmlab.com/mmcv/dist/cpu/torch2.2/index.html` |
| node v20.19.0（含 npm 10.8.2） | `https://nodejs.org/dist/v20.19.0/node-v20.19.0-linux-x64.tar.xz` |
| miner 原生 npm 包（@rollup/rollup-linux-x64-gnu、@esbuild/linux-x64） | registry.npmjs.org，版本号构建时从 `miner/package-lock.json` 读取 |

pip 侧统一 `--no-deps`：清单来自实测可用环境的闭合集合，避免解析器因 mm 系包
版本上界互相降级（mmsegmentation 1.1.2 官方上界 mmcv<2.1.0、mmdet 3.3.0 上界
mmcv<2.2.0，而实测组合是 mmcv 2.2.0）。底座构建时把两者的版本护栏 sed 放宽为
fork 源码树同款边界（mmseg：2.2.0–2.3.0；mmdet：maximum 2.3.0）；交付镜像构建中
Dockerfile.jiangxi 对 mmdet 的原有 sed 因此自动变为 no-op（其 grep 守卫仍通过）。

## 耗时预期（2026-09-16 实测，网络正常、层缓存清空）

| 步骤 | 实测 |
| --- | --- |
| shim | <10s |
| 底座全量构建 | 约 15–20 分钟（apt ~4min、Miniconda ~2min、conda env create 217s、pip install 156s、node 下载 ~1min、npm 原生包 119s；含重试容错预留） |
| 交付镜像 | 构建步骤 7.3 分钟 + 上下文传输约 8–10 分钟（约 4.3G：模型 3.5G + 瓦片 532M） |

实测坑（均已固化进 Dockerfile/清单）：
1. archive.ubuntu.com 边缘节点持续 502 → apt 源换 tuna（http，因基础镜像尚无
   ca-certificates，装好后其余下载全走 https）；
2. Miniconda 自带 defaults 通道触发非交互 ToS 阻断 → `/opt/conda/.condarc` 置空
   channels（本环境 conda 包实测全部来自 conda-forge）；
3. PyPI mmsegmentation/mmdet 的 mmcv 版本护栏与本组合冲突 → 见上文 sed 放宽；
4. `npm --version` 的 shebang 是 `env node` → 检查时需 PATH 含 /opt/node20/bin。

## 与旧底座（squashed-20260915）的关系

- 包集合等价：conda 依赖按导出清单精确钉版重建；pip 75 条钉子全部同版；
  node v20.19.0 / npm 10.8.2 一致。重建后 `conda list` / `pip freeze` 与旧底座
  diff 结论见 AGENTS.md §4.1（2026-09-16 记录）。
- 刻意差异（无害化清理）：
  1. 不再携带云南时代 `/app` 业务内容（旧底座内 `/app/backend/model` 仍有
     change_detection/classification/custom_models 等云南目录与 8GB+ 死重）；
  2. ENV 清除云南血统（旧底座带 MYSQL 凭据、大理 TIF 路径、paddle_rs 库名等
     ——重建底座只保留 `PATH`/`TZ`/`FLASK_CONFIG=production`/`DEBIAN_FRONTEND`）；
  3. mmsegmentation 由指向已消失云南旧路径的 editable 安装改为 PyPI 正式安装
     （运行时真实生效的 mmseg 始终是 `JIANGXI_MMSEG_SOURCE_ROOT`（PYTHONPATH）指向的
     `/app/backend/model/jiangxi/dinov3_swinV1` fork 源码树，行为不变）；
  4. `/app/miner` 只预置 package.json/package-lock.json 与两个 Linux 原生 npm 包
     （`Dockerfile.jiangxi` 构建交付镜像时从底座 COPY 回补离线 npm ci 的原生依赖）。
- 旧底座处置：`jiangxi-runtime:current` / `squashed-20260915` 及既有交付镜像一律
  保留不动；替换现役底座属跨交付变更，须用户确认后另行推进。

## 验收记录（2026-09-16，全部真跑）

- 底座 `jiangxi-runtime:rebuilt-20260915`（80f79a74aec3，**5.76GB**，13 层）：
  构建门全绿——MMSeg310 激活下 `import flask, openpyxl, rasterio, torch, mmseg,
  mmcv, mmdet` + `from mmcv.ops import nms` + `torch.__version__=='2.2.2+cpu'` +
  osgeo 兜底 + node v20.19.0 / npm 10.8.2。
- 交付镜像 `geoview-jiangxi:cpu-20260915-rebuilt`（3268bd170b13，**14.7GB**，28 层）：
  Dockerfile.jiangxi 原样、三个 ARG 换新底座 + shim；构建门含 PYTHONPATH fork 的
  import 集合与 node 版本检查，全绿。
- 容器内单测（卷挂载 worktree backend+docker，SECRET_KEY 注入）：
  `python -m unittest discover -s backend -p "test*.py"` → **Ran 167 tests ... OK**。
- 资产校验：`validate_jiangxi_assets.py` → Excel 348 / SHP 348 / KMZ 348、交集 348、
  重复 0、**status: PASS**。
- 行为探测（镜像内置 backend 起真实 Flask 进程）：未登录
  `GET /static/upload/x.png` → **401**；未知路由 `/no/such/route` → **404**；
  `/api/auth/session` → 200。
- 独立性：rebuilt 底座与 `yunnan-runtime:current` 的 RootFS.Layers 交集 = 2，
  且两个都是内容中立层——ubuntu:20.04 官方发行版层（470b66ea…）+ Dockerfile ENV
  产生的 0 字节通用空层（5f70bf18…）；与 `squashed-20260915` 交集 = 0。
  底座 FS 抽查 `find / -iname '*yunnan*'` 等无业务命中（仅 stdalign/gdalimport
  恰含 "dali" 子串的系统文件误报）；镜像 ENV 无 MYSQL_*/大理 TIF/paddle_rs 残留。
- 环境 diff（rebuilt vs squashed）：conda 包集合与版本/构建串差异 **0**；
  pip 版本错配 **0**；唯一形态差异 mmsegmentation 由指向已消失云南旧路径的
  editable 安装变为 PyPI 正式安装（运行时被 PYTHONPATH fork 覆盖，行为不变）；
  GDAL/packaging 两条 conda file:// 条目逐字节一致。

## 耗时预期

见上文「耗时预期（2026-09-16 实测）」。

## 离线替代方案

公网不可达时的等价路径（清单不变，只换源）：

1. conda：tuna 镜像换为内网镜像或官方 `conda-forge`/`anaconda` CDN（environment.yml
   的 channels 是 URL，可整串替换；build 串在 conda-forge 与其镜像间通用）。
2. pip：`pip download -r docker/runtime-env/MMSeg310.requirements.txt` 在有网机器
   预下载（同样带 pytorch CPU `--extra-index-url` 与 openmmlab `--find-links`），
   连同 miniconda sh、node tar.xz 一并摆渡后 `pip install --no-index --find-links <dir>`。
3. npm：`npm ci` 在有网机器跑出 node_modules 后整目录摆渡（交付镜像构建本身已是
   `--offline` + 仓库内 `.npm-cache`，只需保证缓存随仓库摆渡）。
4. ubuntu:20.04 与 apt 包：`docker save` 母镜像 + `apt-get download` 预取 deb。
