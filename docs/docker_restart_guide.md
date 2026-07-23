# Docker 重启与排障

## 1. 标准重启

```bash
cd /path/to/GeoView
docker compose -f docker-compose.prod.yml restart
docker compose -f docker-compose.prod.yml ps
```

当前编排会启动 `backend`、`frontend`、`miner-api`、`miner-web`、`mysql` 五个服务。

## 2. 重建应用容器

不清理 MySQL 和业务数据卷：

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate backend frontend miner-api miner-web
docker logs --tail 200 cugrs-backend
docker logs --tail 200 cugrs-miner-api
```

## 3. 完整停止与启动

```bash
docker compose -f docker-compose.prod.yml down

export APP_IMAGE=geoview-runtime:current
export MYSQL_IMAGE=registry.openanolis.cn/openanolis/mysql:8.0.30-8.6
export OFFLINE_MAP_DIR="$(pwd)/offline_bundle/maps/dali"
export MINER_TILE_TIF_PATH="/offline_maps/dali/澶х悊鐧芥棌鑷不宸瀇鍗浘1_Level_15.tif"
export MINER_MAP_PROVIDER=local
export MINER_LOCAL_TILE_URL='http://localhost:8000/tiles/{z}/{x}/{y}.png'

docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker compose -f docker-compose.prod.yml ps
```

## 4. 容器名冲突

报错示例：`container name "/cugrs-mysql" is already in use`

```bash
docker rm -f cugrs-backend cugrs-frontend cugrs-miner-api cugrs-miner-web cugrs-mysql
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

## 5. config.yaml 挂载错误

报错包含：`/app/config.yaml ... not a directory`

检查：

```bash
ls -lah config.yaml
```

修复：

```bash
rm -rf config.yaml
cp -f offline_bundle/config.yaml ./config.yaml
docker compose -f docker-compose.prod.yml up -d --force-recreate backend frontend miner-api miner-web
```

## 6. 灰底图或瓦片 404

```bash
docker exec cugrs-miner-api sh -lc 'echo "$MINER_TILE_TIF_PATH"; ls -lah /offline_maps/dali'
curl -I http://127.0.0.1:8000/tiles/5/24/13.png
```

判断：

- `200 image/png`：底图链路正常
- `404`：通常是 `OFFLINE_MAP_DIR` 未挂到真实 tif 目录，或 `MINER_TILE_TIF_PATH` 文件名不匹配

当前推荐：

```bash
export OFFLINE_MAP_DIR="$(pwd)/offline_bundle/maps/dali"
export MINER_TILE_TIF_PATH="/offline_maps/dali/澶х悊鐧芥棌鑷不宸瀇鍗浘1_Level_15.tif"
```
