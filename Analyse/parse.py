import signal
from pathlib import Path

from loguru import logger

from utils.structure import *
from utils.schema import *
from utils.nlp import *
import spacy
import pandas as pd
import os
from tqdm import tqdm

from utils.nlp import count_nlp_metrics
from utils.schema import count_schema_metrics
from utils.structure import count_structure_metrics
from utils.rules import *

from LLMREST_core.src.swagger import SwaggerParser

current_file = Path(__file__).resolve()

guru_checked = current_file.parents[0] / 'OAS' / 'processed_file' / 'guru'
swaggerhub_checked = current_file.parents[0] / 'OAS' / 'processed_file' / 'swaggerhub'
tool_checked = current_file.parents[0] / 'OAS' / 'processed_file' / 'tools'

guru_save = current_file.parents[0] / 'data' / 'guru'
swaggerhub_save = current_file.parents[0] / 'data' / 'swaggerhub'
tool_save = current_file.parents[0] / 'data' / 'tools'


def recursion_limit_handler(limit, parsed_url, recursions=()):
    """https://github.com/RonnyPfannschmidt/prance/blob/main/COMPATIBILITY.rst"""
    return None


def timeout_handler(signum, frame):
    raise TimeoutError


def init_data_frame(data_path):
    if os.path.exists(f'{data_path}/structure_info.csv'):
        structure_info = pd.read_csv(os.path.join(data_path, "structure_info.csv")).drop(columns=['Unnamed: 0'])
        data_model_info = pd.read_csv(os.path.join(data_path, "data_model_info.csv")).drop(columns=['Unnamed: 0'])
        nlp_info = pd.read_csv(os.path.join(data_path, "nlp_info.csv")).drop(columns=['Unnamed: 0'])
        obey_info = pd.read_csv(os.path.join(data_path, "obey_info.csv")).drop(columns=['Unnamed: 0'])
    else:
        structure_info = pd.DataFrame(
            columns=["SUT", "Paths", "Methods", "Operations", "Parametric Operations", "Parametered Operations",
                     "Used Parameters", "Distinct Parameters", "Parameters Per Operations", "Path Depth",
                     "Path Depth Variance", "Example Rate", "Default Rate", "Type", "Method Count"])
        data_model_info = pd.DataFrame(
            columns=["SUT", "Defined Schemas", "Distinct Used Schemas", "Properties", "Used Properties",
                     "Distinct Used Properties", "Properties Per Schema"])
        nlp_info = pd.DataFrame(
            columns=["SUT", "CLI_Index", "ARI_Index", "Described Operations Rate", "Described Parameters Rate",
                     "Described Property Rate", "Described Operations"])
        obey_info = pd.DataFrame(
            columns=["SUT", "A1-1", "A1-2", "A1-3", "A1-4",
                     "A2-1",
                     "A3-1", "A3-2",
                     "A4-1",
                     "B1-1", "B1-2", "Operations with Problem",
                     "B2-1",
                     "C1-1", "C1-2", "C1-3",
                     "C2-1", "C2-2",
                     "D1-1", "D1-2", "In Host", "D1-3",
                     "D3-1", "D3-2",
                     "Paths",
                     "Operations",
                     "Body Operations",
                     "Parameters",
                     "Status Codes"
                     ]
        )

    return structure_info, data_model_info, nlp_info, obey_info


def load_suts(swagger_path, spec_file, error_suts):
    sut_path = str(swagger_path / spec_file)
    try:
        parser = SwaggerParser(str(sut_path))
        operations = parser.extract()
        spec = parser._swagger
        if sut_path.endswith(".json"):
            with open(sut_path, 'r') as file:
                raw_spec = json.load(file)
        elif sut_path.endswith(".yaml"):
            with open(sut_path, 'r') as file:
                raw_spec = yaml.safe_load(file)
    except:
        error_suts.append(spec_file.split(".")[0])
        return None, None, None

    return spec, raw_spec, operations


def parse_structure_metrics(raw_spec, operations, sut_name, error_suts, structure_info):
    structure_metrics = count_structure_metrics(raw_spec, operations)
    if structure_metrics is None:
        error_suts.append(sut_name)
        return structure_info, None
    structure_info = structure_info._append({
        "SUT": sut_name,
        "Paths": structure_metrics["paths"],
        "Methods": structure_metrics["used_methods"],
        "Operations": structure_metrics["operations"],
        "Parametric Operations": structure_metrics["parametric_operations"],
        "Parametered Operations": structure_metrics["parametered_operations"],
        "Used Parameters": structure_metrics["used_parameters"],
        "Distinct Parameters": structure_metrics["distinct_parameters"],
        "Parameters Per Operations": structure_metrics["parameters_per_operations"],
        "Path Depth": structure_metrics["path_depth"],
        "Path Depth Variance": structure_metrics["path_depth_variance"],
        "Example Rate": structure_metrics["example_rate"],
        "Default Rate": structure_metrics["default_rate"],
        "Type": structure_metrics["type"],
        "Method Count": structure_metrics["method_num"]
    }, ignore_index=True)

    return structure_info, structure_metrics


def parse_data_model_metrics(raw_spec, data_model_info, sut_name):
    data_model_metrics = count_schema_metrics(raw_spec)
    data_model_info = data_model_info._append({
        "SUT": sut_name,
        "Defined Schemas": data_model_metrics["defined_schemas"],
        "Distinct Used Schemas": data_model_metrics["used_schemas"],
        "Properties": data_model_metrics["properties"],
        "Used Properties": data_model_metrics["used_properties"],
        "Distinct Used Properties": data_model_metrics["distinct_properties"],
        "Properties Per Schema": data_model_metrics["properties"] / data_model_metrics["defined_schemas"]
        if data_model_metrics["defined_schemas"] > 0 else 0
    }, ignore_index=True)

    return data_model_info, data_model_metrics


def parse_nlp_metrics(raw_spec, operations, nlp, sut_name, error_suts, nlp_info, data_model_metrics):
    nlp_metrics = count_nlp_metrics(raw_spec, operations, nlp)
    if nlp_metrics is None:
        error_suts.append(sut_name)
        return nlp_info, None
    nlp_info = nlp_info._append({
        "SUT": sut_name,
        "CLI_Index": nlp_metrics["cli_index"],
        "ARI_Index": nlp_metrics["ari_index"],
        "Described Operations Rate": nlp_metrics["operation_description_coverage_rate"],
        "Described Parameters Rate": nlp_metrics["parameter_description_coverage_rate"],
        "Described Property Rate": data_model_metrics["described_properties"] / data_model_metrics["properties"]
        if data_model_metrics["properties"] > 0 else 0,
        "Described Operations": nlp_metrics["described_endpoints"],
    }, ignore_index=True)

    return nlp_info, nlp_metrics


def parse_spec_metrics(sut_name, spec, raw_spec, operations, obey_info):
    obey_info = check(sut_name, spec, raw_spec, operations, obey_info)
    return obey_info


def parse(data_path, swagger_path):
    error_suts = []

    structure_info, data_model_info, nlp_info, obey_info = init_data_frame(data_path)

    nlp = spacy.load("en_core_web_sm")
    nlp.max_length = 2000000

    num = 0
    for spec_file in tqdm(os.listdir(swagger_path)):
        num += 1
        sut_name = spec_file.split(".")[0]
        logger.debug(f"Processing sut: {sut_name}")

        processed_suts = structure_info.SUT.to_list()

        if sut_name in processed_suts:
            logger.debug(f"Already processed: {sut_name}")
            continue

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(60)
        try:
            spec, raw_spec, operations = load_suts(swagger_path, spec_file, error_suts)
            if spec is None:
                logger.debug(f"Error loading spec: {sut_name}")
                continue
        except TimeoutError:
            print(f"Time out")
            error_suts.append(sut_name)
            continue
        finally:
            signal.alarm(0)

        structure_info, structure_metrics = parse_structure_metrics(raw_spec, operations, sut_name, error_suts,
                                                                    structure_info)
        if structure_metrics is None:
            continue

        data_model_info, data_model_metrics = parse_data_model_metrics(raw_spec, data_model_info, sut_name)

        nlp_info, nlp_metrics = parse_nlp_metrics(raw_spec, operations, nlp, sut_name, error_suts, nlp_info,
                                                  data_model_metrics)
        if nlp_metrics is None:
            continue

        obey_info = parse_spec_metrics(sut_name, spec, raw_spec, operations, obey_info)

        structure_info.to_csv(os.path.join(data_path, "structure_info.csv"))
        data_model_info.to_csv(os.path.join(data_path, "data_model_info.csv"))
        nlp_info.to_csv(os.path.join(data_path, "nlp_info.csv"))
        obey_info.to_csv(os.path.join(data_path, "obey_info.csv"))

    return error_suts


if __name__ == '__main__':
    # guru_error_suts = parse(guru_save, guru_checked)
    swaggerhub_error_suts = parse(swaggerhub_save, swaggerhub_checked)
    # tool_error_suts = parse(tool_save, tool_checked)
