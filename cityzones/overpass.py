# encoding:utf-8
"""
RiskZones classification
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
"""

import requests

API_ENDPOINT = 'https://overpass-api.de/api/interpreter'

def get_osm(bottom: float, left: float, top: float, right: float, request_timeout: int) -> str:
    """
    Query Overpass API and request the OSM from the bounding box specified by the parameters.
    The OSM data will arrive in XML format.
    """
    query = f'''
      nwr({bottom},{left},{top},{right});
      out;
    '''

    res = requests.get(API_ENDPOINT, data=query, timeout=request_timeout)
    return res.content.decode()
