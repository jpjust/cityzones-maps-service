#!/usr/bin/env python3
# encoding: utf-8
"""
CityZones Maps-service worker module
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

*******************************************************************************

This script acts as a worker for the CityZones application server.

It will periodically request a task from the web service and run it with
riskzones.py locally, sending the results back to the web service. The worker
performs the classifications requested online.
"""

from cityzones import riskzones
import os
import sys
import subprocess
import json
import requests
import time
from dotenv import dotenv_values
from requests_toolbelt import MultipartEncoder
from datetime import datetime

# Load current directory .env or default configuration file
CONF_DEFAULT_PATH='/etc/cityzones/maps-service.conf'
if os.path.exists('.env'):
    config = dotenv_values('.env')
elif os.path.exists(CONF_DEFAULT_PATH):
    config = dotenv_values(CONF_DEFAULT_PATH)
else:
    print(f'No .env file in current path nor configuration file at {CONF_DEFAULT_PATH}. Please create a configuration fom .env.example.')
    exit(1)

sleep_time = int(config['SLEEP_INT'])

def logger(text: str):
    print(f'{datetime.now().isoformat()}: {text}', file=sys.stderr)

def delete_task_files(task: dict):
    """
    Delete task files described in its config data.
    """
    fileslist = []
    fileslist.append(f"{config['TASKS_DIR']}/{task['config']['base_filename']}.json")
    fileslist.append(task['config']['geojson'])
    fileslist.append(task['config']['pois'])
    fileslist.append(task['config']['output'])
    fileslist.append(task['config']['output_edus'])
    fileslist.append(task['config']['output_roads'])
    fileslist.append(task['config']['res_data'])

    for file in fileslist:
        if os.path.isfile(file):
            os.remove(file)

def get_task() -> dict:
    """
    Request a task from the web app.
    """
    try:
        res = requests.get(f'{config["API_URL"]}/task', headers={'X-API-Key': config["API_KEY"]})
    except requests.exceptions.ConnectionError:
        logger(f'There was an error trying to connect to the server.')
        return None

    if res.status_code == 204:
        logger('No task received from server.')
        return None
    elif res.status_code == 401:
        logger('Not authorized! Check API_KEY.')
        return None
    elif res.status_code != 200:
        logger('An error ocurred while trying to get a task from server.')
        return None

    data = res.content.decode()
    return json.loads(data)

def process_task(task: dict):
    """
    Process a task.
    """
    taskcfg = task['config']
    geojson = task['geojson']
    logger(f'Starting task {taskcfg["base_filename"]}...')

    # Apply directories path to configuration
    try:
        taskcfg['geojson'] = f"{config['TASKS_DIR']}/{taskcfg['geojson']}"
        taskcfg['pois'] = f"{config['TASKS_DIR']}/{taskcfg['pois']}"
        taskcfg['output'] = f"{config['OUT_DIR']}/{taskcfg['output']}"
        taskcfg['output_edus'] = f"{config['OUT_DIR']}/{taskcfg['output_edus']}"
        taskcfg['output_roads'] = f"{config['OUT_DIR']}/{taskcfg['output_roads']}"
        taskcfg['res_data'] = f"{config['OUT_DIR']}/{taskcfg['res_data']}"
        filename = f"{config['TASKS_DIR']}/{taskcfg['base_filename']}.json"
    except KeyError:
        logger('A key is missing in task JSON file. Aborting!')
        return

    # Write temp configuration files
    fp_config = open(filename, 'w')
    json.dump(taskcfg, fp_config)
    fp_config.close()

    fp_geojson = open(f"{taskcfg['geojson']}", 'w')
    json.dump(geojson, fp_geojson)
    fp_geojson.close()

    # Extract data from PBF file
    try:
        res = subprocess.run([
            config['OSMIUM_PATH'],
            'extract',
            '-b',
            f'{taskcfg["left"]},{taskcfg["bottom"]},{taskcfg["right"]},{taskcfg["top"]}',
            config['PBF_FILE'],
            '-o',
            taskcfg['pois'],
            '--overwrite'
        ], capture_output=True, timeout=int(config['SUBPROC_TIMEOUT']))
    except subprocess.TimeoutExpired:
        logger("Timeout running osmium for the task's AoI.")
        return

    if res.returncode != 0:
        logger(f'There was an error while extracting map data using {taskcfg["base_filename"]} coordinates.')
        return

    # Run riskzones.py
    try:
        res = subprocess.run([
            sys.executable,
            riskzones.__file__,
            filename
        ], timeout=int(config['SUBPROC_TIMEOUT']))
    except subprocess.TimeoutExpired:
        logger("Timeout running RiskZones for the task.")
        return

    if res.returncode != 0:
        logger(f'There was an error while running riskzones.py for {taskcfg["base_filename"]}.')
        return

    # Post results to the web app
    encoder = MultipartEncoder(
        fields={
            'map': ('map.csv', open(taskcfg['output'], 'rb'), 'text/csv'),
            'edus': ('edus.csv', open(taskcfg['output_edus'], 'rb'), 'text/csv'),
            'roads': ('roads.csv', open(taskcfg['output_roads'], 'rb'), 'text/csv'),
            'res_data': ('res_data.json', open(taskcfg['res_data'], 'rb'), 'application/json'),
        }
    )

    logger(f'Sending data to web service...')
    try:
        req = requests.post(
            f'{config["API_URL"]}/result/{task["id"]}',
            headers={
                'Content-type': encoder.content_type,
                'X-API-Key': config["API_KEY"]
            },
            data=encoder
        )

        if req.status_code == 201:
            logger(f'Results for {taskcfg["base_filename"]} sent successfully.')
        elif req.status_code == 401:
            logger('Not authorized! Check API_KEY.')
        else:
            logger(f'The server reported an error for {taskcfg["base_filename"]} data.')
        
    except requests.exceptions.ConnectionError:
        logger(f'There was an error trying to connect to the server.')
    
if __name__ == '__main__':
    # Create the queue and output directories
    try:
        os.makedirs(config['TASKS_DIR'])
        os.makedirs(config['OUT_DIR'])
    except FileExistsError:
        pass

    # Check if the PBF file exists. If not, download from Planet OSM
    if not os.path.exists(config['PBF_FILE']):
        PBF_URL = 'https://planet.openstreetmap.org/pbf/planet-latest.osm.pbf'
        print(f'{config["PBF_FILE"]} not found. Downloading from {PBF_URL}...')
        with requests.get(PBF_URL, stream=True) as r:
            with open(config['PBF_FILE'], 'wb') as f:
                f.write(r.content)

    # Main loop
    while True:
        task = get_task()
        if task != None:
            process_task(task)
            delete_task_files(task)
        time.sleep(sleep_time)
