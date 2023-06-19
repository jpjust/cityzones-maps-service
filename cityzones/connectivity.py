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
import multiprocessing as mp
import requests
import json
import utils
import os

def init_zones(grid: dict, nets: list, aps: list, weight: dict):
    """
    Initialize every zone in the grid and set their DPConn.
    """
    print("Setting zones' DPConn... ", end='')
    
    # Initialize grid structure
    for zone in grid['zones']:
        zone['dpconn'] = 0

    # Calculate the weighted sum of the networks types parameters
    sum_nets = 0
    for net in nets:
        sum_nets += weight['S'] * net['s'] + weight['T'] * net['t'] + weight['R'] * net['r'] - weight['C'] * net['c']

    for id in grid['zones_inside']:
        zone = grid['zones'][id]

        sum_coverage = 0
        for ap in aps:
            sum_coverage += __coverage(zone, ap) * (weight['S'] * ap['s'] + weight['T'] * ap['t'] + weight['R'] * ap['r'] - weight['C'] * ap['c'])
        
        zone['dpconn'] = sum_coverage / sum_nets

    print('Done!')

def __coverage(zone: dict, ap: dict):
    """
    Check if zone is within coverage of an Access Point.
    """
    return utils.__calculate_distance(zone, ap) <= ap['range']

def __index_cell_list_file(in_file: str, out_file: str):
    """
    Create an index from the original OpenCellID file.
    """
    fp_in = open(in_file, 'r')
    radios = []

    for line in fp_in:
        try:
            radio, mcc, net, area, cell, unit, lon, lat, range, samples, changeable, created, updated, averageSignal = line.strip().split(',')
            range = int(range)
            if range == 0:
                continue

            lat = float(lat)
            lon = float(lon)

            radios.append({
                'lat': lat,
                'lon': lon,
                'range': range
            })
            
        except ValueError:
            pass
    
    fp_in.close()

    radios.sort(key=lambda radio: radio['lon'])
    radios.sort(key=lambda radio: radio['lat'])

    fp_out = open(out_file, 'w')
    for radio in radios:
        fp_out.write(f'{radio["lat"]:019.7f},{radio["lon"]:019.7f},{radio["range"]:019d}\n')

    fp_out.close()

def __get_radios_from_index(index_file: str, bottom: float, left: float, top: float, right: float) -> list:
    """
    Read the index and return the radios whiting the latitude boundaries.
    """
    fp = os.open(index_file, os.O_RDONLY)
    len = os.stat(fp).st_size

    LINE_LEN = 60
    lines = len / LINE_LEN
    start = end = 0

    # Find the start of the index
    i = int(lines / 2)
    os.lseek(fp, i * LINE_LEN, os.SEEK_SET)
    pos = i * LINE_LEN
    while True:
        lat, lon, range = os.read(fp, LINE_LEN).decode().strip().split(',')
        diff = abs(float(lat) - bottom)

        if float(lat) == bottom or i == 1 or diff <= 0.01:
            start = pos
            break
        elif float(lat) < bottom:
            offset = int(i / 2) * LINE_LEN
            os.lseek(fp, offset, os.SEEK_CUR)
            pos += offset
            i += int(i / 2)
        else:
            offset = int(i / 2) * LINE_LEN
            os.lseek(fp, -offset, os.SEEK_CUR)
            pos -= offset
            i -= int(i / 2)

    # Find the end of the index
    i = int(lines / 2)
    os.lseek(fp, i * LINE_LEN, os.SEEK_SET)
    pos = i * LINE_LEN
    while True:
        lat, lon, range = os.read(fp, LINE_LEN).decode().strip().split(',')
        diff = abs(float(lat) - top)

        if float(lat) == top or i == 1 or diff <= 0.01:
            end = pos
            break
        elif float(lat) < top:
            offset = int(i / 2) * LINE_LEN
            os.lseek(fp, offset, os.SEEK_CUR)
            pos += offset
            i += int(i / 2)
        else:
            offset = int(i / 2) * LINE_LEN
            os.lseek(fp, -offset, os.SEEK_CUR)
            pos -= offset
            i -= int(i / 2)

    # Get the radios in the interval
    os.lseek(fp, start, os.SEEK_SET)
    radios = []
    while (start < end):
        lat, lon, range = os.read(fp, LINE_LEN).decode().strip().split(',')
        start += LINE_LEN

        radios.append({
            'lat': float(lat),
            'lon': float(lon),
            'range': int(range)
        })

    os.close(fp)
    return radios
