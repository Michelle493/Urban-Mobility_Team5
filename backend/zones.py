import json
import shapefile
from pyproj import Transformer

transformer = Transformer.from_crs("EPSG:2263", "EPSG:4326", always_xy=True)

reader = shapefile.Reader("data/taxi_zones.shp")

zones = {}
for rec, shape in zip(reader.records(), reader.shapes()):
    zone_id = rec["LocationID"]
    if zone_id not in zones:
        zones[zone_id] = []

    points = shape.points
    starts = list(shape.parts) + [len(points)]
    for i in range(len(shape.parts)):
        ring = []
        for x, y in points[starts[i]:starts[i + 1]]:
            lon, lat = transformer.transform(x, y)
            ring.append([round(lon, 5), round(lat, 5)])
        zones[zone_id].append([ring])

features = []
for zone_id in zones:
    features.append({
        "type": "Feature",
        "properties": {"LocationID": zone_id},
        "geometry": {"type": "MultiPolygon", "coordinates": zones[zone_id]},
    })

with open("data/zones.geojson", "w") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f)

print("zones written:", len(features))