# encoding:utf-8
"""
CityZones classification: elevation layer
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

This module contains the functions for calculating emergency risk from land
elevation.

After creating a grid object, use the following functions to calculate zone
risks:

- elevation.init_zones(grid)
"""

from config import *
import multiprocessing as mp
import requests
import json

API_ENDPOINT = 'https://api.open-elevation.com/api/v1/lookup'
COORD_SET_SIZE = 500

def init_zones(grid: dict):
    """
    Initialize every zone in the grid and set their elevation.
    """
    print("Setting zones' elevation... ", end='')
    
    # Initialize grid structure
    for zone in grid['zones']:
        zone['elevation'] = 0

    # Collect all coordinates
    coord_set = []
    coord = []

    for id in grid['zones_inside']:
        zone = grid['zones'][id]
        coord.append({
            'latitude': zone['lat'],
            'longitude': zone['lon']
        })

        # If the coord list is full, append it to the set and create a new one for the next set
        if len(coord) == COORD_SET_SIZE:
            coord_set.append(coord)
            coord = []

    # Make a request for each set
    zone_start = 0
    for coord in coord_set:
        request = {
            'locations': coord
        }
        res = requests.post(API_ENDPOINT, data=json.dumps(request), headers={'Content-Type': 'application/json'}, timeout=60)

        if res.status_code != 200:
            raise Exception
        
        elevations = json.loads(res.content.decode())

        # Set the elevations
        zone_end = zone_start + len(elevations['results'])
        i = 0
        for id in grid['zones_inside'][zone_start:zone_end]:
            zone = grid['zones'][id]
            zone['elevation'] = elevations['results'][i]['elevation']
            i += 1
        
        zone_start = zone_end

    print('Done!')
