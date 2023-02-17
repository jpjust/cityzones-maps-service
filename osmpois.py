# encoding:utf-8
"""
RiskZones classification
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
Extract roads and PoIs of types pois_types from OSM file.
'''
def extract_pois(file: str, pois_types: dict) -> tuple[list, list]:
    tree = ET.parse(file)
    root = tree.getroot()
    pois = []
    roads = []
    nodes = {}
    ways = {}
    relations = {}

    # Collect nodes from OSM
    for node in root.iter('node'):
        id = int(node.get('id'))

        node_data = {
            'lat': float(node.get('lat')),
            'lon': float(node.get('lon')),
            'weight': 1.0
        }

        for tag in node.iter('tag'):
            node_data[tag.get('k')] = tag.get('v')
        
        nodes[id] = node_data

        # If this node already represents the requested pois_types, just add it to
        # the list of POIs
        for node_key in node_data.keys():
            try:
                if node_data[node_key] in pois_types[node_key].keys():
                    if 'poi_weight' in node_data.keys():
                        node_data['weight'] = float(node_data['poi_weight'])
                    else:
                        node_data['weight'] = pois_types[node_key][node_data[node_key]]['w']
                    pois.append(node_data)
            except KeyError:
                pass
    
    # Collect ways from OSM
    for way in root.iter('way'):
        id = int(way.get('id'))

        way_data = {
            'weight': 1.0
        }

        # Ways contain a set of nodes, so we must gather them
        way_nodes = []
        way_roads = []
        for node in way.iter('nd'):
            way_nodes.append(int(node.get('ref')))

            # Combine nodes in a way to make roads
            if len(way_nodes) < 2: continue
            try:
                road = {}
                road['start'] = {}
                road['end'] = {}
                road['start']['lat'] = nodes[way_nodes[-2]]['lat']
                road['start']['lon'] = nodes[way_nodes[-2]]['lon']
                road['end']['lat'] = nodes[way_nodes[-1]]['lat']
                road['end']['lon'] = nodes[way_nodes[-1]]['lon']
                way_roads.append(road)
            except KeyError:
                pass
        
        # Check if this way is a highway (roads, streets, etc.)
        for tag in way.iter('tag'):
            way_data[tag.get('k')] = tag.get('v')
            if tag.get('k') == 'highway' and tag.get('v') in ['motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential']:
                roads += way_roads

        # Get the first available node to copy its coordinates
        # (depending on the boundaries of the exported OSM file, some
        # nodes may be out of the map)
        for node in way_nodes:
            if node in nodes:
                way_data['lat'] = float(nodes[node]['lat'])
                way_data['lon'] = float(nodes[node]['lon'])
                break

        ways[id] = way_data

        # If this way already represents the requested pois_types, just add it to
        # the list of POIs
        for way_key in way_data.keys():
            try:
                if way_data[way_key] in pois_types[way_key].keys():
                    if 'poi_weight' in way_data.keys():
                        way_data['weight'] = float(way_data['poi_weight'])
                    else:
                        way_data['weight'] = pois_types[way_key][way_data[way_key]]['w']
                    pois.append(way_data)
            except KeyError:
                pass

    # Collect relations from OSM
    for relation in root.iter('relation'):
        id = int(relation.get('id'))

        relation_data = {
            'weight': 1.0
        }

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
                break

        relations[id] = relation_data

        # If this relation represents the requested pois_types, just add it to
        # the list of POIs
        for relation_key in relation_data.keys():
            try:
                if relation_data[relation_key] in pois_types[relation_key].keys():
                    if 'poi_weight' in relation_data.keys():
                        relation_data['weight'] = float(relation_data['poi_weight'])
                    else:
                        relation_data['weight'] = pois_types[relation_key][relation_data[relation_key]]['w']
                    pois.append(relation_data)
            except KeyError:
                pass

    return pois, roads

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
