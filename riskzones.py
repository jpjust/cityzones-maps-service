# encoding:utf-8
"""
RiskZones classification
Copyright (C) 2022 - 2023 João Paulo Just Peixoto

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

*******************************************************************************

This module contains the functions for calculating zone risks from PoIs inside
a bbox region.

After creating a grid object, use the following functions to calculate zone
risks:

- init_zones_by_polygon(grid, list): select only zones inside the AoI delimited
                                     by the polygon in 'list'.
- calculate_risk_from_pois(grid, pois): calculate the risk level for each zone
                                        considering every PoI in 'pois'.
- set_edus_positions_*: calculate EDUs positiong from risks using a specific
                        positioning algorithm.
"""

from dotenv import load_dotenv
load_dotenv()

import osmpois
import time
import json
import geojson
import sys
import os
import random
import resource
import numpy
import multiprocessing as mp

# Exception classes.
class OutOfBounds(Exception):
    pass

class SkipZone(Exception):
    pass

# Exit status
EXIT_OK = 0
EXIT_HELP = 1
EXIT_CACHE_CORRUPTED = 2
EXIT_NO_ZONES = 3
EXIT_NO_POIS = 4
EXIT_NO_MEMORY = 5

# Resources limits
RES_MEM_SOFT, RES_MEM_HARD = resource.getrlimit(resource.RLIMIT_DATA)
RES_MEM_SOFT = int(os.getenv('MEM_LIMIT')) * (1024 ** 2) if os.getenv('MEM_LIMIT') != None else 1024 ** 3
resource.setrlimit(resource.RLIMIT_DATA, (RES_MEM_SOFT, RES_MEM_HARD))

# Maximum and minimum values for integers.
MIN_NUM = 10 ** (-10)
MAX_NUM = 10 ** 10

# Positioning modes.
UNBALANCED = 1
BALANCED = 2
RESTRICTED = 3

# Multiprocessing
MP_WORKERS=None  # If None, will use a value returned by the system

def create_riskzones_grid(left: float, bottom: float, right: float, top: float, zone_size: int, M: int, n_edus: int) -> dict:
    """
    Create a riskzones grid object for futher manipulation.
    """
    grid = {
        'left': left,
        'bottom': bottom,
        'right': right,
        'top': top,
        'zone_size': zone_size,
        'width': abs(right - left),
        'height': abs(top - bottom),
        'M': M,
        'n_edus': n_edus,
        'edus': {},
        'polygons': [],
        'pol_points': 0,
        'zones': [],
        'zones_inside': [],
        'pois': [],
        'roads': [],
        'roads_points': 0,
        'polygons': []
    }

    # EDUs lists
    for m in range(1, M + 1):
        grid['edus'][m] = []

    # Grid setup
    w = calculate_distance({'lat': top, 'lon': left}, {'lat': top, 'lon': right})
    h = calculate_distance({'lat': top, 'lon': left}, {'lat': bottom, 'lon': left})
    grid['grid_x'] = int(w / zone_size)
    grid['grid_y'] = int(h / zone_size)
    grid['zone_center'] = {'x': grid['width'] / grid['grid_x'] / 2, 'y': grid['height'] / grid['grid_y'] / 2}
    print(f'Grid size: {grid["grid_x"]}x{grid["grid_y"]}')

    return grid

def calculate_distance(a: dict, b: dict) -> float:
    """
    Calculate the distance from a to b using haversine formula.
    """
    lat1 = numpy.radians(a['lat'])
    lat2 = numpy.radians(b['lat'])
    lon1 = numpy.radians(a['lon'])
    lon2 = numpy.radians(b['lon'])
    r = 6378137
    return 2 * r * numpy.arcsin(numpy.sqrt(numpy.sin((lat2 - lat1) / 2) ** 2 + numpy.cos(lat1) * numpy.cos(lat2) * numpy.sin((lon2 - lon1) / 2) ** 2))

def calculate_distance_in_grid(grid: dict, a: dict, b: dict) -> int:
    """
    Calculate the distance from a to b in the grid.
    """
    x1 = a['id'] % grid['grid_x']
    x2 = b['id'] % grid['grid_x']
    y1 = int(a['id'] / grid['grid_x'])
    y2 = int(b['id'] / grid['grid_x'])
    return numpy.sqrt(abs(x2 - x1) ** 2 + abs(y2 - y1) ** 2)

def init_zones(grid: dict):
    """
    Initialize every zone in the grid.
    """
    print('Initializing data structure for zones... ', end='')
    try:
        grid['zones'].clear()
        grid['zones_inside'].clear()

        for j in range(grid['grid_y']):
            for i in range(grid['grid_x']):
                zone = {
                    'id': j * grid['grid_x'] + i,
                    'lat': (j / grid['grid_y'] * grid['height']) + grid['bottom'] + grid['zone_center']['y'],
                    'lon': (i / grid['grid_x'] * grid['width']) + grid['left'] + grid['zone_center']['x'],
                    'risk': 1.0,
                    'RL': grid['M'],
                    'inside': True,
                    'has_edu': False,
                    'is_road': False
                }

                grid['zones'].append(zone)
                grid['zones_inside'].append(zone['id'])

    except MemoryError:
        print('--- Memory limit reached! ---')
        print(f'riskzones is configured to use at most {RES_MEM_SOFT} bytes of memory.')
        print('If you think this limit is too low, you can raise it by setting the value of RES_MEM_SOFT in this script.')
        exit(EXIT_NO_MEMORY)
    
    print('Done!')

def load_zones(grid: dict, zones: list):
    """
    Load zones from JSON data.
    """
    grid['zones'].clear()
    grid['zones_inside'].clear()

    grid['zones'] = zones
    grid['zones'].sort(key=lambda zone : zone['id'])

    for zone in grid['zones']:
        if zone['inside']:
            grid['zones_inside'].append(zone['id'])

def add_polygon(grid: dict, polygons: list):
    """
    Add the polygons in the list into the grid.
    """
    grid['polygons'].clear()
    grid['pol_points'] = 0
    for polygon in polygons:
        grid['polygons'].append(polygon)
        grid['pol_points'] += len(polygon)

def init_zones_by_polygon(grid: dict):
    """
    Check every zone if it is inside the polygon area.
    """
    print('Checking zones inside the polygon... ', end='')

    grid['zones_inside'].clear()
    
    with mp.Pool(processes=MP_WORKERS) as pool:
        payload = []
        for zone in grid['zones']:
            payload.append((zone, grid['polygons']))
        grid['zones'] = pool.starmap(check_zone_in_polygon_set, payload)
    
    for zone in grid['zones']:
        if zone['inside'] == True:
            grid['zones_inside'].append(zone['id'])

    print('Done!')
    print(f'{len(grid["zones_inside"])} of {len(grid["zones"])} zones inside the polygon.')

def init_pois_by_polygon(grid: dict, pois: list) -> list:
    """
    Check every PoI if it is inside the polygon area.
    """
    print(f'Checking PoIs inside the polygon... ', end='')

    grid['pois'].clear()
    pois_results = []
    
    with mp.Pool(processes=MP_WORKERS) as pool:
        payload = []
        for poi in pois:
            payload.append((poi, grid['polygons']))
        pois_results = pool.starmap(check_zone_in_polygon_set, payload)
    
    for poi in pois_results:
        if poi['inside'] == True:
            grid['pois'].append(poi)

    print('Done!')
    print(f'{len(grid["pois"])} of {len(pois)} PoIs inside the polygon.')

def check_zone_in_polygon_set(zone: dict, polygons: dict) -> bool:
    """
    Check a zone is inside any polygon in a polygons set.
    """
    zone['inside'] = False
    for pol in polygons:
        if check_zone_in_polygon(zone, pol):
            zone['inside'] = True
            break

    return zone

def check_zone_in_polygon(zone: dict, polygon: list) -> bool:
    """
    Check if a zone is inside a polygon.
    """
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
    for i in range(-1, len(polygon) - 1):
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
            if check_intersection(line1, line2):
                intersec += 1
    
    return intersec % 2 == 1

def check_intersection(line1: dict, line2: dict) -> bool:
    """
    Check if line1 and line2 intersects.
    """
    if line2['p1']['lon'] == line2['p2']['lon']:
        a2 = MAX_NUM
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

def add_roads(grid: dict, roads: list):
    """
    Add roads to zones list.
    """
    for road in roads:
        # Ignore points outside the grid
        if road['start']['lat'] < grid['bottom'] or road['start']['lat'] > grid['top'] \
           or road['end']['lat'] < grid['bottom'] or road['end']['lat'] > grid['top'] \
           or road['start']['lon'] < grid['left'] or road['start']['lon'] > grid['right'] \
           or road['end']['lon'] < grid['left'] or road['end']['lon'] > grid['right']:
           continue

        a = coordinates_to_id(grid, road['start']['lat'], road['start']['lon'])
        b = coordinates_to_id(grid, road['end']['lat'], road['end']['lon'])

        if a < 0 or b < 0 or a >= len(grid['zones']) or b >= len(grid['zones']):
            continue
        
        # Select the movement approach
        dist_x = b % grid['grid_x'] - a % grid['grid_x']
        dist_y = int(b / grid['grid_x']) - int(a / grid['grid_x'])

        if abs(dist_x) >= abs(dist_y):
            move_zones_x(grid, a, b, dist_x, dist_y)
        else:
            move_zones_y(grid, a, b, dist_x, dist_y)

        grid['zones'][a]['is_road'] = grid['zones'][b]['is_road'] = True
    
    # Count road zones
    for zone in grid['zones']:
        if zone['is_road']:
            grid['roads_points'] += 1

def coordinates_to_id(grid: dict, lat, lon):
    """
    Calculate the zone ID from its coordinates.
    """
    prop_x = (lon - grid['left']) / abs(grid['width'])
    prop_y = (lat - grid['bottom']) / abs(grid['height'])
    pos_x = int(prop_x * grid['grid_x'])
    pos_y = int(prop_y * grid['grid_y'])
    return pos_y * grid['grid_x'] + pos_x

def move_zones_x(grid: dict, a: dict, b: dict, dist_x: int, dist_y: int):
    """
    Move through road in X axis
    """
    if dist_x == 0:
        return

    # Calculate movement steps
    if dist_y > 0:
        step_y = (dist_y + 1) / (abs(dist_x) + 1)
    else:
        step_y = (dist_y - 1) / (abs(dist_x) + 1)
    delta_y = 0.0
    id = a
    num_x = int(dist_x / abs(dist_x))
    if dist_y != 0:
        num_y = grid['grid_x'] * (int(dist_y / abs(dist_y)))
    else:
        num_y = 0
    
    # While getting near to the destination zone, keep moving.
    # If we start to get far, stop!
    prev_dist = dist = calculate_distance(grid['zones'][id], grid['zones'][b])
    while dist <= prev_dist:
        id += num_x
        delta_y = delta_y + step_y
        if abs(delta_y) >= 1:
            id += num_y
            delta_y -= int(delta_y / abs(delta_y))

        if id < 0 or id > len(grid['zones']):
            break

        try:
            grid['zones'][id]['is_road'] = True

            # Update distance
            prev_dist = dist
            dist = calculate_distance(grid['zones'][id], grid['zones'][b])
        except IndexError:
            break
    
def move_zones_y(grid: dict, a: dict, b: dict, dist_x: int, dist_y: int):
    """
    Move through road in Y axis
    """
    if dist_y == 0:
        return

    # Calculate movement steps
    if dist_x > 0:
        step_x = (dist_x + 1) / (abs(dist_y) + 1)
    else:
        step_x = (dist_x - 1) / (abs(dist_y) + 1)
    delta_x = 0.0
    id = a
    if dist_x != 0:
        num_x = int(dist_x / abs(dist_x))
    else:
        num_x = 0
    num_y = grid['grid_x'] * (int(dist_y / abs(dist_y)))

    # While getting near to the destination zone, keep moving.
    # If we start to get far, stop!
    prev_dist = dist = calculate_distance(grid['zones'][id], grid['zones'][b])
    while dist <= prev_dist:
        id += num_y
        delta_x = delta_x + step_x
        if abs(delta_x) >= 1:
            id += num_x
            delta_x -= int(delta_x / abs(delta_x))
        
        if id < 0 or id > len(grid['zones']):
            break

        try:
            grid['zones'][id]['is_road'] = True

            # Update distance
            prev_dist = dist
            dist = calculate_distance(grid['zones'][id], grid['zones'][b])
        except IndexError:
            break

def calculate_risk_from_pois(grid: dict):
    """
    Calculate the risk perception considering all PoIs.
    """
    if len(grid['pois']) == 0:
        return

    print(f'Calculating risk perception... ', end='')

    with mp.Pool(processes=MP_WORKERS) as pool:
        payload = []
        for id in grid['zones_inside']:
            payload.append((grid['zones'][id], grid['pois']))
        risks = pool.starmap(calculate_risk_of_zone, payload)
    
    for risk in risks:
        grid['zones'][risk[0]]['risk'] = risk[1]

    normalize_risks(grid)
    calculate_RL(grid)

    print('Done!')

def calculate_risk_of_zone(zone: dict, pois: list) -> float:
    """
    Calculate the risk perception considering all PoIs.
    """
    sum = 0

    for poi in pois:
        sum += poi['weight'] / (calculate_distance(zone, poi) ** 2)

    return (zone['id'], 1 / sum)

def normalize_risks(grid: dict):
    """
    Normalize the risk perception values.
    """
    min = max = grid['zones'][grid['zones_inside'][0]]['risk']

    for id in grid['zones_inside']:
        if grid['zones'][id]['risk'] > max: max = grid['zones'][id]['risk']
        if grid['zones'][id]['risk'] < min: min = grid['zones'][id]['risk']
    
    amplitude = max - min
    if amplitude == 0:
        amplitude = 1

    for id in grid['zones_inside']:
        grid['zones'][id]['risk'] = (grid['zones'][id]['risk'] - min) / amplitude
    
def calculate_RL(grid: dict):
    """
    Calculate the RL according to risk perception.
    """
    for id in grid['zones_inside']:
        if grid['zones'][id]['risk'] == 0:
            grid['zones'][id]['RL'] = 1
        else:
            rl = grid['M'] - numpy.minimum(abs(int(numpy.log(grid['zones'][id]['risk']))), grid['M'] - 1)
            grid['zones'][id]['RL'] = int(rl)

def get_number_of_zones_by_RL(grid: dict) -> dict:
    """
    Calculate the number of zones by RL.
    """
    nzones = {}
    for i in range(1, grid['M'] + 1):
        nzones[i] = 0
    
    for id in grid['zones_inside']:
        nzones[grid['zones'][id]['RL']] += 1
    
    return nzones
    
def get_number_of_edus_by_RL(grid: dict, n_edus: int) -> dict:
    """
    Calculate the number of EDUs that must be positioned in each RL.
    """
    nzones = get_number_of_zones_by_RL(grid)
    
    sum = 0
    for i in range(1, grid['M'] + 1):
        sum += i * nzones[i]

    nedus = {}
    for i in range(1, grid['M'] + 1):
        ni = (n_edus * i * nzones[i]) / sum
        nedus[i] = int(ni)

    return nedus

def get_zones_by_RL(grid: dict) -> dict:
    """
    Get a dict of zones by RL.
    """
    zones_by_RL = {}
    for i in range(grid['M'] + 1):
        zones_by_RL[i] = []

    for id in grid['zones_inside']:
        zones_by_RL[grid['zones'][id]['RL']].append(grid['zones'][id])
    
    return zones_by_RL

def set_edus_positions_random(grid: dict):
    """
    Randomly select zones for EDUs positioning.
    """
    random.seed()
    zones_by_RL = get_zones_by_RL(grid)
    grid['edus'] = {}
    edus = get_number_of_edus_by_RL(grid, grid['n_edus'])
    
    for i in range(1, grid['M'] + 1):
        grid['edus'][i] = random.choices(zones_by_RL[i], k=edus[i])

def reset_edus_flag(grid: dict, n_edus=None):
    """
    Reset EDUs flag.
    """
    for zone in grid['zones']:
        zone['has_edu'] = False
    
    grid['edus'] = {}
    for i in range(1, grid['M'] + 1):
        grid['edus'][i] = []                                            # Final list of EDUs in zone i

def reset_edus_data(grid: dict, n_edus=None):
    """
    Reset EDUs data to prepare them for a positioning algorithm.
    """
    if n_edus == None:
        n_edus = grid['n_edus']
    edus = get_number_of_edus_by_RL(grid, n_edus)
    grid['At'] = {}
    grid['Ax'] = {}
    grid['radius'] = {}
    grid['step'] = {}
    grid['step_x'] = {}
    grid['step_y'] = {}
    grid['zone_in_y'] = {}
    grid['min_dist'] = {}

    for i in range(1, grid['M'] + 1):
        if edus[i] == 0:
            edus[i] = 1
        grid['At'][i] = get_number_of_zones_by_RL(grid)[i]              # Area of the whole RL
        grid['Ax'][i] = numpy.round(grid['At'][i] / edus[i])            # Coverage area of an EDU
        grid['radius'][i] = numpy.sqrt(grid['Ax'][i]) / 2               # Radius of an EDU
        grid['step'][i] = int(2 * grid['radius'][i] + 1)                # Step distance on x and y directions
        grid['step_x'][i] = grid['step_y'][i] = 0                       # The steps are accounted individually for each RL
        grid['zone_in_y'][i] = False                                    # To check if there was any zone for a RL in any y
        grid['min_dist'][i] = 2 * grid['radius'][i] + 1                 # Minimum distance an EDU must have from another in this RL
    grid['smallest_radius'] = grid['radius'][grid['M']]                 # Radius of the highest level
    grid['highest_radius'] = grid['radius'][1]                          # Radius of the lowest level
    grid['search_range'] = -int(numpy.ceil(2 * grid['grid_x'] / grid['smallest_radius']))
    
    # Make sure there are no 0 radius
    if grid['smallest_radius'] == 0: grid['smallest_radius'] = 1
    if grid['highest_radius'] == 0: grid['highest_radius'] = 1

    grid['zones'].sort(key=lambda zone : zone['id'])

def set_edus_positions_uniform(grid, mode: int):
    """
    Uniformly select zones for EDUs positioning.
    """
    reset_edus_flag(grid)
    reset_edus_data(grid)
    
    print('Positioning EDUs...', end='\r')

    if mode == UNBALANCED:
        set_edus_positions_uniform_unbalanced(grid)
    elif mode == BALANCED:
        set_edus_positions_uniform_balanced(grid)
    elif mode == RESTRICTED:
        set_edus_positions_uniform_restricted(grid)
    
    print('Positioning EDUs... 100.00%')
        
def set_edus_positions_uniform_unbalanced(grid):
    """
    Unbalanced positioning mode.
    """
    print('Chosen positioning method: uniform unbalanced.')
    for y in range(grid['grid_y']):
        # First, reset step for every RL in x direction and check if there was any zone in y
        for i in range(1, grid['M'] + 1):
            grid['step_x'][i] = 0
            if grid['zone_in_y'][i]:
                grid['step_y'][i] += 1
                grid['zone_in_y'][i] = False

        # For each zone in this row, check if it is inside AoI and check if it is time to
        # put an EDU in it
        for x in range(grid['grid_x']):
            id = grid['grid_x'] * y + x
            zone = grid['zones'][id]
            if not zone['inside']: continue

            for i in range(1, grid['M'] + 1):
                if zone['RL'] != i: continue
                grid['zone_in_y'][i] = True  # If there was any zone for this RL in this y, we can increment step_y later

                if grid['step_x'][i] % grid['step'][i] == 0 and grid['step_y'][i] % grid['step'][i] == 0:
                    grid['edus'][i].append(zone)
                    
                grid['step_x'][i] += 1

                prog = (id / len(grid['zones'])) * 100
                print(f'Positioning EDUs... {prog:.2f}%', end='\r')
    
def set_edus_positions_uniform_balanced(grid: dict):
    """
    Balanced positioning mode.
    """
    print('Chosen positioning method: uniform balanced.')
    y = int(grid['smallest_radius'])
    while y < grid['grid_y']:
        x = 0
        try:
            while x < grid['grid_x']:
                while True:
                    # Get the zone in this coordinate by its ID
                    id = grid['grid_x'] * y + x
                    zone = grid['zones'][id]

                    # The zone must be inside the AoI, otherwise, check the next zone
                    if zone['inside']:
                        break
                    elif x >= grid['grid_x']:
                        raise OutOfBounds
                    else:
                        x += 1

                try:
                    # Don't even try if we are still within the range of another EDU
                    for i in range(1, grid['M'] + 1):
                        for edu in grid['edus'][i][-1:grid['search_range']:-1]:
                            dist = calculate_distance_in_grid(grid, zone, edu)
                            if dist < grid['min_dist'][zone['RL']]:
                                raise SkipZone

                    zone['has_edu'] = True
                    grid['edus'][zone['RL']].append(zone)
                    x += int(grid['smallest_radius'] * 2)
                
                except SkipZone:
                    x += 1
            
                prog = (id / len(grid['zones'])) * 100
                print(f'Positioning EDUs... {prog:.2f}%', end='\r')

        except IndexError:
            pass
        except OutOfBounds:
            pass
        
        y += 1

def set_edus_positions_uniform_restricted(grid: dict):
    """
    Restricted positioning mode.
    """
    print('Moving EDUs to permitted zones...')

    final_edus = {}
    for i in range(1, grid['M'] + 1):
        final_edus[i] = []

    edus_total = 0
    edus_remaining = grid['n_edus'] - edus_total
    n_run = 0

    # Repeat until all EDUs are positioned
    while edus_remaining > 0:
        print(f"\n> Run #{n_run}, {edus_remaining} EDUs left.")

        reset_edus_flag(grid)
        reset_edus_data(grid, edus_remaining)
        set_edus_positions_uniform_balanced(grid)
        n_run += 1

        # For each EDU check if it is in a permitted zone (only roads for now).
        # If not, move it to the nearest permitted zone.
        for i in range(1, grid['M'] + 1):
            zones_removal = []

            for zone in grid['edus'][i]:
                if zone['is_road']: continue

                # Mark the zone for EDU removal (it is not a road)
                zone_id = zone['id']
                zones_removal.append(zone)
                zone['has_edu'] = False

                # Find another zone within the RL radius to place the EDU
                spiral_path = get_spiral_path(grid, grid['radius'][i])
                for step in spiral_path:
                    zone_id += step
                    try:
                        nearby_zone = grid['zones'][zone_id]
                        if not nearby_zone['inside']: continue
                        if not nearby_zone['is_road']: continue
                        if nearby_zone['has_edu']: continue
                        if nearby_zone in final_edus[i]: continue

                        nearby_zone['has_edu'] = True
                        grid['edus'][i].append(nearby_zone)
                        break
                    except IndexError:
                        continue
        
            # Remove from grid['edus'] all zones that have been marked for removal
            for zone in zones_removal:
                grid['edus'][i].remove(zone)
            
        # Move all the positioned EDUs to the final structure
        for i in range(1, grid['M'] + 1):
            final_edus[i].extend(grid['edus'][i])
            grid['edus'][i] = []

        # Recalculate the total and remaining
        edus_total = 0
        for i in range(1, grid['M'] + 1):
            edus_total += len(final_edus[i])
        edus_remaining = grid['n_edus'] - edus_total
    
    # Positioning finished. Move final_edus to grid
    for i in range(1, grid['M'] + 1):
        grid['edus'][i] = [*final_edus[i]]

def get_spiral_path(grid: dict, range_radius: int) -> list:
    """
    Compute a spiral path for zone search whithin a range.
    """
    steps = []
    step = -1

    while True:
        step_signal = int(step / abs(step))
        for s in range(0, step, step_signal):
            steps.append(step_signal * grid['grid_x'])
        for s in range(0, step, step_signal):
            steps.append(step_signal)
        step += step_signal
        step *= -1
        if abs(step) > range_radius:
            break

    return steps

def get_zones_in_area(grid: dict, center_id: int, radius: int) -> list:
    """
    Get all zones within a squared area.
    """
    center_x = int(center_id % grid['grid_x'])
    center_y = int(center_id / grid['grid_x'])
    zones = []

    for i in range(center_y - radius, center_y + radius + 1):
        if i < 0: continue
        if i >= grid['grid_y']: break

        for j in range(center_x - radius, center_x + radius + 1):
            if j < 0: continue
            if j >= grid['grid_x']: break

            zones.append(grid['zones'][i * grid['grid_x'] + j])
    
    zones.sort(key=lambda zone : zone['id'])
    return zones

if __name__ == '__main__':
    """
    Main program.
    """
    if len(sys.argv) < 2:
        print(f'Use: {sys.argv[0]} config.json\n')
        print('config.json is a configuration file in JSON format. See examples in conf folder.')
        sys.exit(EXIT_HELP)

    # Python multiprocessing start method
    mp.set_start_method('spawn')

    # Config file
    fp = open(sys.argv[1], 'r')
    conf = json.load(fp)
    fp.close()

    # Create a new grid and initialize its zones
    grid = create_riskzones_grid(
        conf['left'], conf['bottom'], conf['right'], conf['top'],
        conf['zone_size'], conf['M'], conf['edus']
    )
    init_zones(grid)

    # Get PoIs and roads from OSM file
    pois, roads = osmpois.extract_pois(conf['pois'], conf['pois_types'])

    # Load cache file if enabled
    cache_filename = f'{os.path.splitext(sys.argv[1])[0]}.cache'
    if conf['cache_zones'] == True and os.path.isfile(cache_filename):
        try:
            print(f'Loading cache file {cache_filename}...')
            fp = open(cache_filename, 'r')
            load_zones(grid, json.load(fp))
            fp.close()
        except json.JSONDecodeError:
            print('The cache file is corrupted. Delete it and run the program again.')
            exit(EXIT_CACHE_CORRUPTED)
    else:
        # GeoJSON file
        try:
            fp = open(conf['geojson'], 'r')
            geojson_collection = geojson.load(fp)
            fp.close()

            polygons = []
            if geojson_collection.type == 'FeatureCollection':
                if geojson_collection.features[0].geometry.type == 'Polygon':
                    polygons.append(geojson_collection.features[0].geometry.coordinates[0])
                elif geojson_collection.features[0].geometry.type == 'MultiPolygon':
                    polygons = geojson_collection.features[0].geometry.coordinates[0]

            add_polygon(grid, polygons)
            print(f'{grid["pol_points"]} points form the AoI polygon.')

            time_begin = time.perf_counter()
            init_zones_by_polygon(grid)
            if len(grid['zones_inside']) == 0:
                print('No zones to classify!')
                exit(EXIT_NO_ZONES)

            init_pois_by_polygon(grid, pois)
            if len(grid['pois']) == 0:
                print('No PoIs inside the AoI!')
                exit(EXIT_NO_POIS)
        except KeyError:
            print('WARNING: No GeoJSON file specified. Not filtering by AoI polygon.')
            grid['pois'] = pois
        except FileNotFoundError:
            print(f'WARNING: GeoJSON file {conf["geojson"]} not found. Not filtering by AoI polygon.')
            grid['pois'] = pois

        # Calculate risks
        calculate_risk_from_pois(grid)

        # Output elapsed time
        time_classification = time.perf_counter() - time_begin
        print(f'Classification time: {round(time_classification, 3)} seconds.')

    # Write cache file
    if conf['cache_zones'] == True and not os.path.isfile(cache_filename):
        print('Writing cache file... ', end='')
        fp = open(cache_filename, 'w')
        json.dump(grid['zones'], fp)
        fp.close()
        print('Done!')

    # Run EDUs positioning algorithm
    time_begin = time.perf_counter()

    add_roads(grid, roads)
    print(f'{grid["roads_points"]} allowed zones.')

    if conf['edu_alg'] == 'random':
        set_edus_positions_random(grid)
    elif conf['edu_alg'] == 'balanced':
        set_edus_positions_uniform(grid, UNBALANCED)
    elif conf['edu_alg'] == 'enhanced':
        set_edus_positions_uniform(grid, BALANCED)
    elif conf['edu_alg'] == 'restricted':
        set_edus_positions_uniform(grid, RESTRICTED)

    # Output elapsed time
    time_positioning = time.perf_counter() - time_begin
    print(f'Positioning time: {round(time_positioning, 3)} seconds.')

    print('Writing output CSV files... ', end='')

    # Write a JSON file with results data
    if 'res_data' in conf.keys():
        n_edus = 0
        for i in range(1, grid['M'] + 1):
            n_edus += len(grid['edus'][i])

        res_data = {
            'n_zones': len(grid['zones_inside']),
            'n_pois': len(grid['pois']),
            'n_edus': n_edus,
            'time_classification': time_classification,
            'time_positioning': time_positioning
        }

        fp = open(conf['res_data'], 'w')
        json.dump(res_data, fp)
        fp.close()

    # Write a CSV file with risk zones
    row = 0
    data = 'system:index,class,.geo\n'
    grid['zones_inside'].sort()

    for id in grid['zones_inside']:
        coordinates = f'[{grid["zones"][id]["lon"]},{grid["zones"][id]["lat"]}]'
        data += f'{row:020},{grid["zones"][id]["RL"]},"{{""type"":""Point"",""coordinates"":{coordinates}}}"\n'
        row += 1

    fp = open(conf['output'], 'w')
    fp.write(data)
    fp.close()
    
    # Write a CSV file with EDUs positions
    if 'output_edus' in conf.keys():
        row = 0
        data = 'system:index,.geo\n'

        for i in range(1, grid['M'] + 1):
            for zone in grid['edus'][i]:
                coordinates = f'[{zone["lon"]},{zone["lat"]}]'
                data += f'{row:020},"{{""type"":""Point"",""coordinates"":{coordinates}}}"\n'
                row += 1

        fp = open(conf['output_edus'], 'w')
        fp.write(data)
        fp.close()

    # Write a CSV file with forbidden zones
    if 'output_roads' in conf.keys():
        row = 0
        data = 'system:index,.geo\n'

        for id in grid['zones_inside']:
            zone = grid['zones'][id]
            if zone['is_road']:
                coordinates = f'[{zone["lon"]},{zone["lat"]}]'
                data += f'{row:020},"{{""type"":""Point"",""coordinates"":{coordinates}}}"\n'
                row += 1

        fp = open(conf['output_roads'], 'w')
        fp.write(data)
        fp.close()

    print('Done.')
    exit(EXIT_OK)
