import json
from typing import List
import yaml

from LLMREST_core.src.rest import RestOp
from utils.schema import *


def find_all_descriptions(info):
    descriptions = []
    if isinstance(info, dict):
        for key, value in info.items():
            if key == "description":
                if isinstance(value, str):
                    descriptions.append(value)
            else:
                descriptions.extend(find_all_descriptions(value))
    elif isinstance(info, list):
        for item in info:
            descriptions.extend(find_all_descriptions(item))
    elif isinstance(info, str):
        pass
    return descriptions


def count_nlp_metrics(spec: dict, operations: List[RestOp], nlp):
    """
     Metrics Explained:
  1. endpointsDescCoverage: Proportion of HTTP methods (endpoints) that have descriptions or summaries.
     Formula: (Number of described endpoints) / (Total number of HTTP methods)
 
  2. descriptionsSizes: Array of word counts for descriptions and summaries of each endpoint.
 
  3. averageMeanSentenceCountPerHundredWords: Average number of sentences per 100 words.
     Helps measure the density of sentence structures in the documentation.
     Formula: (Number of sentences / Number of words)  100
 
  4. averageMeanCharacterCountPerHundredWords: Average number of characters per 100 words.
     Reflects verbosity or compactness of descriptions.
     Formula: (Number of characters / Number of words)  100
 
  5. colemanLiauIndex: A readability score indicating the complexity of the documentation.
     Based on sentence and character counts.
     Formula: 0.0588  (Average characters per 100 words) - 
              0.296  (Average sentences per 100 words) - 15.8
     Lower values indicate easier-to-read documentation.
 
  6. averageWordPerSentence: Average number of words per sentence.
     Indicates sentence length, which affects readability.
     Formula: (Total words in all descriptions) / (Total sentences in all descriptions)
 
  7. averageCharacterPerWord: Average number of characters per word.
     Indicates word length, with higher values suggesting more complex vocabulary.
     Formula: (Total characters in all descriptions) / (Total words in all descriptions)
 
  8. automatedReadabilityIndex: Another readability metric based on word and sentence length.
     Formula: 4.71  (Average characters per word) +
              0.5  (Average words per sentence) - 21.43
     Lower values indicate simpler documentation.
    """

    described_endpoints = [operation for operation in operations if
                           operation.description and operation.description != ""]
    if len(operations) == 0:
        endpointsDescCoverage = 0
    else:
        endpointsDescCoverage = len(described_endpoints) / len(operations)

    desc_string = ""
    descriptions = find_all_descriptions(spec)
    for description in descriptions:
        if description.endswith("."):
            desc_string += description + " "
        else:
            desc_string += description + ". "

    if desc_string == "":
        colemanLiauIndex = 0
        automatedReadabilityIndex = 0
    else:
        try:
            nlp_desc = nlp(desc_string)
            character = len(nlp_desc.text)
            word = [token for token in nlp_desc if token.is_alpha]
            sentence = list(nlp_desc.sents)
            averageMeanSentenceCountPerHundredWords = (len(sentence) / len(word)) * 100
            averageMeanCharacterCountPerHundredWords = (character / len(word)) * 100
            if len(sentence) == 0:
                averageWordPerSentence = len(word)
            else:
                averageWordPerSentence = len(word) / len(sentence)
            averageCharacterPerWord = character / len(word)

            colemanLiauIndex = 0.0588 * averageMeanCharacterCountPerHundredWords - 0.296 * averageMeanSentenceCountPerHundredWords - 15.8
            automatedReadabilityIndex = 4.71 * averageCharacterPerWord + 0.5 * averageWordPerSentence - 21
        except:
            colemanLiauIndex = 0
            automatedReadabilityIndex = 0

    parameters = []
    for operation in operations:
        for p in operation.parameters:
            parameters.append(p.factor)
    described_parameters = [parameter for parameter in parameters if
                            parameter.description and parameter.description != ""]
    if len(parameters) == 0:
        parametersDescCoverage = 0
    else:
        parametersDescCoverage = len(described_parameters) / len(parameters)

    prop_descriptions = []
    operation_descriptions = [operation.description for operation in operations if
                              operation.description and operation.description != ""]
    param_descriptions = [parameter.description for parameter in described_parameters]
    for description in descriptions:
        if description not in operation_descriptions and description not in param_descriptions:
            prop_descriptions.append(description)

    return {
        "operation_description_coverage_rate": endpointsDescCoverage,
        "parameter_description_coverage_rate": parametersDescCoverage,
        "described_prop": len(prop_descriptions),
        "cli_index": colemanLiauIndex,
        "ari_index": automatedReadabilityIndex,
        "described_endpoints": len(described_endpoints),
    }
