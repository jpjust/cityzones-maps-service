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

from dotenv import load_dotenv
load_dotenv()

import os
import sys
import subprocess
import json
import requests
import time
from requests_toolbelt import MultipartEncoder
from datetime import datetime

sleep_time = int(os.getenv('SLEEP_INT'))

def logger(text: str):
    print(f'{datetime.now().isoformat()}: {text}')

def delete_task_files(task: dict):
    """
    Delete task files described in its config data.
    """
    fileslist = []
    fileslist.append(f"{os.getenv('TASKS_DIR')}/{task['config']['base_filename']}.json")
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
        res = requests.get(f'{os.getenv("API_URL")}/task', headers={'X-API-Key': os.getenv("API_KEY")})
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
    config = task['config']
    geojson = task['geojson']
    logger(f'Starting task {config["base_filename"]}...')

    # Apply directories path to configuration
    try:
        config['geojson'] = f"{os.getenv('TASKS_DIR')}/{config['geojson']}"
        config['pois'] = f"{os.getenv('TASKS_DIR')}/{config['pois']}"
        config['output'] = f"{os.getenv('OUT_DIR')}/{config['output']}"
        config['output_edus'] = f"{os.getenv('OUT_DIR')}/{config['output_edus']}"
        config['output_roads'] = f"{os.getenv('OUT_DIR')}/{config['output_roads']}"
        config['res_data'] = f"{os.getenv('OUT_DIR')}/{config['res_data']}"
        filename = f"{os.getenv('TASKS_DIR')}/{config['base_filename']}.json"
    except KeyError:
        logger('A key is missing in task JSON file. Aborting!')
        return

    # Write temp configuration files
    fp_config = open(filename, 'w')
    json.dump(config, fp_config)
    fp_config.close()

    fp_geojson = open(f"{config['geojson']}", 'w')
    json.dump(geojson, fp_geojson)
    fp_geojson.close()

    # Extract data from PBF file
    try:
        res = subprocess.run([
            os.getenv('OSMIUM_PATH'),
            'extract',
            '-b',
            f'{config["left"]},{config["bottom"]},{config["right"]},{config["top"]}',
            os.getenv('PBF_FILE'),
            '-o',
            config['pois'],
            '--overwrite'
        ], capture_output=True, timeout=int(os.getenv('SUBPROC_TIMEOUT')))
    except subprocess.TimeoutExpired:
        logger("Timeout running osmium for the task's AoI.")
        return

    if res.returncode != 0:
        logger(f'There was an error while extracting map data using {config["base_filename"]} coordinates.')
        return

    # Run riskzones.py
    try:
        res = subprocess.run([
            sys.executable,
            'riskzones.py',
            filename
        ], timeout=int(os.getenv('SUBPROC_TIMEOUT')))
    except subprocess.TimeoutExpired:
        logger("Timeout running RiskZones for the task.")
        return

    if res.returncode != 0:
        logger(f'There was an error while running riskzones.py for {config["base_filename"]}.')
        return

    # Post results to the web app
    encoder = MultipartEncoder(
        fields={
            'map': ('map.csv', open(config['output'], 'rb'), 'text/csv'),
            'edus': ('edus.csv', open(config['output_edus'], 'rb'), 'text/csv'),
            'roads': ('roads.csv', open(config['output_roads'], 'rb'), 'text/csv'),
            'res_data': ('res_data.json', open(config['res_data'], 'rb'), 'application/json'),
        }
    )

    logger(f'Sending data to web service...')
    try:
        req = requests.post(
            f'{os.getenv("API_URL")}/result/{task["id"]}',
            headers={
                'Content-type': encoder.content_type,
                'X-API-Key': os.getenv("API_KEY")
            },
            data=encoder
        )

        if req.status_code == 201:
            logger(f'Results for {config["base_filename"]} sent successfully.')
        elif req.status_code == 401:
            logger('Not authorized! Check API_KEY.')
        else:
            logger(f'The server reported an error for {config["base_filename"]} data.')
        
    except requests.exceptions.ConnectionError:
        logger(f'There was an error trying to connect to the server.')
    
if __name__ == '__main__':
    # Create the queue and output directories
    try:
        os.makedirs(os.getenv('TASKS_DIR'))
        os.makedirs(os.getenv('OUT_DIR'))
    except FileExistsError:
        pass

    # Main loop
    while True:
        task = get_task()
        if task != None:
            process_task(task)
            delete_task_files(task)
        time.sleep(sleep_time)
