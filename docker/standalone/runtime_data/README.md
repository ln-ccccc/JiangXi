在执行 `docker build -f docker/standalone/Dockerfile.jiangxi ...` 之前，
请先把江西单镜像首启所需数据放入当前目录：

- `Mine.csv`
- `348个图斑.shp`
- `348个图斑.shx`
- `348个图斑.dbf`
- `348个图斑.prj`

这些文件会被打包到镜像内的 `/app/runtime_data`，
供 `seed-jiangxi-runtime.sh` 和 `miner/server.js` 在 standalone 模式下直接使用。
