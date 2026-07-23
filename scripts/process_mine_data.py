import geopandas as gpd
import pandas as pd
import json
import os
from pathlib import Path

def convert_shp_to_geojson(shp_path, output_path):
    print(f"Loading Shapefile from {shp_path}...")
    gdf = gpd.read_file(shp_path)
    # Ensure CRS is WGS84 for web maps
    if gdf.crs != "EPSG:4326":
        print(f"Converting CRS from {gdf.crs} to EPSG:4326...")
        gdf = gdf.to_crs("EPSG:4326")
    
    # Ensure FID is a property in the GeoJSON
    if 'FID' not in gdf.columns:
        print("FID not found in columns, using index as FID...")
        gdf['FID'] = gdf.index
    
    # We only need FID and geometry for the map
    gdf.to_file(output_path, driver='GeoJSON')
    print(f"Converted {shp_path} to {output_path}")

def process_excel(xlsx_path, output_path):
    print(f"Processing Excel from {xlsx_path}...")
    df = pd.read_excel(xlsx_path)
    
    # Identify NDVI columns
    ndvi_cols = [c for c in df.columns if 'NDVI_' in c]
    
    data = {}
    for _, row in df.iterrows():
        # Ensure FID is used as key
        fid = int(row['FID'])
        
        # AI prediction results
        ai_data = {
            "type": str(row.get('预测修复类型', '未知')),
            "confidence": float(row.get('预测置信度', 0)),
            "consistent": str(row.get('是否与原始修复模式一致', '未知')),
            "suggestion": str(row.get('复核建议', '无'))
        }
        
        # Environmental factors
        env_data = {
            "land_type": str(row.get('土地利用类型', '未知')),
            "lithology": str(row.get('岩性', '未知')),
            "elevation": float(row.get('elevation', 0)),
            "slope": float(row.get('slope', 0)),
            "aspect": float(row.get('aspect', 0))
        }
        
        # NDVI time series
        ndvi_series = []
        for col in ndvi_cols:
            year = int(col.split('_')[1])
            val = row[col]
            if pd.notnull(val):
                ndvi_series.append({"year": year, "value": float(val)})
        
        # Sort NDVI by year
        ndvi_series.sort(key=lambda x: x['year'])
        
        data[fid] = {
            "fid": fid,
            "name": str(row.get('TBBH', f"图斑_{fid}")),
            "area": float(row.get('TBTYMJ', 0)),
            "ai": ai_data,
            "env": env_data,
            "ndvi": ndvi_series
        }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Processed Excel data saved to {output_path}")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    runtime_data = project_root / "docker" / "standalone" / "runtime_data"
    miner_data = project_root / "miner" / "data"
    miner_data.mkdir(parents=True, exist_ok=True)

    shp_file = Path(
        os.getenv(
            "MINER_DEFAULT_GEO_SOURCE_PATH",
            runtime_data / "348个图斑.shp",
        )
    )
    xlsx_file = Path(
        os.getenv(
            "MINER_ECOLOGY_WORKBOOK_PATH",
            miner_data / "348图斑_TableMERNet无图像预测结果.xlsx",
        )
    )

    geojson_out = miner_data / "mines_348.json"
    attr_out = miner_data / "indices_2013_2025.json"
    
    convert_shp_to_geojson(shp_file, geojson_out)
    process_excel(xlsx_file, attr_out)
