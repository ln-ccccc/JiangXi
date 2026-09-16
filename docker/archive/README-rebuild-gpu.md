# JiangXi GPU 链自包含重建手册（v2，2026-09-16）

本手册配套同目录两个 v2 构建定义：

- `Dockerfile.jiangxi-inference-gpu-v2` → `jiangxi-inference-worker:gpu-v2`（CUDA 推理底座）
- `Dockerfile.jiangxi-analysis-worker-gpu-v2` → `jiangxi-analysis-worker:gpu-v2`（GPU 交付链中间层）

**状态：仅定义，未构建。** 两个 Dockerfile 与本手册在 2026-09-16 编写完毕，尚未执行
任何 `docker build`；下述版本号全部来自当日对现役镜像的只读实测（`docker run` /
`docker inspect`），不是臆造值。重建前置的背景事实见 AGENTS.md §4.1：v1 GPU 链的
上游 `geoview-inference-worker:current` 已不在本地镜像库，v1 定义不可原样重建；
v2 的目的就是让整条 GPU 链未来能从第三方公共基础镜像
`nvidia/cuda:12.8.0-devel-ubuntu22.04` 直接重建，零依赖云南血统镜像。

阅读顺序：AGENTS.md（§3/§4/§4.1/§5/§5.1/§7）→ 本手册 → 两个 v2 Dockerfile 头注释。

---

## 1. 重建目标链与各环节职责

```text
nvidia/cuda:12.8.0-devel-ubuntu22.04（第三方公共基础，需联网拉取）
  └─ jiangxi-inference-worker:gpu-v2        ← Dockerfile.jiangxi-inference-gpu-v2
       venv(torch 2.7.0+cu128) + 源码编译 mmcv 2.1.0 + 江西模型四件套（三哈希构建期校验）
  └─ jiangxi-runtime:rebuilt-20260915       ← 并行批次从源码重建的 CPU 底座（前置依赖）
  └─ jiangxi-analysis-worker:gpu-v2         ← Dockerfile.jiangxi-analysis-worker-gpu-v2
       = v2 推理底座 + 从 rebuilt CPU 底座拷 10 个 conda 包目录 + mmcv/mmengine 修补
  └─ geoview-jiangxi:jiangxi-gpu-<日期>-v2  ← docker/standalone/Dockerfile.jiangxi（现役，不改）
       JIANGXI_BASE_IMAGE / JIANGXI_GPU_COMPAT_IMAGE = analysis-worker v2，
       JIANGXI_RUNTIME_COMPAT_IMAGE = jiangxi-runtime:rebuilt-20260915
```

场景说明：AGENTS §4 规定**现役交付构建**离线进行（用已导入的本地 GPU 基础镜像）；
本手册描述的是**底座消失后的重建场景**，允许联网（拉 nvidia/cuda 公共基础、
PyTorch cu128 官方索引、PyPI）。一旦 v2 链建成并验收，镜像可 `docker save` 导出，
之后的交付构建回到离线模式（仅把 §4 命令里的 tag 换成 v2 产物）。

---

## 2. 版本核实记录（2026-09-16 实测，v2 钉死依据）

实测对象与探测方法（Git Bash 下必须加 `MSYS_NO_PATHCONV=1`，否则
`--entrypoint /opt/...` 被 MSYS 加 `D:/Git` 前缀——AGENTS §7 已记载的坑）：

```bash
MSYS_NO_PATHCONV=1 docker run --rm --entrypoint /opt/venv/bin/python \
  jiangxi-analysis-worker:gpu -c "import torch; print(torch.__version__)"
```

| 组件 | v1 inference venv<br>(0d2b4e8093ba) | v1 analysis venv<br>(71f55653f308) | 交付镜像 conda MMSeg310<br>(jiangxi-gpu-20260915-recheck) | v2 钉死值 |
| --- | --- | --- | --- | --- |
| python | 3.10.12 | 3.10.12（同 venv 血统） | 3.10.20 | 3.10（Ubuntu 22.04 系统 python3，补丁版随 apt 浮动） |
| torch | 2.7.0+cu128 | 2.7.0+cu128 | 2.7.0+cu128 | **2.7.0+cu128**（官方 cu128 索引） |
| torchvision | 0.22.0+cu128 | 0.22.0+cu128 | 0.22.0+cu128 | **0.22.0+cu128** |
| torch.version.cuda | 12.8 | 12.8 | 12.8 | **12.8**（基础镜像 12.8.0-devel） |
| mmcv（二进制/dist-info） | 2.1.0 | 2.1.0 | 2.1.0（自 analysis venv 拷入） | **2.1.0**（源码编译，`mmcv-2.1.0.dist-info` 必须按名落盘——standalone 契约） |
| mmcv（version.py 报告值） | 2.1.0 | 2.2.0（v1 sed） | 2.2.0 | analysis 阶段 sed 为 **2.2.0**（vendored mmseg 断言要求，见 §8） |
| mmengine | 0.10.4 | 0.10.4 | 0.10.4 | **0.10.4** |
| mmsegmentation（site-packages） | 1.2.2 | 1.2.2 | 1.1.2（conda） | venv **1.2.2**；运行时生效的是 PYTHONPATH 上的 vendored **1.1.2** |
| mmdet | 无（实测 MISSING） | 无 | 3.3.0（conda 侧） | venv 不装 mmdet（与 v1 一致；mmdet 归 conda/rebuilt 底座侧） |
| opencv | headless 4.10.0.84 | headless 4.10.0.84 | 4.10.0.84（conda 非 headless） | venv **opencv-python-headless 4.10.0.84** |
| rasterio / numpy / shapely | 1.4.4 / 1.26.4 / 1.8.5.post1 | 同左 | 同左 | **1.4.4 / 1.26.4 / 1.8.5.post1** |
| Pillow / PyYAML | 11.3.0 / 6.0.3 | 同左 | 12.2.0 / 6.0.3 | venv **11.3.0 / 6.0.3**（云南原版区间内取实测值钉死） |
| addict / yapf | 2.4.0 / 0.43.0 | 同左 | 同左 | **2.4.0 / 0.43.0**（mmcv 运行依赖，显式钉死） |
| Flask 组 | 2.2.2 / F-SA 2.5.1 / SA 1.4.46 / PyMySQL 1.2.0 / Werkzeug 2.2.3 / dotenv 1.2.2 | 同左 | flask 2.2.2 等 | 同 v1 venv 实测值逐项钉死 |
| gdal | 系统库（apt libgdal30 + rasterio wheel 自带） | 同左 | conda gdal 3.13.0 | v2 venv 侧 = apt `gdal-bin`+`libgdal30`+`libgeos-c1v5` + rasterio wheel；osgeo/geopandas 回退归 conda 侧（见 §8） |

补充实测事实（对验收与排障重要）：

- v1 analysis venv 里 `import mmseg` **会失败**（`AssertionError: MMCV==2.2.0 is
  used but incompatible`）：sed 把 mmcv 报告值改成 2.2.0 后，site-packages 的
  mmseg 1.2.2（要求 mmcv<2.2.0）断言不过。v1 镜像里没有江西 vendored 源码树
  （只拷了 model.pth），PYTHONPATH 落空才撞上它。v2 推理底座带全四件套，
  `import mmseg` 落到 vendored 1.1.2（要求 2.2.0<=mmcv<2.3.0），sed 后可正常
  导入——v2 因此把 mmseg 导入纳入构建期验证。
- conda 拷入的 10 个包在 v1 venv 里**可导入但 metadata 不可见**（只拷包目录、
  不拷 dist-info），且传递依赖（et_xmlfile、scipy 等）只存在于 conda 侧——
  venv 内不可做完整 import 验证，v1/v2 均只验证目录落盘。
- 现役交付镜像 conda 侧 `mmcv.__version__` 报告 2.2.0、dist-info 为 2.1.0、
  `from mmcv.ops import nms` 正常、mmdet 3.3.0 正常——这是 v2 要复现的运行时
  真值（standalone 构建把 venv 的 mmcv 目录拷进 conda 环境替换 ABI 不兼容的
  原 mmcv 2.2.0）。

---

## 3. 前置条件

### 3.1 基础镜像与网络

```powershell
docker pull nvidia/cuda:12.8.0-devel-ubuntu22.04   # 约 4-5GB 下载、约 7GB 解压
```

构建期需访问：`download.pytorch.org/whl/cu128`（torch+torchvision wheel 约
1.2-1.5GB 下载）、`pypi.org`（mmengine/mmseg/rasterio 等约 600MB-1GB、
mmcv 2.1.0 sdist 约 10MB）。pip 重试参数已在 Dockerfile 内置
（`--retries 12 --timeout 180`，apt `-o Acquire::Retries=5`）。

### 3.2 rebuilt CPU 底座就绪检查（前置依赖，并行批次产出）

analysis-worker v2 会从 `jiangxi-runtime:rebuilt-20260915` 的 conda 环境拷包，
构建前确认布局与现役底座一致（任一失败先找 CPU 底座重建批次，不要绕过）：

```bash
MSYS_NO_PATHCONV=1 docker run --rm --entrypoint /bin/bash jiangxi-runtime:rebuilt-20260915 -c \
  'test -d /opt/conda/envs/MMSeg310/lib/python3.10/site-packages/flask_cors \
   && test -d /opt/conda/envs/MMSeg310/lib/python3.10/site-packages/skimage \
   && test -d /opt/conda/envs/MMSeg310/lib/python3.10/site-packages/sqlparse \
   && test -x /opt/node20/bin/node && echo REBUILT-RUNTIME-OK'
```

> 2026-09-16 编写本手册时 `jiangxi-runtime:rebuilt-20260915` 尚未出现在本地镜像库
> （重建批次进行中）。它就绪前只能构建 v2 推理底座，analysis-worker v2 无法开始。

### 3.3 磁盘、时长与工具

- Docker Desktop 数据盘已在 `F:\images\jiangxi\DockerDesktopWSL`（AGENTS §4）。
  建议空闲空间：**F 盘 ≥ 90GB**（pip/BuildKit 缓存 ~10GB + 推理底座镜像 ~18-22GB
  + analysis-worker ~19-23GB + 最终交付镜像 ~44GB；两中间镜像删除后可回收）。
- 构建前记录 C/F 可用空间；大构建可能撑大
  `C:\Users\Administrator\AppData\Local\Temp` 的 `swap.vhdx`，勿在运行中删除。
- 构建上下文约 3.5GB（`backend/model/jiangxi` 全量，含 model.pth 1.97GB 与
  dinov3 依赖权重；`.dockerignore` 已放行该目录并排除其余模型目录）。
- **时长预估**：mmcv 源码编译是长杆——7 个 CUDA arch、`MAX_JOBS=2`（内存约束）
  在 16GB 内存机器上典型 2-6 小时；加上 torch 下载与其余步骤，整链（两个
  Dockerfile）预计 3-8 小时。BuildKit 的 pip/mmcv 缓存挂载能让失败重跑只补做
  失败步骤。
- 需要 Docker BuildKit（`RUN --mount=type=cache` 与 heredoc 语法）；Docker
  Desktop 默认开启。
- Git Bash 下所有含容器内路径的 docker 命令一律 `MSYS_NO_PATHCONV=1` 前缀。

---

## 4. 构建命令序列

**构建上下文必须包含模型四件套**：`backend/model/` 整目录被 `.gitignore` 忽略
（第 19 行），模型文件只存在于主工作树的未跟踪文件里——**worktree 检出里没有
`backend/model`**（2026-09-16 实测确认）。因此 v2 定义合入 main 前后都应从
主工作树构建；若一定要在 worktree 里试构建，先把
`backend/model/jiangxi`（3.5GB）完整拷入该 worktree（gitignored，不会误入提交），
拷入不完整会被三哈希构建门直接拦下。

tag 约定：可变日期 tag `gpu-v2-YYYYMMDD` 记录构建批次，浮动 tag `gpu-v2` 指向
最新成功批次；**在整链验收通过并经用户确认前，不把任何 v2 tag 指向现役交付链
引用的稳定名**（`jiangxi-analysis-worker:gpu`、`geoview-jiangxi:jiangxi-gpu`）。

### 4.1 v2 推理底座（PowerShell，主工作树为构建上下文）

```powershell
Set-Location D:\项目\JiangXi\JiangXi-Platform   # 主工作树（见上文模型说明）
docker build --progress=plain `
  -f docker/archive/Dockerfile.jiangxi-inference-gpu-v2 `
  -t jiangxi-inference-worker:gpu-v2-20260916 `
  -t jiangxi-inference-worker:gpu-v2 `
  .
```

ARG 均有默认值（torch 2.7.0 / torchvision 0.22.0 / cuda 12.8 / mmcv 2.1.0 /
arch 列表），无特殊理由不要改；改版本等于换 ABI，必须重走全部验收门。

### 4.2 v2 analysis worker

```powershell
docker build --progress=plain `
  -f docker/archive/Dockerfile.jiangxi-analysis-worker-gpu-v2 `
  --build-arg JIANGXI_INFERENCE_IMAGE=jiangxi-inference-worker:gpu-v2 `
  --build-arg JIANGXI_REBUILT_RUNTIME_IMAGE=jiangxi-runtime:rebuilt-20260915 `
  -t jiangxi-analysis-worker:gpu-v2-20260916 `
  -t jiangxi-analysis-worker:gpu-v2 `
  .
```

### 4.3 最终交付镜像（现役 standalone Dockerfile，参数对齐 §4 但换 v2 tag）

```powershell
docker build --progress=plain -f docker/standalone/Dockerfile.jiangxi `
  --build-arg JIANGXI_BASE_IMAGE=jiangxi-analysis-worker:gpu-v2 `
  --build-arg JIANGXI_RUNTIME_COMPAT_IMAGE=jiangxi-runtime:rebuilt-20260915 `
  --build-arg JIANGXI_GPU_COMPAT_IMAGE=jiangxi-analysis-worker:gpu-v2 `
  --build-arg JIANGXI_INFERENCE_DEVICE=cuda:0 `
  -t geoview-jiangxi:jiangxi-gpu-20260916-v2 .
```

运行参数（env 文件、SQLite、`--gpus all`、端口 4173/4174/5178、卷）与
AGENTS §4 完全一致，仅镜像 tag 不同；两期对比影像仍需容器创建后
`docker cp` 重放（AGENTS §4 末尾注意事项）。

---

## 5. 验收门（全部通过前不切稳定标签、不删任何现役镜像）

### 5.1 构建期自动门（Dockerfile 内置，失败即构建失败）

- 推理底座：mmcv wheel 编译后 `from mmcv.ops import roi_align` + torch/cuda/mmcv
  版本断言；全栈导入冒烟（PYTHONPATH 清空下 site-packages mmseg 1.2.2 组合）；
  模型三哈希（config/checkpoint/source + 依赖权重 + region/classes 契约）。
- analysis worker：`from mmcv.ops import nms`；vendored mmseg 1.1.2 导入且路径
  断言；mmcv 报告值 2.2.0 断言；`mmcv-2.1.0.dist-info` 按名落盘（standalone
  COPY 契约）；mmengine PYTHON_ROOT_DIR 修补后 grep 验证；conda 拷入包目录
  落盘抽查。

### 5.2 镜像级手动门（GPU 主机，`--gpus all`）

```bash
# 1) CUDA 可见性与设备（RTX 5060 / Blackwell sm_120）
MSYS_NO_PATHCONV=1 docker run --rm --gpus all --entrypoint /opt/venv/bin/python \
  jiangxi-analysis-worker:gpu-v2 -c \
  "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"

# 2) nms 真实执行（不是只 import：构造 CUDA 张量跑一遍算子）
MSYS_NO_PATHCONV=1 docker run --rm --gpus all --entrypoint /opt/venv/bin/python \
  jiangxi-analysis-worker:gpu-v2 -c \
  "import torch; from mmcv.ops import nms; b=torch.tensor([[0,0,10,10],[1,1,11,11],[0,0,10,10.]],device='cuda'); s=torch.tensor([0.9,0.8,0.7],device='cuda'); d,i=nms(b,s,0.5); print('nms cuda ok',d.shape,i.tolist())"
```

通过标准：`True`、正确设备名、nms 输出合法。这一步是 AGENTS §7
"必须 `from mmcv.ops import nms` 且至少一次真实 CUDA 推理"的算子级前置。

### 5.3 链级验收门（最终交付镜像，对齐 AGENTS §5/§5.1 与 2026-09-15 验收口径）

按 §4.3 建镜像、按 §4 参数起容器后，逐项执行并记录：

1. **容器内全量单测**（镜像一致解释器）：`docker exec` 进容器，conda 激活
   MMSeg310，`cd /app && python -m unittest discover -s backend -p "test*.py"`，
   期望全绿（20260915-recheck 基线 167 项；含 `test_jiangxi_gpu_contract.py`
   对 standalone Dockerfile 的 mmcv 契约断言）。
2. **资产校验**：`python /app/backend/tools/validate_jiangxi_assets.py`
   → 348/348/348、无重复；模型资产/哈希由启动时 worker 校验通过。
3. **真实推理双跑（§5.1 重复执行）**：推理 001（2011→2021 连续两遍）与
   002（纯数字 TBBH）completed，设备 cuda:0；第二遍验证状态清理与句柄回收。
4. **健康检查跨推理窗口（EPIPE 回归）**：推理进行中 HEALTHCHECK 保持 healthy
   （worker infer 线程化 + ping 即时应答，2026-09-15 C 批修复的行为不回退）。
5. **混合小批次**：≥3 组不同形态输入（不同地市/编号格式/最长跨度）串行推理。
6. 前端两道门在宿主机照常：`miner: npm run verify`、`frontend: npm run build`。
7. 浏览器冒烟：地图/解译/结果链路 + `JIANGXI_INFERENCE_DEVICE` 显示为 cuda:0。

### 5.4 切换与收尾

全部门通过后：向用户申请确认，将 `geoview-jiangxi:jiangxi-gpu` 指向 v2 交付
镜像，旧容器停止保留为回退；v2 中间镜像若不再复用可 `docker save` 归档到
`F:\images\jiangxi` 后删除以回收磁盘。

---

## 6. 回退方案

- **现役 GPU 中间镜像**：`jiangxi-analysis-worker:gpu`（71f55653f308）与
  `jiangxi-inference-worker:gpu`（0d2b4e8093ba）**保留不删**——它们是当前唯一
  可用的 GPU 交付链上游；v2 任何阶段失败，§4.3 立即换回 AGENTS §4 原样参数
  （`JIANGXI_BASE_IMAGE=jiangxi-analysis-worker:gpu` 等）即可继续交付。
- **现役交付实例**：`geoview-jiangxi:jiangxi-gpu-20260915-recheck`（415e3379340b）
  与运行容器 `geoview-jiangxi-gpu-recheck` 不动；stable 标签 `jiangxi-gpu` 在
  用户确认前不指向 v2。
- **构建中途失败**：BuildKit 缓存挂载保留 pip 包与（同 key 的）编译中间产物，
  修复后重跑同命令只补做失败层；mmcv 编译中断最常见（内存/网络），重跑前确认
  `MAX_JOBS=2` 未被调大。
- **v2 链建成但验收失败（单测/推理不过）**：保留 v2 镜像供定位，交付继续走
  现役链；差异根因（多为 ABI/依赖漂移）写回本手册风险清单后再试。

---

## 7. 风险清单

| # | 风险 | 说明与缓解 |
| --- | --- | --- |
| R1 | torch/mmcv ABI 不匹配 | v2 与现役镜像钉死完全相同的 torch 2.7.0+cu128 + mmcv 2.1.0 源码 + cu128 索引，ABI 面与 v1 一致；残余风险是 PyPI mmcv 2.1.0 sdist 或 torch cu128 wheel 的上游再发布（极低，版本号钉死）。缓解：§5.2 的 nms CUDA 实测 + §5.3 真实推理双跑，任一失败即停。 |
| R2 | mmcv 编译时长与中断 | 7 arch × MAX_JOBS=2 → 2-6h；断电/断网/OOM 中断用 BuildKit 缓存重跑。内存紧张时不要调大 MAX_JOBS（并行 nvcc 峰值是被刻意抑制的）。 |
| R3 | CUDA 下载体积 | 基础镜像 ~4-5GB + torch wheel ~1.5GB + nvidia 依赖包 ~3GB（安装态）；弱网环境预留充足时间，pip 重试已内置。 |
| R4 | rebuilt CPU 底座布局漂移 | analysis-worker v2 假设 rebuilt 底座保持 `/opt/conda/envs/MMSeg310/lib/python3.10/site-packages` 布局；§3.2 preflight 拦截，布局变化需先改 COPY 路径。 |
| R5 | devel 单一基础镜像体积 | v2 运行层比 v1（base 血统）多 ~3-4GB nvcc/工具链。验收后可改回云南原版 base/devel 两段拆分（纯瘦身，不动版本）。 |
| R6 | venv 内 mmseg 导入边界 | 未 sed 的推理底座里 vendored mmseg（要求 mmcv>=2.2.0）不可导入——已在 Dockerfile 用 `PYTHONPATH=` 清空做 site-packages 组合验证；直接 `docker run` 推理底座并 import mmseg 会断言失败，属预期（见 Dockerfile 头注释），不是缺陷。 |
| R7 | 入口脚本指向已剔除源码 | analysis-worker v2 的 ENTRYPOINT 依赖 `analysis_worker.py`（现行代码已删，复审 E 批）。镜像作为 standalone 构建基础时无影响（standalone 覆盖 ENTRYPOINT 并剔除脚本）；独立运行该入口会立即退出，属如实记录的 v1 遗留语义。 |
| R8 | conda 包 venv 内不完整 | 10 个拷入包缺传递依赖与 dist-info（v1 同款行为）；任何"在 analysis-worker 容器里直接跑业务"的尝试都不受支持，业务验证一律在最终交付镜像内做。 |
| R9 | Git Bash 路径转换 | 所有含 `/opt/...` 参数的 docker 命令必须 `MSYS_NO_PATHCONV=1`（本手册命令已带）。 |

---

## 8. 与归档 v1 的差异表

| 维度 | 归档 v1（inference 0d2b4e8093ba / analysis 71f55653f308） | v2（本目录定义） |
| --- | --- | --- |
| inference 上游 | `FROM geoview-inference-worker:current`（标签已消失，不可重建） | `FROM nvidia/cuda:12.8.0-devel-ubuntu22.04`（第三方公共基础，可随时重建） |
| 血统构成 | base（运行）+ devel（mmcv 构建）两段 + 云南构建层 | devel 单一基础，两阶段均在同一 tag 内 |
| 模型来源 | 从 `jiangxi-runtime:current`（含云南 30 层死重）拷 model.pth 至 mmseg_config | 构建上下文直接 COPY `backend/model/jiangxi` 四件套至现役路径 |
| 模型校验 | sha256sum 打印 + 文件存在检查 | metadata.json 三哈希 + 依赖权重 + region/classes，算法与 `mmseg_inference_caller.py` 逐字一致，失配即构建失败 |
| venv 环境 | 继承云南构建时的解析结果（版本未显式钉死在 v1 Dockerfile） | torch/mmcv/mmengine/mmseg/opencv/rasterio/... 全部按 2026-09-16 实测钉死 |
| mmcv 修补 | sed 2.1.0→2.2.0（无验证） | 同款 sed + 构建期断言 mmcv 报告值 2.2.0、dist-info 2.1.0 在位 |
| mmengine 修补 | sed PYTHON_ROOT_DIR（无验证） | 同款 sed + grep 验证修补生效 |
| 构建期 mmseg 验证 | 无（且 venv 内 import 会失败） | vendored 1.1.2 导入 + 路径断言（v2 底座带全源码树之利） |
| 包搬运来源 | `jiangxi-runtime:current` conda MMSeg310 | `jiangxi-runtime:rebuilt-20260915` conda MMSeg310（源码重建版，零云南层） |
| 入口 | v1 analysis 继承 run_inference-worker 健康探针（与实际入口错配） | inference 底座：真实 hold 入口 + 对应 cmdline 探针；analysis：探针目标与入口脚本一致 |
| 健康检查 | 继承自云南的 run_inference_worker.py /proc/1/cmdline 检查 | 同形态，检查各自镜像真实声明的入口进程名 |

---

## 9. 事实出入记录（编写时核实，与既往描述不符处如实列出）

1. **"GDAL/PROJ 回退逻辑"的出处**：云南参考 Dockerfile（`Dockerfile.inference-gpu`）
   中没有显式的回退代码块，只有 apt 安装 `gdal-bin`/`libgdal30`/`libgeos-c1v5`
   系统库；Python 侧栅格栈实际由 rasterio wheel 自带 GDAL/PROJ 提供。真正的
   geopandas→`osgeo.ogr` 显式回退校验位于江西现役
   `docker/standalone/Dockerfile.jiangxi`（conda 侧）。v2 推理底座按云南配方装
   系统库，并在头注释/本节记录该归属。
2. **"从 jiangxi-runtime:current 拷 conda"**：v1 实际拷的是 conda MMSeg310
   site-packages 里的 10 个包目录（flask_cors、skimage 等），不是整个 conda
   环境；且不带 dist-info（metadata 不可见）。v2 保持同行为。
3. **"mmseg/mmdet/mmcv 依赖"**：v1 推理 venv 实测**没有 mmdet**（`importlib.metadata`
   报 MISSING）；mmdet 3.3.0 只存在于交付镜像 conda 环境。v2 venv 同样不装 mmdet。
4. **归档 v1 注释"current Jiangxi source tree's mmcv>=2.2 guard"**：该守卫在当前
   源码的 `backend/applications/` 业务代码中不存在，其实体是
   `backend/model/jiangxi/dinov3_swinV1/mmseg/__init__.py` 的
   `MMCV_MIN='2.2.0'` / `MMCV_MAX='2.3.0'` 导入断言（vendored mmseg 1.1.2）。
   这正是 sed 的真实依据，v2 头注释已改写为准确表述。
5. **v1 血统**：任务描述"FROM nvidia/cuda:12.8.0-devel-ubuntu22.04 与归档原版
   一致的血统"——实测 v1 运行层血统是 `nvidia/cuda:12.8.0-base-ubuntu22.04`，
   devel 只用于 mmcv 构建阶段（云南 Dockerfile 两段结构）。v2 按任务钉 devel
   统一基础（同一 12.8.0 工具链线，ABI 等价），体积代价与后续瘦身路径见 §7 R5。
6. **v1 inference 镜像的 mmseg 导入**：venv `import mmseg` 报 1.1.2 而非 pip 的
   1.2.2——镜像 PYTHONPATH 指向云南 vendored 树（mmseg_config 路径）。v2 无该
   云南树，PYTHONPATH 指向江西 vendored 树，行为对齐现役约定。
7. **模型资产不入 git**：`backend/model/` 整目录被 `.gitignore` 忽略、
   `git ls-files backend/model` 为 0——江西模型四件套是主工作树的未跟踪文件。
   这决定了 v2 构建上下文的选择（见 §4 开头），也意味着换机重建时模型目录
   需单独迁移（哈希由 metadata.json 把关）。

---

维护约定：本手册与两个 v2 Dockerfile 同批评审；任何实际构建发生后，请把实测
耗时、镜像体积、验收结果回填到 §3.3 与 §5，并更新文件头的"未构建"状态。
