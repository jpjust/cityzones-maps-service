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
import fcntl

# Length of each line in index
LINE_LEN = 34

# Multiprocessing
MP_WORKERS=None  # If None, will use a value returned by the system

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

    # First we need to filter the database to keep only coordinates and range
    fp_in = open(in_file, 'r')
    fp_out = os.open(out_file, os.O_CREAT | os.O_TRUNC | os.O_WRONLY)
    lines = 0

    for line in fp_in:
        try:
            radio, mcc, net, area, cell, unit, lon, lat, r, samples, changeable, created, updated, averageSignal = line.strip().split(',')
            r = int(r)
            if r == 0:
                # Let's discard no range cells
                continue

            lat = float(lat)
            lon = float(lon)

            os.write(fp_out, f'{lat:012.7f},{lon:012.7f},{r:07d}\n'.encode())
            lines += 1
            
        except ValueError:
            pass
    
    fp_in.close()
    os.close(fp_out)
    fp_out = os.open(out_file, os.O_RDWR | os.O_SYNC)

    # Now we do a quick sort in the output file
    __qsort_file(fp_out, 0, lines - 1, 1)
    __qsort_file(fp_out, 0, lines - 1, 0)
    os.close(fp_out)

def __qsort_file(fp: int, p: int, r: int, key_idx: int):
    if p < r:
        (p, r, q) = __qsort_partition_file(fp, p, r, key_idx)
        __qsort_file(fp, p, q - 1, key_idx)
        __qsort_file(fp, q + 1, r, key_idx)

def __qsort_file_mp(fp: int, p: int, r: int, key_idx: int):
    payload = [(fp, p, r, key_idx)]

    while len(payload) > 0:
        print(f'payload = {payload}')
        with mp.Pool(processes=len(payload)) as pool:
            qlist = pool.starmap(__qsort_partition_file, payload)
        
        payload.clear()
        print(f'qlist = {qlist}')
        for (p, r, q) in qlist:
            if p < q - 1: payload.append((fp, p, q - 1, key_idx))
            if q + 1 < r: payload.append((fp, q + 1, r, key_idx))

        os.fsync(fp)

def __qsort_file_iterative(fp: int, p: int, r: int, key_idx: int):
    slices = [{'p': p, 'r': r}]

    while True:
        if len(slices) == 0:
            break

        slice = slices.pop(0)
        sp = slice['p']
        sr = slice['r']

        if sp < sr:
            q = __qsort_partition_file(fp, sp, sr, key_idx)
            slices.append({'p': sp, 'r': q - 1})
            slices.append({'p': q + 1, 'r': sr})

def __qsort_partition_file(fp: int, p: int, r: int, key_idx: int) -> int:
    """
    Partition the lines between p and r.
    Return the new index of the pivot.
    """
    os.lseek(fp, r * LINE_LEN, os.SEEK_SET)
    pivot = os.read(fp, LINE_LEN)
    key_pivot = pivot.decode().strip().split(',')
    
    print(f'partitioning from {p} to {r}. pivot = {key_pivot[key_idx]}')
    
    i = p - 1
    for j in range(p, r):
        os.lseek(fp, j * LINE_LEN, os.SEEK_SET)
        A = os.read(fp, LINE_LEN)
        key_A = A.decode().strip().split(',')
        
        if key_A[key_idx] <= key_pivot[key_idx]:
            i += 1
            __swap_lines_file(fp, i, j)
    
    q = i + 1
    __swap_lines_file(fp, q, r)
    return (p, r, q)

def __swap_lines_file(fp: int, line1: int, line2: int):
    """
    Swap lines 1 and 2 in file fp.
    """
    # os.lockf(fp, os.F_LOCK, 0)
    # fcntl.flock(fp, fcntl.LOCK_EX)

    # Read both lines
    # os.lseek(fp, line1 * LINE_LEN, os.SEEK_SET)
    data_line1 = os.pread(fp, LINE_LEN, line1 * LINE_LEN)
    # os.lseek(fp, line2 * LINE_LEN, os.SEEK_SET)
    data_line2 = os.pread(fp, LINE_LEN, line2 * LINE_LEN)

    # Write lines back
    # os.lseek(fp, line1 * LINE_LEN, os.SEEK_SET)
    os.pwrite(fp, data_line2, line1 * LINE_LEN)
    # os.lseek(fp, line2 * LINE_LEN, os.SEEK_SET)
    os.pwrite(fp, data_line1, line2 * LINE_LEN)

    # os.lockf(fp, os.F_ULOCK, 0)
    # fcntl.flock(fp, fcntl.LOCK_UN)
    
def __get_radios_from_index(index_file: str, bottom: float, left: float, top: float, right: float) -> list:
    """
    Read the index and return the radios whiting the latitude boundaries.
    """
    fp = os.open(index_file, os.O_RDONLY)
    len = os.stat(fp).st_size

    lines = len / LINE_LEN
    start = end = 0

    # Find the start of the index
    i = int(lines / 2)
    os.lseek(fp, i * LINE_LEN, os.SEEK_SET)
    pos = i * LINE_LEN
    while True:
        lat, lon, radius = os.read(fp, LINE_LEN).decode().strip().split(',')
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
        lat, lon, radius = os.read(fp, LINE_LEN).decode().strip().split(',')
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
        lat, lon, radius = os.read(fp, LINE_LEN).decode().strip().split(',')
        start += LINE_LEN

        radios.append({
            'lat': float(lat),
            'lon': float(lon),
            'range': int(radius)
        })

    os.close(fp)
    return radios
