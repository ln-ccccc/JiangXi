# 江西单镜像运行目录

- `Dockerfile.jiangxi`: 江西专用单镜像构建入口
- `start-jiangxi-standalone.sh`: 单容器启动入口
- `init-sqlite-runtime.sh`: SQLite 运行时初始化
- `seed-jiangxi-runtime.sh`: 江西首次初始化导入
- `healthcheck.sh`: 单镜像健康检查
- `config.standalone.yaml`: 单镜像默认端口与运行配置

## SQLite 单镜像模式

- 数据库文件默认位于 `/app/runtime_data/jiangxi.sqlite3`
- 首次启动会自动建库、建表、初始化管理员并导入江西数据
- 当前单镜像不再依赖 MySQL 服务端
- 运行时默认使用 `DB_BACKEND=sqlite`

## 运行数据准备

在执行构建前，请先将以下江西运行数据放入 `docker/standalone/runtime_data`：

- `Mine.csv`
- `348个图斑.shp`
- `348个图斑.shx`
- `348个图斑.dbf`
- `348个图斑.prj`
- `Jiangxi_NaturalMine.kmz`

## 构建

```bash
docker build -f docker/standalone/Dockerfile.jiangxi -t geoview-jiangxi:standalone .
```

## 运行

如 `4173`、`4174` 或 `5178` 已被本机其他服务占用，请先确认冲突资源归属，再执行：

```bash
cp .env.example .env
# 编辑 .env，替换 ADMIN_PASSWORD 和 SECRET_KEY 占位符。
docker run -d --name geoview-jiangxi --env-file .env -p 127.0.0.1:4173:4000 -p 127.0.0.1:4174:3000 -p 127.0.0.1:5178:5008 geoview-jiangxi:standalone
```

`ADMIN_PASSWORD` 和 `SECRET_KEY` 为必需环境变量。缺失时容器会在启动阶段失败并输出明确提示；不要在命令行或文档中写入真实凭据。

## 验收

- 访问 Miner：`http://127.0.0.1:4173/#/map`
- 访问解译平台：`http://127.0.0.1:4174/#/segmentation`
- 访问后端：`http://127.0.0.1:5178`
- 登录后确认项目列表为江西默认项目
- 确认地图加载江西面图斑数据
- 确认主流程不再出现云南口径

## 地物分类模型

独立镜像固定使用 CPU。运行地物分类前，必须在 `JIANGXI_MMSEG_MODEL_ROOT` 内提供江西专用且 CPU 兼容的配置、权重和 `metadata.json`，并通过对应环境变量指向文件；自定义源码目录可选。元数据必须声明 `region=jiangxi`、六类固定顺序以及配置/权重 SHA-256。模型加载后还会校验实际类别和分类头数量。工程不会自动选择 GPU，也不会回退到云南模型。
