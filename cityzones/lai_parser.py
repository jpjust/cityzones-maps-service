# encoding:utf-8
"""
CityZones classification: Leaf Area Index layer
Copyright (C) 2026 João Paulo Just Peixoto

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

This module contains the functions for reading Leaf Area Index data from CSV
files and insert them into RiskZones grid.

After creating a grid object, use the following functions to get LAI data:

- lai_parser.init_zones(grid)
"""

import csv
from scipy.spatial import cKDTree

def init_zones(grid: dict, lai_filename: str):
    """
    Initialize every zone in the grid and set their LAI.
    """
    print("Setting zones' Leaf Area Index... ", end='')

    # Initialize grid structure
    for zone in grid['zones']:
        zone['lai'] = 0

    # zone_coords = [(float(zone['lon']), float(zone['lat'])) for zone in grid['zones']]
    # zone_tree = cKDTree(zone_coords)

    # # Read CSV file
    # with open(lai_filename, mode='r', encoding='utf-8', newline='') as f:
    #     reader = csv.reader(f)
    #     next(reader, None)

    #     for x, y, z, lai in reader:
    #         _, zone_index = zone_tree.query((float(x), float(y)))
    #         nearest_zone = grid['zones'][zone_index]
    #         nearest_zone['lai'] = float(lai)

    # Read CSV file
    lai_coords = []
    lai_values = []
    with open(lai_filename, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        next(reader, None)

        for x, y, z, lai in reader:
            lai_coords.append((float(x), float(y)))
            lai_values.append(float(lai))

    zone_tree = cKDTree(lai_coords)

    for zone in grid['zones']:
        _, coord_index = zone_tree.query((float(zone['lon']), float(zone['lat'])))
        zone['lai'] = lai_values[coord_index]
