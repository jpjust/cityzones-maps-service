# encoding:utf-8
"""
Risk Zones classification
Copyright (C) 2022 João Paulo Just Peixoto

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

import xml.etree.ElementTree as ET

'''
Extract PoIs of type amenity from OSM file.
'''
def extract_pois(file, amenity):
    tree = ET.parse(file)
    root = tree.getroot()
    pois = []
    nodes = {}
    ways = {}
    relations = {}

    # Collect nodes from OSM
    for node in root.iter('node'):
        id = int(node.get('id'))

        node_data = {
            'lat': float(node.get('lat')),
            'lon': float(node.get('lon')),
            'weight': 1
        }

        for tag in node.iter('tag'):
            node_data[tag.get('k')] = tag.get('v')
        
        nodes[id] = node_data

        # If this node already represents the requested amenity, just add it to
        # the list of POIs
        try:
            if node_data['amenity'] in amenity:
                pois.append(node_data)
        except KeyError:
            pass
    
    # Collect ways from OSM
    for way in root.iter('way'):
        id = int(way.get('id'))

        way_data = {}

        for tag in way.iter('tag'):
            way_data[tag.get('k')] = tag.get('v')

        # Ways contain a set of nodes, so we must gather them
        way_nodes = []
        for node in way.iter('nd'):
            way_nodes.append(int(node.get('ref')))

        # Get the first available node to copy its coordinates
        # (depending on the boundaries of the exported OSM file, some
        # nodes may be out of the map)
        for node in way_nodes:
            if node in nodes:
                way_data['lat'] = float(nodes[node]['lat'])
                way_data['lon'] = float(nodes[node]['lon'])
                way_data['weight'] = float(nodes[node]['weight'])
                break

        ways[id] = way_data

        # If this way already represents the requested amenity, just add it to
        # the list of POIs
        try:
            if way_data['amenity'] in amenity:
                pois.append(way_data)
        except KeyError:
            pass

    # Collect relations from OSM
    for relation in root.iter('relation'):
        id = int(relation.get('id'))

        relation_data = {}

        for tag in relation.iter('tag'):
            relation_data[tag.get('k')] = tag.get('v')

        # Relations contain a set of ways, so we must gather them
        relation_ways = []
        for member in relation.iter('member'):
            if member.get('type') == 'way':
                relation_ways.append(int(member.get('ref')))

        # Get the first available way to copy its coordinates
        # (depending on the boundaries of the exported OSM file, some
        # ways may be out of the map)
        for way in relation_ways:
            if way in ways:
                relation_data['lat'] = float(ways[way]['lat'])
                relation_data['lon'] = float(ways[way]['lon'])
                relation_data['weight'] = float(ways[way]['weight'])
                break

        relations[id] = relation_data

        # If this relation represents the requested amenity, just add it to
        # the list of POIs
        try:
            if relation_data['amenity'] in amenity:
                pois.append(relation_data)
        except KeyError:
            pass

    return pois

'''
Main program.
'''
if __name__ == '__main__':
    file = input('Input OSM filename: ')
    amenity = input('Input amenity type (hospital, police, fire_station): ')
    pois = extract_pois(file, amenity)
    
    message = f"{len(pois)} PoIs found:"
    print(f"\n{message}")
    print('-' * len(message))

    for hospital in pois:
        print(f"Name: {hospital['name']}")
        print(f"Coordinates: {hospital['lon']},{hospital['lat']}\n")
