import random
import time
from random import choices

import click
import requests
import json
import time

from loguru import logger

from LLMREST_core.src.agents import OperationAgent, ParameterAgent, ResponseAgent
from LLMREST_core.src.configs import Config
from LLMREST_core.src.languagemodel import OperationModel
from LLMREST_core.src.executor import RestRequest
from LLMREST_core.src.swagger import SwaggerParser
from LLMREST_core.src.infos import Infos


class MALLM:
    def __init__(self, config: Config):
        parse = SwaggerParser(config.spec_file, config.server)
        self.config = config
        self.exp_name = config.exp_name
        self.operations = parse.extract()
        self.info = Infos(self.operations)
        if config.saved_data is not None:
            self.info.load_saved_data(config.saved_data)
        self.output_path = config.output_path
        self.op_agent = OperationAgent(self.operations, config)
        self.param_agent = ParameterAgent(config)
        self.response_agent = ResponseAgent(config)
        self.header_auth = {}
        self.time_budget = config.budget
        self.header_auth = config.header_auth

    # def get_token(self, port):
    #     logger.info("Getting access token")
    #     auth = {
    #         "grant_type": "password",
    #         "username": "root",
    #         "password": "MySuperSecretAndSecurePassw0rd!"
    #     }
    #     header = {
    #         "Content-Type": "application/json",
    #     }
    #     while True:
    #         try:
    #             res = requests.post(f"http://localhost:{port}/oauth/token", data=json.dumps(auth), headers=header)
    #             token = res.json()["access_token"]
    #             break
    #         except:
    #             time.sleep(10)
    #     logger.info("Access token: " + token)
    #     return token

    def run(self):

        start_time = time.time()

        while time.time() - start_time < self.time_budget:
            sequence = self.op_agent.action(self.info)
            logger.info(f"Generated sequence: {sequence}")
            for operation in sequence:
                logger.debug(f"Handling {sequence.index(operation)+1}-th operation: {operation}")
                operation.tested_times += 1
                cases, constraints = self.param_agent.action(self.info, operation)
                self.response_agent.action(operation, self.info, cases, constraints)
            self.info.save_data(self.config.save_path)
            time.sleep(4)

        logger.info("Time Out")



@click.command()
@click.option('--exp_name', type=str, required=True, help='Name of the experiment')
@click.option('--spec_file', type=str, required=True, help='Path to the spec file')
@click.option('--budget', type=float, required=True, help='Budget for the experiment, in seconds')
@click.option('--output_path', type=str, required=True, help='Path to the output directory')
@click.option('--server', type=str, required=False, help='URL of the server, e.g. http://localhost:5000. If not provided, the server will be inferred from the spec file')
@click.option('--token', type=str, required=False, help='Token Value')
@click.option('--saved_data', type=str, required=False, help='Path to the saved data file')
def command(exp_name, spec_file, budget, output_path, server, token, saved_data):
    main(exp_name, spec_file, budget, output_path, server, token, saved_data)


def main(exp_name, spec_file, budget, output_path, server, token, saved_data):
    config = Config(exp_name, spec_file, budget, output_path, server, token, saved_data)
    mallm = MALLM(config)
    mallm.run()


if __name__ == '__main__':
    command()

