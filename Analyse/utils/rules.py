import json
import re

from LLMREST_core.src.rest import HeaderParam, QueryParam

import yaml
from utils.nltk import *
import spacy
import Levenshtein


def A1_1(spec):
    obeyed_paths = []
    for path in spec.paths:
        url = path.url
        if not url.endswith("/"):
            obeyed_paths.append(url)
    return obeyed_paths


def A1_2(spec):
    obeyed_paths = []
    for path in spec.paths:
        url = path.url
        if not "_" in url:
            obeyed_paths.append(url)
    return obeyed_paths


def A1_3(spec):
    obeyed_paths = []
    for path in spec.paths:
        url = path.url
        if url == url.lower():
            obeyed_paths.append(url)
    return obeyed_paths


def A1_4(spec):
    obeyed_paths = []
    extensions = [".json", ".js", ".php", ".xml", ".gif", ".jpg", ".png", ".java", ".py", ".asp", ".jsp", ".html",
                  ".css", ".scss", ".less", ".ts", ".jsx", ".tsx", ".vue", ".php", ".rb", ".cs",
                  ".cpp", ".c", ".h", ".hpp", ".go", ".kt", ".swift", ".m", ".mm", ".php", ".pl", ".sh", ".bash",
                  ".zsh", ".ps1", ".bat", ".yaml", ".yml", ".html", ]
    for path in spec.paths:
        url = path.url
        add = True
        for ext in extensions:
            if ext in url:
                add = False
        if add:
            obeyed_paths.append(url)
    return obeyed_paths


def A2_1(spec):
    return has_relation(spec.paths)


def A3_1(spec):
    obeyed_paths = []
    words = [
        "create", "add", "generate", "produce", "construct", "make", "establish", "save", "insert",
        "read", "fetch", "acquire", "find", "search", "get", "retrieve", "list", "show", "display",
        "update", "renew", "modify", "revise", "change", "edit", "patch", "alter", "put", "replace",
        "delete", "remove", "erase", "destroy", "cancel", "terminate", "kill", "end", "stop",
    ]
    for path in spec.paths:
        url = path.url
        add = True
        for word in words:
            if word in url.lower():
                add = False
        if add:
            obeyed_paths.append(url)
    return obeyed_paths


def A3_2(spec):
    return not "api" in spec.servers[0].url.lower()


# def A3_4(spec):
#     return not "api" in spec.servers[0].url.lower()


# A4-1
def A4_1(operations):
    obeyed_operations = []
    param_used = {}
    keys = ["limit", "offset", "page", "per_page", "page size", "starting_after", "ending_before", "before",
            "search criteria", "created before", "created after", ]
    for op in operations:
        for param in op.parameters:
            if isinstance(param, QueryParam):
                param_name = param.factor.name
                for keyword in keys:
                    distance = Levenshtein.distance(keyword, param_name)
                    if distance <= 1:
                        if param_name not in param_used:
                            param_used[param_name] = 1
                        else:
                            param_used[param_name] += 1
                        if op not in obeyed_operations:
                            obeyed_operations.append(op)
                        break
    return obeyed_operations, param_used


# B1-1
def B1_1(operations):
    obeyed_operations = []
    standard_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "CONNECT", "OPTIONS", "TRACE", "HEAD"]
    for op in operations:
        if op.verb.value.upper() not in standard_methods:
            continue
        else:
            obeyed_operations.append(op.__repr__())
    return obeyed_operations


# B1-2
def B1_2(operations, spec):
    correct_used_operations = []
    problem_operations = []
    words_info = {
        "post": ["create", "add", "generate", "produce", "construct", "make", "establish", "save", "insert", ],
        "get": ["read", "fetch", "acquire", "find", "search", "get", "retrieve", "list", "show", "display", ],
        "put": ["update", "renew", "modify", "revise", "change", "edit", "patch", "alter", "put", "replace", ],
        "delete": ["delete", "remove", "erase", "destroy", "cancel", "terminate", "kill", "end", "stop", ],
    }
    a3_1_result = A3_1(spec)
    for op in operations:
        if op.path.__str__() not in a3_1_result:
            problem_operations.append(op.__repr__())
            if op.verb.value in words_info:
                for word in words_info[op.verb.value]:
                    if word in op.path.__str__().lower():
                        if op.__repr__() not in correct_used_operations:
                            correct_used_operations.append(op.__repr__())
    return correct_used_operations, problem_operations


# B2-1
def B2_1(spec):
    obeyed_operations = []
    status_codes = [
        100, 101,
        200, 201, 202, 204, 205, 206,
        300, 301, 302, 303, 304, 307, 308,
        400, 401, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414,
        415, 416, 417,
        500, 501, 502, 503, 504, 505
    ]
    status_code_used = {}
    for path in spec.paths:
        for op in path.operations:
            if op.responses is None:
                continue
            else:
                add = True
                for response in op.responses:
                    if response.code in status_codes:
                        if response.code not in status_code_used:
                            status_code_used[response.code] = 1
                        else:
                            status_code_used[response.code] += 1
                    else:
                        add = False
                if add:
                    obeyed_operations.append(op.__repr__())
    return obeyed_operations, status_code_used


# C1-1
def C1_1(spec):
    obeyed_operations = []
    for path in spec.paths:
        for op in path.operations:
            if op.responses is None:
                continue
            else:
                for response in op.responses:
                    headers = response.headers
                    if len(headers) > 0:
                        for header in headers:
                            if "content-type" in header.name.lower():
                                if op.__repr__() not in obeyed_operations:
                                    obeyed_operations.append(op.__repr__())
                                continue
    return obeyed_operations


# C1-2
def C1_2(operations):
    obeyed_operations = []
    for op in operations:
        for param in op.parameters:
            if isinstance(param, HeaderParam):
                if param.factor.name.lower() == "accept":
                    obeyed_operations.append(op.__repr__())
                    continue
    return obeyed_operations


# C1-3
def C1_3(operations):
    obeyed_operations = []
    keys = ["key", "token", "authorization"]
    for op in operations:
        for param in op.parameters:
            param_name = param.factor.name
            for keyword in keys:
                distance = Levenshtein.distance(keyword, param_name)
                if distance <= 1:
                    if op not in obeyed_operations:
                        obeyed_operations.append(op)
                    break
    return obeyed_operations


# C2-1
def C2_1(spec):
    obeyed_operations = []
    body_operations = []
    for path in spec.paths:
        for op in path.operations:
            if op.request_body is not None:
                body_operations.append(op.__repr__())
                for content in op.request_body.content:
                    if content.type.value == "application/json":
                        obeyed_operations.append(op.__repr__())
    return obeyed_operations, body_operations


# C2-2
def C2_2(spec):
    obeyed_operations = []
    for path in spec.paths:
        for op in path.operations:
            if op.responses is None:
                continue
            else:
                for response in op.responses:
                    try:
                        for prop in response.content[0].schema.properties:
                            prop_name = prop.name.lower()
                            if prop_name.lower() in ["links", "_links"]:
                                if op not in obeyed_operations:
                                    obeyed_operations.append(op)
                    except:
                        continue
    return obeyed_operations


def D1_1(operations):
    obeyed_operations = []
    for op in operations:
        for param in op.parameters:
            if isinstance(param, HeaderParam):
                if param.factor.name.lower() == "version":
                    if op.__repr__() not in obeyed_operations:
                        obeyed_operations.append(op.__repr__())
                    break
    return obeyed_operations


# D1-2
def D1_2(spec):
    obeyed_paths = []
    in_host = None
    for path in spec.paths:
        url = path.url
        if re.search(r"v(ers?|ersion)?[0-9.]+(-?(alpha|beta|rc)([0-9.]+\+?[0-9]?|[09]?))?", url.lower()):
            continue
        else:
            obeyed_paths.append(url)
    if re.search(r"v(ers?|ersion)?[0-9.]+(-?(alpha|beta|rc)([0-9.]+\+?[0-9]?|[09]?))?", spec.servers[0].url.lower()):
        in_host = True
    else:
        in_host = False
    return obeyed_paths, in_host


# D1-3
def D1_3(operations):
    obeyed_operations = []
    for op in operations:
        for param in op.parameters:
            if isinstance(param, QueryParam):
                if param.factor.name.lower() == "version":
                    if op.__repr__() not in obeyed_operations:
                        obeyed_operations.append(op.__repr__())
                    break
    return obeyed_operations


# D3-1
def D3_1(spec):
    keys = ["cache-control", "expires", "date"]
    obeyed_operations = []
    for path in spec.paths:
        for op in path.operations:
            if op.responses is None:
                continue
            else:
                for response in op.responses:
                    try:
                        headers = response.headers
                        if len(headers) > 0:
                            for header in headers:
                                if header.name.lower() in keys:
                                    if op.__repr__() not in obeyed_operations:
                                        obeyed_operations.append(op.__repr__())
                                    continue
                    except:
                        continue
    return obeyed_operations


# D3-2
def D3_2(spec):
    keys = ["etag", "last-modified"]
    obeyed_operations = []
    for path in spec.paths:
        for op in path.operations:
            if op.responses is None:
                continue
            else:
                for response in op.responses:
                    try:
                        headers = response.headers
                        if len(headers) > 0:
                            for header in headers:
                                if header.name.lower() in keys:
                                    if op.__repr__() not in obeyed_operations:
                                        obeyed_operations.append(op.__repr__())
                                    continue
                    except:
                        continue
    return obeyed_operations


def check(sut_name, spec, raw_spec, operations, obey_info):
    nlp = spacy.load('en_core_web_sm')

    A1_1_result = A1_1(spec)
    A1_2_result = A1_2(spec)
    A1_3_result = A1_3(spec)
    A1_4_result = A1_4(spec)
    A2_1_result = A2_1(spec)
    A3_1_result = A3_1(spec)
    A3_2_result = A3_2(spec)
    A4_1_op, A4_1_param = A4_1(operations)
    B1_1_result = B1_1(operations)
    B1_2_result, op_with_problem = B1_2(operations, spec)
    B2_1_result, status_code_used = B2_1(spec)
    C1_1_result = C1_1(spec)
    C1_2_result = C1_2(operations)
    C1_3_result = C1_3(operations)
    C2_1_result, body_operations = C2_1(spec)
    C2_2_result = C2_2(spec)
    D1_1_result = D1_1(operations)
    D1_2_result, in_host = D1_2(spec)
    D1_3_result = D1_3(operations)
    D3_1_result = D3_1(spec)
    D3_2_result = D3_2(spec)

    obey_info = obey_info._append({
        "SUT": sut_name,
        "A1-1": len(A1_1_result),
        "A1-2": len(A1_2_result),
        "A1-3": len(A1_3_result),
        "A1-4": len(A1_4_result),
        "A2-1": len(A2_1_result),
        "A3-1": len(A3_1_result),
        "A3-2": A3_2_result,
        "A4-1": len(A4_1_op),
        "B1-1": len(B1_1_result),
        "B1-2": len(B1_2_result),
        "Operations with Problem": len(op_with_problem),
        "B2-1": len(B2_1_result),
        "C1-1": len(C1_1_result),
        "C1-2": len(C1_2_result),
        "C1-3": len(C1_3_result),
        "C2-1": len(C2_1_result),
        "C2-2": len(C2_2_result),
        "D1-1": len(D1_1_result),
        "D1-2": len(D1_2_result),
        "In Host": in_host,
        "D1-3": len(D1_3_result),
        "D3-1": len(D3_1_result),
        "D3-2": len(D3_2_result),
        "Paths": len(spec.paths),
        "Operations": len(operations),
        "Body Operations": len(body_operations),
        "Parameters": len([param for op in operations for param in op.parameters]),
        "Status Codes": json.dumps(status_code_used),
        "Page Param": json.dumps(A4_1_param)
    }, ignore_index=True)

    return obey_info
