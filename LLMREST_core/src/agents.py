import itertools
import json
import random
import string
from typing import List

from loguru import logger

from LLMREST_core.src.languagemodel import OperationModel, ConstraintModel, ValueModel, DependencyModel, OracleModel
from LLMREST_core.src.executor import RestRequest
from LLMREST_core.src.factor import AbstractFactor, Value, ValueType, EnumFactor, BooleanFactor
from LLMREST_core.src.keywords import Method, DataType
from LLMREST_core.src.rest import RestOp, BodyParam, RestParam, PathParam, QueryParam, HeaderParam, ContentType
from LLMREST_core.src.swagger import SwaggerParser
from LLMREST_core.src.configs import *
from LLMREST_core.src.infos import Infos
import signal


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError


class Agent:
    def __init__(self, config):
        self.config = config


class OperationAgent(Agent):
    def __init__(self, operations: List[RestOp], config):
        super().__init__(config)
        self.language_model = OperationModel(config)
        self.operations = operations

    def action(self, infos):
        if len(infos.successful_operations) == 0:
            logger.info("Generating initial sequence")
            if len(infos.operations) == 1:
                seq = [infos.operations[0].__repr__()]
            else:
                if len(infos.test_sequence.get("all", [])) == 0:
                    seq = self.language_model.generate_initial_seq(infos)
                else:
                    seq = random.choice(list(infos.test_sequence.get("all")))
        else:
            logger.info("Generating new sequence")
            seq = self.generate_new_sequence(infos)
        sequence = []
        for op in seq:
            for operation in self.operations:
                if operation.__repr__() == op:
                    sequence.append(operation)
                    break
        return sequence

    def generate_new_sequence(self, infos):
        infos.to_test = [op for op in infos.operations if op.__repr__() not in infos.successful_operations]
        if len(infos.to_test) == 0:
            operation = random.choice(infos.operations)
        else:
            if random.uniform(0, 1) < 0.8:
                operation = random.choice(infos.to_test)
            else:
                to_test = [op for op in infos.operations if op.__repr__() not in infos.to_test]
                operation = random.choice(to_test)
        if sorted(infos.operations, key=lambda x: x.tested_times)[-1].tested_times > 50:
            operation = sorted(infos.operations, key=lambda x: x.tested_times)[0]
            return [operation.__repr__()]

        if len(infos.test_sequence.get(operation.__repr__(), [])) > 0:
            max_length = 0
            for seq in list(infos.test_sequence[operation.__repr__()]):
                if len(seq) > max_length:
                    max_length = len(seq)
            if max_length >= len(infos.operations) - 1 or len(infos.test_sequence[operation.__repr__()]) > 2:
                return list(random.choice(list(infos.test_sequence[operation.__repr__()])))
            else:
                if random.uniform(0, 1) < 0.98:
                    return list(random.choice(list(infos.test_sequence[operation.__repr__()])))
                else:
                    return self.language_model.generate_new_sequence(infos, operation)
        else:
            if random.uniform(0, 1) < 0.8:
                seq = random.choice(list(infos.test_sequence.get("all")))
                index = list(seq).index(operation.__repr__())
                infos.test_sequence[operation.__repr__()] = list(seq)[0:index]
                return list(seq)[0:index]
            else:
                return self.language_model.generate_new_sequence(infos, operation)


class ParameterAgent(Agent):
    def __init__(self, config):
        super().__init__(config)
        self.constraint_agent = ConstraintAgent(config)
        self.value_agent = ValueAgent(self.constraint_agent,config)

    def random_action(self):
        pass

    def llm_action(self):
        pass

    @staticmethod
    def select_param(infos, operation: RestOp, constraints, validate=False):
        for factor in operation.get_leaf_factors():
            for constraint in constraints:
                if factor.name in constraint and f"_{factor.name}" not in constraint and f"{factor.name}_" not in constraint:
                    factor.is_constraint = True
                    break
        essential_param = [factor for factor in operation.get_leaf_factors() if factor.is_essential]
        required_param = [factor for factor in operation.get_leaf_factors() if factor.required]

        optional_param = [factor for factor in operation.get_leaf_factors() if factor not in essential_param]

        if validate:
            if len(required_param) > 0:
                return required_param
            else:
                return essential_param

        if operation.__repr__() not in infos.successful_operations and operation.tested_times < 3:
            logger.debug(f"Have not been successfully tested")
            method = random.choices(["essential", "mixed"], [0.98, 0.02])[0]
            if method == "essential":
                return essential_param
            else:
                return essential_param + random.sample(optional_param, random.randint(0, len(optional_param)))

        else:
            method = random.choices(["part", "all"], [0.7, 0.3])[0]
            if method == "part":
                selected_param = essential_param + random.sample(optional_param, random.randint(0, len(optional_param)))
            else:
                selected_param = operation.get_leaf_factors()
            return selected_param

    def action(self, infos, operation, validate=False):
        constraints = self.constraint_agent.action(infos, operation)
        selected_param = self.select_param(infos, operation, constraints, validate)
        logger.debug(f"Selected {len(selected_param)} parameters: {selected_param}")
        cases = self.value_agent.action(selected_param, infos, operation, constraints)

        return cases, constraints


class ConstraintAgent(Agent):
    def __init__(self, config):
        super().__init__(config)
        self.language_model = ConstraintModel(config)

    def llm_action(self, infos, operation) -> List[str]:
        if infos.constraint.get(operation.__repr__(), None) is not None:
            logger.debug(f"LLM have used to generate constraints for {operation.__repr__()}")
            if len(infos.constraint[operation.__repr__()]) > 0:
                return list(infos.constraint[operation.__repr__()].keys())
                # method = random.choices(["new", "llm"], [0.01, 0.99])[0]
                # if method == "new":
                #     logger.debug(f"Try to extract constraints again.")
                #     return self.language_model.extract_constraint(infos, operation)
                # else:
                #     return list(infos.constraint[operation.__repr__()].keys())
            else:
                logger.debug(f"No Constraints")
                return []
        else:
            logger.debug(f"Use LLM to extract constraints for {operation.__repr__()}")
            return self.language_model.extract_constraint(infos, operation)

    def cut_domains(self, domains):
        length = 1
        for domain in domains:
            length *= len(domain)
        if length > 500:
            new_domains = []
            for domain in domains:
                new_domain = []
                dynamic_domain = [v for v in domain if v.generator == ValueType.Dynamic]
                example_domain = [v for v in domain if v.generator == ValueType.Example]
                random_domain = [v for v in domain if v.generator == ValueType.Random]
                none_domain = [v for v in domain if v.generator == ValueType.NULL]
                if len(dynamic_domain) > 0:
                    new_domain.append(random.choice(dynamic_domain))
                if len(new_domain) == 0:
                    if len(example_domain) > 0:
                        new_domain.extend(random.sample(example_domain, 1))
                else:
                    if len(example_domain) > 0:
                        new_domain.append(random.choice(example_domain))
                if len(none_domain) > 0:
                    new_domain.append(Value(None, ValueType.NULL, DataType.NULL))
                if len(new_domain) == 0:
                    if len(random_domain) > 0:
                        new_domain.append(random.choice(random_domain))
                    else:
                        pass

                if len(new_domain) == 0:
                    new_domain = domain
                if len(new_domain) > 4:
                    new_domain = random.sample(new_domain, 4)
                new_domains.append(new_domain)
                return new_domains
            # domains.clear()
            # domains.extend(new_domains)
            # domains = new_domains
        else:
            return domains

    def resolve_constraints(self, constraints, operation, infos,
                            factors_with_constraints, domains_with_constraints):
        cases = []
        self.cut_domains(domains_with_constraints)
        for combination in itertools.product(*domains_with_constraints):
            case = {}
            for i, factor in enumerate(factors_with_constraints):
                case[factor.get_global_name] = combination[i]
            if case not in cases:
                cases.append(case)
            if len(cases) > 500:
                break

        if cases == [{}]:
            return []
        checked_cases = []
        if operation.__repr__() in infos.allowed_constraints:
            if len(infos.allowed_constraints[operation.__repr__()]) > 0:
                for case in cases:
                    flag = True
                    for constraint in infos.allowed_constraints[operation.__repr__()]:
                        if len(infos.allowed_constraints[operation.__repr__()][constraint]) > 0:
                            add = False
                            for pattern in infos.allowed_constraints[operation.__repr__()][constraint]:
                                case_pattern = {}
                                for f in pattern:
                                    if f not in case:
                                        pass
                                    else:
                                        case_pattern[f] = case[f].generator
                                add = all([case_pattern[f] == pattern[f] for f in case_pattern])
                                if add:
                                    break
                                else:
                                    continue
                            if not add:
                                flag = False
                                break
                        else:
                            continue
                    if flag:
                        checked_cases.append(case)
            else:
                checked_cases = cases
        else:
            checked_cases = cases

        return checked_cases

    def action(self, infos, operation) -> List[str]:
        if operation not in infos.constraint:
            return self.llm_action(infos, operation)
        else:
            logger.debug(f"Have used LLM to generate constraints for {operation.__repr__()}")
            return list(infos.constraint[operation.__repr__()].keys())


class ValueAgent(Agent):
    def __init__(self, constraint_agent, config):
        super().__init__(config)
        self.language_model = ValueModel(config)
        self.dependency_agent = DependencyAgent(config)
        self.constraint_agent = constraint_agent

    def llm_action(self, selected_factors, infos, operation):
        for f in selected_factors:
            f.gen_dependency_value(operation, infos)
            f.gen_domain(infos)

    def random_action(self, selected_factor: List[AbstractFactor], infos, operation):
        if operation.__repr__() not in infos.successful_operations and operation.tested_times < 3:
            succeeded = False
        else:
            succeeded = True
        for f in selected_factor:
            f.gen_random_domain(infos, "random", succeeded)

    def gen_llm_value(self, infos, operation):
        no_ask_factors = [EnumFactor, BooleanFactor]
        factors_to_ask = [f for f in operation.get_leaf_factors() if f.__class__ not in no_ask_factors]

        if infos.llm_value.get(operation.__repr__(), None) is not None:
            if len(infos.llm_value[operation.__repr__()]) > 0:
                for f in infos.llm_value[operation.__repr__()]:
                    for factor in operation.get_leaf_factors():
                        if factor.get_global_name == f:
                            if len(factor.llm_examples) >= 3:
                                operation.generated_value = True
                                break
                    if operation.generated_value:
                        break
                    else:
                        continue
        if not operation.generated_value:
            infos.llm_value[operation.__repr__()] = dict()
            self.language_model.generate_value(infos, operation, factors_to_ask)
        elif operation.generated_value:
            if len(factors_to_ask) > 0:
                if len(factors_to_ask[0].llm_examples) >= 3:
                    pass
                else:
                    if random.uniform(0, 1) < 0.8:
                        self.language_model.generate_value(infos, operation, factors_to_ask, "new")
        operation.generated_value = True

    def action(self, selected_factors: List[AbstractFactor], infos, operation, constraints, budget=500):
        if len(selected_factors) == 0:
            return [{}]

        self.dependency_agent.action(infos, operation)

        self.gen_llm_value(infos, operation)

        if operation.__repr__() not in infos.successful_operations and operation.tested_times < 3:
            self.llm_action(selected_factors, infos, operation)
        else:
            self.random_action(selected_factors, infos, operation)

        factors_with_constraints = [f for f in selected_factors if f.is_constraint]
        domains_with_constraints = [f.domain for f in factors_with_constraints]

        factors_without_constraints = [f for f in selected_factors if not f.is_constraint]
        domains_without_constraints = [f.domain for f in factors_without_constraints]

        solutions = []
        if len(constraints) > 0:
            logger.debug(f"Resolve constraints for {operation.__repr__()}")
            timeout = 10
            signal.signal(signal.SIGALRM, timeout_handler)
            # 设置闹钟，超时后触发信号
            signal.alarm(timeout)
            try:
                solutions = self.constraint_agent.resolve_constraints(constraints, operation, infos,
                                                                      factors_with_constraints,
                                                                      domains_with_constraints)
            except TimeoutError:
                print(
                    f"Function {self.constraint_agent.resolve_constraints.__name__} timed out after {timeout} seconds.")
                solutions = []
            finally:
                # 取消闹钟
                signal.alarm(0)

        test_cases = []
        timeout = 10
        signal.signal(signal.SIGALRM, timeout_handler)
        # 设置闹钟，超时后触发信号
        signal.alarm(timeout)
        try:
            if operation.tested_times > 20:
                new_domains = []
                for domains in domains_with_constraints:
                    new_domain = []
                    for v in domains:
                        if v.generator == ValueType.Random:
                            new_domain.append(v)
                        elif v.generator == ValueType.NULL:
                            new_domain.append(v)
                        else:
                            pass
                    new_domains.append(new_domain)
                domains_with_constraints = new_domains

            if len(solutions) > 0:
                if len(factors_without_constraints) == 0:
                    test_cases.extend(solutions)
                elif len(factors_without_constraints) > 0:
                    length = 1
                    for _ in domains_without_constraints:
                        length = length * len(_)
                        if length > 500:
                            break
                    if length * len(solutions) < 500:
                        for _ in itertools.product(*domains_without_constraints):
                            for solution in solutions:
                                case = {}
                                for i in range(len(factors_without_constraints)):
                                    case[factors_without_constraints[i].get_global_name] = _[i]
                                case.update(solution)
                                test_cases.append(case)
                    else:
                        while len(test_cases) < 500:
                            solution = random.choice(solutions)
                            case = {_f.get_global_name: random.choice(_d) for _f, _d in
                                    zip(factors_without_constraints, domains_without_constraints)}
                            case.update(solution)
                            if case not in test_cases:
                                test_cases.append(case)
            else:
                if len(factors_with_constraints) > 0:
                    length = 1
                    for _ in domains_without_constraints + domains_with_constraints:
                        length *= len(_)
                        if length > budget:
                            break
                    if length <= budget:
                        for _ in itertools.product(*domains_without_constraints + domains_with_constraints):
                            case = {}
                            all_factors = factors_without_constraints + factors_with_constraints
                            for i in range(len(all_factors)):
                                case[all_factors[i].get_global_name] = _[i]
                            test_cases.append(case)
                    else:
                        while len(test_cases) < budget:
                            all_factors = factors_without_constraints + factors_with_constraints
                            all_domains = domains_without_constraints + domains_with_constraints
                            case = {_f.get_global_name: random.choice(_d) for _f, _d in zip(all_factors, all_domains)}
                            if case not in test_cases:
                                test_cases.append(case)
                else:
                    length = 1
                    for _ in domains_without_constraints:
                        length *= len(_)
                        if length > budget:
                            break
                    if length <= budget:
                        for _ in itertools.product(*domains_without_constraints):
                            case = {}
                            for i in range(len(factors_without_constraints)):
                                case[factors_without_constraints[i].get_global_name] = _[i]
                            test_cases.append(case)
                    else:
                        while len(test_cases) < budget - 1:
                            case = {_f.get_global_name: random.choice(_d) for _f, _d in
                                    zip(factors_without_constraints, domains_without_constraints)}
                            if case not in test_cases:
                                test_cases.append(case)
        except TimeoutError:
            print(f"Function {self.constraint_agent.resolve_constraints.__name__} timed out after {timeout} seconds.")
            test_cases = []
        finally:
            # 取消闹钟
            signal.alarm(0)
            return test_cases


class DependencyAgent(Agent):
    def __init__(self, config):
        super().__init__(config)
        self.language_model = DependencyModel(config)

    def bind_params(self, infos, operation):
        self.language_model.bind_parameters(infos, operation)

    def action(self, infos, operation):
        essential_factors = [f for f in operation.get_leaf_factors() if f.is_essential]
        if len(essential_factors) > 0:
            self.bind_params(infos, operation)
        else:
            logger.info(f"No need to bind parameters for {operation.__repr__()}")


class ResponseAgent(Agent):
    def __init__(self, config):
        super().__init__(config)
        self.request_executor = RestRequest(config.query_auth, config.header_auth)
        self.oracle_agent = OracleAgent(config)

    def action(self, operation, infos, cases, constraints):
        status_codes, response_datas = self.execute(infos, operation, cases)
        self.handle_response(cases, status_codes, response_datas, operation, infos, constraints)
        # self.oracle_agent.action(cases, status_codes, response_datas, operation, infos)

        return status_codes, response_datas

    def handle_response(self, cases, status_codes, response_datas, operation, infos, constraints=None):
        if constraints is None:
            constraints = []
        # cases = cases[0:len(status_codes)]
        success_cases = [case for case in cases if 200 <= status_codes[cases.index(case)] < 300]
        error_cases = [case for case in cases if 500 <= status_codes[cases.index(case)] < 600]
        logger.info(f"Success cases: {len(success_cases)}, Error cases: {len(error_cases)}")
        # if len(success_cases) == 0:
        #     for factor in operation.get_leaf_factors():
        #         if len(factor.llm_examples) > 0 and operation.tested_times < 4:
        #             factor.llm_examples.pop(random.randint(0, len(factor.llm_examples) - 1))
        for i in range(len(cases)):
            case = cases[i]
            status_code = status_codes[i]
            response_data = response_datas[i]
            if 200 <= status_code < 300:
                infos.append_response(operation, response_data)
                if operation.__repr__() not in infos.successful_operations:
                    infos.successful_operations.append(operation.__repr__())
                if len(constraints) > 0:
                    infos.check_constraint_from_response(operation, constraints, case)
                    if infos.allowed_constraints.get(operation.__repr__(), None) is not None:
                        if len(infos.allowed_constraints[operation.__repr__()]) == 0:
                            infos.constraint[operation.__repr__()] = {}
                infos.confirm_binding(operation, case)
                if operation.verb in [Method.POST, Method.GET]:
                    infos.extract_response_values(operation, response_data)
            if 400 <= status_code < 500:
                infos.save_response_data(operation, response_data, case)
            if status_code >= 500:
                if "error" in operation.__repr__().lower():
                    if operation.__repr__() not in infos.successful_operations:
                        infos.successful_operations.append(operation.__repr__())

    def execute(self, infos, operation, cases):
        status_codes = []
        response_datas = []
        for case in cases:
            status_code, response_data = self.execute_case(infos, operation, case)
            status_codes.append(status_code)
            response_datas.append(response_data)
            # if operation.verb == Method.POST:
            #     if len([s for s in status_codes if 200 <= s < 300]) >= 1:
            #         break
        return status_codes, response_datas

    def execute_case(self, infos, op: RestOp, case):
        media_types = [
            ContentType.JSON, ContentType.JSON_TEXT, ContentType.JSON_ANY, ContentType.XML, ContentType.FORM,
            ContentType.MULTIPART_FORM, ContentType.PLAIN_TEXT, ContentType.HTML, ContentType.PDF, ContentType.PNG,
            ContentType.BINARY, ContentType.ANY
        ]
        methods = [Method.GET, Method.POST, Method.PUT, Method.DELETE, Method.PATCH]
        for p in op.parameters:
            p.factor.set_value(case)
        url = op.resolved_url()
        method = op.verb
        query_param = {p.factor.name: p.factor.printable_value() for p in op.parameters
                       if isinstance(p, QueryParam) and p.factor.value is not None}
        header_param = {p.factor.name: p.factor.printable_value() for p in op.parameters
                        if isinstance(p, HeaderParam) and p.factor.value is not None}
        body_param = next(filter(lambda p: isinstance(p, BodyParam), op.parameters), None)
        body = body_param.factor.printable_value() if body_param is not None else None
        kwargs = dict()
        if body_param is not None:
            kwargs["Content-Type"] = body_param.content_type
            header_param["Content-Type"] = body_param.content_type.value
        if op.__repr__() in infos.successful_operations:
            if random.uniform(0, 1) < 0.1:
                method = random.choice(methods)
            if random.uniform(0, 1) < 0.1:
                kwargs["Content-Type"] = random.choice(media_types)
        status_code, response_data = self.request_executor.send(
            method,
            url,
            header_param,
            query=query_param,
            body=body,
            **kwargs
        )
        return status_code, response_data


class OracleAgent(Agent):
    def __init__(self, config):
        super().__init__(config)
        self.language_model = OracleModel(config)

    def action(self, cases, status_codes, response_datas, operation, infos):
        success_cases = [case for case in cases if 200 <= status_codes[cases.index(case)] < 300]
        error_cases = [case for case in cases if status_codes[cases.index(case)] >= 500]
        if len(success_cases) == 0:
            return
        for i in range(len(cases)):
            case = cases[i]
            status_code = status_codes[i]
            response_data = response_datas[i]
            if 200 <= status_code < 300:
                self.compare_for_oracle(infos, operation, case, response_data)

    def compare_for_oracle(self, infos, operation, case, response_data):
        if operation.verb == Method.DELETE:
            direct_ancestor = self.find_resource(infos, operation)
            if direct_ancestor is None:
                return
            resource_info = self.get_system_status(infos, direct_ancestor)
            for f in operation.get_leaf_factors():
                if f.get_global_name in case:
                    v_to_find = case[f.get_global_name].val
                    if v_to_find is None:
                        continue
                    for response in resource_info:
                        if json.dumps(v_to_find) in json.dumps(response):
                            infos.save_fp(operation, case, response, direct_ancestor)
                            break

        elif operation.verb in [Method.POST, Method.GET]:
            if operation.__repr__() not in infos.oracles:
                self.language_model.generate_oracle(infos, operation)
            oracle = infos.oracles[operation.__repr__()]
            if len(oracle) == 0:
                return
            else:
                for factor_name, response_factor in oracle.items():
                    if factor_name in case:
                        if case[factor_name].val is not None:
                            value_in_case = case[factor_name].val
                            if not self.check_oracle_value(infos, response_data, response_factor, value_in_case):
                                infos.save_fp(operation, case, response_data)
                                return
        elif operation.verb == Method.PUT:
            pass

    def check_oracle_value(self, infos, response_data, response_factor, value_to_check):
        info_dict = response_data
        value = infos.get_value_from_dict(info_dict, response_factor)
        if value is not None:
            if str(value) == str(value_to_check):
                return True
            else:
                return False
        else:
            return False

    def find_resource(self, infos, operation):
        ancestors = [op for op in infos.operations if op.path.is_ancestor_of(operation.path)]
        ancestor = None
        ancestor_length = 0
        for a in ancestors:
            if len(a.path.elements) > ancestor_length:
                ancestor = a
                ancestor_length = len(a.path.elements)
        return ancestor

    def get_system_status(self, infos, operation):
        valid_param_agent = ParameterAgent()
        valid_response_agent = ResponseAgent()
        cases, constraints = valid_param_agent.action(infos, operation, validate=True)
        status, response = valid_response_agent.action(operation, infos, cases, constraints)
        resource_info = []
        for i in range(len(cases)):
            if 200 <= status[i] < 300:
                resource_info.append(response[i])
        return resource_info


if __name__ == '__main__':
    parse = SwaggerParser()
    operations = parse.extract()
    op = operations[5]
    infos = Infos(operations)
