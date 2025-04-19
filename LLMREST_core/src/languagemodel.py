import json
import os
import time
import random

from loguru import logger
from openai import OpenAI

from LLMREST_core.src.factor import StringFactor, NumberFactor, BooleanFactor, IntegerFactor, ArrayFactor, ObjectFactor
from LLMREST_core.src.swagger import SwaggerParser
from LLMREST_core.src.configs import *
from LLMREST_core.src.infos import Infos
from LLMREST_core.src.utils import count_tokens
from LLMREST_core.src.prompt import *


def get_type(factor):
    if isinstance(factor, StringFactor):
        return "string"
    elif isinstance(factor, NumberFactor):
        return "number"
    elif isinstance(factor, BooleanFactor):
        return "boolean"
    elif isinstance(factor, IntegerFactor):
        return "integer"
    elif isinstance(factor, ArrayFactor):
        return "array"
    elif isinstance(factor, ObjectFactor):
        return "body"


class LanguageModel:
    def __init__(self, config):
        if config.api_key is None:
            raise ValueError("OPENAI API key is required for OpenAI language model, found None.")
        else:
            self.api_key = config.api_key
        self.base_url = config.openai_url if config.openai_url is not None else None

        self.client = OpenAI(api_key=self.api_key) if self.base_url is None else OpenAI(api_key=self.api_key, base_url=self.base_url)

        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = 8000

    def call(self, messages, temperature=0.2):
        if len(messages) == 0:
            return None, None
        num_tokens = count_tokens(messages, self.model)
        if num_tokens > self.max_tokens:
            logger.warning("Query length exceeds the maximum limit, please reduce the number of tokens")
            return "", messages
        count = 0
        while count < 3:
            try:
                start_time = time.time()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    top_p=0.99,
                    frequency_penalty=0,
                    presence_penalty=0,
                    max_tokens=4096,
                    response_format={"type": "json_object"}
                )
                end_time = time.time()
                logger.info(f"Time taken for response: {end_time - start_time}")
                return response.choices[0].message.content, messages
            except Exception as e:
                logger.error(f"Error in calling language model: {e}")
                logger.error("Retrying...")
                count += 1
        return "", messages


class OperationModel(LanguageModel):
    def __init__(self, config):
        super().__init__(config)

    def generate_prompt(self, infos, op_to_test):
        op_info = []
        for operation in infos.operations:
            op_info.append(
                {
                    "name": operation.__repr__(),
                    "description": operation.description,
                }
            )
        user_prompt = OPERATION_PROMPT.format(op_info, op_to_test)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}]
        return messages

    def generate_new_sequence(self, infos, op_to_test):
        messages = self.generate_prompt(infos, op_to_test)
        response, _ = self.call(messages)
        sequence = json.loads(response)["sequence"]
        infos.save_test_sequence(sequence, op_to_test)
        return sequence

    def generate_initial_seq(self, infos):
        op_info = []
        for operation in infos.operations:
            op_info.append(
                {
                    "name": operation.__repr__(),
                    "description": operation.description,
                }
            )
        user_prompt = initial_sequence.format(op_info)
        messages = [{"role": "user", "content": user_prompt}]
        response, _ = self.call(messages)
        sequence = json.loads(response)["sequence"]
        infos.save_test_sequence(sequence)
        return sequence


class ConstraintModel(LanguageModel):
    def __init__(self, config):
        super().__init__(config)

    def generate_prompt(self, operation):
        info = []
        leaves = [f.get_global_name for f in operation.get_leaf_factors()]
        for f in operation.get_leaf_factors():
            if f.description is not None:
                if "(deprecated)" in f.description.lower():
                    continue
            info.append(
                {
                    "name": f.get_global_name,
                    "type": get_type(f),
                    "description": f.description,
                }
            )
        user_prompt = IDL_PROMPT.format(leaves, info)
        messages = [{"role": "system", "content": SYS_IDL}, {"role": "user", "content": user_prompt}]
        return messages

    def extract_constraint(self, infos, operation):
        messages = self.generate_prompt(operation)
        response, _ = self.call(messages)
        constraints = json.loads(response)["constraints"]
        infos.save_constraint(operation, constraints)
        return constraints


class ValueModel(LanguageModel):
    def __init__(self, config):
        super().__init__(config)

    def generate_prompt(self, infos, operation, factor_to_ask, method=None):
        info = list()
        for f in factor_to_ask:
            f_info = {
                "name": f.get_global_name,
                "type": get_type(f),
            }
            if f.description is not None:
                f_info["description"] = f.description
            info.append(f_info)
        if method == "new":
            responses = infos.response_strings[operation.__repr__()]
        else:
            responses = []
        prompt = VALUE_PROMPT.format(operation.__repr__(), info, infos.constraint[operation.__repr__()].keys(),
                                     responses)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
        return messages

    def save_value(self, operation, factor_to_ask, value, infos):
        for factor in factor_to_ask:
            if factor.get_global_name in value:
                factor.llm_examples.extend(value[factor.get_global_name])
                if factor.get_global_name not in infos.llm_value[operation.__repr__()]:
                    infos.llm_value[operation.__repr__()][factor.get_global_name] = value[factor.get_global_name]
                else:
                    for val in value[factor.get_global_name]:
                        if val not in infos.llm_value[operation.__repr__()][factor.get_global_name]:
                            infos.llm_value[operation.__repr__()][factor.get_global_name].append(val)

    def generate_value(self, infos, operation, factor_to_ask, method=None):
        messages = self.generate_prompt(infos, operation, factor_to_ask, method)
        logger.info(f"Generating value for params of {operation.__repr__()}")
        response, _ = self.call(messages, 0.7)
        values = json.loads(response)
        self.save_value(operation, factor_to_ask, values, infos)


class DependencyModel(LanguageModel):
    def __init__(self, config):
        super().__init__(config)

    def generate_dependency_prompt(self, infos, operation):
        op_info = {
            "name": operation.__repr__(),
            "description": operation.description,
        }
        tested_infos = []
        for op in infos.operations:
            if op.__repr__() in infos.successful_operations:
                tested_infos.append(
                    {
                        "name": op.__repr__(),
                        "description": op.description,
                    }
                )
        param_info = []
        essential_params = [f for f in operation.get_leaf_factors() if f.is_essential]
        infos.query_confirmed_binding(operation, essential_params)
        # ask_params = essential_params
        ask_params = [f for f in essential_params if
                      f.get_global_name not in infos.confirmed_binding[operation.__repr__()]]
        if len(ask_params) == 0:
            return []
        for f in ask_params:
            param_info.append(
                {
                    "name": f.get_global_name,
                    "type": get_type(f),
                    "description": f.description,
                }
            )
        user_prompt = BINDING.format(op_info, param_info, tested_infos)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}]
        return messages

    def extract_dependency(self, infos, operation):
        messages = self.generate_dependency_prompt(infos, operation)
        if len(messages) == 0:
            return None, []
        logger.info(f"Extracting dependency for {operation.__repr__()}")
        response, _ = self.call(messages)
        dependencies = json.loads(response)
        messages.append({"role": "system", "content": response})
        infos.save_dependency(operation, dependencies)
        return dependencies, messages

    def find_key_name(self, info, name="response", key_name_list=None):
        key_name_list = key_name_list if key_name_list is not None else []
        if isinstance(info, list):
            new_name = name + "._item"
            for item in info:
                self.find_key_name(item, new_name, key_name_list)
        if isinstance(info, dict):
            for key, value in info.items():
                new_name = name + f".{str(key)}"
                self.find_key_name(value, new_name, key_name_list)
        else:
            if name not in key_name_list:
                key_name_list.append(name)
        return key_name_list

    def find_response_key(self, responses):
        key_name_list = []
        for response in responses:
            name_list = self.find_key_name(response)
            for name in name_list:
                if name not in key_name_list:
                    key_name_list.append(name)
        return key_name_list

    def generate_bind_prompt(self, ops, infos, messages):
        try:
            dependent_info = {}
            for op in ops:
                dependent_info[op.__repr__()] = []
                if len(op.responses) > 0:
                    success_responses = [response for response in op.responses if 200 <= response.status_code < 300]
                    if len(success_responses) == 0:
                        dependent_info[op.__repr__()] = self.find_response_key(infos.responses[op.__repr__()])
                        continue
                    else:
                        for response in success_responses:
                            if len(response.contents) == 0:
                                continue
                            else:
                                response_factor = response.contents[0][1]
                                for factor in response_factor.get_leaves():
                                    dependent_info[op.__repr__()].append(factor.get_global_name)
                                if len(dependent_info[op.__repr__()]) > 100:
                                    dependent_info[op.__repr__()] = self.find_response_key(infos.responses[op.__repr__()])
                                else:
                                    break
                        if len(dependent_info[op.__repr__()]) == 0:
                            dependent_info[op.__repr__()] = self.find_response_key(infos.responses[op.__repr__()])
                else:
                    dependent_info[op.__repr__()] = self.find_response_key(infos.responses[op.__repr__()])
            user_prompt = FIND_PARAM.format(dependent_info) + FIND_PARAM_TASK
            messages.append({"role": "user", "content": user_prompt})
            return messages
        except Exception as e:
            logger.error(f"Error in generating bind prompt: {e}")
            return None

    def bind_parameters(self, infos, operation):
        if operation.__repr__() in infos.bindings:
            logger.info(f"Binding already exists for {operation.__repr__()}")
        else:
            if len(infos.successful_operations) == 0:
                logger.info(f"No successful operations found")
            else:
                dependencies, messages = self.extract_dependency(infos, operation)
                if dependencies is None:
                    if len(infos.bindings.get(operation.__repr__())) == 0:
                        logger.info(f"No dependent operations found")
                        infos.save_binding(operation, {})
                        return {}
                    else:
                        logger.info(f"Binding already exists for {operation.__repr__()}")
                        return infos.bindings.get(operation.__repr__())
                dependent_op = set()
                for factor, op_str in dependencies.items():
                    if op_str is not None:
                        dependent_op.add(op_str)
                if len(dependent_op) == 0:
                    infos.save_binding(operation, {})
                    logger.info(f"No dependent operations found")
                else:
                    ops = [op for op in infos.operations if op.__repr__() in dependent_op]
                    logger.info(f"Find bindings for {operation}")
                    messages = self.generate_bind_prompt(ops, infos, messages)
                    if messages is not None:
                        response, _ = self.call(messages)
                        bindings = json.loads(response)
                    else:
                        bindings = {}
                    logger.info(f"Bindings: {bindings}")
                    infos.save_binding(operation, bindings)
                    return bindings


class OracleModel(LanguageModel):
    def __init__(self, config):
        super().__init__(config)

    def generate_prompt(self, infos, operation):
        factor_info = []
        response_info = []
        for f in operation.get_leaf_factors():
            factor_info.append(
                {
                    "name": f.get_global_name,
                    "type": f.type,
                    "description": f.description,
                }
            )
        for response in operation.responses:
            if 200 <= response.status_code < 300:
                for f in response.contents[0][1].get_leaves():
                    response_info.append(
                        {
                            "name": f.get_global_name,
                            "type": f.type,
                            "description": f.description,
                        }
                    )
        user_prompt = ORACLE.format(operation.__repr__(), factor_info, response_info)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}]
        return messages

    def generate_oracle(self, infos, operation):
        messages = self.generate_prompt(infos, operation)
        logger.info(f"Generating oracle for {operation.__repr__()}")
        response, _ = self.call(messages)
        oracle = json.loads(response)
        logger.info(f"Oracle: {oracle}")
        infos.save_oracle(oracle, operation)
        return oracle


if __name__ == '__main__':
    parse = SwaggerParser()
    operations = parse.extract()
    op = operations[0]
    infos = Infos(operations)
    oc_model = OracleModel()
    oc_model.generate_oracle(infos, op)

