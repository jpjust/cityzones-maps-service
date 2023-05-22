import sys
import json

FILEPATH = '/home/just/Downloads/GeoJSON/portugal_full.geojson'

fp = open(FILEPATH, 'r')
geojson = json.load(fp)
fp.close()

for feature in geojson['features']:
    cidade = feature['properties']['NAME_2']
    coordenadas = feature['geometry']

    fp = open(f'{cidade}.geojson', 'w')
    output = {
        "type": "FeatureCollection",
        "name": cidade,
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        },
        "features": [{
            "type": "Feature",
            "properties": {
                "NAME_1": cidade
            },
            "geometry": coordenadas
        }]
    }
    json.dump(output, fp)
    fp.close()
    #sys.exit()
