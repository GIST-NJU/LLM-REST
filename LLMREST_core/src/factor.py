import abc
import base64
import datetime
import os
import random
import re
import string
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any, List, Union, Tuple

import Levenshtein
import rstr

from LLMREST_core.src.keywords import DataType


class ValueType(Enum):
    Enum = "enum"
    Default = "default"
    Example = "example"
    Random = "random"
    Dynamic = "dynamic"
    Blank = "blank"
    NULL = "Null"


@dataclass(frozen=True)
class Value:
    val: object = None
    generator: ValueType = ValueType.NULL
    type: DataType = DataType.NULL


class AbstractFactor(metaclass=abc.ABCMeta):
    value_nums = 2
    """
    Abstract class for Factors
    """

    def __init__(self, name: str):
        self.name: str = name
        self.description: Optional[str] = None
        self.type: DataType = DataType.NULL
        # Set the required flag to true
        self.required: bool = False
        self.parent: Optional[AbstractFactor] = None

        self.examples: list = []
        self.llm_examples: list = []
        self._default: Optional[Any] = None
        self.format = None
        self.is_constraint = False
        self.domain: list[Value] = list()
        # self.isReuse: bool = False

        self.dependency_value = []
        self._mutate_values = []
        self.set_mutate_values(self._mutate_values)

        self.value = None

    @staticmethod
    def get_ref(ref: str, definitions: dict):
        """get definition with the ref name"""
        return definitions.get(ref.split("/")[-1], {})

    @property
    def is_essential(self):
        return self.is_constraint or self.required

    def see_all_factors(self) -> List:
        """get factors itself and its children"""
        if self.name is None or self.name == "":
            return list()
        else:
            return [self]

    def gen_domain(self, infos, succeeded=False):
        pass

    def gen_random_domain(self, infos, method=None, succeeded=False):
        pass

    def gen_dependency_value(self, op, infos):
        self.dependency_value.clear()
        if self.get_global_name in infos.bindings.get(op.__repr__(), {}):
            dependent_dict = infos.bindings[op.__repr__()][self.get_global_name]
            if len(dependent_dict) > 0:
                for op_str, dependent_factor in dependent_dict.items():
                    dependent_values = infos.get_dependent_values(op_str, dependent_factor)
                    if len(dependent_values) > 0:
                        self.dependency_value.extend(dependent_values[0:min(4, len(dependent_values))])

    @staticmethod
    def _analyse_url_relation(op, op_set, param_name):
        high_weight = list()
        low_weight = list()
        url = op.path.__repr__()
        for candidate in op_set:
            other_url = candidate.path.__repr__()
            if other_url.strip("/") == url.split("{" + param_name + "}")[0].strip("/"):
                high_weight.append(candidate)
            elif other_url.strip("/") == url.split("{" + param_name + "}")[0].strip("/") + "/{" + param_name + "}":
                high_weight.append(candidate)
            else:
                low_weight.insert(0, candidate)
        return high_weight, low_weight

    @staticmethod
    def find_dynamic(paramName, response, path=None):
        if re.search(r"[-_]?id[-_]?", paramName) is not None:
            name = "id"
        if path is None:
            path = []
        if isinstance(response, list):
            local_path = path[:]
            if response:
                for result in AbstractFactor.find_dynamic(paramName, response[0], local_path):
                    yield result
        elif isinstance(response, dict):
            for k, v in response.items():
                local_path = path[:]
                similarity = AbstractFactor.match(paramName, k)
                if similarity > 0.9:
                    local_path.append(k)
                    yield local_path, similarity, v
                elif isinstance(v, (list, dict)):
                    local_path.append(k)
                    for result in AbstractFactor.find_dynamic(paramName, v, local_path[:]):
                        yield result
        else:
            pass

    @staticmethod
    def match(str_a, str_b):
        str_a = "".join(c for c in str_a if c.isalnum())
        str_b = "".join(c for c in str_b if c.isalnum())
        distance = Levenshtein.distance(str_a.lower(), str_b.lower())
        length_total = len(str_a) + len(str_b)
        return round((length_total - distance) / length_total, 2)

    def add_domain_to_map(self, domain_map: dict):
        if len(self.domain) > 0:
            domain_map[self.get_global_name] = self.domain
        return domain_map

    def set_value(self, case):
        self.value = None
        for name, value in case.items():
            if name == self.get_global_name:
                self.value = value

    def printable_value(self, response=None):
        if self.value is not None:
            if self.value.val == "blank":
                return ""
            else:
                return self.value.val
        else:
            return None

    @staticmethod
    def _assemble_dynamic(path, response):
        value = response
        for p in path:
            if isinstance(value, list):
                try:
                    value = value[0]
                except IndexError:
                    return None
            try:
                value = value.get(p)
            except (AttributeError, TypeError):
                return None
            else:
                if value is None:
                    return None
        return value

    def get_leaves(self) -> Tuple:
        """
        Get all leaves of the factor tree,
        excluding arrays and objects themselves.
        """
        return self,

    def get_mutate_value(self):
        # if random.random() < 0.1:
        #     param_type = random.choice([StringFactor, IntegerFactor, NumberFactor, BooleanFactor])
        # else:
        #     param_type = self.__class__
        #
        # if param_type == StringFactor:
        #     if self.format is None:
        #         param_format = random.choice(['date', 'date-time', 'password', 'byte', 'binary'])
        #     else:
        #         param_format = self.format
        #
        #     if param_format == 'date':
        #         random_date = datetime.date.fromtimestamp(
        #             random.randint(0, int(datetime.datetime.now().timestamp())))
        #         return random_date.strftime('%Y-%m-%d'), param_type
        #     elif param_format == 'date-time':
        #         random_datetime = datetime.datetime.fromtimestamp(
        #             random.randint(0, int(datetime.datetime.now().timestamp())))
        #         return random_datetime.strftime('%Y-%m-%dT%H:%M:%SZ'), param_type
        #     elif param_format == 'password':
        #         random_password_length = random.randint(5, 10)
        #         characters = string.ascii_letters + string.digits + string.punctuation
        #         return ''.join(random.choice(characters) for _ in range(random_password_length)), param_type
        #     elif param_format == 'byte':
        #         random_byte_length = random.randint(1, 10)
        #         return base64.b64encode(os.urandom(random_byte_length)).decode('utf-8'), param_type
        #     elif param_format == 'binary':
        #         random_binary_length = random.randint(1, 10)
        #         return ''.join(random.choice(['0', '1']) for _ in range(random_binary_length)), param_type
        # elif param_type == IntegerFactor:
        #     return random.randint(-100000, 100000), param_type
        # elif param_type == NumberFactor:
        #     return random.uniform(-100000, 100000), param_type
        # elif param_type == BooleanFactor:
        #     return random.choice([True, False]), param_type
        # else:
        #     return None
        mutated = random.choices(self._mutate_values,
                                 weights=[x[1] for x in self._mutate_values], k=1)[0]
        self._mutate_values.remove(mutated)
        self._mutate_values.append((mutated[0], mutated[1] * 0.9))
        return mutated[0]

    def wrap_mutate_value(self, mutate_value, param_type):
        if param_type == StringFactor:
            return Value(mutate_value, ValueType.Random, DataType.String)
        if param_type == IntegerFactor:
            return Value(mutate_value, ValueType.Random, DataType.Integer)
        if param_type == NumberFactor:
            return Value(mutate_value, ValueType.Random, DataType.Number)
        if param_type == BooleanFactor:
            return Value(mutate_value, ValueType.Random, DataType.Bool)

    def __repr__(self):
        return self.get_global_name

    @property
    def get_global_name(self):
        if self.parent is not None:
            return f"{self.parent.get_global_name}.{self.name}"
        else:
            return self.name

    def __hash__(self):
        return hash(self.get_global_name)

    def __eq__(self, other):
        if isinstance(other, self.__class__) and self.get_global_name == other.get_global_name:
            return True
        else:
            return False

    def set_description(self, text: str):
        if text is None:
            return
        if text.startswith("'"):
            text = text[1:]
        if text.endswith("'"):
            text = text[:-1]
        if text.startswith('"'):
            text = text[1:]
        if text.endswith('"'):
            text = text[:-1]
        text = text.strip()
        if len(text) == 0:
            return
        self.description = text

    def set_example(self, example):
        parsed_example = self._spilt_example(example)
        if parsed_example is not None:
            for e in parsed_example:
                if e not in self.examples:
                    self.examples.append(e)

    def set_llm_example(self, example):
        parsed_example = self._spilt_example(example)
        if parsed_example is not None:
            for e in parsed_example:
                if e not in self.llm_examples:
                    self.llm_examples.append(e)

    def clear_llm_example(self):
        self.llm_examples.clear()

    @property
    def all_examples(self):
        return self.examples + self.llm_examples

    @staticmethod
    def _spilt_example(example) -> Union[list, None]:
        if example is None:
            return None
        if isinstance(example, list):
            return example
        if isinstance(example, dict):
            raise ValueError("Example cannot be a dict")
        return [example]

    def set_default(self, default_value):
        if default_value is not None:
            self._default = default_value

    def mutate_example(self, value):
        if random.uniform(0, 1) < 0.2:
            if self.__class__ == StringFactor:
                random_string = ''.join(
                    random.choice(string.ascii_letters) for _ in range(random.randint(1, 5)))
                return value + random_string
            elif self.__class__ == IntegerFactor:
                return value + random.randint(-2, 10)
            elif self.__class__ == NumberFactor:
                return value + random.uniform(-2, 10)
        else:
            return value

    def set_mutate_values(self, to_update):
        for t in {StringFactor, BooleanFactor, IntegerFactor, NumberFactor, ArrayFactor, ObjectFactor}:
            if isinstance(self, t):
                continue
            else:
                if t is StringFactor:
                    to_update.append((Value("blank", ValueType.Blank, DataType.String), 1))
                    random_date = datetime.date.fromtimestamp(
                        random.randint(0, int(datetime.datetime.now().timestamp())))
                    to_update.append((Value(random_date.strftime('%Y-%m-%d'), ValueType.Random, DataType.String), 1))
                    random_datetime = datetime.datetime.fromtimestamp(
                        random.randint(0, int(datetime.datetime.now().timestamp())))
                    to_update.append(
                        (Value(random_datetime.strftime('%Y-%m-%dT%H:%M:%SZ'), ValueType.Random, DataType.String), 1))
                    random_password_length = random.randint(5, 10)
                    characters = string.ascii_letters + string.digits + string.punctuation
                    password = ''.join(random.choice(characters) for _ in range(random_password_length))
                    to_update.append((Value(password, ValueType.Random, DataType.String), 1))
                    random_byte_length = random.randint(1, 10)
                    byte_str = base64.b64encode(os.urandom(random_byte_length)).decode('utf-8')
                    to_update.append((Value(byte_str, ValueType.Random, DataType.String), 1))
                    random_binary_length = random.randint(1, 10)
                    binary_str = ''.join(random.choice(['0', '1']) for _ in range(random_binary_length))
                    to_update.append((Value(binary_str, ValueType.Random, DataType.String), 1))
                elif t is IntegerFactor:
                    to_update.append((Value(random.randint(-100000, 100000), ValueType.Random, DataType.Integer), 1))
                    to_update.append((Value(0, ValueType.Random, DataType.Integer), 1))
                    to_update.append((Value(-1, ValueType.Random, DataType.Integer), 1))
                    to_update.append((Value(random.randint(100000000, 1000000000), ValueType.Random, DataType.Integer), 1))
                elif t is NumberFactor:
                    to_update.append((Value(random.uniform(-100000, 100000), ValueType.Random, DataType.Number), 1))
                    to_update.append((Value(0.0, ValueType.Random, DataType.Number), 1))
                    to_update.append((Value(-1.0, ValueType.Random, DataType.Number), 1))
                    to_update.append(
                        (Value(random.randint(100000000, 1000000000), ValueType.Random, DataType.Integer), 1))
                elif t is BooleanFactor:
                    to_update.append((Value(True, ValueType.Random, DataType.Bool), 1))
                    to_update.append((Value(False, ValueType.Random, DataType.Bool), 1))
                elif isinstance(t, ArrayFactor):
                    to_update.append((Value([], ValueType.NULL, DataType.Array), 1))
                elif isinstance(t, ObjectFactor):
                    to_update.append((Value({}, ValueType.NULL, DataType.Object), 1))
                else:
                    pass
        if (Value(None, ValueType.NULL, self.type), 1) not in to_update:
            to_update.append((Value(None, ValueType.NULL, self.type), 1))


class StringFactor(AbstractFactor):
    def __init__(self, name: str, format: str = None, min_length: int = 0, max_length: int = 100, pattern: str = None):
        super().__init__(name)
        self.type = DataType.String
        self.format = format
        self.minLength = min_length
        self.maxLength = max_length
        self.pattern = pattern

    def gen_domain(self, infos, succeeded=False):
        self.domain.clear()
        if len(self.dependency_value) > 0:
            for v in self.dependency_value:
            # v = random.choice(self.dependency_value)
                self.domain.append(Value(v, ValueType.Dynamic, DataType.String))
        else:
            if self.name in infos.response_values:
                self.domain.append(
                    Value(random.choice(infos.response_values[self.name]), ValueType.Dynamic, DataType.String))

        self.domain.append(Value("blank", ValueType.Blank, DataType.String))

        if self._default is not None:
            self.domain.append(Value(self._default, ValueType.Default, DataType.String))
        if len(self.examples) > 0:
            self.domain.append(Value(random.choice(self.examples), ValueType.Example, DataType.String))
        if len(self.llm_examples) > 0:
            if len(self.domain) == 0:
                for e in random.sample(self.llm_examples, min(2, len(self.llm_examples))):
                    if succeeded:
                        self.domain.append(Value(self.mutate_example(e), ValueType.Example, DataType.String))
                    else:
                        self.domain.append(Value(e, ValueType.Example, DataType.String))
            else:
                if random.uniform(0, 1) < 0.8:
                    if succeeded:
                        self.domain.append(
                            Value(self.mutate_example(random.choice(self.llm_examples)), ValueType.Example,
                                  DataType.String))
                    else:
                        self.domain.append(Value(self.llm_examples[0], ValueType.Example, DataType.String))
                else:
                    for e in random.sample(self.llm_examples, min(2, len(self.llm_examples))):
                        if succeeded:
                            self.domain.append(Value(self.mutate_example(e), ValueType.Example, DataType.String))
                        else:
                            self.domain.append(Value(e, ValueType.Example, DataType.String))

        if self.format is not None:
            self.gen_domain_by_format(infos, succeeded=succeeded)
        else:
            self.gen_random_domain(infos, succeeded=succeeded)

        if not self.required:
            self.domain.append(Value(None, ValueType.NULL, DataType.String))

    def gen_domain_by_format(self, infos, succeeded):
        if self.pattern is not None:
            if random.uniform(0, 1) < 0.7:
                random_string = rstr.xeger(self.pattern)
                self.domain.append(Value(str(random_string), ValueType.Random, DataType.String))
        if self.format == "date":
            random_date = datetime.date.fromtimestamp(
                random.randint(0, int(datetime.datetime.now().timestamp()))).strftime('%Y-%m-%d')
            self.domain.append(Value(str(random_date), ValueType.Random, DataType.String))
        elif self.format == "date-time":
            random_datetime = datetime.datetime.fromtimestamp(
                random.randint(0, int(datetime.datetime.now().timestamp())))
            self.domain.append(Value(str(random_datetime), ValueType.Random, DataType.String))
        elif self.format == "password":
            random_password_length = random.randint(5, 10)
            characters = string.ascii_letters + string.digits + string.punctuation
            password = ''.join(random.choice(characters) for _ in range(random_password_length))
            self.domain.append(Value(password, ValueType.Random, DataType.String))
        elif self.format == "byte":
            random_byte_length = random.randint(1, 10)
            byte_str = base64.b64encode(os.urandom(random_byte_length)).decode('utf-8')
            self.domain.append(Value(str(byte_str), ValueType.Random, DataType.String))
        elif self.format == "binary":
            random_binary_length = random.randint(1, 10)
            binary_str = ''.join(random.choice(['0', '1']) for _ in range(random_binary_length))
            self.domain.append(Value(binary_str, ValueType.Random, DataType.String))
        else:
            self.gen_random_domain(infos, succeeded=succeeded)

    def gen_random_domain(self, infos, method=None, succeeded=False):
        if method == "random":
            self.domain.clear()
            if len(self.dependency_value) > 0:
                self.domain.append(Value(random.choice(self.dependency_value), ValueType.Dynamic, DataType.String))
            else:
                if self.name in infos.response_values:
                    self.domain.append(
                        Value(random.choice(infos.response_values[self.name]), ValueType.Dynamic, DataType.String))

            if succeeded:
                if len(self.all_examples) > 0:
                    self.domain.append(Value(self.mutate_example(random.choice(self.all_examples)), ValueType.Example,
                                             DataType.String))
            else:
                if len(self.all_examples) > 0:
                    self.domain.append(Value(random.choice(self.all_examples), ValueType.Example, DataType.String))
            for i in range(0, 2):
                if random.uniform(0, 1) < 0.8:
                    # mutate_value, param_type = self.get_mutate_value()
                    # self.domain.append(self.wrap_mutate_value(mutate_value, param_type))
                    self.domain.append(self.get_mutate_value())
                else:
                    if random.uniform(0, 1) < 0.5:
                        if random.uniform(0, 1) < 0.99:
                            random_string = ''.join(random.choice(string.ascii_letters) for _ in
                                                    range(random.randint(self.minLength, self.maxLength)))
                        else:
                            random_string = ''.join(random.choice(string.ascii_letters) for _ in range(1, 10000))
                    else:
                        if random.uniform(0, 1) < 0.99:
                            random_string = ''.join(
                                random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in
                                range(random.randint(self.minLength, self.maxLength)))
                        else:
                            random_string = ''.join(
                                random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in
                                range(1, 10000))
                    self.domain.append(Value(random_string, ValueType.Random, DataType.String))
            if succeeded:
                self.domain.append(Value(None, ValueType.NULL, DataType.String))
            else:
                if not self.required:
                    self.domain.append(Value(None, ValueType.NULL, DataType.String))
        else:
            random_string = ''.join(
                random.choice(string.ascii_letters) for _ in range(random.randint(self.minLength, self.maxLength)))
            self.domain.append(Value(random_string, ValueType.Random, DataType.String))


class IntegerFactor(AbstractFactor):
    def __init__(self, name: str, minimum: int = None, maximum: int = None):
        super().__init__(name)
        self.type = DataType.Integer
        self.minimum = minimum
        self.maximum = maximum

    def gen_domain(self, infos, succeeded=False):
        self.domain.clear()

        if len(self.dependency_value) > 0:
            for v in self.dependency_value:
            # v = random.choice(self.dependency_value)
                self.domain.append(Value(v, ValueType.Dynamic, DataType.Integer))
        else:
            if self.name in infos.response_values:
                self.domain.append(
                    Value(random.choice(infos.response_values[self.name]), ValueType.Dynamic, DataType.Integer))

        if self._default is not None:
            self.domain.append(Value(self._default, ValueType.Default, DataType.Integer))

        if len(self.examples) > 0:
            self.domain.append(Value(random.choice(self.examples), ValueType.Example, DataType.Integer))
        if len(self.llm_examples) > 0:
            if len(self.domain) == 0:
                for e in random.sample(self.llm_examples, min(2, len(self.llm_examples))):
                    if succeeded:
                        self.domain.append(Value(self.mutate_example(e), ValueType.Example, DataType.Integer))
                    else:
                        self.domain.append(Value(e, ValueType.Example, DataType.Integer))
            else:
                for e in random.sample(self.llm_examples, min(2, len(self.llm_examples))):
                    if succeeded:
                        self.domain.append(Value(self.mutate_example(e), ValueType.Example, DataType.Integer))
                    else:
                        self.domain.append(Value(e, ValueType.Example, DataType.Integer))

        self.gen_random_domain(infos, succeeded=succeeded)

        if not self.required:
            self.domain.append(Value(None, ValueType.NULL, DataType.Integer))

    def gen_random_domain(self, infos, method=None, succeeded=False):
        if method == "random":
            self.domain.clear()
            if len(self.dependency_value) > 0:
                self.domain.append(Value(random.choice(self.dependency_value), ValueType.Dynamic, DataType.Integer))
            else:
                if self.name in infos.response_values:
                    self.domain.append(
                        Value(random.choice(infos.response_values[self.name]), ValueType.Dynamic, DataType.Integer))
            if len(self.all_examples) > 0:
                self.domain.append(Value(random.choice(self.all_examples), ValueType.Example, DataType.Integer))

            if random.uniform(0, 1) < 0.6:
                for i in range(0, 2):
                    # mutate_value, param_type = self.get_mutate_value()
                    # self.domain.append(self.wrap_mutate_value(mutate_value, param_type))
                    self.domain.append(self.get_mutate_value())
            else:
                if random.uniform(0, 1) < 0.6:
                    random_int = self.gen_random_value()
                    self.domain.append(Value(random_int, ValueType.Random, DataType.Integer))
                else:
                    self.gen_edge_domain()
            if succeeded:
                self.domain.append(Value(None, ValueType.NULL, DataType.Integer))
            else:
                if not self.required:
                    self.domain.append(Value(None, ValueType.NULL, DataType.Integer))
        else:
            random_int = self.gen_random_value()
            self.domain.append(Value(random_int, ValueType.Random, DataType.Integer))

    def gen_edge_domain(self):
        for value in [0,  -1]:
            self.domain.append(Value(value, ValueType.Default, DataType.Integer))

    def gen_random_value(self):
        if self.minimum is not None and self.maximum is not None:
            random_int = random.randint(self.minimum, self.maximum)
            return random_int
        elif self.minimum is not None:
            random_int = random.randint(self.minimum, self.minimum + 100000000)
            return random_int
        elif self.maximum is not None:
            random_int = random.randint(self.maximum - 100000000, self.maximum)
            return random_int
        else:
            random_int = random.randint(-100000000, 100000000)
            return random_int


class NumberFactor(AbstractFactor):
    def __init__(self, name: str, minimum: int = None, maximum: int = None):
        super().__init__(name)
        self.type = DataType.Number
        self.minimum = minimum
        self.maximum = maximum

    def gen_domain(self, infos, succeeded=False):
        self.domain.clear()

        if len(self.dependency_value) > 0:
            for v in self.dependency_value:
            # v = random.choice(self.dependency_value)
                self.domain.append(Value(v, ValueType.Dynamic, DataType.Number))
        else:
            if self.name in infos.response_values:
                self.domain.append(
                    Value(random.choice(infos.response_values[self.name]), ValueType.Dynamic, DataType.Number))

        if self._default is not None:
            self.domain.append(Value(self._default, ValueType.Default, DataType.Number))

        if len(self.examples) > 0:
            self.domain.append(Value(random.choice(self.examples), ValueType.Example, DataType.Number))
        if len(self.llm_examples) > 0:
            if len(self.domain) == 0:
                for e in random.sample(self.llm_examples, min(2, len(self.llm_examples))):
                    if succeeded:
                        self.domain.append(Value(self.mutate_example(e), ValueType.Example, DataType.Number))
                    else:
                        self.domain.append(Value(e, ValueType.Example, DataType.Number))
            else:
                for e in random.sample(self.llm_examples, min(2, len(self.llm_examples))):
                    if succeeded:
                        self.domain.append(Value(self.mutate_example(e), ValueType.Example, DataType.Number))
                    else:
                        self.domain.append(Value(e, ValueType.Example, DataType.Number))

        self.gen_random_domain(infos, succeeded=succeeded)

        if not self.required:
            self.domain.append(Value(None, ValueType.NULL, DataType.Number))

    def gen_random_domain(self, infos, method=None, succeeded=False):
        if method == "random":
            self.domain.clear()
            if len(self.dependency_value) > 0:
                self.domain.append(Value(random.choice(self.dependency_value), ValueType.Dynamic, DataType.Number))
            else:
                if self.name in infos.response_values:
                    self.domain.append(
                        Value(random.choice(infos.response_values[self.name]), ValueType.Dynamic, DataType.Number))

            if succeeded:
                if len(self.all_examples) > 0:
                    self.domain.append(Value(self.mutate_example(random.choice(self.all_examples)), ValueType.Example,
                                             DataType.Number))
            else:
                if len(self.all_examples) > 0:
                    self.domain.append(Value(random.choice(self.all_examples), ValueType.Example, DataType.Number))

            if random.uniform(0, 1) < 0.6:
                for i in range(0, 2):
                    # mutate_value, param_type = self.get_mutate_value()
                    # self.domain.append(self.wrap_mutate_value(mutate_value, param_type))
                    self.domain.append(self.get_mutate_value())
            else:
                if random.uniform(0, 1) < 0.6:
                    random_number = self.gen_random_value()
                    self.domain.append(Value(random_number, ValueType.Random, DataType.Number))
                else:
                    self.gen_edge_domain()
            if succeeded:
                self.domain.append(Value(None, ValueType.NULL, DataType.Number))
            else:
                if not self.required:
                    self.domain.append(Value(None, ValueType.NULL, DataType.Integer))
        else:
            random_number = self.gen_random_value()
            self.domain.append(Value(random_number, ValueType.Random, DataType.Number))

    def gen_edge_domain(self):
        for value in [0.0, -1.0]:
            self.domain.append(Value(value, ValueType.Default, DataType.Number))

    def gen_random_value(self):
        if self.minimum is not None and self.maximum is not None:
            random_number = random.uniform(self.minimum, self.maximum)
            return random_number
        elif self.minimum is not None:
            random_number = random.uniform(self.minimum, self.minimum + 10000)
            return random_number
        elif self.maximum is not None:
            random_number = random.uniform(self.maximum - 10000, self.maximum)
            return random_number
        else:
            random_number = random.uniform(-1000, 1000)
            return random_number


class BooleanFactor(AbstractFactor):
    def __init__(self, name: str):
        super().__init__(name)
        self.type = DataType.Bool

    def gen_domain(self, infos, succeeded=False):
        self.domain.clear()
        self.domain.append(Value(True, ValueType.Enum, DataType.Bool))
        self.domain.append(Value(False, ValueType.Enum, DataType.Bool))
        if not self.required:
            self.domain.append(Value(None, ValueType.Enum, DataType.Bool))

    def gen_random_domain(self, infos, method=None, succeeded=False):
        if method == "random":
            self.domain.clear()
            for i in range(0, 2):
                if random.uniform(0, 1) < 0.6:
                    # mutate_value, param_type = self.get_mutate_value()
                    # self.domain.append(self.wrap_mutate_value(mutate_value, param_type))
                    self.domain.append(self.get_mutate_value())
                else:
                    random_bool = random.choice([True, False])
                    if Value(random_bool, ValueType.Random, DataType.Bool) not in self.domain:
                        self.domain.append(Value(random_bool, ValueType.Random, DataType.Bool))
        else:
            random_bool = random.choice([True, False])
            self.domain.append(Value(random_bool, ValueType.Random, DataType.Bool))


class ObjectFactor(AbstractFactor):
    def __init__(self, name: str):
        super().__init__(name)
        self.type = DataType.Object

        self.properties: List[AbstractFactor] = []

    def add_property(self, p: AbstractFactor):
        self.properties.append(p)
        p.parent = self

    def gen_domain(self, infos, succeeded=False):
        self.domain.clear()
        for p in self.properties:
            p.gen_domain(infos, succeeded)

    def gen_random_domain(self, infos, method=None, succeeded=False):
        self.domain.clear()
        for p in self.properties:
            p.gen_random_domain(infos, method, succeeded)

    def add_domain_to_map(self, domain_map: dict):
        for p in self.properties:
            p.add_domain_to_map(domain_map)
        return domain_map

    def set_value(self, case):
        self.value = None
        for p in self.properties:
            p.set_value(case)
        property_not_none = [p for p in self.properties if p.printable_value() is not None]
        if len(property_not_none) > 0:
            self.value = {}
            for p in property_not_none:
                self.value[p.name] = p.printable_value()
        else:
            if random.uniform(0, 1) < 0.5:
                self.value = None
            else:
                self.value = {}

    def get_leaves(self) -> Tuple:
        leaves = []
        for p in self.properties:
            leaves.extend(p.get_leaves())
        return tuple(leaves)

    def printable_value(self, response=None):
        if self.value is None:
            return None
        return self.value


class ArrayFactor(AbstractFactor):
    def __init__(self, name: str):
        super().__init__(name)
        self.type = DataType.Array
        self.item: Optional[AbstractFactor] = None

    def set_item(self, item: AbstractFactor):
        self.item = item
        self.item.parent = self

    def gen_domain(self, infos, succeeded=False):
        self.domain.clear()
        if self.item is not None:
            self.item.gen_domain(infos, succeeded)

    def gen_random_domain(self, infos, method=None, succeeded=False):
        self.domain.clear()
        if self.item is not None:
            self.item.gen_random_domain(infos, method, succeeded)

    def add_domain_to_map(self, domain_map: dict):
        if self.item is not None:
            self.item.add_domain_to_map(domain_map)
        return domain_map

    def set_value(self, case):
        self.value = None
        self.item.set_value(case)
        if self.item.printable_value() is not None:
            self.value = []
            self.value.append(self.item.printable_value())

    def get_leaves(self) -> Tuple:
        return self.item.get_leaves()

    def printable_value(self, response=None):
        if self.value is None:
            return None
        return self.value


class EnumFactor(AbstractFactor):
    def __init__(self, name: str, enum_value: list):
        super().__init__(name)
        self.enum_value = enum_value

    def gen_domain(self, infos, succeeded=False):
        self.domain.clear()
        for e in self.enum_value:
            self.domain.append(Value(e, ValueType.Enum, DataType.NULL))
        if not self.required:
            self.domain.append(Value(None, ValueType.NULL, DataType.String))

    def gen_random_domain(self, infos, method=None, succeeded=False):
        self.domain.clear()
        for e in self.enum_value:
            self.domain.append(Value(e, ValueType.Enum, DataType.NULL))
        if not self.required:
            self.domain.append(Value(None, ValueType.NULL, DataType.String))
