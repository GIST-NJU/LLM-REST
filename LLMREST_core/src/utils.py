from typing import Dict, List
import tiktoken
from loguru import logger


def count_tokens(messages: List[Dict[str, str]], model: str) -> int:
    token_num = 0
    for message in messages:
        string_to_count = message.get("content")
        encoding = tiktoken.encoding_for_model("gpt-4")
        num_tokens = len(encoding.encode(string_to_count))
        token_num += num_tokens
    logger.info(f"token nums: {token_num}")
    return token_num