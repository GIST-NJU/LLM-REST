import json

import yaml
import requests
from loguru import logger
from tqdm import tqdm
import os
from pathlib import Path
from datetime import datetime

current_file = Path(__file__).resolve()


def download_guru():
    """
    Download the latest API specifications from the APIs.guru repository.
    """

    def check_version(versions: dict):
        format_str = '%Y-%m-%dT%H:%M:%S.%fZ'
        latest_time = datetime.strptime("2000-01-01T00:00:00.000Z", format_str).timestamp()
        latest_version = None
        for version, version_info in versions.items():
            update_time = version_info.get("added")
            if update_time:
                time = datetime.strptime(update_time, format_str)
                if time.timestamp() > latest_time:
                    latest_time = time.timestamp()
                    latest_version = version
        return latest_version

    save_path = current_file.parents[0] / 'OAS' / 'raw_file' / 'guru'

    meta_info_path = current_file.parents[0] / 'OAS' / 'guru_info.json'

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    if not os.path.exists(meta_info_path):
        logger.info("Getting metadata from APIs.guru...")
        url = "https://api.apis.guru/v2/list.json"

        response = requests.get(url)
        apis = response.json()

        with open(meta_info_path, "w") as f:
            json.dump(apis, f)

    with open(meta_info_path, "r") as file:
        apis = json.load(file)

    logger.info("Downloading API specifications from APIs.guru...")
    for api, info in tqdm(apis.items()):
        name_list = api.split(":")
        name = name_list[0].split(".")[0]
        if len(name_list) > 1:
            name += f"_{name_list[1]}"
        versions = info["versions"]
        if len(versions) > 1:
            latest_version = check_version(versions)
        else:
            latest_version = list(versions.keys())[-1]

        latest_version_info = versions[latest_version]
        version = latest_version.replace(".", "_")

        version_name = f"{name}_{version}.yaml"

        if version_name not in os.listdir(save_path):
            try:
                swagger_url = latest_version_info["swaggerUrl"]
                response = requests.get(swagger_url)
                spec = response.json()
                with open(os.path.join(save_path, version_name), "w") as f:
                    yaml.dump(spec, f)
            except Exception as e:
                continue


def download_swaggerhub():
    """
    Download the latest API specifications from the SwaggerHub repository.
    """

    def get_meta_data(meta_info_path):
        metadata = []
        offset = []
        info = {
            "offset": offset,
            "metadata": metadata
        }
        for i in tqdm(range(0, 100)):
            try:
                url = f"http://api.swaggerhub.com/specs?limit=100&page={i}&state=PUBLISHED"
                response = requests.get(url)
                data = response.json()
                if response.status_code == 200:
                    info["offset"].append(i)
                    for item in data.get("apis"):
                        info["metadata"].append(item)
                else:
                    logger.error(f"Error in {i}: {response.status_code}")
                with open(meta_info_path, "w") as f:
                    json.dump(info, f)
            except Exception as e:
                logger.error(f"Error in {i}: {e}")

    save_path = current_file.parents[0] / 'OAS' / 'raw_file' / 'swaggerhub'
    meta_info_path = current_file.parents[0] / 'OAS' / 'swaggerhub_info.json'

    if not os.path.exists(meta_info_path):
        logger.info("Getting metadata from SwaggerHub...")
        get_meta_data(meta_info_path)

    with open(meta_info_path, "r") as file:
        info = json.load(file)

    metadata = info["metadata"]

    logger.info("Downloading API specifications from SwaggerHub...")
    for info in tqdm(metadata):
        swagger_url = None
        version = None
        name = info["name"]
        properties = info["properties"]
        for prop in properties:
            if prop["type"] == "X-Version":
                version = prop["value"]
            if prop["type"] == "Swagger":
                swagger_url = prop["url"]
        if swagger_url is not None:
            file_name = f"{name.replace(' ', '_')}_{version}.yaml"
            if file_name not in os.listdir(save_path):
                try:
                    response = requests.get(swagger_url)
                    spec = response.json()
                    with open(os.path.join(save_path, file_name), "w") as f:
                        yaml.dump(spec, f)
                except Exception as e:
                    logger.error(f"Error: {e}")


if __name__ == '__main__':
    download_guru()
    download_swaggerhub()
