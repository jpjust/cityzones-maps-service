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

def get_osm_from_bbox(filename: str, bottom: float, left: float, top: float, right: float, request_timeout: int) -> str:
    """
    Query Overpass API and request the OSM from the bounding box specified by the parameters.
    The OSM data will arrive in XML format.
    """
    query = f'''
      nwr({bottom},{left},{top},{right});
      out;
    '''

    res = requests.get(API_ENDPOINT, data=query, stream=True, timeout=request_timeout)
    with open(filename, 'wb') as fp:
        for chunk in res.iter_content():
            fp.write(chunk)

    return res.status_code

def get_osm_from_polygon(filename: str, polygon: list, request_timeout: int) -> str:
    """
    Query Overpass API and request the OSM from the polygon specified by the parameters.
    The OSM data will arrive in XML format.
    """
    poly = ''
    for coordinate in polygon:
        poly += f'{coordinate[1]} {coordinate[0]} '
    
    query = f'''
      nwr(poly:"{poly.strip()}");
      out;
    '''

    res = requests.get(API_ENDPOINT, data=query, timeout=request_timeout)
    with open(filename, 'wb') as fp:
        for chunk in res.iter_content():
            fp.write(chunk)

    return res.status_code

def get_osm_from_geojson(filename: str, geo_json: dict, request_timeout: int) -> str:
    """
    Query Overpass API and request the OSM from the coordinates in the GeoJSON specified by the parameters.
    The OSM data will arrive in XML format.
    """
    poly_list = []
    polygons = geo_json['features'][0]['geometry']['coordinates']
    for polygon in polygons:
        poly_list.append(polygon[0])
    
    query = '(\n'
    for polygon in poly_list:
        for coordinate in polygon:
            poly += f'{coordinate[0]} {coordinate[1]} '
        query += f'  nwr(poly:"{poly.strip()}");\n'
    
    query += ')\nout;\n'

    res = requests.get(API_ENDPOINT, data=query, timeout=request_timeout)
    with open(filename, 'wb') as fp:
        for chunk in res.iter_content():
            fp.write(chunk)

    return res.status_code
