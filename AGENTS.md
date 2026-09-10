# 江西项目 AGENTS.md

本文件是江西省矿山生态修复监测平台的项目级工作笔记。开始新的开发、调试或验收任务前，先阅读本文件，再检查 `git status` 和相关代码。

## 1. 项目边界

- 本仓库是江西项目，不得回退到云南模型、云南数据或云南默认配置。
- 业务主键是 `TBBH`；`map_fid` 只用于 SHP/KMZ 和历史输出目录的技术编号。
- 江西权威资产是 Excel、SHP（含 SHX/DBF/PRJ）和 KMZ 三件套，共 348 条记录。
- `Mine.csv` 只用于结构校验和差异报告，不得静默覆盖权威三件套。
- 映射不确定、资产哈希不一致、模型资产缺失或依赖缺失，必须阻止启动或导入。

## 2. 运行架构

默认 standalone 端口：

- Miner 地图：`127.0.0.1:4173` -> 容器 `4000`
- 解译前端：`127.0.0.1:4174` -> 容器 `3000`
- Flask 后端：`127.0.0.1:5178` -> 容器 `5008`

运行数据必须挂载到 `/app/runtime_data`，其中包含 SQLite、种子标记、manifest 和推理结果；容器重建时不得丢失该卷。

Standalone 启动顺序中，`docker/write-runtime-env.py` 负责生成前端公开地址；`backend/app.py` 在
`STANDALONE_MODE=1` 时不得再覆盖 `/app/frontend/.env`。GPU standalone 必须显式使用 SQLite，不能继承
根目录 `.env` 中供 Compose 使用的 MySQL 配置。

## 3. 推理设备契约

所有推理入口读取 `JIANGXI_INFERENCE_DEVICE`：

- 未设置时默认为 `cpu`。
- GPU 镜像显式设置为 `cuda:0`。
- 允许值只有 `cpu` 和 `cuda:0`；`cuda` 会规范化为 `cuda:0`。
- 不允许 `auto`，不允许 GPU 不可用时静默回退 CPU。
- CPU 镜像是离线可复现基线；GPU 镜像是单独的加速配置。

GPU standalone 在 `cuda:0` 下自动启用本地 Unix Socket Worker：
`/tmp/jiangxi-mmseg-worker.sock`。Worker 在 Flask 启动前完成一次模型 SHA-256 校验、
类别合同校验和模型加载，并串行复用同一显存模型；后续请求不得重新加载模型、不得回退到 CPU
或一次性子进程。Worker Socket 丢失或返回异常时，推理应明确失败。Docker 健康检查在 GPU
模式只 ping 已就绪 Worker；CPU 模式保持每次健康检查的模型资产校验。

前端运行时设备变量由 `docker/write-runtime-env.py` 写入：`VUE_APP_JIANGXI_INFERENCE_DEVICE` 和 `VITE_JIANGXI_INFERENCE_DEVICE`。

## 4. 镜像命名与构建

- CPU 基线：`geoview-jiangxi:standalone-cpu`
- GPU 稳定标签：`geoview-jiangxi:jiangxi-gpu`
- GPU 不可变验收标签：`geoview-jiangxi:jiangxi-gpu-YYYYMMDD-<purpose>`
- Docker Desktop 数据盘已迁移到 `F:\images\jiangxi\DockerDesktopWSL\disk\docker_data.vhdx`。
  构建层、缓存和镜像数据写入 Docker 数据盘，不要在 C 盘创建构建副本；源代码仍位于
  `D:\项目\JiangXi\JiangXi-Platform`，构建产物和镜像归档放到 `F:\images\jiangxi`。
- 大体积 Docker 构建仍可能触发 WSL 在 `C:\Users\Administrator\AppData\Local\Temp` 创建或扩展
  `swap.vhdx`。构建前记录 C/F 可用空间；不要在运行 Docker/WSL 时删除该交换盘。若要把 WSL swap
  迁移到 F 盘，必须先取得用户明确授权，并安排 Docker/WSL 重启窗口。

GPU 构建使用已导入的本地 GPU 基础镜像，不允许现场联网：

```powershell
docker build --progress=plain -f docker/standalone/Dockerfile.jiangxi `
  --build-arg JIANGXI_BASE_IMAGE=jiangxi-analysis-worker:gpu `
  --build-arg JIANGXI_RUNTIME_COMPAT_IMAGE=jiangxi-runtime:gpu `
  --build-arg JIANGXI_GPU_COMPAT_IMAGE=jiangxi-analysis-worker:gpu `
  --build-arg JIANGXI_INFERENCE_DEVICE=cuda:0 `
  -t geoview-jiangxi:jiangxi-gpu-YYYYMMDD `
  -t geoview-jiangxi:jiangxi-gpu .
```

GPU 容器必须使用 `--gpus all`。面向用户运行时与 CPU 版使用相同的标准端口
`4173/4174/5178`；切换前先停止旧实例并保留为回退副本，不能让 GPU 前端仍指向已废弃的临时端口。

```powershell
docker run -d --name geoview-jiangxi-gpu --gpus all --env-file .env `
  -e DB_BACKEND=sqlite `
  -e SQLITE_PATH=/app/runtime_data/jiangxi.sqlite3 `
  -e JIANGXI_INFERENCE_DEVICE=cuda:0 `
  -e VUE_APP_MINER_URL=http://127.0.0.1:4173/ `
  -e VUE_APP_BACKEND_URL=http://127.0.0.1:5178/ `
  -e VITE_GEOVIEW_URL=http://127.0.0.1:4174/ `
  -v jiangxi-runtime-gpu-f-20260829c:/app/runtime_data `
  -p 127.0.0.1:4173:4000 -p 127.0.0.1:4174:3000 -p 127.0.0.1:5178:5008 `
  geoview-jiangxi:jiangxi-gpu
```

2026-09-08 当前已验收运行实例：`geoview-jiangxi-gpu-20260908`，稳定标签
`geoview-jiangxi:jiangxi-gpu` 指向 `geoview-jiangxi:jiangxi-gpu-20260908-batching`
（在 epipefix 基础上新增：同尺寸瓦片批量前向——实测 GPU 暖跑推理约 -45%，
批量大小 JIANGXI_MMSEG_BATCH_SIZE 可调、批量失败自动退回逐张；EPIPE 修复与
entrypoint 自动重启监督见 §7；测试方法手册见 docs/testing_playbook.md）。
不替换江西模型权重。历史镜像与回退容器已经用户确认（磁盘受限）于 2026-09-08
清理；CPU 版镜像 `geoview-jiangxi:cpu-20260908`（协作者 Mac 用）保留。除非
用户明确确认，不删除 CPU 镜像或运行数据卷。

2026-09-10 起现行已验收实例：`geoview-jiangxi-gpu-20260909`，镜像
`geoview-jiangxi:jiangxi-gpu-20260909-offline`（stable 标签 `jiangxi-gpu` 已同步指向）。
该镜像为**自包含收尾版**：main 全部修复（离线底图边界遮罩、层级钳制、瓦片 URL env
严格校验、批量前向、EPIPE 修复）+ 32,214 张离线瓦片 z8-13 全部烘焙，容器创建即
完整可用，不再依赖 docker cp 热部署。运行参数与 §4 命令一致，env 文件改为
`D:\项目\JiangXi\jx_env_gpu_20260909.env`（从旧容器运行时 env 净化生成，去重并
钉死权威值；原 Temp 下 jx_env_offline.txt 血统污染已弃用）。
仍需容器创建后重放的只剩 `/app/backend/bianhua_2years/`（甲方 189 tif）。
验收记录：资产校验 PASS（348/348/348、无重复）；推理 001 对 2011→2021 连续双跑 +
002 对（纯数字 TBBH）均 completed，cuda:0/RTX 5060、峰值显存 2.8GB、暖跑单图斑
推理 0.79s；浏览器视觉验收（边界内影像、边界外遮罩）通过。
回退副本：旧容器 `geoview-jiangxi-gpu-20260908`（已停止）与旧镜像
`jiangxi-gpu-20260908-batching` 保留，经用户确认后方可删除。
2026-09-10 收编重建：`jiangxi-gpu-20260910-ui`（stable `jiangxi-gpu` 已指向，
ghcr 标签 `20260910-ui` 已备）包含全部 main 修复与新 UI（分页、tile bleeding
根治、山地制图台重设计、解译平台统一、Segmentation 拆分）。运行容器
`geoview-jiangxi-gpu-20260910` 已验收：116 单测 OK、资产 PASS、推理双跑+
混合格式 completed（cuda:0）、冒烟 PASS。env 文件同前。2026-09-10 用户确认后已清理：旧容器
`geoview-jiangxi-gpu-20260909/20260908` 与镜像 `jiangxi-gpu-20260909-offline`
、`jiangxi-gpu-20260908-batching`、`jiangxi-gpu-20260910-fixes`（含 ghcr 标签）。
代码级回退仍可用 git tag `ui-legacy-20260910`（重建镜像即可恢复旧 UI）。
不替换江西模型权重。CPU 版镜像 `geoview-jiangxi:cpu-20260908`（协作者 Mac 用，
不含 2026-09-09 之后的修复）保留，需时再重建。除非用户明确确认，不删除 CPU
镜像或运行数据卷。

注意：两期对比影像（`/app/backend/bianhua_2years/`，甲方 189 个 tif）位于
容器可写层，**重建容器即丢失**；需从宿主机 `D:\项目\jiangxi_data\影像文件\`
重新 `docker cp` 放入（`docker cp "D:\项目\jiangxi_data\影像文件\." 容器名:/app/backend/bianhua_2years/`）。
GPU 镜像重建必须使用本节原样参数（JIANGXI_BASE_IMAGE=jiangxi-analysis-worker:gpu），
换用其他 base 会复现 §7 的 GLIBC_2.32 worker 崩溃。

## 5. 必跑验证

后端单测必须在**与镜像一致的解释器**里跑（2026-09-09 教训：宿主机三个 Python
环境漂移，同一命令给出三份假失败清单，见 docs/testing_playbook.md T19）。权威跑法
是在运行容器内用 MMSeg310 环境：

```bash
docker exec <运行容器> bash -c \
  'source /opt/conda/etc/profile.d/conda.sh && conda activate MMSeg310 \
   && cd /app && python -m unittest discover -s backend -p "test*.py"'
docker exec <运行容器> bash -c \
  'source /opt/conda/etc/profile.d/conda.sh && conda activate MMSeg310 \
   && python /app/backend/tools/validate_jiangxi_assets.py'
```

前端两道门在宿主机跑（Node 环境稳定，未观察到漂移）：

```powershell
Set-Location miner
npm run verify
Set-Location ..\frontend
npm run build
Set-Location ..
```

容器验收必须确认：348 条 GeoJSON、TBBH 唯一、manifest 哈希一致、模型资产通过、设备为预期值，并完成一次限制数量的真实 CPU/GPU 推理。GPU 未通过前，不删除 CPU 镜像。

### 5.1 连续运行验证（防"单次通过、批量崩溃"）

任何"执行一次"型的验证（推理、导入、导出、备份恢复），单次成功不算通过，必须按三级递进补齐：

1. **重复执行**：同一操作连续跑第二遍。第一遍验证功能，第二遍验证状态清理与资源回收（临时目录、连接、句柄、缓存是否污染下一轮）。
2. **混合小批次**：抽样 ≥3 组不同形态的输入（不同地市、不同编号格式、不同数据量、最长跨度组合）串行执行，验证批处理路径的逐项隔离与累积效应。
3. **全量回归**：以上通过后再跑一次全量。

技巧细则、失效机制分析与本项目案例见 `docs/testing_playbook.md`（随迭代持续补充，新条目须按其模板回答"为什么有效"）。

原理：单次冒烟无法暴露"上一轮残留状态毒害下一轮"的失效，而这类失效在交付后几乎必然被用户触发（2026-09-07 推理 worker 崩溃即由此发现，见 §7）。

## 6. 安全与协作约定

- 不要在日志、文档、提交或回复中写入真实管理员密码、`SECRET_KEY`、数据库密码或 token。
- 不要执行 `git reset --hard`、批量删除或覆盖未知用户文件。
- 数据库迁移、清理镜像或删除容器前，先确认准确目标并保留可回滚副本。
- 模型必须使用江西受控目录和 `metadata.json` 中的配置、权重、源码及依赖权重哈希。
- 六类顺序固定为：`grassland`、`forest`、`building`、`road`、`bareground`、`water`。
- 先复现和定位根因，再写失败测试，再做最小修复；保留用户已有未提交改动。

## 7. 调试经验

- 结果图片偶发加载失败的根因包括 Flask 会话过期导致结果 URL 返回 401，以及并发推理共享临时目录导致互相清理；当前已使用活动会话、会话心跳、可见图片错误状态和每次推理独立临时目录。
- 道路类别大面积误判不是 CPU/GPU 设备本身造成的，优先检查模型权重、训练域、类别映射、预处理和输入影像分辨率。
- 本地 GPU 基础镜像能够看到 RTX 5060。最终可用组合是 `jiangxi-analysis-worker:gpu` 的 glibc/系统层、
  `jiangxi-runtime:gpu` 的 `MMSeg310` Conda 环境，以及 `jiangxi-analysis-worker:gpu` 的 MMCV 原生扩展；
  直接把该扩展复制到 `jiangxi-runtime:gpu` 会触发 `GLIBC_2.32`，不能跨基础镜像复制 `.so`。
- `jiangxi-runtime:gpu` 原始 `mmcv 2.2.0` 的 `_ext` 与 Torch ABI 不兼容；最终镜像必须验证
  `from mmcv.ops import nms` 和至少一次真实 CUDA 推理，不能只检查 Python 包名。
- 推理 worker 崩溃（2026-09-07 发现，同日修复）：worker 推理耗时长于健康检查 ping 超时（2s）时，
  healthcheck 会留下一条已被客户端放弃的陈旧连接；worker 处理完推理后 accept 到该连接，
  `_read_message` 得到空请求、构造错误响应后 `_send_message` 对已关闭的对端写入触发 EPIPE，
  异常逃逸出 serve 循环导致 worker 进程退出；entrypoint 的 `wait -n` 又将任一子服务退出
  放大为整机 terminate。表现为"每次启动只能完成一次推理，第二次推理必崩"。已修复：
  serve 循环对单连接发送失败仅记日志并继续（per-connection try/except），signal 注册
  限制主线程使 serve_worker 可测试；entrypoint 将 worker 改入带 TERM 转发的自动重启
  监督循环（注意脚本头部 `set -euo pipefail`，循环内 `wait` 必须就地兜底非零退出码）。
  回归测试 `test_survives_client_disconnect_before_response`；验收为同对影像连续双跑
  跨健康检查窗口。
- 环境变量"血统污染"（2026-09-09 定性）：最初 PowerShell `docker run -e` 里的瓦片
  URL 模板值被损坏成 `/tiles/{z}/{x}/{y}.png/{x}/{y}.png}`，经 env 导出文件与容器
  重建链路代代相传，被 write-runtime-env.py 写进前端 .env 使整层瓦片 404。Git Bash
  下 `docker run -e VAR=/tiles/...` 还会被 MSYS 路径转换加 `D:/Git` 前缀，属同类坑
  （容器内传路径参数一律 `MSYS_NO_PATHCONV=1`）。根治：write-runtime-env.py 对
  MINER_LOCAL_TILE_URL 做正则严格校验，非标准 XYZ 模板一律回退默认值，启动自愈；
  不要试图逐个清洗 env 文件血统。
- 离线底图 Leaflet 三课（2026-09-09）：① GeoJSON 坐标是 `[lng,lat]`，喂给
  `L.polygon` 前必须翻转为 `[lat,lng]`，否则孔洞环被投影到视口外、经渲染裁剪后
  整个从 `d` 属性消失，遮罩变成盖满全球的实心块（症状：省界内也黑屏但瓦片请求
  全部 200）；② 图层级 `maxZoom/minZoom` 的语义是"越界隐藏整层"而不是限制缩放，
  防黑屏的层级钳制必须用地图级 `setMaxZoom/setMinZoom`；③ `minNativeZoom` 让低
  层级复用所设层级瓦片降采样（配 map minZoom=7），是"缩小影像不消失"的关键，
  而图层 `minZoom` 会在低层级直接隐藏整层，二者不可混用。
