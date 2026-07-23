# 矿山监测数据全量重构与 AI 预测集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 348 个矿区图斑的 Shapefile 边界和 Excel AI 预测数据整合进系统，替换旧的演示数据，实现高精度地图展示、AI 智能诊断和 13 年长时序分析。

**Architecture:**
1. 数据预处理：通过 Python 脚本将 Shapefile 转换为 GeoJSON，并清洗 Excel 数据。
2. 后端适配：修改 `miner/server.js`，实现对新 GeoJSON 和长时序 Excel 数据的加载与 API 响应。
3. 前端展示：重构 Vue 组件，集成 AI 预测模块、环境画像和 2013-2025 年 NDVI 时序图表。

**Tech Stack:** Node.js, Express, Vue.js, Python (pandas, geopandas, shapely).

---

### Task 1: 数据预处理与格式转换

**Files:**
- Create: `scripts/process_mine_data.py`
- Output: `miner/data/mines_348.json` (GeoJSON)
- Output: `miner/data/indices_2013_2025.json` (Processed Excel)

- [ ] **Step 1: 编写 Shapefile 转 GeoJSON 脚本**
```python
import geopandas as gpd
import json

def convert_shp_to_geojson(shp_path, output_path):
    gdf = gpd.read_file(shp_path)
    # 确保坐标系为 WGS84
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    gdf.to_file(output_path, driver='GeoJSON')
    print(f"Converted {shp_path} to {output_path}")

# 使用路径: D:\Wechat\record\xwechat_files\wxid_w50x2jimjwr821_56b0\msg\file\2026-06\基础数据\348个图斑.shp
convert_shp_to_geojson(r"D:\Wechat\record\xwechat_files\wxid_w50x2jimjwr821_56b0\msg\file\2026-06\基础数据\348个图斑.shp", "miner/data/mines_348.json")
```

- [ ] **Step 2: 编写 Excel 数据提取脚本**
```python
import pandas as pd
import json

def process_excel(xlsx_path, output_path):
    df = pd.read_excel(xlsx_path)
    # 提取核心字段和 NDVI 时序字段
    ndvi_cols = [c for c in df.columns if 'NDVI_' in c]
    core_cols = ['FID', '预测修复类型', '预测置信度', '是否与原始修复模式一致', '土地利用类型', '岩性', 'elevation', 'slope', 'aspect']
    
    data = {}
    for _, row in df.iterrows():
        fid = int(row['FID'])
        data[fid] = {
            "ai": {
                "type": row['预测修复类型'],
                "confidence": row['预测置信度'],
                "consistent": row['是否与原始修复模式一致']
            },
            "env": {
                "land_type": row['土地利用类型'],
                "lithology": row['岩性'],
                "elevation": row['elevation'],
                "slope": row['slope'],
                "aspect": row['aspect']
            },
            "ndvi": [{"year": int(c.split('_')[1]), "value": row[c]} for c in ndvi_cols]
        }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Processed Excel data saved to {output_path}")

process_excel(r"D:\项目\JiangXi\YunNan_prechange_20260703_223508\348图斑_TableMERNet无图像预测结果.xlsx", "miner/data/indices_2013_2025.json")
```

- [ ] **Step 3: 执行脚本并验证生成文件**
Run: `python scripts/process_mine_data.py`
Expected: 生成 `miner/data/mines_348.json` 和 `miner/data/indices_2013_2025.json`。

- [ ] **Step 4: Commit**
```bash
git add miner/data/
git commit -m "data: convert shp to geojson and process excel attributes"
```

---

### Task 2: 后端 API 重构

**Files:**
- Modify: `miner/server.js`

- [ ] **Step 1: 更新 `initData` 加载逻辑**
修改 `server.js` 头部加载逻辑，读取新的 JSON 文件替代旧的 KML 和 Excel 加载。
```javascript
// 修改前
// const kmlPath = path.resolve(process.cwd(), 'yunnan.kml');
// ndviData = await loadIndexData('NDVI_2year.xlsx', ...);

// 修改后
let detailedData = {};
async function initData() {
    const geojsonPath = path.resolve(__dirname, 'data/mines_348.json');
    const attrPath = path.resolve(__dirname, 'data/indices_2013_2025.json');
    
    if (fs.existsSync(geojsonPath)) {
        const geojson = JSON.parse(fs.readFileSync(geojsonPath, 'utf-8'));
        minesData = geojson.features;
    }
    
    if (fs.existsSync(attrPath)) {
        detailedData = JSON.parse(fs.readFileSync(attrPath, 'utf-8'));
    }
}
```

- [ ] **Step 2: 调整 API 路由响应**
更新 `/api/stats` 和 `/api/mines/indices` 接口，返回 AI 预测和长时序数据。
```javascript
app.get('/api/mines/details', (req, res) => {
    const { fid } = req.query;
    const data = detailedData[fid];
    if (!data) return res.status(404).json({ error: 'Not found' });
    res.json(data);
});
```

- [ ] **Step 3: 重启服务器并测试 API**
Run: `node miner/server.js`
Test: `curl http://localhost:8000/api/mines/details?fid=1`
Expected: 返回包含 AI 预测和 NDVI 2013-2025 的 JSON。

- [ ] **Step 4: Commit**
```bash
git add miner/server.js
git commit -m "feat: update backend to serve new mine data and AI attributes"
```

---

### Task 3: 前端 Dashboard 重构

**Files:**
- Modify: `miner/src/App.vue`

- [ ] **Step 1: 更新地图加载逻辑**
将地图数据源改为从 `/api/geojson` 获取转换后的 348 图斑边界。
```javascript
// App.vue
async function fetchMines() {
    const res = await axios.get('/api/geojson');
    // 使用 L.geoJSON(res.data) 渲染多边形
}
```

- [ ] **Step 2: 重构详情面板组件**
添加 AI 诊断卡片和环境画像展示。
```html
<template>
  <div v-if="selectedMine" class="detail-panel">
    <div class="ai-card">
      <h3>🤖 AI 修复预测</h3>
      <p>类型: {{ selectedMine.ai.type }}</p>
      <p>置信度: {{ (selectedMine.ai.confidence * 100).toFixed(2) }}%</p>
    </div>
    <div class="env-card">
      <h3>⛰️ 自然环境画像</h3>
      <ul>
        <li>海拔: {{ selectedMine.env.elevation }}m</li>
        <li>坡度: {{ selectedMine.env.slope }}°</li>
      </ul>
    </div>
  </div>
</template>
```

- [ ] **Step 3: 升级 NDVI 图表**
更新 ECharts 配置，支持 2013-2025 年的时间轴展示。

- [ ] **Step 4: 运行前端并验证展示效果**
Run: `npm run dev`
Expected: 地图显示多边形边界，点击矿区显示 AI 预测和长时序图表。

- [ ] **Step 5: Commit**
```bash
git add miner/src/App.vue
git commit -m "feat: redesign dashboard with AI insights and long-term charts"
```
