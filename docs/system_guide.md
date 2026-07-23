# GeoView 系统说明

本文档记录当前可运行版本的服务、目录、持久化和部署约束。

## 1. 服务与端口

| 服务 | 技术栈 | 宿主机端口 | 验证地址 |
| --- | --- | --- | --- |
| GeoView 前端 | Vue | 3000 | `http://localhost:3000/` |
| GeoView 后端 | Flask | 5008 | `http://localhost:5008/` |
| Miner 前端 | Vue/Vite | 4000 | `http://localhost:4000/` |
| Miner 后端 | Node/Express | 8000 | `http://localhost:8000/api/stats` |
| MySQL | MySQL 8.0 | 3307 | 容器内 `3306` |

注意：Miner 后端根路径 `http://localhost:8000/` 返回 `404` 是正常现象。

## 2. 容器内关键目录

```text
/app/backend
/app/frontend
/app/miner
/app/backend/static
/app/miner/change_matrix_outputs
/app/miner/public/tiles
/offline_maps/dali
```

## 3. Docker 编排

当前生产编排文件：

```text
docker-compose.prod.yml
```

当前镜像：

```text
APP_IMAGE=geoview-runtime:current
MYSQL_IMAGE=registry.openanolis.cn/openanolis/mysql:8.0.30-8.6
```

命名卷：

```text
geoview_backend_static
geoview_mysql_data
geoview_hf_cache
geoview_miner_outputs
geoview_miner_tiles
```

## 4. 江西默认源与地图模式

江西区域化后的默认业务数据源为：

```text
D:\项目\江西数据\Jiangxi_NaturalMine.kmz
```

进行最小联调或浏览器验收时，建议显式提供：

```bash
export ADMIN_PASSWORD='<强密码>'
export SECRET_KEY='<临时或正式密钥>'
export MINER_DEFAULT_KMZ_PATH='D:\项目\江西数据\Jiangxi_NaturalMine.kmz'
export MINER_MAP_PROVIDER=gaode
```

说明：

- `MINER_DEFAULT_KMZ_PATH` 用于把 `miner` 与后端相关链路统一锁定到江西权威图斑源。
- `MINER_MAP_PROVIDER=gaode` 是当前江西最小验收推荐值，可直接验证在线卫星底图链路。
- `docker-compose.prod.yml` 当前仍保留本地离线瓦片挂载能力；若切回离线模式，需要继续提供 `OFFLINE_MAP_DIR` 与 `MINER_TILE_TIF_PATH`。

离线底图模式示例：

```bash
export OFFLINE_MAP_DIR="/path/to/GeoView/offline_bundle/maps/dali"
export MINER_TILE_TIF_PATH="/offline_maps/dali/澶х悊鐧芥棌鑷不宸瀇鍗浘1_Level_15.tif"
export MINER_MAP_PROVIDER=local
export MINER_LOCAL_TILE_URL='http://localhost:8000/tiles/{z}/{x}/{y}.png'
```

离线底图验证：

```bash
docker exec cugrs-miner-api sh -lc 'echo "$MINER_TILE_TIF_PATH"; ls -lah /offline_maps/dali'
curl -I http://127.0.0.1:8000/tiles/5/24/13.png
```

## 5. 部署入口

- 项目概览：`project_summary.md`
- 离线部署：`offline_deployment_guide.md`
- 管理员登录与最小验收：`admin_login.md`
- Docker 调试：`docker_hotfix_debug.md`
- 重启排障：`docker_restart_guide.md`
- 以上交付文档同步提供于根目录 `docs/` 与 `offline_bundle/docs/`

## 6. 离线包热修

当前交付目录未包含 `hotfix_rebuild.sh` 和 `source/GeoView_source_*.tar.gz` 这类源码重建材料；`offline_bundle` 仅保留运行镜像、数据卷归档和部署文档。

如需重建镜像，需先补齐独立的源码包与热修脚本，再按补充材料中的说明执行。
