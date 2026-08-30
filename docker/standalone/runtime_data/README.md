在执行 `docker build -f docker/standalone/Dockerfile.jiangxi ...` 之前，
请先把江西单镜像首启所需数据放入当前目录：

- `Mine.csv`
- `348个图斑.shp`
- `348个图斑.shx`
- `348个图斑.dbf`
- `348个图斑.prj`
- `Jiangxi_NaturalMine.kmz`
- `Jiangxi_asset_manifest.json`

这些文件会被打包到镜像内的 `/app/runtime_data`，
供 `seed-jiangxi-runtime.sh` 和 `miner/server.js` 在 standalone 模式下直接使用。
权威 Excel 位于 `miner/data/348图斑_TableMERNet无图像预测结果.xlsx`；manifest 必须由
`python backend/tools/build_jiangxi_asset_manifest.py` 生成，并在交付前通过
`python backend/tools/validate_jiangxi_assets.py`。
