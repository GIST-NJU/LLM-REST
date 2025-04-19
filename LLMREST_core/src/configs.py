import os


class Config:
    def __init__(self, exp_name, spec_file, budget, output_path, server, token, saved_data):
        self.exp_name = exp_name
        self.spec_file = spec_file
        self.budget = budget
        self.output_path = output_path
        self.server = server
        self.token = token
        self.saved_data = saved_data

        self.save_path = os.path.join(self.output_path, f"{exp_name}.json")

        if self.token is not None and self.token != "":
            self.header_auth = {"Authorization": f"Bearer {self.token}"}
        else:
            self.header_auth = {}

        self.query_auth = {}
        self.api_key = "sk-QKBW0aRWkwGm7anAD0Bb7d469e6e4d40B6E3B7B4D4589a61"
        self.openai_url = "https://api.bianxieai.com/v1"
        self.model = "gpt-4o"
        self.temperature = 0.2


