# encoding:utf-8
"""
CityZones classification: rivers layer
Copyright (C) 2023 João Paulo Just Peixoto

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

This module contains the functions for calculating emergency risk regarding
the presence of rivers

After creating a grid object, use the following functions to calculate zone
risks:

- riversrisk.init_zones(grid)
"""

from dotenv import dotenv_values
import math
import os
import multiprocessing as mp
try:
    from config import *
    import utils
except ModuleNotFoundError:
    from cityzones.config import *
    from cityzones import utils

# Load current directory .env or default configuration file
CONF_DEFAULT_PATH='/etc/cityzones/maps-service.conf'
if os.path.exists('.env'):
    config = dotenv_values('.env')
elif os.path.exists(CONF_DEFAULT_PATH):
    config = dotenv_values(CONF_DEFAULT_PATH)

MP_WORKERS=None

def init_zones(grid: dict):
    """
    Initialize every zone in the grid and set their distance to a river.
    """
    print("Setting zones' river distance... ", end='')
    
    # Initialize grid structure
    for zone in grid['zones']:
        zone['river_dist'] = math.inf
        zone['hrdiff'] = 0

    # Collect all zones that are marked as a river zone
    river_zones_ids = []
    for zone in grid['zones']:
        if zone['is_river']:
            river_zones_ids.append(zone['id'])

    # Check all zones against all rivers data
    with mp.Pool(processes=MP_WORKERS) as pool:
        payload = []
        for zone in grid['zones']:
            payload.append((grid, zone, river_zones_ids))
        dists = pool.starmap(__get_distance_from_river, payload)
    
    for res in dists:
        grid['zones'][res[0]]['river_dist'] = res[1]
        grid['zones'][res[0]]['hrdiff'] = res[2]

    print('Done!')

def __get_distance_from_river(grid: dict, zone: dict, rivers: list):
    """
    Get the distance of a zone from the nearest river.
    """
    distance = math.inf
    hdiff = 0
    for id in rivers:
        zone_dist = utils.__calculate_distance_in_grid(grid, zone, grid['zones'][id])
        if zone_dist < distance:
            distance = zone_dist
            hdiff = zone['elevation'] - grid['zones'][id]['elevation']

    return (zone['id'], distance, hdiff)
