import json
from typing import List

import prance
import yaml

from LLMREST_core.src.rest import RestOp


# schema



def find_schema_in_schema(spec, used_schemas):
    new_used_schemas = set()
    for schema in used_schemas:
        new_used_schemas.add(schema)
        schema_info = spec["components"]["schemas"][schema]
        if "items" in schema_info:
            if "$ref" in schema_info["items"]:
                ref_string = schema_info["items"]["$ref"]
                schema_name = ref_string.split("/")[-1]
                if schema_name in spec["components"]["schemas"]:
                    new_used_schemas.add(schema_name)
        if "properties" in schema_info:
            for prop, prop_data in schema_info["properties"].items():
                if "$ref" in prop_data:
                    ref_string = prop_data["$ref"]
                    schema_name = ref_string.split("/")[-1]
                    if schema_name in spec["components"]["schemas"]:
                        new_used_schemas.add(schema_name)
                if "items" in prop_data:
                    if "$ref" in prop_data["items"]:
                        ref_string = prop_data["items"]["$ref"]
                        schema_name = ref_string.split("/")[-1]
                        if schema_name in spec["components"]["schemas"]:
                            new_used_schemas.add(schema_name)
    if new_used_schemas == used_schemas:
        return new_used_schemas
    else:
        return find_schema_in_schema(spec, new_used_schemas)


def find_used_schema(spec):
    used_schemas = set()
    if spec.get("paths") and len(spec.get("paths")) > 0:
        for path, path_data in spec["paths"].items():
            for method, method_data in path_data.items():
                if isinstance(method_data, dict):
                    if "requestBody" in method_data:
                        body_info = method_data["requestBody"]
                        if "content" in body_info:
                            for content_type, content_data in body_info["content"].items():
                                if "schema" in content_data:
                                    if "$ref" in content_data["schema"]:
                                        ref_string = content_data["schema"]["$ref"]
                                        used_schema = ref_string.split("/")[-1]
                                        if used_schema in spec["components"]["schemas"]:
                                            used_schemas.add(used_schema)
                    if "responses" in method_data:
                            for response_code, response_data in method_data["responses"].items():
                                if "content" in response_data:
                                    for content_type, content_data in response_data["content"].items():
                                        if "schema" in content_data:
                                            if "$ref" in content_data["schema"]:
                                                ref_string = content_data["schema"]["$ref"]
                                                used_schema = ref_string.split("/")[-1]
                                                if used_schema in spec["components"]["schemas"]:
                                                    used_schemas.add(used_schema)
    used_schemas = find_schema_in_schema(spec, used_schemas)
    return used_schemas


# properties
def count_properties(spec):
    properties = list()
    described_properties = list()
    if spec.get("components"):
        if spec["components"].get("schemas"):
            for schema, schema_data in spec["components"]["schemas"].items():
                if "properties" in schema_data:
                    for prop, prop_data in schema_data["properties"].items():
                        properties.append(prop)
                        if "description" in prop_data:
                            described_properties.append(prop)
    if spec.get("paths") and len(spec.get("paths")) > 0:
        for path, path_data in spec["paths"].items():
            for method, method_data in path_data.items():
                if isinstance(method_data, dict):
                    if "requestBody" in method_data:
                        body_info = method_data["requestBody"]
                        if "content" in body_info:
                            for content_type, content_data in body_info["content"].items():
                                if "schema" in content_data:
                                    if "properties" in content_data["schema"]:
                                        for prop, prop_data in content_data["schema"]["properties"].items():
                                            properties.append(prop)
                                            if "description" in prop_data:
                                                described_properties.append(prop)
                    if "responses" in method_data:
                            for response_code, response_data in method_data["responses"].items():
                                if "content" in response_data:
                                    for content_type, content_data in response_data["content"].items():
                                        if "schema" in content_data:
                                           if "properties" in content_data["schema"]:
                                                for prop, prop_data in content_data["schema"]["properties"].items():
                                                    properties.append(prop)
                                                    if "description" in prop_data:
                                                        described_properties.append(prop)

    return properties, described_properties


def find_used_properties(used_schemas, spec):
    used_properties = list()
    for schema in used_schemas:
        schema_info = spec["components"]["schemas"][schema]
        if "properties" in schema_info:
            for prop, prop_data in schema_info["properties"].items():
                used_properties.append(prop)
    if spec.get("paths") and len(spec.get("paths")) > 0:
        for path, path_data in spec["paths"].items():
            for method, method_data in path_data.items():
                if isinstance(method_data, dict):
                    if "requestBody" in method_data:
                        body_info = method_data["requestBody"]
                        if "content" in body_info:
                            for content_type, content_data in body_info["content"].items():
                                if "schema" in content_data:
                                    if "properties" in content_data["schema"]:
                                        for prop, prop_data in content_data["schema"]["properties"].items():
                                            used_properties.append(prop)
                    if "responses" in method_data:
                            for response_code, response_data in method_data["responses"].items():
                                if "content" in response_data:
                                    for content_type, content_data in response_data["content"].items():
                                        if "schema" in content_data:
                                           if "properties" in content_data["schema"]:
                                                for prop, prop_data in content_data["schema"]["properties"].items():
                                                    used_properties.append(prop)
    return used_properties


def find_distinct_properties(used_properties):
    distinct_properties = set()
    for prop in used_properties:
        distinct_properties.add(prop)
    return distinct_properties


def count_schema_metrics(spec: dict):
    """
    Schema Metrics:
    1. defined_schemas: Number of schemas explicitly defined in the `components.schemas` section (from bundled OpenAPI spec).
    2. used_schemas: Number of schemas used in the `requestBody` and `response` sections of the OpenAPI spec.
    3. properties: Total number of properties across all schemas.
    4. used_properties: Number of properties used in the `requestBody` and `response` sections of the OpenAPI spec.
    5. distinct_properties: Unique property names across all schemas.
    """

    defined_schemas = spec.get("components", {}).get("schemas", {})
    if len(defined_schemas) == 0:
        schema_metrics = {
            "defined_schemas": 0,
            "used_schemas": 0,
            "properties": 0,
            "used_properties": 0,
            "distinct_properties": 0,
            "described_properties": 0,
        }
        return schema_metrics

    used_schemas = find_used_schema(spec)
    properties, described_properties = count_properties(spec)
    used_properties = find_used_properties(used_schemas, spec)
    distinct_properties = find_distinct_properties(used_properties)

    schema_metrics = {
        "defined_schemas": len(defined_schemas),
        "used_schemas": len(used_schemas),
        "properties": len(properties),
        "used_properties": len(used_properties),
        "distinct_properties": len(distinct_properties),
        "described_properties": len(described_properties),
    }

    return schema_metrics
