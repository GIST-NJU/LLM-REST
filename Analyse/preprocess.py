from pathlib import Path

import yaml
import json
import os

from tqdm import tqdm

current_file = Path(__file__).resolve()


guru_v3 = current_file.parents[0] / 'OAS' / 'v3_file' / 'guru'
swaggerhub_v3 = current_file.parents[0] / 'OAS' / 'v3_file' / 'swaggerhub'
tool_v3 = current_file.parents[0] / 'OAS' / 'v3_file' / 'tools'

guru_checked = current_file.parents[0] / 'OAS' / 'processed_file' / 'guru'
swaggerhub_checked = current_file.parents[0] / 'OAS' / 'processed_file' / 'swaggerhub'
tool_checked = current_file.parents[0] / 'OAS' / 'processed_file' / 'tools'

def read_file(file_path):
    if file_path.endswith(".yaml"):
        with open(file_path, "r", encoding="UTF-8") as yaml_file:
            return yaml.safe_load(yaml_file)
    elif file_path.endswith(".json"):
        with open(file_path, "r", encoding="UTF-8") as json_file:
            return json.load(json_file)
    else:
        raise Exception("Invalid file format")

def check_format(info):
    if isinstance(info, dict):
        if info.get("format") in ["uint32", "uint64", "int32", "int64"]:
            if info.get("format") == "uint32":
                info["format"] = "int32"
            if info.get("format") == "uint64":
                info["format"] = "int64"
            if info.get("type") != "integer":
                info["type"] = "integer"
        if info.get("type") == "file":
            info["type"] = "string"
        if info.get("format") == "datetime":
            info["format"] = "date-time"
        if info.get("format") in ["csv"]:
            info["format"] = "binary"
        if info.get("format") == "ip":
            info.pop("format")
    return info

def check_content(content, all_content_type):
    new_body_info = {}
    for content_type, content_info in content.items():
        if content_type not in all_content_type:
            new_body_info["application/json"] = content_info
        else:
            new_body_info[content_type] = content_info
        if content_info.get("schema"):
            content_info["schema"] = check_format(content_info.get("schema"))
    return new_body_info

def check_dict(info):
    if isinstance(info, dict):
        check_format(info)
        for key, value in info.items():
            if isinstance(value, dict):
                check_dict(value)
    elif isinstance(info, list):
        for item in info:
            return check_dict(item)
    elif isinstance(info, str):
        return info



# 纠正文件
def check(sut_name, spec, all_content_type):
    # check info
    if not spec.get("info"):
        spec["info"] = {
            "title": f"{sut_name} API",
            "version": "1.0.0"
        }

    # check path parameters
    for path, path_info in spec.get("paths").items():
        for method, method_info in path_info.items():
            if isinstance(method_info, dict):
                if method_info.get("parameters"):
                    for parameter in method_info.get("parameters"):
                        if parameter.get("in") == "path":
                            # check required
                            if parameter.get("required") is None or parameter.get("required") is False:
                                parameter["required"] = True

    # check content type
    for path, path_info in spec.get("paths").items():
        for method, method_info in path_info.items():
            if isinstance(method_info, dict):
                if method_info.get("requestBody"):
                    if method_info.get("requestBody").get("content"):
                        new_body_info = check_content(method_info.get("requestBody").get("content"), all_content_type)
                        method_info["requestBody"]["content"] = new_body_info

                if method_info.get("responses"):
                    for status_code, response_info in method_info.get("responses").items():
                        if response_info.get("content"):
                            new_response_info = check_content(response_info.get("content"), all_content_type)
                            response_info["content"] = new_response_info

    if spec.get("components"):
        if spec.get("components").get("responses"):
            for response_name, response_info in spec.get("components").get("responses").items():
                if response_info.get("content"):
                    new_response_info = check_content(response_info.get("content"), all_content_type)
                    response_info["content"] = new_response_info


    # convert invalid type and format
    check_dict(spec)

    for path, path_info in spec.get("paths").items():
        for method, method_info in path_info.items():
            if isinstance(method_info, dict):
                if method_info.get("parameters"):
                    for parameter in method_info.get("parameters"):
                        if parameter.get("schema"):
                            checked_info = check_format(parameter.get("schema"))
                            parameter["schema"] = checked_info

    if spec.get("components"):
        if spec.get("components").get("schemas"):
            for definition_name, definition_info in spec.get("components").get("schemas").items():
                if definition_info.get("properties"):
                    for property_name, property_info in definition_info.get("properties").items():
                        checked_info = check_format(property_info)
                        definition_info["properties"][property_name] = checked_info

    # default not in enum
    for path, path_info in spec.get("paths").items():
        for method, method_info in path_info.items():
            if isinstance(method_info, dict):
                if method_info.get("parameters"):
                    for parameter in method_info.get("parameters"):
                        if parameter.get("schema") and parameter.get("schema").get("enum"):
                            if parameter.get("schema").get("default") not in parameter.get("schema").get("enum"):
                                temp = {}
                                for key, value in parameter.get("schema").items():
                                    if key != "default":
                                        temp[key] = value
                                parameter["schema"] = temp

    # required in properties
    if spec.get("components"):
        if spec.get("components").get("schemas"):
            for definition_name, definition_info in spec.get("components").get("schemas").items():
                if definition_info.get("properties"):
                    for property_name, property_info in definition_info.get("properties").items():
                        if property_info.get("required") is not None:
                            property_info.pop("required")

    return spec


def pre_handle(raw_file_path, converted_file_path):
    all_content_type = ["application/json", "application/xml",
                        'application/x-www-form-urlencoded', 'multipart/form-data',
                        'text/plain', 'text/html', 'application/pdf', 'image/png',
                        'application/octet-stream']
    for file in tqdm(os.listdir(raw_file_path)):
        file_path = os.path.join(raw_file_path, file)

        destination_path = os.path.join(converted_file_path, file)
        sut_name = file.split(".")[0]
        if os.path.exists(destination_path):
            continue
        try:
            spec = read_file(file_path)
        except Exception as e:
            print(f"{e}")
            continue
        try:
            modified_spec = check(sut_name, spec, all_content_type)
            if file.endswith(".json"):
                with open(destination_path, "w") as file:
                    json.dump(modified_spec, file, indent=2)
            else:
                with open(destination_path, "w") as file:
                    yaml.dump(modified_spec, file)
        except Exception as e:
            print(f"Error in {sut_name}: {e}")
            if file.endswith(".json"):
                with open(destination_path, "w") as file:
                    json.dump(spec, file, indent=2)
            else:
                with open(destination_path, "w") as file:
                    yaml.dump(spec, file)

if __name__ == '__main__':
    pre_handle(guru_v3, guru_checked)
    pre_handle(swaggerhub_v3, swaggerhub_checked)
    pre_handle(tool_v3, tool_checked)
