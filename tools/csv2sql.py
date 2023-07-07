# To select cells inside a polygon:
#
# SELECT id,ST_AsText(coord) FROM `cells` WHERE MBRContains(ST_GeomFromText('Polygon((-39.088252 -13.379074, -39.089363 -13.341446, -39.046233 -13.342497, -39.044822 -13.384983, -39.088252 -13.379074))'), coord);

import sys

TABLE_NAME = 'cells'
BATCH_SIZE = 1000

fp = open(sys.argv[1], 'r')
i = 0

for line in fp:
    radio, mcc, net, area, cell, unit, lon, lat, r, samples, changeable, created, updated, averageSignal = line.strip().split(',')

    try:
        r = int(r)
        if r == 0:
            # Let's discard no range cells
            continue

        lat = float(lat)
        lon = float(lon)

        if i % BATCH_SIZE == 0:
            print(';')
            print(f'INSERT INTO `{TABLE_NAME}` VALUES (NULL, ST_GeomFromText("POINT({lon} {lat})"), {r}, 1)', end='')
        else:
            print(f', (NULL, ST_GeomFromText("POINT({lon} {lat})"), {r}, 1)', end='')
        
        i += 1
    except ValueError:
        pass

fp.close()
print(';')
