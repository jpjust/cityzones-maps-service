# encoding:utf-8
"""
RiskZones classification
Copyright (C) 2022 - 2023 João Paulo Just Peixoto

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

def extract_nodes(file: str) -> tuple[dict, dict, dict]:
    '''
    Extract nodes, ways and relations from an OSM file.
    '''
    tree = ET.parse(file)
    root = tree.getroot()

    nodes = {}
    ways = {}
    relations = {}

    # Collect nodes from OSM
    for node in root.iter('node'):
        id = int(node.get('id'))
        node_data = {}

        for tag in node.iter('tag'):
            node_data[tag.get('k')] = tag.get('v')

        node_data['lat'] = float(node.get('lat'))
        node_data['lon'] = float(node.get('lon'))
        node_data['weight'] = 1.0
        node_data['badpoi'] = False
        node_data['zone_id'] = None

        nodes[id] = node_data

    # Collect ways from OSM
    for way in root.iter('way'):
        id = int(way.get('id'))
        way_data = {}

        for tag in way.iter('tag'):
            way_data[tag.get('k')] = tag.get('v')

        way_data['nodes'] = []

        # Ways contain a set of nodes, so we must gather them
        for node in way.iter('nd'):
            node_id = int(node.get('ref'))
            if node_id in nodes.keys():
                way_data['nodes'].append(nodes[node_id])

        ways[id] = way_data

    # Collect relations from OSM
    for relation in root.iter('relation'):
        id = int(relation.get('id'))
        relation_data = {}

        for tag in relation.iter('tag'):
            relation_data[tag.get('k')] = tag.get('v')

        relation_data['ways'] = []
        relation_data['nodes'] = []

        # Relations contain a set of ways, so we must gather them
        for member in relation.iter('member'):
            member_id = int(member.get('ref'))
            if member.get('type') == 'way' and member_id in ways.keys():
                relation_data['ways'].append(ways[member_id])
                relation_data['nodes'] += ways[member_id]['nodes']
            if member.get('type') == 'node' and member_id in nodes.keys():
                relation_data['nodes'].append(nodes[member_id])

        relations[id] = relation_data

    return nodes, ways, relations

def extract_pois(file: str, pois_types: dict) -> tuple[list, list, list]:
    '''
    Extract paths and PoIs of types pois_types from OSM file.
    '''
    nodes, ways, relations = extract_nodes(file)

    pois = []
    roads = []
    rivers = []

    # Check data in nodes
    for id in nodes.keys():
        node = nodes[id]
        for node_key in node.keys():
            if node_key in pois_types and node[node_key] in pois_types[node_key].keys():
                w = pois_types[node_key][node[node_key]]['w']
                poi_data = {
                    'lat': float(node.get('lat')),
                    'lon': float(node.get('lon')),
                    'weight': w,
                    'badpoi': False if w >= 0 else True,
                    'zone_id': None
                }
                pois.append(poi_data)

    # Check data in ways
    for id in ways.keys():
        way = ways[id]
        if len(way['nodes']) == 0:
            continue
        first_node = way['nodes'][0]

        for way_key in way.keys():
            if way_key in pois_types and way[way_key] in pois_types[way_key].keys():
                w = pois_types[way_key][way[way_key]]['w']
                poi_data = {
                    'lat': float(first_node.get('lat')),
                    'lon': float(first_node.get('lon')),
                    'weight': w,
                    'badpoi': False if w >= 0 else True,
                    'zone_id': None
                }
                pois.append(poi_data)

        # Check for paths (roads, rivers, ...)
        if len(way['nodes']) >= 2:
            for i in range(len(way['nodes']) - 1):
                path_point = {}
                path_point['start'] = {}
                path_point['end'] = {}
                path_point['start']['lat'] = way['nodes'][i]['lat']
                path_point['start']['lon'] = way['nodes'][i]['lon']
                path_point['end']['lat'] = way['nodes'][i + 1]['lat']
                path_point['end']['lon'] = way['nodes'][i + 1]['lon']

                if way.get('highway') in ['motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential']:
                    roads.append(path_point)
                elif way.get('water') == 'river' or way.get('waterway') == 'river' or way.get('water') == 'lake':
                    rivers.append(path_point)

    # Check data in relations
    for id in relations.keys():
        relation = relations[id]
        if len(relation['nodes']) == 0:
            continue
        first_node = relation['nodes'][0]

        for relation_key in relation.keys():
            if relation_key in pois_types and relation[relation_key] in pois_types[relation_key].keys():
                w = pois_types[relation_key][relation[relation_key]]['w']
                poi_data = {
                    'lat': float(first_node.get('lat')),
                    'lon': float(first_node.get('lon')),
                    'weight': w,
                    'badpoi': False if w >= 0 else True,
                    'zone_id': None
                }
                pois.append(poi_data)

        # Check for paths (roads, rivers, ...)
        if len(relation['nodes']) >= 2:
            for i in range(len(relation['nodes']) - 1):
                path_point = {}
                path_point['start'] = {}
                path_point['end'] = {}
                path_point['start']['lat'] = relation['nodes'][i]['lat']
                path_point['start']['lon'] = relation['nodes'][i]['lon']
                path_point['end']['lat'] = relation['nodes'][i + 1]['lat']
                path_point['end']['lon'] = relation['nodes'][i + 1]['lon']

                if relation.get('highway') in ['motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential']:
                    roads.append(path_point)
                elif relation.get('water') == 'river' or relation.get('waterway') == 'river' or relation.get('water') == 'lake':
                    rivers.append(path_point)

    return pois, roads, rivers

'''
Main program.
'''
if __name__ == '__main__':
    file = input('Input OSM filename: ')
    pois_type = input('Input pois type (hospital, police, fire_station): ')
    pois = extract_pois(file, {'amenity': pois_type})

    message = f"{len(pois)} PoIs found:"
    print(f"\n{message}")
    print('-' * len(message))

    for poi in pois:
        print(f"Name: {poi['name']}")
        print(f"Coordinates: {poi['lon']},{poi['lat']}\n")
