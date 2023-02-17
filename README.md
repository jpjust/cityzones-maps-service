# Maps-service for CityZones

This program is the implementation of the approach proposed in my paper regarding risk zones for smart cities (waiting for approval).

## RiskZones module

`riskzones.py` reads the configuration from a JSON file to create a grid of zones, define its risk levels by calculating the distance from each zone to each point of interest and distribute EDUs (Emergency Detection Units) ramdonly prioritizing more risky zones.

See the JSON files in `conf` folder for examples of how to delimit the grid area and other parameters. The properties of the configuration file are self explanatory.

You will also need an OSM file (OpenStreetMap) for the city and also a GeoJSON file containing the polygon that limit the boundaries of the city. The file `extract.sh` contains some information on how to extract an OSM file of a specific region from a large OSM file.

If you don't have a GeoJSON file for the city you are working on, you can convert its shapefile to GeoJSON using some GIS software as QGIS. If you don't have the shapefile, you will need to perform a search for it on the web.

The output properties of the configuration file specifies two output files: the main output which will contain the zones and its classes of risk and an EDUs output which will contain the position of the EDUs on the region.

To plot a map of the risk zones and the EDUs, run the script in `gee_riskzones.js` on Google Earch Engine (you will need to upload your output CSV files as assets on GEE) or use the web interface at http://cityzones.just.pro.br.

## Worker

The `worker.py` program acts as a Worker module for the CityZones Application server: https://github.com/jpjust/cityzones-application-server

It will periodically requests a task from CityZones web service to perform it locally and then send the results back. If you want to contribute to the project being a Maps-service worker, contact-me at joao.just@ifba.edu.br

For the worker to work, you need to copy `.env.example` as `.env` and setup your API Key. The key will be provided by me to allow your device to request tasks from the CityZones Application server. If you want to try the project on your own, you will need to run the Application server and then configure a worker on it to get a key.

## Dependencies

To install all modules needed by riskzones and its worker, run:

`python3 -m pip install osmpois geojson numpy requests requests-toolbelt`

## Memory limit

To avoid memory issues `riskzones.py` sets a memory limit. Edit `.env` in the root directory and set `MEM_LIMIT` to the value of your choice. By default, riskzones.py limits itself to 1 GiB of RAM.

## CityZones Web: online interface

There is a online web interface for CityZones: http://cityzones.just.pro.br

This web application provides a GUI to request an AoI classification with RiskZones algorithm. All requests are processed by a remote worker and sent back to the online service. Visit the CityZones Web site to get more help.
