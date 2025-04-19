from pathlib import Path

from loguru import logger
from tqdm import tqdm
import os
import json

import requests
import yaml

current_file = Path(__file__).resolve()
guru_path = current_file.parents[0] / 'OAS' / 'raw_file' / 'guru'
swaggerhub_path = current_file.parents[0] / 'OAS' / 'raw_file' / 'swaggerhub'
tool_path = current_file.parents[0] / 'OAS' / 'raw_file' / 'tools'

guru_v3 = current_file.parents[0] / 'OAS' / 'v3_file' / 'guru'
swaggerhub_v3 = current_file.parents[0] / 'OAS' / 'v3_file' / 'swaggerhub'
tool_v3 = current_file.parents[0] / 'OAS' / 'v3_file' / 'tools'


def convert_swagger_to_openapi_3(raw_folder, v3_folder):
    convert_url = "https://converter.swagger.io/api/convert"

    for spec_name in tqdm(os.listdir(raw_folder)):
        sut_name = spec_name.split(".")[0]
        if os.path.exists(os.path.join(v3_folder, sut_name + ".yaml")):
            continue
        else:
            logger.info(f"Converting {sut_name}")
        try:
            if spec_name.endswith(".json"):
                with open(os.path.join(raw_folder, spec_name), "r", encoding="UTF-8") as f:
                    spec = json.load(f)
            else:
                with open(os.path.join(raw_folder, spec_name), "r", encoding="UTF-8") as f:
                    spec = yaml.load(f, Loader=yaml.FullLoader)
        except:
            continue
        if isinstance(spec, dict):
            if "swagger" in spec:
                if str(spec.get("swagger")).startswith("2"):
                    try:
                        response = requests.post(convert_url, json=spec)
                        if response.status_code == 200:
                            v3_spec = json.loads(response.text)
                            with open(os.path.join(v3_folder, sut_name + ".yaml"), "w") as f:
                                yaml.dump(v3_spec, f)
                        else:
                            continue
                    except:
                        continue
                else:
                    with open(os.path.join(v3_folder, sut_name + ".yaml"), "w") as f:
                        yaml.dump(spec, f)
            else:
                with open(os.path.join(v3_folder, sut_name + ".yaml"), "w") as f:
                    yaml.dump(spec, f)


if __name__ == '__main__':
    convert_swagger_to_openapi_3(guru_path, guru_v3)
    convert_swagger_to_openapi_3(swaggerhub_path, swaggerhub_v3)
    convert_swagger_to_openapi_3(tool_path, tool_v3)
