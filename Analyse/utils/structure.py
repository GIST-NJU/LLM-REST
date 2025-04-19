import json
from typing import List

import numpy as np

from LLMREST_core.src.factor import BooleanFactor, EnumFactor, ArrayFactor, ObjectFactor
from LLMREST_core.src.rest import RestOp, QueryParam, PathParam, BodyParam


def get_type_format(factor, type):
    if factor.type and factor.type.value != "NONE":
        if factor.type.value not in type:
            type[factor.type.value] = {"num": 1, "format": []}
        else:
            type[factor.type.value]["num"] += 1
            if hasattr(factor, "format") and factor.format is not None:
                if factor.format not in type[factor.type.value]["format"]:
                    type[factor.type.value]["format"].append(factor.format)
    return type


def count_structure_metrics(spec: dict, operations: List[RestOp]):
    """
    Structure Metrics:
    1. paths: Total number of paths defined in the OpenAPI spec.
    2. operations: Total number of operations (HTTP methods) defined across all paths.
    3. used_methods: Number of unique HTTP methods used in the spec.
    4. parametered_operations: Number of operations that define parameters.
    5. distinct_parameters: Unique parameter names across all operations.
    6. parameters_per_operations: Average number of parameters per operation.
     Formula: (Total parameters) / (Total operations)
    7. used_parameters: Total number of parameters used across all operations.
    8. parametric_operations: Number of operations that use query or path parameters.
    9. path_depth: Average depth of the path
    10. example_rate: The rate of parameters that have examples
    11. default_rate: The rate of parameters that have default values
    """

    operation_num = len(operations)
    if operation_num == 0:
        return None

    path_num = len(spec.get("paths"))

    used_methods = set()
    method_num = {}
    for operation in operations:
        used_methods.add(operation.verb.value)
        if operation.verb.value not in method_num:
            method_num[operation.verb.value] = 1
        else:
            method_num[operation.verb.value] += 1

    depths = [len(operation.path.elements) for operation in operations]
    average_depth = sum(depths) / len(depths)
    variance = np.var(depths)

    parametered_operations = [operation for operation in operations if len(operation.parameters) > 0]

    distinct_parameters = set()
    for operation in operations:
        for factor in operation.get_leaf_factors():
            distinct_parameters.add(factor.name)

    used_parameters = [factor for operation in operations for factor in operation.get_leaf_factors()]
    if operation_num == 0:
        parameters_per_operations = 0
    else:
        parameters_per_operations = len(used_parameters) / operation_num

    parametric_operations = []
    for operation in operations:
        for param in operation.parameters:
            if isinstance(param, QueryParam) or isinstance(param, PathParam):
                parametric_operations.append(operation)
                break

    example_factor = [factor for factor in used_parameters if len(factor.all_examples) > 0]
    default_factor = []
    for factor in used_parameters:
        if hasattr(factor, "_default"):
            if factor._default is not None:
                default_factor.append(factor)
    example_rate = len(example_factor) / len(used_parameters) if len(used_parameters) > 0 else 0
    default_rate = len(default_factor) / len(used_parameters) if len(used_parameters) > 0 else 0

    ex_body_params = []
    for operation in operations:
        for param in operation.parameters:
            if isinstance(param, BodyParam):
                continue
            else:
                ex_body_params.append(param.factor)

    type = {}
    for operation in operations:
        for param in operation.parameters:
            if isinstance(param, BodyParam):
                type = get_type_format(param.factor, type)
                for factor in param.factor.get_leaves():
                    type = get_type_format(factor, type)
            else:
                if isinstance(param.factor, ArrayFactor) or isinstance(param.factor, ObjectFactor):
                    type = get_type_format(param.factor, type)
                    for factor in param.factor.get_leaves():
                        type = get_type_format(factor, type)
                else:
                    type = get_type_format(param.factor, type)

    structure_metrics = {
        "paths": path_num,
        "operations": operation_num,
        "used_methods": len(used_methods),
        "parametered_operations": len(parametered_operations),
        "distinct_parameters": len(distinct_parameters),
        "parameters_per_operations": parameters_per_operations,
        "used_parameters": len(used_parameters),
        "ex_body_params": len(ex_body_params),
        "parametric_operations": len(parametric_operations),
        "path_depth": average_depth,
        "path_depth_variance": variance,
        "example_rate": example_rate,
        "default_rate": default_rate,
        "type": json.dumps(type),
        "method_num": json.dumps(method_num)
    }

    return structure_metrics
