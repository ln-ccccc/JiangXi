param(
  [string]$Image = 'geoview-jiangxi:gpu',
  [string]$ContainerName = 'geoview-jiangxi-gpu',
  [string]$EnvFile = '.env'
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $EnvFile)) {
  throw "找不到环境文件：$EnvFile。请复制 .env.example 后填写 ADMIN_PASSWORD 与 SECRET_KEY。"
}
if (docker ps -a --format '{{.Names}}' | Select-String -SimpleMatch $ContainerName -Quiet) {
  throw "容器 $ContainerName 已存在。请先确认并停止或删除该容器后再启动。"
}

docker run -d --name $ContainerName --gpus all --env-file $EnvFile -p 4000:4000 -p 5008:5008 `
  -e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=compute,utility $Image
if ($LASTEXITCODE -ne 0) { throw 'GPU 容器启动失败。请先运行 docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi 检查 GPU 透传。' }
