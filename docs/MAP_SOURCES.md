# 美国地图数据与投影

本版组织视觉模型使用 **50 州与哥伦比亚特区**的真实简化边界。底图随 HTML 内嵌，浏览不请求任何地图瓦片、外部脚本或地图账户。组织标记来自 Markdown 档案中的公开城市、校园或总部位置；标记精度不应超出档案的 `location.precision`。

## 来源与许可

- 数据版本：[us-atlas 3.0.1 states-10m.json](https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/states-10m.json)。下载日期：2026-10-24。
- 上游：[topojson/us-atlas](https://github.com/topojson/us-atlas)。README 将本数据描述为 2017 年美国 Census cartographic state boundaries 的量化、简化 TopoJSON 分发。
- Census 原始系列：[Cartographic Boundary Files](https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html)。底图不是实时行政区划或导航精度服务。
- ISC 许可全文保存在 `data/geography/LICENSE.us-atlas.txt`，版权所有者为 Michael Bostock。原始 TopoJSON 保存在 `data/geography/states-10m.topo.json`。
- 原始文件 SHA-256：`d76b391ccfa8bff601d51e3e3da5d43a89fa46cd5caca72ce731b383be5596d0`。

`data/geography/us-states.md` 是来源与版本说明。构建时先验证 SHA-256，再解码 TopoJSON 差分弧线与反向弧线，合并闭合环，按同一坐标变换生成 SVG 路径。路径保留一位小数，约为本地图视口的 0.1 单位；这不提升原始地图精度。

## 坐标契约

`graph.geography` 包含：

```text
viewBox: "0 0 1000 600"
states: [{id: 两位 FIPS, name, region, path: SVG path data}]
projection: {type: "equirectangular-with-insets", regions: {mainland, alaska, hawaii}}
source_url, upstream_url, dataset, license, retrieved_at, source_sha256, scope
```

每个投影区域有 `lon: [west,east]`、`lat: [south,north]`、`box: [x,y,width,height]`。地理坐标和组织标记必须使用同一公式：

```text
mapX = x + (longitude - west) / (east - west) * width
mapY = y + (north - latitude) / (north - south) * height
```

| 区域 | 经度范围 | 纬度范围 | 显示框 x,y,width,height |
| --- | --- | --- | --- |
| mainland | −125 … −66 | 24 … 50 | 0,0,1000,600 |
| alaska | −190 … −130 | 50 … 72 | 20,480,230,105 |
| hawaii | −161 … −154 | 18 … 23 | 285,490,130,85 |

本土使用等距圆柱投影，视觉距离和面积有失真。阿拉斯加和夏威夷被移位、缩放为插图，不表达它们与本土的实际距离。阿拉斯加正经度先减 360，使跨日期变更线的阿留申群岛在插图中连续。源数据中五个领地未纳入当前州界视图；这只是本版范围限制，不是对其政治地位的判断。

## 更新与可复现

更换底图时同时更新原始文件、ISC 或新数据的许可、来源说明、文件哈希与本页，并运行 `scripts/dev.sh check`。组织位置更新只改 `data/entities` 的相应 Markdown，不能手改生成后的 JSON 或 SVG。不要将城市中心近似坐标标为精确办公地址；公开官网的城市/地址证据与地图坐标近似误差分别记录。
