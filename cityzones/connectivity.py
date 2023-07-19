# encoding:utf-8
"""
CityZones classification: connectivity layer
Copyright (C) 2023 Thiago C. Jesus, João Paulo Just Peixoto

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

This module contains the functions for calculating Dependable-Quality Connectivity (DPConn)
of the zones.

After creating a grid object, use the following functions to calculate DPConn:
"""

from config import *
from dotenv import dotenv_values
import requests
import json
import utils
import os

# Load current directory .env or default configuration file
CONF_DEFAULT_PATH='/etc/cityzones/maps-service.conf'
if os.path.exists('.env'):
    config = dotenv_values('.env')
elif os.path.exists(CONF_DEFAULT_PATH):
    config = dotenv_values(CONF_DEFAULT_PATH)

API_ENDPOINT = f'{config["API_URL"]}/cells'

def init_zones(grid: dict, params: dict):
    """
    Initialize every zone in the grid and set their DPConn.
    """
    print("Setting zones' DPConn... ", end='')
    
    # Initialize grid structure
    for zone in grid['zones']:
        zone['dpconn'] = 0

    # Calculate the weighted sum of the networks types parameters
    cells = __get_cells_within_bbox(grid['left'], grid['top'], grid['right'], grid['bottom'])
    types = set()

    # Collect types
    for cell in cells:
        types.add(cell['type'])

    # Compute sum_nets
    sum_nets = 0
    for type in types:
        sum_nets += params['weight']['S'] * params[type]['S'] + params['weight']['T'] * params[type]['T'] + params['weight']['R'] * params[type]['R'] - params['weight']['C'] * params[type]['C']

    # Compute DPConn for each cell
    for id in grid['zones_inside']:
        zone = grid['zones'][id]

        sum_coverage = 0
        for cell in cells:
            cell_params = params['weight']['S'] * params[cell['type']]['S'] + params['weight']['T'] * params[cell['type']]['T'] + params['weight']['R'] * params[cell['type']]['R'] - params['weight']['C'] * params[cell['type']]['C']
            sum_coverage += __coverage(zone, cell) * cell_params
        
        zone['dpconn'] = sum_coverage / sum_nets

    print('Done!')

def __coverage(zone: dict, ap: dict):
    """
    Check if zone is within coverage of an Access Point.
    """
    return utils.__calculate_distance(zone, ap) <= ap['range']

def __get_cells_within_bbox(left: float, top: float, right: float, bottom: float) -> list:
    res = requests.get(f'{API_ENDPOINT}/{left}/{top}/{right}/{bottom}', headers={'accept': 'application/json', 'X-API-Key': config["API_KEY"]}, timeout=int(config['NET_TIMEOUT']))

    if res.status_code != 200:
        raise Exception
    
    return json.loads(res.content.decode())
