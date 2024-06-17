# encoding:utf-8
"""
RiskZones classification
Copyright (C) 2024 João Paulo Just Peixoto

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

from dotenv import dotenv_values
import requests
import time
import json
import os
try:
    from config import *
except ModuleNotFoundError:
    from cityzones.config import *

# Load current directory .env or default configuration file
CONF_DEFAULT_PATH='/etc/cityzones/maps-service.conf'
if os.path.exists('.env'):
    config = dotenv_values('.env')
elif os.path.exists(CONF_DEFAULT_PATH):
    config = dotenv_values(CONF_DEFAULT_PATH)

API_ENDPOINT = 'https://api.mapbox.com/isochrone/v1'

def get_traveltime(lat: float, lon: float, maxtime: int) -> list:
    """
    Get a list of polygons and holes of the area with `maxtime` minutes
    travel time from the specified coordinates.
    """

    res = requests.get(f'{API_ENDPOINT}/mapbox/walking/{lon},{lat}?contours_minutes={maxtime}&polygons=true&access_token={config["MAPBOX_API_KEY"]}', timeout=int(config['NET_TIMEOUT']))

    if res.status_code != 200:
        print(f'STATUS CODE: {res.status_code}')
        raise Exception

    response = json.loads(res.content.decode())
    poligons = []

    for feature in response['features']:
        for polygon in feature['geometry']['coordinates']:
            poligons.append(polygon)
    
    return poligons
