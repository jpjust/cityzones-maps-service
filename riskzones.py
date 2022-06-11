# encoding:utf-8
"""
Risk Zones classification
Copyright (C) 2022 João Paulo Just Peixoto

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import osmpois
import json
import sys
import os
import random
import numpy

'''
This class contains the methods for calculating zone risks from PoIs
inside a bbox region.

After instantiating an object, use the following methods to calculate
zone risks:

- init_zones_by_polygon(list): select only zones inside the AoI delimited
                               by the polygon in 'list'
- calculate_risk_from_pois(pois): calculate the risk level for each zone
                                  considering every PoI in 'pois'
- set_edus_positions_random: calculate EDUs positiong from risks
'''
class RiskZonesGrid:

    min_num = 10 ** (-10)
    max_num = 10 ** 10

    def __init__(self, left: float, bottom: float, right: float, top: float, zone_size: int, M: int, n_edus:int):
        self.left = left
        self.bottom = bottom
        self.right = right
        self.top = top
        self.width = abs(right - left)
        self.height = abs(top - bottom)
        self.M = M
        self.n_edus = n_edus
        self.edus = {}
        self.zones = []
        self.n_zones_inside = 0
        self.polygons = []

        # Grid setup
        w = self.__calculate_distance({'lat': top, 'lon': left}, {'lat': top, 'lon': right})
        h = self.__calculate_distance({'lat': top, 'lon': left}, {'lat': bottom, 'lon': left})
        self.zone_size = zone_size
        self.grid_x = int(w / zone_size)
        self.grid_y = int(h / zone_size)
        self.zone_center = {'x': self.width / self.grid_x / 2, 'y': self.height / self.grid_y / 2}
        print(f"Grid size: {self.grid_x}x{self.grid_y}")
        self.__init_zones()
    
    '''
    Initialize every zone.
    '''
    def __init_zones(self):
        for j in range(self.grid_y):
            for i in range(self.grid_x):
                zone = {
                    'id': j * self.grid_x + i,
                    'lat': (j / self.grid_y * self.height) + self.bottom + self.zone_center['y'],
                    'lon': (i / self.grid_x * self.width) + self.left + self.zone_center['x'],
                    'risk': 1.0,
                    'RL': 0,
                    'inside': True
                }

                self.zones.append(zone)

        self.n_zones_inside = len(self.zones)
    
    '''
    Check every zone if it is inside the polygon area.
    '''
    def init_zones_by_polygon(self, polygon: dict):
        prog = 0.0
        i = 0
        total = len(self.zones)
        print(f'Checking zones inside the polygon... {prog:.2f}%', end='\r')
        zones_inside = 0

        for coord in polygon:
            self.polygons.append(coord[0])
        
        for zone in self.zones:
            i += 1
            zone['inside'] = False
            for pol in self.polygons:
                if self.__check_zone_in_polygon(zone, pol):
                    zone['inside'] = True
                    zones_inside += 1
                    break
            prog = (i / total) * 100
            print(f'Checking zones inside the polygon... {prog:.2f}%', end='\r')
        
        print(f'\n{zones_inside} zones inside the polygon.')
        self.n_zones_inside = zones_inside

    '''
    Check if a zone is inside a polygon.

    For each zone, trace a line to the right and check how many times it
    intersects a boundary. If the number of intersections if odd, then it is
    inside the polygon.
    '''
    def __check_zone_in_polygon(self, zone: dict, polygon: list) -> bool:
        line1 = {
            'p1': {
                'lon': zone['lon'],
                'lat': zone['lat']
            },
            'p2': {
                'lon': zone['lon'] + 180,
                'lat': zone['lat']
            }
        }

        intersec = 0
        for i in range(len(polygon) - 1):
            line2 = {
                'p1': {
                    'lon': polygon[i][0],
                    'lat': polygon[i][1]
                },
                'p2': {
                    'lon': polygon[i + 1][0],
                    'lat': polygon[i + 1][1]
                }
            }

            # We only need to check the zone against lines at its right and if zone's latitude
            # is between the line's latitudes
            if  (line2['p1']['lon'] >= zone['lon'] or line2['p2']['lon'] >= zone['lon']) and \
               ((line2['p1']['lat'] <= zone['lat'] <= line2['p2']['lat']) or ((line2['p2']['lat'] <= zone['lat'] <= line2['p1']['lat']))):
                if self.__check_intersection(line1, line2):
                    intersec += 1
        
        return intersec % 2 == 1
    
    '''
    Check if line1 and line2 intersects.
    '''
    def __check_intersection(self, line1: dict, line2: dict) -> bool:
        if line2['p1']['lon'] == line2['p2']['lon']:
            a2 = RiskZonesGrid.max_num
        else:
            a2 = (line2['p1']['lat'] - line2['p2']['lat']) / (line2['p1']['lon'] - line2['p2']['lon'])
        b1 = -1
        b2 = -1
        c1 = line1['p1']['lat']
        c2 = line2['p1']['lat'] - a2 * line2['p1']['lon']
        
        f1_1 = numpy.sign(b1 * line2['p1']['lat'] + c1)
        f1_2 = numpy.sign(b1 * line2['p2']['lat'] + c1)
        f2_1 = numpy.sign(a2 * line1['p1']['lon'] + b2 * line1['p1']['lat'] + c2)
        f2_2 = numpy.sign(a2 * line1['p2']['lon'] + b2 * line1['p2']['lat'] + c2)

        return f1_1 != f1_2 and f2_1 != f2_2

    '''
    Calculate the risk perception considering all PoIs.
    '''
    def calculate_risk_from_pois(self, pois: dict):
        prog = 0.0
        i = 0
        total = len(self.zones)
        print(f'Calculating risk perception... {prog:.2f}%', end='\r')

        for zone in self.zones:
            i += 1
            sum = 0
            for poi in pois:
                sum += poi['weight'] / (self.__calculate_distance(zone, poi) ** 2)
            zone['risk'] = 1 / sum

            prog = (i / total) * 100
            print(f'Calculating risk perception... {prog:.2f}%', end='\r')
        
        self.__normalize_risks()
        self.__calculate_RL()
        print('')

    '''
    Calculate the distance from a to b using haversine formula.
    '''
    def __calculate_distance(self, a: dict, b: dict) -> float:
        lat1 = numpy.radians(a['lat'])
        lat2 = numpy.radians(b['lat'])
        lon1 = numpy.radians(a['lon'])
        lon2 = numpy.radians(b['lon'])
        r = 6378137
        return 2 * r * numpy.arcsin(numpy.sqrt(numpy.sin((lat2 - lat1) / 2) ** 2 + numpy.cos(lat1) * numpy.cos(lat2) * numpy.sin((lon2 - lon1) / 2) ** 2))

    '''
    Normalize the risk perception values.
    '''
    def __normalize_risks(self):
        min = max = self.zones[0]['risk']

        for zone in self.zones:
            if zone['risk'] > max: max = zone['risk']
            if zone['risk'] < min: min = zone['risk']
        
        amplitude = max - min

        for zone in self.zones:
            zone['risk'] = (zone['risk'] - min) / amplitude
    
    '''
    Calculate the RL according to risk perception.
    '''
    def __calculate_RL(self):
        for zone in self.zones:
            if zone['risk'] == 0:
                zone['RL'] = 1
            else:
                rl = self.M - numpy.minimum(abs(int(numpy.log10(zone['risk']))), self.M - 1)
                zone['RL'] = int(rl)

    '''
    Sort zones by its risk levels.
    '''
    def sort_zones_by_risk(self):
        self.zones.sort(key=lambda zone : zone['risk'])
    
    '''
    Calculate the number of zones by RL.
    '''
    def __get_number_of_zones_by_RL(self) -> list:
        nzones = {}
        for i in range(1, self.M + 1):
            nzones[i] = 0
        
        for zone in self.zones:
            if zone['inside']:
                nzones[zone['RL']] += 1
        
        return nzones
    
    '''
    Calculate the number of EDUs that must be positioned in each RL.
    
    See paper.
    '''
    def __get_number_of_edus_by_RL(self) -> dict:
        nzones = self.__get_number_of_zones_by_RL()
        
        sum = 0
        for i in range(1, self.M + 1):
            sum += i * nzones[i]

        nedus = {}
        for i in range(1, self.M + 1):
            ni = (self.n_edus * i * nzones[i]) / sum
            nedus[i] = int(ni)

        return nedus

    '''
    Get a dict of zones by RL.
    '''
    def __get_zones_by_RL(self) -> dict:
        zones_by_RL = {}
        for i in range(self.M + 1):
            zones_by_RL[i] = []

        for zone in grid.zones:
            if zone['inside']:
                zones_by_RL[zone['RL']].append(zone)
        
        return zones_by_RL

    '''
    Randomly select zones for EDUs positioning.
    '''
    def set_edus_positions_random(self):
        random.seed()
        zones_by_RL = self.__get_zones_by_RL()
        self.edus = {}
        edus = self.__get_number_of_edus_by_RL()
        
        for i in range(1, self.M + 1):
            self.edus[i] = random.choices(zones_by_RL[i], k=edus[i])

    '''
    Uniformly select zones for EDUs positioning.
    '''
    def set_edus_positions_uniform(self):
        zones_by_RL = self.__get_zones_by_RL()
        self.edus = {}
        edus = self.__get_number_of_edus_by_RL()
        At = Ax = radius = step = start = {}

        for i in range(1, self.M + 1):
            zones_by_RL[i].sort(key=lambda zone : zone['id'])
            At[i] = self.__get_number_of_zones_by_RL()[i]  # Area of the whole RL
            Ax[i] = numpy.ceil(At[i] / edus[i])            # Coverage area of an EDU
            radius[i] = numpy.ceil(numpy.sqrt(Ax[i]) / 2)  # Radius of an EDU
            step[i] = 2 * radius[i] - 1                    # Step distance on x and y directions
            start[i] = int(radius[i] / 2)                  # Start coordinate
            self.edus[i] = []                              # Final list of EDUs in zone i
        
        for x in range(self.grid_x):
            for y in range(self.grid_y):
                id = x * y + x
                zone = self.zones[id]
                if not zone['inside']: continue

                for i in range(1, self.M + 1):
                    if x == y == start[i] or (x % step[i] == 0 and y % step[i] == 0):
                        self.edus[i].append(zone)

'''
Main program.
'''
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Use: {sys.argv[0]} config.json\n")
        print("config.json is a configuration file in JSON format. See examples in conf folder.")
        sys.exit()

    # Config file
    fp = open(sys.argv[1], 'r')
    conf = json.load(fp)
    fp.close()

    grid = RiskZonesGrid(
        conf['left'], conf['bottom'], conf['right'], conf['top'],
        conf['zone_size'], conf['M'], conf['edus']
    )

    # Load cache file if enabled
    cache_filename = f"{os.path.splitext(sys.argv[1])[0]}.cache"
    if conf['cache_zones'] == True and os.path.isfile(cache_filename):
        try:
            print(f"Loading cache file {cache_filename}...")
            fp = open(cache_filename, 'r')
            grid.zones = json.load(fp)
            fp.close()
        except json.JSONDecodeError:
            print("The cache file is corrupted. Delete it and run the program again.")
            sys.exit()

        zones_inside = 0
        for zone in grid.zones:
            if zone['inside']: zones_inside += 1
        grid.n_zones_inside = zones_inside
    else:
        pois = osmpois.extract_pois(conf['pois'], conf['amenities'])

        # GeoJSON file
        fp = open(conf['geojson'], 'r')
        geojson = json.load(fp)
        fp.close()
        grid.init_zones_by_polygon(geojson['features'][0]['geometry']['coordinates'])
        
        # Calculate risks
        grid.calculate_risk_from_pois(pois)

    # Write cache file
    if conf['cache_zones'] == True:
        fp = open(cache_filename, 'w')
        json.dump(grid.zones, fp)
        fp.close()

    # Write a CSV file with risk zones
    row = 0
    data = ''
    data += 'system:index,class,.geo\n'

    for zone in grid.zones:
        if zone['inside']:
            coordinates = f"[{zone['lon']},{zone['lat']}]"
            data += f'{row:020},{zone["RL"]},"{{""type"":""Point"",""coordinates"":{coordinates}}}"\n'
            row += 1

    fp = open(conf['output'], 'w')
    fp.write(data)
    fp.close()
    
    # Write a CSV file with EDUs positioning
    #grid.set_edus_positions_random()
    grid.set_edus_positions_uniform()
    row = 0
    data = ''
    data += 'system:index,.geo\n'

    for i in range(1, grid.M + 1):
        for zone in grid.edus[i]:
            coordinates = f"[{zone['lon']},{zone['lat']}]"
            data += f'{row:020},"{{""type"":""Point"",""coordinates"":{coordinates}}}"\n'
            row += 1

    fp = open(conf['output_edus'], 'w')
    fp.write(data)
    fp.close()

    print("Done.")
