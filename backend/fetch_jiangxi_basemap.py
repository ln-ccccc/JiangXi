"""联网下载江西矿区带 ESRI 卫星瓦片并拼接为带地理参考的 GeoTIFF（一次性测试工具）。

bbox：经度 117.40-117.80、纬度 28.30-28.62（上饶横峰矿区带，覆盖图斑 map_fid=22）
输出：/app/runtime_data/jiangxi-test-basemap.tif（EPSG:3857，JPEG 压缩）
"""
import math
import os
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = 112.90, 23.95, 119.00, 30.65  # 江西省全域 + 0.5° 缓冲
Z_MIN, Z_MAX = 8, 13
TILE_DIR = "/app/miner/public/tiles"
OUT_TIF = ""
URL_TMPL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"


def deg2tile(lon, lat, z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def tile_bounds_merc(z, x, y):
    def x2lon(x):
        return x / (2 ** z) * 360.0 - 180.0

    def y2lat(y):
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / (2 ** z)))))

    def lat2merc_y(lat_deg):
        # Web Mercator Y：R × atanh(sin φ)。此前误用经度线性常数 111319.49，
        # 会产生约 100 倍的南北偏移（症状：瓦片落在赤道附近、矿点 404）
        return 6378137.0 * math.atanh(math.sin(math.radians(lat_deg)))

    left, right = 6378137.0 * math.radians(x2lon(x)), 6378137.0 * math.radians(x2lon(x + 1))
    top, bottom = lat2merc_y(y2lat(y)), lat2merc_y(y2lat(y + 1))
    return (left, bottom, right, top)


def fetch_one(args):
    z, x, y = args
    out = os.path.join(TILE_DIR, str(z), str(x), f"{y}.png")
    if os.path.exists(out) and os.path.getsize(out) > 100:
        return (z, x, y, "cached")
    url = URL_TMPL.format(z=z, y=y, x=x)
    last = ""
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "jiangxi-basemap-test/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            if resp.status == 200 and len(data) > 100:
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out, "wb") as f:
                    f.write(data)
                return (z, x, y, "ok")
            return (z, x, y, f"http_{resp.status}")
        except Exception as exc:
            last = str(exc)
    return (z, x, y, f"err:{last[:40]}")


def main():
    jobs = []
    z15_meta = None
    for z in range(Z_MIN, Z_MAX + 1):
        x0, y0 = deg2tile(LON_MIN, LAT_MAX, z)
        x1, y1 = deg2tile(LON_MAX, LAT_MIN, z)
        xa, xb = int(math.floor(x0)), int(math.ceil(x1))
        ya, yb = int(math.floor(y0)), int(math.ceil(y1))
        for x in range(xa, xb):
            for y in range(ya, yb):
                jobs.append((z, x, y))
        if z == Z_MAX:
            z15_meta = (xa, ya, xb, yb)
    total = len(jobs)
    print(f"[dl] 计划下载 {total} 个瓦片（z{Z_MIN}-z{Z_MAX}）", flush=True)

    done = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for z, x, y, st in pool.map(fetch_one, jobs):
            done += 1
            if done % 100 == 0:
                print(f"[dl] {done}/{total} 最近: z{z}/{x}/{y} {st}", flush=True)
    ok = sum(1 for _ in os.popen(f"find {TILE_DIR} -name '*.png'"))
    print(f"[dl] 完成，磁盘瓦片 {ok} 个", flush=True)

    print('[done] 全部层级下载完成', flush=True)


if __name__ == "__main__":
    sys.exit(main())
