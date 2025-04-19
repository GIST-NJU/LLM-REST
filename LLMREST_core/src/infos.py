import json
import os
import random
from typing import Set, List, Dict, Tuple, Optional

from loguru import logger
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from LLMREST_core.src.factor import AbstractFactor, ValueType, Value
from LLMREST_core.src.keywords import Method, DataType
from LLMREST_core.src.rest import RestOp


def decode_value_type(dct):
    for key, value in dct.items():
        if isinstance(value, str):
            try:
                dct[key] = ValueType(value)
            except ValueError:
                pass
    return dct


class Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ValueType):
            return o.value
        if isinstance(o, AbstractFactor):
            return o.get_global_name
        if isinstance(o, RestOp):
            return o.__repr__()
        if isinstance(o, tuple):
            return list(o)
        if isinstance(o, set):
            return list(o)
        if isinstance(o, Value):
            return o.val
        return super().default(o)


class Infos:
    def __init__(self, operations: List[RestOp]):
        self.operations = operations
        self.to_test: List[str] = [op.__repr__() for op in operations]
        self.test_sequence: Dict[str, Set[Tuple[str]]] = {"all": set()}
        for op in self.operations:
            self.test_sequence[op.__repr__()] = set()
        self.successful_operations: List[str] = []
        self.constraint: Dict[str, Dict[str, List[AbstractFactor]]] = {}
        self.llm_value: Dict[str, Dict[str, List[str]]] = {}
        self.allowed_constraints: Dict[str, Dict[str: List[Dict[str, ValueType]]]] = {}
        self.dependency: Dict[str, Dict[str, str]] = {}
        self.bindings: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.responses: Dict[str, List[Optional]] = {}
        self.confirmed_binding: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.response_values: Dict[str, List[str]] = {}
        self.producer = {}
        self.consumer = {}
        self.response_strings: Dict[str, Set[str]] = {}
        for op in operations:
            self.response_strings[op.__repr__()] = set()
        self.oracles: Dict[str, Dict[str, str]] = {}
        self.error_matched: Dict[str, Optional] = {}

    def save_test_sequence(self, sequence, op_to_test=None):
        if len(sequence) == len(self.operations):
            if "all" not in self.test_sequence:
                self.test_sequence["all"] = set()
            self.test_sequence["all"].add(tuple(sequence))

        if op_to_test is not None:
            self.test_sequence[op_to_test.__repr__()].add(tuple(sequence))
        else:
            for op in self.to_test:
                if op in sequence:
                    op_seq = sequence[0: sequence.index(op) + 1]
                    self.test_sequence[op].add(tuple(op_seq))

    def save_constraint(self, operation, constraints):
        if len(constraints) > 0:
            if operation.__repr__() not in self.constraint:
                self.constraint[operation.__repr__()] = dict()
            for constraint in constraints:
                if constraint not in self.constraint[operation.__repr__()]:
                    self.constraint[operation.__repr__()][constraint] = []
                for factor in operation.get_leaf_factors():
                    if factor.get_global_name in constraint and f"_{factor.get_global_name}" not in constraint and f"{factor.get_global_name}_" not in constraint:
                        self.constraint[operation.__repr__()][constraint].append(factor)
        else:
            if operation.__repr__() not in self.constraint:
                self.constraint[operation.__repr__()] = dict()

    def check_constraint_from_response(self, operation, constraints, case):
        if self.allowed_constraints.get(operation.__repr__(), None) is None:
            self.allowed_constraints[operation.__repr__()] = dict()
        for constraint in constraints:
            if constraint not in self.allowed_constraints[operation.__repr__()]:
                self.allowed_constraints[operation.__repr__()][constraint] = []
            related_factors = [f for f in operation.get_leaf_factors() if f.get_global_name in constraint and
                               f"_{f.get_global_name}" not in constraint and f"{f.get_global_name}_" not in constraint]
            pattern = {}
            for factor in related_factors:
                if factor.get_global_name in case:
                    pattern[factor.get_global_name] = case[factor.get_global_name].generator
            if len(pattern) == len(related_factors):
                if pattern not in self.allowed_constraints[operation.__repr__()][constraint]:
                    self.allowed_constraints[operation.__repr__()][constraint].append(pattern)

    def append_response(self, operation, response):
        if operation.__repr__() not in self.responses:
            self.responses[operation.__repr__()] = []
        if isinstance(response, dict) or isinstance(response, list):
            if len(response) == 0:
                return
        if len(self.responses[operation.__repr__()]) < 10:
            self.responses[operation.__repr__()].append(response)
        else:
            self.responses[operation.__repr__()].pop(0)
            self.responses[operation.__repr__()].append(response)

    def save_binding(self, operation, binding):
        if operation.__repr__() not in self.bindings:
            self.bindings[operation.__repr__()] = dict()
        if len(binding) == 0:
            return
        for factor, dependent_dicts in binding.items():
            if factor not in self.bindings[operation.__repr__()]:
                self.bindings[operation.__repr__()][factor] = dict()
            for op_str, dependent_list in dependent_dicts.items():
                self.bindings[operation.__repr__()][factor][op_str] = dependent_list

    def get_value_from_dict(self, info_dict, factor_name):
        try:
            for _ in factor_name.split("."):
                if _ == "response":
                    continue
                if _ == "_item":
                    if len(info_dict) > 0:
                        if random.uniform(0, 1) < 0.9:
                            info_dict = info_dict[0]
                        else:
                            info_dict = random.choice(info_dict)
                    else:
                        pass
                else:
                    info_dict = info_dict.get(_, None)
            return info_dict
        except:
            return None

    def get_dependent_values(self, op_str, dependent_factor):
        try:
            response_list = self.responses.get(op_str, [])
            if len(response_list) == 0:
                return []
            else:
                dependent_values = []
                for response in reversed(response_list):
                    if self.get_value_from_dict(response, dependent_factor) not in dependent_values:
                        if self.get_value_from_dict(response, dependent_factor) is not None:
                            dependent_values.append(self.get_value_from_dict(response, dependent_factor))
                return dependent_values
        except Exception as e:
            return []

    def save_dependency(self, operation, dependencies):
        if operation.__repr__() not in self.dependency:
            self.dependency[operation.__repr__()] = {}
        for f_name, op_str in dependencies.items():
            if op_str is not None:
                self.dependency[operation.__repr__()][f_name] = op_str
            else:
                self.dependency[operation.__repr__()][f_name] = None

    def confirm_binding(self, operation, case):
        # try:
        if operation.__repr__() in self.confirmed_binding:
            return
        else:
            for factor in operation.get_leaf_factors():
                if factor.get_global_name in case:
                    if case[factor.get_global_name].generator == ValueType.Dynamic:
                        if operation.__repr__() in self.bindings:
                            if factor.get_global_name in self.bindings[operation.__repr__()]:
                                if len(self.bindings[operation.__repr__()][factor.get_global_name]) > 0:
                                    self.confirmed_binding[operation.__repr__()] = dict()
                                    self.confirmed_binding[operation.__repr__()][factor.get_global_name] = \
                                        self.bindings[operation.__repr__()][factor.get_global_name]
        # except Exception as e:
        #     logger.error(f"Error in confirm binding: {e}")

    def query_confirmed_binding(self, operation, factors):
        # try:
        if operation.__repr__() not in self.confirmed_binding:
            self.confirmed_binding[operation.__repr__()] = dict()
        for factor in factors:
            op_to_check = []
            for op, factor_dict in self.confirmed_binding.items():
                if factor.get_global_name in factor_dict:
                    if {op: factor.get_global_name} not in op_to_check:
                        op_to_check.append({op: factor.get_global_name})
            for info in op_to_check:
                for op_str, factor_name in info.items():
                    factor_info_check = {}
                    for op in self.operations:
                        if op.__repr__() == op_str:
                            for f in op.get_leaf_factors():
                                if f.get_global_name == factor_name:
                                    factor_info_check.update({
                                        "name": f.get_global_name,
                                        "type": f.type,
                                        "description": f.description,
                                    })
                    factor_info = {
                        "name": factor.get_global_name,
                        "type": factor.type,
                        "description": factor.description,
                    }
                    check = True
                    for k, v in factor_info.items():
                        if v == factor_info_check.get(k, None):
                            pass
                        else:
                            check = False
                    if check:
                        self.confirmed_binding[operation.__repr__()][factor.get_global_name] = \
                            self.confirmed_binding[op_str][factor_name]
                        if operation.__repr__() not in self.bindings:
                            self.bindings[operation.__repr__()] = dict()
                        self.bindings[operation.__repr__()].update(
                            {factor.get_global_name: self.confirmed_binding[op_str][factor_name]})

        # except Exception as e:
        #     logger.error(f"Error in query confirmed binding: {e}")

    def extract_response_values(self, op, response):
        try:
            if isinstance(response, list):
                val = random.choice(response)
                self.extract_response_values(val, op)
            elif isinstance(response, dict):
                key, value = random.choice(list(response.items()))
                if key in self.response_values:
                    if value not in self.response_values[key]:
                        self.response_values[key].append(value)
                if isinstance(value, dict) or isinstance(value, list):
                    self.extract_response_values(value, op)
                else:
                    if key not in self.response_values:
                        self.response_values[key] = []
                    if value not in self.response_values[key]:
                        if key not in self.producer:
                            self.producer[key] = []
                        if op.__repr__() not in self.producer[key]:
                            if op.verb == Method.GET and len(self.producer[key]) > 0:
                                pass
                            else:
                                self.producer[key].append(op.__repr__())
                        self.response_values[key].append(value)
        except Exception as e:
            pass

    def save_response_data(self, op, response_data, case):
        value_set = set()
        for p, v in case.items():
            try:
                if v.type == DataType.String and v.val is not None and v.val != "":
                    value_set.add(v.val)
            except:
                pass
        if self.response_strings.get(op.__repr__()) is None:
            self.response_strings[op.__repr__()] = set()

        response = json.dumps(response_data)
        if len(response) == 0 or response in ["''", '""', " ", "", "{}", "[]", "null", "None"]:
            return
        response = response.strip('"').replace('\\"', '"').replace('\\\\', '\\')
        for v in value_set:
            if str(v) in response and len(str(v)) > 1:
                response = response.replace(str(v), "*")
                break
        if len(self.response_strings[op.__repr__()]) == 0:
            self.response_strings[op.__repr__()].add(response)
        else:
            added = True
            for response_str in self.response_strings[op.__repr__()]:
                if self.calculate_cosine_similarity(response, response_str) >= 0.7:
                    added = False
                    break
            if added:
                self.response_strings[op.__repr__()].add(response)

    @staticmethod
    def calculate_cosine_similarity(string1, string2):
        documents = [string1, string2]
        count_vectorizer = CountVectorizer()
        try:
            sparse_matrix = count_vectorizer.fit_transform(documents)
        except:
            return 1
        cosine_sim = cosine_similarity(sparse_matrix, sparse_matrix)
        similarity_value = cosine_sim[0][1]
        return similarity_value

    def save_oracle(self, oracle, operation):
        if operation.__repr__() not in self.oracles:
            self.oracles[operation.__repr__()] = dict()
        for factor, value in oracle.items():
            if factor not in self.oracles[operation.__repr__()] and factor != "":
                self.oracles[operation.__repr__()][factor] = value

    def save_fp(self, operation, case, response, direct_ancestor=None):
        if operation.__repr__() not in self.error_matched:
            self.error_matched[operation.__repr__()] = {}
            self.error_matched[operation.__repr__()]["consumer"] = []
            self.error_matched[operation.__repr__()]["producer"] = []
        if direct_ancestor is not None:
            if len(self.error_matched[operation.__repr__()]["consumer"]) < 3:
                self.error_matched[operation.__repr__()]["consumer"].append(
                    {"case": case, "ancestor": direct_ancestor.__repr(), "ancestor response": response})
        else:
            if len(self.error_matched[operation.__repr__()]["producer"]) < 3:
                self.error_matched[operation.__repr__()]["producer"].append({"case": case, "response": response})

    def load_saved_data(self, path):
        if not os.path.exists(path):
            return
        with open(path, "r") as f:
            data = json.load(f, object_hook=decode_value_type)
        self.dependency = data["dependency"]
        self.bindings = data["binding"]
        self.confirmed_binding = data["binding"]
        self.allowed_constraints = data["allowed_constraints"]
        try:
            self.test_sequence = data["sequences"]
            for op, seq in self.test_sequence.items():
                new_seq = set()
                for s in seq:
                    new_seq.add(tuple(s))
                self.test_sequence[op] = new_seq
            for op in self.operations:
                if op.__repr__() not in self.test_sequence:
                    self.test_sequence[op.__repr__()] = set()
        except:
            pass
        self.llm_value = data["llm_value"]
        for op in self.operations:
            if op.__repr__() in data["llm_value"]:
                for f in op.get_leaf_factors():
                    if f.get_global_name in data["llm_value"][op.__repr__()]:
                        f.llm_examples = data["llm_value"][op.__repr__()][f.get_global_name]
        constraint = data["constraints"]
        for op_str, constraints in constraint.items():
            self.constraint[op_str] = {}
            op = [op for op in self.operations if op.__repr__() == op_str][0]
            for constraint_str, factors_name in constraints.items():
                if op_str not in self.constraint:
                    self.constraint[op_str] = dict()
                self.constraint[op_str][constraint_str] = []
                for factor in op.get_leaf_factors():
                    if factor.get_global_name in factors_name:
                        self.constraint[op_str][constraint_str].append(factor)
        # self.oracles = data["oracle"]

    def save_data(self, path):
        example_value = {}
        for op in self.operations:
            example_value[op.__repr__()] = {}
            for f in op.get_leaf_factors():
                for v in f.llm_examples:
                    if f.get_global_name not in example_value[op.__repr__()]:
                        example_value[op.__repr__()][f.get_global_name] = []
                    if v not in example_value[op.__repr__()][f.get_global_name]:
                        example_value[op.__repr__()][f.get_global_name].append(v)
        with open(path, "w") as f:
            data = {
                "dependency": self.dependency,
                "binding": self.bindings,
                "allowed_constraints": self.allowed_constraints,
                "constraints": self.constraint,
                "llm_value": example_value,
                "sequences": self.test_sequence,
                "oracle": self.oracles,
                "error_matched": self.error_matched
            }
            json.dump(data, f, indent=2, cls=Encoder)
