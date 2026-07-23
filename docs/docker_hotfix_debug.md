# Docker 调试与热修指令

本文档用于当前 Docker 部署方式：`docker-compose.prod.yml`，对应容器名为 `cugrs-backend`、`cugrs-frontend`、`cugrs-miner-api`、`cugrs-miner-web`、`cugrs-mysql`。

## 1. 查看状态

```bash
cd /path/to/GeoView
docker compose -f docker-compose.prod.yml ps
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
```

## 2. 查看日志

```bash
docker logs --tail 200 cugrs-backend
docker logs --tail 200 cugrs-miner-api
docker logs --tail 120 cugrs-mysql
docker logs -f --tail 200 cugrs-miner-web
```

## 3. 进入容器排查

```bash
docker exec -it cugrs-backend bash
docker exec -it cugrs-miner-api bash
docker exec -it cugrs-mysql bash
```

容器内常用检查：

```bash
cd /app
python -V
node -v
ls -lah /app/backend
ls -lah /app/frontend
ls -lah /app/miner
ls -lah /offline_maps/dali
echo "$MINER_TILE_TIF_PATH"
```

## 4. HTTP 健康检查

```bash
curl -I http://127.0.0.1:3000/
curl -I http://127.0.0.1:4000/
curl -I http://127.0.0.1:5008/
curl -I http://127.0.0.1:8000/api/stats
curl -I http://127.0.0.1:8000/tiles/5/24/13.png
```

说明：

- `http://127.0.0.1:8000/` 返回 `404` 是正常现象。
- `/tiles/5/24/13.png` 返回 `200 image/png` 才表示离线底图链路正常。

## 5. 只重启应用容器

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate backend frontend miner-api miner-web
docker logs --tail 200 cugrs-backend
docker logs --tail 200 cugrs-miner-api
```

## 6. 容器名冲突

```bash
docker rm -f cugrs-backend cugrs-frontend cugrs-miner-api cugrs-miner-web cugrs-mysql
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

## 7. 底图灰底排查

先确认宿主机目录存在数据：

```bash
ls -lah offline_bundle/maps/dali
```

再用正确变量重启：

```bash
export APP_IMAGE=geoview-runtime:current
export MYSQL_IMAGE=registry.openanolis.cn/openanolis/mysql:8.0.30-8.6
export OFFLINE_MAP_DIR="$(pwd)/offline_bundle/maps/dali"
export MINER_TILE_TIF_PATH="/offline_maps/dali/澶х悊鐧芥棌鑷不宸瀇鍗浘1_Level_15.tif"
export MINER_MAP_PROVIDER=local
export MINER_LOCAL_TILE_URL='http://localhost:8000/tiles/{z}/{x}/{y}.png'

docker compose -f docker-compose.prod.yml up -d --force-recreate backend miner-api miner-web
docker exec cugrs-miner-api sh -lc 'echo "$MINER_TILE_TIF_PATH"; ls -lah /offline_maps/dali'
curl -I http://127.0.0.1:8000/tiles/5/24/13.png
```

## 8. 临时热修：覆盖容器内文件

适合快速验证问题。容器重建后会丢失，需要再固化到源码或镜像。

```bash
docker cp backend/applications/api/analysis.py cugrs-backend:/app/backend/applications/api/analysis.py
docker compose -f docker-compose.prod.yml up -d --force-recreate backend
docker logs --tail 200 cugrs-backend
```

## 9. 离线包热修：源码重建镜像

当前交付目录未包含 `hotfix_rebuild.sh`、`source/GeoView_source_*.tar.gz` 等镜像重建材料，不能直接在 `offline_bundle` 中执行源码热修重打包。

如需重建镜像，请先补齐源码包和热修脚本；当前目录可直接验证的交付物仅包括 `docker-compose.prod.yml`、`config.yaml`、`offline_bundle/images/*` 与 `offline_bundle/volumes/*`。
