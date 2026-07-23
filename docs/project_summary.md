# GeoView 项目概览

## 1. 系统组成

- GeoView 前端：Vue + Element Plus，端口 `3000`
- GeoView 后端：Flask/Python，端口 `5008`
- Miner 前端：Vue/Vite，端口 `4000`
- Miner 后端：Node/Express，端口 `8000`
- MySQL：容器内 `3306`，宿主机映射 `3307`

## 2. 当前主要功能

- 地表覆盖分类：上传 GeoTIFF，执行 KML ROI 推理，结果同步到 Miner 输出目录。
- 光谱指数计算：支持 NDVI、NDWI、NDBI、NDSI，生成统计结果、预览图和历史记录。
- Miner 展示：默认按江西口径工作，读取 `D:\项目\江西数据\Jiangxi_NaturalMine.kmz`、变化矩阵输出和指数数据，提供地图展示、趋势统计和导出。
- 联调模式：江西区域最小验收优先使用在线卫星底图 `gaode`；如需纯离线底图，可继续挂载 `offline_bundle/maps/dali` 并切回本地瓦片模式。

## 3. 当前部署方式

生产/离线部署统一使用：

```text
docker-compose.prod.yml
APP_IMAGE=geoview-runtime:current
MYSQL_IMAGE=registry.openanolis.cn/openanolis/mysql:8.0.30-8.6
```

江西区域最小联调建议显式提供以下环境变量：

```text
ADMIN_PASSWORD=<强密码>
SECRET_KEY=<临时或正式密钥>
MINER_DEFAULT_KMZ_PATH=D:\项目\江西数据\Jiangxi_NaturalMine.kmz
MINER_MAP_PROVIDER=gaode
```

如需启用本地离线瓦片，再补充：

```text
OFFLINE_MAP_DIR=/path/to/GeoView/offline_bundle/maps/dali
MINER_TILE_TIF_PATH=/offline_maps/dali/澶х悊鐧芥棌鑷不宸瀇鍗浘1_Level_15.tif
MINER_LOCAL_TILE_URL=http://localhost:8000/tiles/{z}/{x}/{y}.png
```

## 4. 关键验证点

- `http://localhost:3000/`：GeoView 前端
- `http://localhost:4000/`：Miner 前端
- `http://localhost:5008/`：GeoView 后端
- `http://localhost:8000/api/stats`：Miner 后端 API
- `http://localhost:8000/api/projects`：项目工作台 API

江西区域验收时，还应检查：

- 默认业务数据源为 `D:\项目\江西数据\Jiangxi_NaturalMine.kmz`
- 工作台默认项目体现“江西历史成果迁移项目”口径
- 地图页筛选项与主流程文案中不再出现“云南 / 大理 / 曲靖”

`http://localhost:8000/` 根路径返回 `404` 是正常现象。

## 5. 交付文档入口

- 根目录主文档：`docs/`
- 离线包镜像副本：`offline_bundle/docs/`
- 两处文档应与根目录 `docker-compose.prod.yml` 的当前拆分式五服务编排保持一致
