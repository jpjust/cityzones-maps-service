from dotenv import load_dotenv
load_dotenv()

import os
import sys
import subprocess
import json
import urllib.request as request
import time
from urllib.error import URLError
from datetime import datetime

sleep_time = int(os.getenv('SLEEP_INT'))

def logger(text: str):
    print(f'{datetime.now().isoformat()}: {text}')

while True:
    # Request a task from the web app
    try:
        res = request.urlopen(f'{os.getenv("API_URL")}/task')
    except URLError:
        logger(f'The server reported an internal error.')
        time.sleep(sleep_time)
        continue

    if res.status == 204:
        logger('No task received from server.')
        time.sleep(sleep_time)
        continue

    if res.status != 200:
        logger('An error ocurred while trying to get a task from server.')
        time.sleep(sleep_time)
        continue

    data = res.read().decode()
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
    fp_map = open(config['pois'], 'r')
    fp_edus = open(config['output_edus'], 'r')

    req = request.Request(
        f'{os.getenv("API_URL")}/result',
        method='POST',
        headers={
            'Content-type': 'application/json'
        },
        data=json.dumps({
            'id': task['id'],
            'map': fp_map.read(),
            'edus': fp_edus.read()
        }).encode('utf-8')
    )

    fp_map.close()
    fp_edus.close()

    try:
        res = request.urlopen(req)
    except URLError:
        logger(f'The server reported an internal error.')
        time.sleep(sleep_time)
        continue

    if res.status == 201:
        logger(f'Results for {config["base_filename"]} sent successfully.')
    else:
        logger(f'The server reported an error for {config["base_filename"]} data.')
        time.sleep(sleep_time)
