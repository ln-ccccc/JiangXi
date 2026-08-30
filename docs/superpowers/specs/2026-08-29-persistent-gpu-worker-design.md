# GPU 常驻推理 Worker 设计

## 目标

让江西 GPU standalone 在容器启动时完成一次模型完整性校验和模型加载；后续地物分类请求复用该模型，避免每个请求重新启动 Python、重新校验大权重和重新加载 DINOv3+Swin。

## 已确认边界

- 只在 `STANDALONE_MODE=1` 且 `JIANGXI_INFERENCE_DEVICE=cuda:0` 时启用。
- 外部 Flask API、Vue 页面、输出目录和 TBBH/map_fid 结果协议不变。
- CPU 和非 standalone 继续使用现有一次性子进程路径。
- GPU 请求必须串行执行；排队而不是并发加载多个模型。
- 模型完整性校验仍然保留，但移动到 Worker 启动阶段；Docker 健康检查只探测已加载 Worker 的就绪状态。
- Worker 无法启动、Socket 丢失或返回异常时，GPU 请求明确失败，禁止静默回退到慢速 CPU 或一次性模型进程。

## 方案比较

1. 在 Flask 进程内直接缓存模型：调用开销最低，但会把 MMSeg/CUDA 依赖和 Web 服务生命周期耦合，风险最高。
2. 每次继续调用 CLI：改动最小，但无法消除冷启动，不满足性能目标。
3. 独立常驻 Worker（采用）：使用 Unix Socket 接收内部 JSON 请求，启动时加载一次模型，单线程服务请求队列；保持 Flask 与 MMSeg 的现有进程隔离。

## 组件与数据流

```text
浏览器 → Flask /api/analysis/kml_roi_inference
       → kml_roi_infer.py（裁剪、TBBH/map_fid 对齐）
       → mmseg_inference_caller
       → /tmp/jiangxi-mmseg-worker.sock
       → mmseg_worker.py（单队列、已加载模型）
       → PNG/掩码/结果 manifest
```

`mmseg_worker.py` 仅监听容器内 Unix Socket。启动时调用现有 `get_model_paths()` 完整校验配置、主权重、DINO/Swin 依赖权重和受控源码；随后调用 `init_model(..., device='cuda:0')` 并保持模型驻留显存。

每个推理请求只发送输入目录、输出目录与瓦片名称。Worker 返回现有 `results` 结构，并增加 `queue_wait_seconds`、`model_load_once` 与每次推理的峰值显存信息。Worker 单线程处理，后到请求由 Socket backlog 排队。

## 启动、健康与错误处理

- `start-jiangxi-standalone.sh` 在 GPU 模式导出 Worker 开关和 Socket 路径；CPU 模式不导出。
- `docker/entrypoint.sh` 在启动 Flask 前创建 Worker、等待 readiness，并将 Worker PID 纳入退出清理。
- Docker 健康检查在 Worker 启用时执行 `ping`，确认模型已加载、设备为 `cuda:0` 和启动校验状态为成功；不再每 30 秒重新哈希 3.53 GB 权重。
- Worker 失败时，entrypoint 退出并使容器不可用；运行期间 Socket 失效时 API 返回明确的“GPU 推理 Worker 不可用”错误。

## 测试与验收

- Worker 协议：ping、单请求结果、连续请求复用同一已加载模型、错误响应。
- Caller：配置 Socket 时走 Worker；Socket 不存在时报错而不回退；未配置时保留旧子进程路径。
- 启动脚本：GPU 启用 Worker、CPU 不启用、停止信号会关闭 Worker。
- 健康检查：GPU 使用 ping，CPU 保留模型资产校验。
- GPU 验收：镜像启动后确认 Worker 就绪；连续两次同影像请求不重载模型；结果与现有 TBBH/map_fid 结果清单一致；容器重启后重新预热且数据卷保持。

## 非目标

- 不更换模型、权重或类别映射。
- 不改变道路类别精度问题。
- 不修改浏览器 API 请求格式。
- 不引入 Redis、消息队列或额外容器。
