#!/usr/bin/bash
# Risk Zones classification
# Copyright (C) 2022 João Paulo Just Peixoto
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# The following script shows examples on how to:
# 
# 1) Extract an OSM file from a large area downloaded from Planet OSM.
# 2) Filter the OSM file to keep only amenities you are interested on.
# 
# You can skip step 1 if you are able to export the area of interest
# directly from OpenStreetMap web interface.
# 
# You can also skip step 2 if you have a small area or if you don't
# care about high CPU and memory usage. That's it, you can work directly
# with a large OSM file, but osmpois.py will take longer to complete.
# 
# osm and csv folders have examples of both OSM and CSV files for
# Feira de Santana, Brazil.

##########
# Step 1: extraction
# 
# osmium is used to extract an area from a large OSM file.
# Check the JSON examples inside geojson folder.
##########

# Feira de Santana, Bahia, Brazil
osmium extract --config geojson/feira.json --progress /home/just/Downloads/openstreetmap/nordeste-latest.osm

# Porto, Portugal
osmium extract --config geojson/porto.json --progress /home/just/Downloads/openstreetmap/portugal-latest.osm

# Paris, France using osmosis and a PBF file
osmosis --read-pbf file=france.osm.pbf --bounding-box top=48.9281 left=2.1842 bottom=48.7897 right=2.5097 --write-xml file=paris.osm

##########
# Step 2: filtering (optional)
# 
# osmfilter is used to filter elements from an OSM file.
# Just set the elements you want to keep through the --keep argument.
##########

# Emergency buildings or police, hospital, fire stations
osmfilter osm/feira.osm --keep="emergency=yes OR amenity=police =hospital =fire_station" -o=osm/feira_filtered.osm

# Only police depts
osmfilter osm/feira.osm --keep="amenity=police" -o=osm/feira_police.osm

# Only hospitals
osmfilter osm/feira.osm --keep="amenity=hospital" -o=osm/feira_hospital.osm

# Only fire stations
osmfilter osm/feira.osm --keep="amenity=fire_station" -o=osm/feira_fire.osm
