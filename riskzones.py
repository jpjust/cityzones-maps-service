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
import math
import json
import sys
import random
import numpy

'''
This class contains the methods for calculating zone risks from POIs
inside a bbox region.

After instantiating an object, use the following methods to calculate
zone risks:

- init_zones_by_polygon(list): select only zones inside the polygon delimited
                               by 'list'
- calculate_risk_from_pois(pois): calculate the risk level for each zone
                                  considering every POI in 'pois'
- set_edus_positions_random: calculate EDUs positiong from risks
'''
class RiskZonesGrid:

    min_num = 10 ** (-10)
    max_num = 10 ** 10

    def __init__(self, left: float, bottom: float, right: float, top: float, grid_x: int, grid_y: int, classes: int, n_edus:int):
        self.left = left
        self.bottom = bottom
        self.right = right
        self.top = top
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.width = abs(right - left)
        self.height = abs(top - bottom)
        self.classes = classes
        self.n_edus = n_edus
        self.edus = {}
        self.zones = []
        self.polygons = []
        self.__init_zones()
    
    '''
    Initialize every zone.
    '''
    def __init_zones(self):
        for i in range(self.grid_x):
            for j in range(self.grid_y):
                zone = {
                    'lat': (j / self.grid_y * abs(self.top - self.bottom)) + self.bottom,
                    'lon': (i / self.grid_x * abs(self.right - self.left)) + self.left,
                    'risk': 1.0,
                    'sum': 0.0,
                    'class': 0,
                    'inside': False
                }

                self.zones.append(zone)
    
    '''
    Check every zone if it is inside the polygon area.
    '''
    def init_zones_by_polygon(self, polygon: dict):
        prog = 0.0
        i = 0
        total = len(self.zones)
        print(f'Checking zones inside the polygon... {prog:.2f}%', end='\r')

        for coord in polygon:
            self.polygons.append(coord[0])
        
        for zone in self.zones:
            i += 1
            zone['inside'] = False
            for pol in self.polygons:
                if self.__check_zone_in_polygon(zone, pol):
                    zone['inside'] = True
                    break
            prog = (i / total) * 100
            print(f'Checking zones inside the polygon... {prog:.2f}%', end='\r')
        
        print('')

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
    Calculate the risk level considering all POIs.
    '''
    def calculate_risk_from_pois(self, pois: dict):
        prog = 0.0
        i = 0
        total = len(self.zones)
        print(f'Calculating risk levels... {prog:.2f}%', end='\r')

        for zone in self.zones:
            i += 1
            sum = 0
            for poi in pois:
                sum += 1 / (self.__calculate_distance(zone, poi) ** 2)
            zone['risk'] = 1 / sum

            prog = (i / total) * 100
            print(f'Calculating risk levels... {prog:.2f}%', end='\r')
        
        self.__normalize_risks()
        self.__calculate_classes()
        print('')

    '''
    Calculate the distance from a to b.
    '''
    def __calculate_distance(self, a: dict, b: dict) -> float:
        return math.sqrt((a['lat'] - b['lat']) ** 2 + (a['lon'] - b['lon']) ** 2)

    '''
    Normalize the risk levels.
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
    Calculate the classes according to risk levels.
    '''
    def __calculate_classes(self):
        step = 1 / self.classes

        for zone in self.zones:
            for i in range(self.classes):
                if zone['risk'] <= 10 ** (-i):
                    zone['class'] = self.classes - 1 - i

    '''
    Sort zones by its risk levels.
    '''
    def sort_zones_by_risk(self):
        self.zones.sort(key=lambda zone : zone['risk'])
    
    '''
    Calculate the number of zones by class.
    '''
    def __get_number_of_zones_by_class(self) -> list:
        nzones = []
        for i in range(self.classes):
            nzones.append(0)
        
        for zone in self.zones:
            if zone['inside']:
                nzones[zone['class']] += 1
        
        return nzones
    
    '''
    Calculate the number of EDUs that must be positioned in each class so it
    obeys the proportion of ni = (C - i) * ai
    
    See paper.
    '''
    def __get_number_of_edus_by_class(self, n: int) -> list:
        nzones = self.__get_number_of_zones_by_class()

        nedus = []
        for i in range(self.classes):
            nedus.append((i + 1) * nzones[i])
        
        sum = 0
        for i in nedus:
            sum += i
        
        rel = n / sum
        nedus = list(map(lambda x: int(x * rel), nedus))
       
        return nedus

    '''
    Randomly select zones for EDUs positioning.
    '''
    def set_edus_positions_random(self):
        random.seed()
        zones_by_class = {}
        for i in range(self.classes):
            zones_by_class[i] = []

        for zone in grid.zones:
            if zone['inside']:
                zones_by_class[zone['class']].append(zone)

        self.edus = {}
        edus = self.__get_number_of_edus_by_class(self.n_edus)
        
        for i in range(self.classes):
            self.edus[i] = random.choices(zones_by_class[i], k=edus[i])

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
        conf['grid_x'], conf['grid_y'], conf['classes'], conf['edus']
    )

    pois = osmpois.extract_pois(conf['pois'], conf['amenities'])

    # GeoJSON file
    fp = open(conf['geojson'], 'r')
    geojson = json.load(fp)
    fp.close()
    grid.init_zones_by_polygon(geojson['features'][0]['geometry']['coordinates'])
    
    # Calculate risks
    grid.calculate_risk_from_pois(pois)

    # Write a CSV file with risk zones
    row = 0
    data = ''
    data += 'system:index,class,.geo\n'

    for zone in grid.zones:
        if zone['inside']:
            coordinates = f"[{zone['lon']},{zone['lat']}]"
            data += f'{row:020},{zone["class"]},"{{""type"":""Point"",""coordinates"":{coordinates}}}"\n'
            row += 1

    fp = open(conf['output'], 'w')
    fp.write(data)
    fp.close()
    
    # Write a CSV file with EDUs positioning
    grid.set_edus_positions_random()
    row = 0
    data = ''
    data += 'system:index,.geo\n'

    for i in range(grid.classes):
        for zone in grid.edus[i]:
            coordinates = f"[{zone['lon']},{zone['lat']}]"
            data += f'{row:020},"{{""type"":""Point"",""coordinates"":{coordinates}}}"\n'
            row += 1

    fp = open(conf['output_edus'], 'w')
    fp.write(data)
    fp.close()
