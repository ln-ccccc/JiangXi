# GeoView 离线部署指南

本文档是离线环境的最小部署流程。完整服务说明与交付约束见同目录下的 `system_guide.md`。

## 1. 目录要求

在项目根目录执行：

```bash
cd /path/to/GeoView
```

确认关键文件存在：

```bash
test -f docker-compose.prod.yml
test -f config.yaml
test -f offline_bundle/images/geoview_runtime_current.tar
test -f offline_bundle/images/mysql_8.0.30-8.6.tar
test -f offline_bundle/maps/dali/澶х悊鐧芥棌鑷不宸瀇鍗浘1_Level_15.tif
```

## 2. 加载镜像

```bash
docker load -i offline_bundle/images/geoview_runtime_current.tar
docker load -i offline_bundle/images/mysql_8.0.30-8.6.tar
```

## 3. 启动

```bash
export APP_IMAGE=geoview-runtime:current
export MYSQL_IMAGE=registry.openanolis.cn/openanolis/mysql:8.0.30-8.6
export ADMIN_PASSWORD='<强密码>'
export SECRET_KEY='<临时或正式密钥>'
export MINER_DEFAULT_KMZ_PATH='/app/runtime_data/Jiangxi_NaturalMine.kmz'
export MINER_MAP_PROVIDER=gaode

docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

说明：

- 上述脚本是当前江西区域最小验收启动方式，优先验证江西权威 KMZ 源与在线卫星底图链路。
- 江西 Shapefile、KMZ 与运行数据必须通过容器卷挂载到 `/app/runtime_data`；部署配置不得使用 Windows 宿主机绝对路径。
- 建议先从 `.env.example` 创建未跟踪的 `.env`，再设置所有管理员、应用和数据库密钥。MySQL 默认不发布端口。
- 如果现场必须完全离线运行底图，再额外设置 `OFFLINE_MAP_DIR`、`MINER_TILE_TIF_PATH`、`MINER_LOCAL_TILE_URL`，并把 `MINER_MAP_PROVIDER` 切回 `local`。
- `docker-compose.prod.yml` 中仍保留离线瓦片挂载能力，因此离线模式和江西最小联调模式可以按需切换。

## 4. 验证

```bash
docker compose -f docker-compose.prod.yml ps
curl -I http://127.0.0.1:3000/
curl -I http://127.0.0.1:4000/
curl -I http://127.0.0.1:5008/
curl -I http://127.0.0.1:8000/api/stats
```

江西区域最小验收还应补充人工检查：

- 登录 `http://127.0.0.1:4000/` 后，工作台标题与默认项目体现江西口径。
- 地图页筛选项、主流程文案中不再出现“云南 / 大理 / 曲靖”。
- 若当前采用 `MINER_MAP_PROVIDER=gaode`，浏览器网络面板应能看到在线卫星底图请求。

仅当切回 `MINER_MAP_PROVIDER=local` 时，再检查：

```bash
curl -I http://127.0.0.1:8000/tiles/5/24/13.png
```

此时 `/tiles/5/24/13.png` 返回 `200` 才表示离线底图链路正常。

## 5. 常见问题

容器名冲突：

```bash
docker rm -f cugrs-backend cugrs-frontend cugrs-miner-api cugrs-miner-web cugrs-mysql
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

底图灰底或瓦片 `404`：

```bash
docker exec cugrs-miner-api sh -lc 'echo "$MINER_TILE_TIF_PATH"; ls -lah /offline_maps/dali'
curl -I http://127.0.0.1:8000/tiles/5/24/13.png
```

重点检查：

- `OFFLINE_MAP_DIR` 是否指向宿主机上真实存在的 `offline_bundle/maps/dali`
- `MINER_TILE_TIF_PATH` 是否是容器内路径 `/offline_maps/dali/澶х悊鐧芥棌鑷不宸瀇鍗浘1_Level_15.tif`
- `MINER_DEFAULT_KMZ_PATH` 是否显式指向 `/app/runtime_data/Jiangxi_NaturalMine.kmz`
- `MINER_MAP_PROVIDER` 是否与当前验收模式一致：江西最小联调用 `gaode`，纯离线底图用 `local`
- `docker-compose.prod.yml` 是否使用当前镜像名 `geoview-runtime:current`
