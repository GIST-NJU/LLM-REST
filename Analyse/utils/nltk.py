import re

from nltk.corpus import wordnet

# 定义计算语义相似度的函数
def word_similarity(word1, word2):
    synsets1 = wordnet.synsets(word1)
    synsets2 = wordnet.synsets(word2)
    max_similarity = 0
    for synset1 in synsets1:
        for synset2 in synsets2:
            similarity = synset1.path_similarity(synset2)
            if similarity and similarity > max_similarity:
                max_similarity = similarity
    return max_similarity


def hypernym_relationship(word1, word2):
    synsets1 = wordnet.synsets(word1)
    synsets2 = wordnet.synsets(word2)
    for synset1 in synsets1:
        for synset2 in synsets2:
            hypernyms = synset2.hypernyms()
            for hypernym in hypernyms:
                if synset1 == hypernym:
                    return True
    return False


def hyponym_relationship(word1, word2):
    synsets1 = wordnet.synsets(word1)
    synsets2 = wordnet.synsets(word2)
    for synset1 in synsets1:
        for synset2 in synsets2:
            hyponyms = synset2.hyponyms()
            for hyponym in hyponyms:
                if synset1 == hyponym:
                    return True
    return False


def part_holonym_relationship(word1, word2):
    synsets1 = wordnet.synsets(word1)
    synsets2 = wordnet.synsets(word2)
    for synset1 in synsets1:
        for synset2 in synsets2:
            part_holonyms = synset2.part_holonyms()
            for part_holonym in part_holonyms:
                if synset1 == part_holonym:
                    return True
    return False


def part_meronym_relationship(word1, word2):
    synsets1 = wordnet.synsets(word1)
    synsets2 = wordnet.synsets(word2)
    for synset1 in synsets1:
        for synset2 in synsets2:
            part_meronyms = synset2.part_meronyms()
            for part_meronym in part_meronyms:
                if synset1 == part_meronym:
                    return True
    return False


def attribute_relation(word1, word2):
    synsets1 = wordnet.synsets(word1)
    synsets2 = wordnet.synsets(word2)
    for synset1 in synsets1:
        definition = synset1.definition()
        if word2 in definition.lower():
            return True
    for synset2 in synsets2:
        definition = synset2.definition()
        if word1 in definition.lower():
            return True
    return False


def has_relation(paths):
    obeyed_paths = []
    for path in paths:
        url = path.url
        elements = []
        for element in url.split("/"):
            if element == '':
                continue
            if ("{" in element) or ("}" in element):
                element = re.sub(r'[{}]', '', element)
            elements.append(element)

        if len(elements) == 1:
            # obeyed_paths.append(url)
            pass
        else:
            for i in range(len(elements) - 1):
                e1 = elements[i]
                e2 = elements[i + 1]

                is_similar = word_similarity(e1, e2) > 0.8
                is_hypernym = hypernym_relationship(e1, e2)
                is_hyponym = hyponym_relationship(e1, e2)
                part_meronym = part_meronym_relationship(e1, e2)
                part_holonym = part_holonym_relationship(e1, e2)
                has_attribute = attribute_relation(e1, e2) or attribute_relation(e2, e1)

                if is_similar or is_hypernym or is_hyponym or part_meronym or part_holonym or has_attribute:
                    obeyed_paths.append(url)
                    break

    return obeyed_paths

