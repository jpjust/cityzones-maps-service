# encoding: utf-8
"""
Risk Zones classification
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

This script acts as a worker for the RiskZones Web application.

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

while True:
    # Request a task from the web app
    try:
        res = requests.get(f'{os.getenv("API_URL")}/task')
    except requests.exceptions.ConnectionError:
        logger(f'There was an error trying to connect to the server.')
        time.sleep(sleep_time)
        continue

    if res.status_code == 204:
        logger('No task received from server.')
        time.sleep(sleep_time)
        continue

    if res.status_code != 200:
        logger('An error ocurred while trying to get a task from server.')
        time.sleep(sleep_time)
        continue

    data = res.content.decode()
    task = json.loads(data)
    config = task['config']
    geojson = task['geojson']
    logger(f'Starting task {config["base_filename"]}...')

    # Create the queue and output directories
    try:
        os.makedirs(os.getenv('TASKS_DIR'))
        os.makedirs(os.getenv('OUT_DIR'))
    except FileExistsError:
        pass

    # Apply directories path to configuration
    config['geojson'] = f"{os.getenv('TASKS_DIR')}/{config['geojson']}"
    config['pois'] = f"{os.getenv('TASKS_DIR')}/{config['pois']}"
    config['output'] = f"{os.getenv('OUT_DIR')}/{config['output']}"
    config['output_edus'] = f"{os.getenv('OUT_DIR')}/{config['output_edus']}"
    config['output_roads'] = f"{os.getenv('OUT_DIR')}/{config['output_roads']}"
    filename = f"{os.getenv('TASKS_DIR')}/{config['base_filename']}.json"

    # Write temp configuration files
    fp_config = open(filename, 'w')
    json.dump(config, fp_config)
    fp_config.close()

    fp_geojson = open(f"{config['geojson']}", 'w')
    json.dump(geojson, fp_geojson)
    fp_geojson.close()

    # Extract data from PBF file
    res = subprocess.run([
        os.getenv('OSMIUM_PATH'),
        'extract',
        '-b',
        f'{config["left"]},{config["bottom"]},{config["right"]},{config["top"]}',
        os.getenv('PBF_FILE'),
        '-o',
        config['pois'],
        '--overwrite'
    ], capture_output=True)

    if res.returncode != 0:
        logger(f'There was an error while extracting map data using {config["base_filename"]} coordinates.')
        time.sleep(sleep_time)
        continue

    # Run riskzones.py
    res = subprocess.run([
        sys.executable,
        'riskzones.py',
        filename
    ])

    if res.returncode != 0:
        logger(f'There was an error while running riskzones.py for {config["base_filename"]}.')
        time.sleep(sleep_time)
        continue

    # Post results to the web app
    encoder = MultipartEncoder(
        fields={
            'map': ('map.csv', open(config['output'], 'rb'), 'text/plain'),
            'edus': ('edus.csv', open(config['output_edus'], 'rb'), 'text/plain'),
        }
    )

    logger(f'Sending data to web service...')
    try:
        req = requests.post(
            f'{os.getenv("API_URL")}/result/{task["id"]}',
            headers={
                'Content-type': encoder.content_type
            },
            data=encoder
        )

        if req.status_code == 201:
            logger(f'Results for {config["base_filename"]} sent successfully.')
        else:
            logger(f'The server reported an error for {config["base_filename"]} data.')
            time.sleep(sleep_time)
        
        # Remove task files
        os.remove(filename)
        os.remove(config['geojson'])
        os.remove(config['pois'])
        os.remove(config['output'])
        os.remove(config['output_edus'])
        os.remove(config['output_roads'])
    except requests.exceptions.ConnectionError:
        logger(f'There was an error trying to connect to the server.')
        time.sleep(sleep_time)
        continue
    except FileNotFoundError:
        logger(f'WARNING: Some of the task files could not be deleted. Check {os.getenv("TASKS_DIR")} and {os.getenv("OUT_DIR")} later for unneeded files.')
        continue
