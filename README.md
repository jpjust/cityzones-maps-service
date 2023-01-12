# Risk Zones classification

This program is the implementation of the approach proposed in my paper regarding risk zones for smart cities (yet in writing process).

`riskzones.py` reads the configuration from a JSON file to create a grid of zones, define its risk levels by calculating the distance from each zone to each point of interest and distribute EDUs (Emergency Detection Units) ramdonly prioritizing more risky zones.

See the JSON files in `conf` folder for examples of how to delimit the grid area and other parameters. The properties of the configuration file are self explanatory.

You will also need an OSM file (OpenStreetMap) for the city and also a GeoJSON file containing the polygon that limit the boundaries of the city. The file `extract.sh` contains some information on how to extract an OSM file of a specific region from a large OSM file.

If you don't have a GeoJSON file for the city you are working on, you can convert its shapefile to GeoJSON using some GIS software as QGIS. If you don't have the shapefile, you will need to perform a search for it on the web.

The output properties of the configuration file specifies two output files: the main output which will contain the zones and its classes of risk and an EDUs output which will contain the position of the EDUs on the region.

To plot a map of the risk zones and the EDUs, run the script in `gee_riskzones.js` on Google Earch Engine (you will need to upload your output CSV files as assets on GEE) or use the web interface at http://riskzonesweb.just.pro.br.

## Dependencies

To install all modules needed by riskzones and its worker, run:

`python3 -m pip install numpy requests requests-toolbelt`

## Memory limit

To avoid memory issues `riskzones.py` sets a memory limit. Copy `.env.example` as `.env` in the root directory and set `MEM_LIMIT` to the value of your choice. By default, riskzones.py limits itself to 1 GiB of RAM.

## RiskZones Web: online interface

There is a online web interface for riskzones: http://riskzonesweb.just.pro.br

This web application provides a GUI to request an AoI classification with Risk Zones algorithm. All requests are processed by a remote worker and sent back to the online service. Visit the Risk Zones Web site to get more help.

## Worker

The worker program is the `worker.py` script. It periodically request tasks from the web service to run locally, sending back the results. To run it, first make a copy of `.env.example` into `.env` and set it up. Then run:

`python3 worker.py`

and it will start working.
