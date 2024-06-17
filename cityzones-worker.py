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
from cityzones import overpass
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
request_timeout = int(config['NET_TIMEOUT'])

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
    fileslist.append(task['config']['extract'])

    for file in fileslist:
        if os.path.isfile(file):
            os.remove(file)

def get_task() -> dict:
    """
    Request a task from the web app.
    """
    try:
        res = requests.get(f'{config["API_URL"]}/tasks', headers={'X-API-Key': config["API_KEY"]}, timeout=request_timeout, verify=False)
    except requests.exceptions.ConnectionError:
        logger(f'There was an error trying to connect to the server.')
        return None
    except requests.exceptions.ReadTimeout:
        logger(f'Conenction timed-out while requesting a task.')
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
        taskcfg['extract'] = f"{config['OUT_DIR']}/extract_{taskcfg['pois']}"
        taskcfg['pois'] = f"{config['TASKS_DIR']}/{taskcfg['pois']}"
        taskcfg['output'] = f"{config['OUT_DIR']}/{taskcfg['output']}"
        taskcfg['output_edus'] = f"{config['OUT_DIR']}/{taskcfg['output_edus']}"
        taskcfg['output_roads'] = f"{config['OUT_DIR']}/{taskcfg['output_roads']}"
        taskcfg['output_rivers'] = f"{config['OUT_DIR']}/{taskcfg['output_rivers']}"
        taskcfg['output_elevation'] = f"{config['OUT_DIR']}/{taskcfg['output_elevation']}"
        taskcfg['output_slope'] = f"{config['OUT_DIR']}/{taskcfg['output_slope']}"
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

    # Extract data from Overpass API
    logger('Extracting AoI from Overpass API...')
    try:
        overpass.get_osm_from_bbox(taskcfg['pois'], taskcfg["bottom"], taskcfg["left"], taskcfg["top"], taskcfg["right"], request_timeout)
    except requests.exceptions.ConnectionError:
        logger(f'There was an error trying to connect to the Overpass server.')
        return None
    except requests.exceptions.ReadTimeout:
        logger(f'Conenction timed-out while requesting data from Overpass.')
        return None

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
        logger(f'There was an error while running riskzones.py for {taskcfg["base_filename"]}. Return code: {res.returncode}')
        return

    # Post results to the web app
    encoder = MultipartEncoder(
        fields={
            'task[data][map]': ('map.csv', open(taskcfg['output'], 'rb'), 'text/csv'),
            'task[data][edus]': ('edus.csv', open(taskcfg['output_edus'], 'rb'), 'text/csv'),
            'task[data][roads]': ('roads.csv', open(taskcfg['output_roads'], 'rb'), 'text/csv'),
            'task[data][rivers]': ('rivers.csv', open(taskcfg['output_rivers'], 'rb'), 'text/csv'),
            'task[data][elevation]': ('elevation.csv', open(taskcfg['output_elevation'], 'rb'), 'text/csv'),
            'task[data][slope]': ('slope.csv', open(taskcfg['output_slope'], 'rb'), 'text/csv'),
            'task[res_data]': ('res_data.json', open(taskcfg['res_data'], 'rb'), 'application/json'),
        }
    )

    logger(f'Sending data to web service...')
    try:
        req = requests.put(
            f'{config["API_URL"]}/tasks/{task["id"]}',
            headers={
                'Content-type': encoder.content_type,
                'X-API-Key': config["API_KEY"]
            },
            data=encoder,
            timeout=request_timeout,
            verify=False
        )

        if req.status_code == 201:
            logger(f'Results for {taskcfg["base_filename"]} sent successfully.')
        elif req.status_code == 401:
            logger('Not authorized! Check API_KEY.')
        else:
            logger(f'The server reported an error for {taskcfg["base_filename"]} data.')
        
    except requests.exceptions.ConnectionError:
        logger(f'There was an error trying to connect to the server.')
    except requests.exceptions.ReadTimeout:
        logger(f'Conenction timed-out while sending the results.')

    
if __name__ == '__main__':
    # Create the queue and output directories
    try:
        os.makedirs(config['TASKS_DIR'])
        os.makedirs(config['OUT_DIR'])
    except FileExistsError:
        pass

    # Main loop
    while True:
        task = get_task()
        if task != None:
            process_task(task)
            delete_task_files(task)
        time.sleep(sleep_time)
