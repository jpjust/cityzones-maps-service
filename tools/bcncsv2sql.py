import sys

TABLE_NAME = 'cells'
BATCH_SIZE = 10000

radios_ids = {
    'GSM': 1,
    'CDMA': 2,
    'UMTS': 3,
    'LTE': 4,
    'NR': 5,
    'Wi-Fi': 6
}

fp = open(sys.argv[1], 'r')
i = 0

for line in fp:
    geo_epgs_4326_x,geo_epgs_4326_y = line.strip().split(',')

    try:
        r = 50
        lat = float(geo_epgs_4326_x)
        lon = float(geo_epgs_4326_y)

        if i % BATCH_SIZE == 0:
            print(';')
            print(f'INSERT INTO `{TABLE_NAME}` VALUES (NULL, ST_GeomFromText("POINT({lon} {lat})"), {r}, {radios_ids["Wi-Fi"]})', end='')
        else:
            print(f', (NULL, ST_GeomFromText("POINT({lon} {lat})"), {r}, {radios_ids["Wi-Fi"]})', end='')
        
        i += 1
    except ValueError:
        pass

fp.close()
print(';')
