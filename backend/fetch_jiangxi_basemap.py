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

LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = 117.40, 28.30, 117.80, 28.62
Z_MIN, Z_MAX = 8, 15
TILE_DIR = "/app/runtime_data/jiangxi_tiles"
OUT_TIF = "/app/runtime_data/jiangxi-test-basemap.tif"
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

    xa, ya, xb, yb = z15_meta
    cols, rows = (xb - xa) * 256, (yb - ya) * 256
    print(f"[stitch] z15 画布 {cols}x{rows}px", flush=True)
    canvas = np.zeros((rows, cols, 3), dtype=np.uint8)
    filled = 0
    for x in range(xa, xb):
        for y in range(ya, yb):
            p = os.path.join(TILE_DIR, str(Z_MAX), str(x), f"{y}.png")
            if not os.path.exists(p):
                continue
            tile = cv2.imread(p)
            if tile is None:
                continue
            px, py = (x - xa) * 256, (y - ya) * 256
            canvas[py:py + 256, px:px + 256] = cv2.cvtColor(tile, cv2.COLOR_BGR2RGB)
            filled += 1
    print(f"[stitch] 贴入 {filled} 块瓦片", flush=True)

    tmp_png = "/app/runtime_data/jiangxi-test-basemap.png"
    cv2.imwrite(tmp_png, canvas)

    # 范围 = 左上瓦片的左/上边缘 与 右下瓦片的右/下边缘
    left, _, _, top = tile_bounds_merc(Z_MAX, xa, ya)
    _, _, right, bottom = tile_bounds_merc(Z_MAX, xb - 1, yb - 1)
    rc = subprocess.run(
        ["gdal_translate", "-of", "GTiff", "-a_srs", "EPSG:3857",
         "-a_ullr", str(left), str(top), str(right), str(bottom),
         "-co", "COMPRESS=JPEG", "-co", "JPEG_QUALITY=85",
         tmp_png, OUT_TIF],
        check=False,
    ).returncode
    print(f"[gdal] rc={rc} 输出: {OUT_TIF}", flush=True)
    os.remove(tmp_png)
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
