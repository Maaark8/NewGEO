from __future__ import annotations

import hashlib
import math
import re


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "why",
    "with",
}


def normalize_markdown(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    collapsed: list[str] = []
    blank_count = 0
    for line in lines:
        if line.strip():
            blank_count = 0
            collapsed.append(line)
            continue
        blank_count += 1
        if blank_count <= 1:
            collapsed.append("")
    return "\n".join(collapsed).strip()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9%]+", text.lower())


def sentence_fragments(text: str) -> list[str]:
    normalized = normalize_markdown(text)
    if not normalized:
        return []
    return [fragment.strip() for fragment in re.split(r"(?<=[.!?])\s+", normalized) if fragment.strip()]


def first_paragraph(text: str) -> str:
    normalized = normalize_markdown(text)
    return normalized.split("\n\n", maxsplit=1)[0].strip() if normalized else ""


def extract_numeric_claims(text: str) -> list[str]:
    return [fragment for fragment in sentence_fragments(text) if any(char.isdigit() for char in fragment)]


def concise_summary(text: str, max_words: int = 18) -> str:
    words = normalize_markdown(text).split()
    return " ".join(words[:max_words]).strip()


def generate_embedding(text: str, dimensions: int = 24) -> list[float]:
    vector = [0.0 for _ in range(dimensions)]
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = digest[0] % dimensions
        sign = 1.0 if digest[1] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def keyword_overlap(query: str, text: str) -> float:
    query_terms = [term for term in tokenize(query) if term not in STOPWORDS]
    if not query_terms:
        return 0.0
    content_terms = set(tokenize(text))
    matches = sum(1 for term in query_terms if term in content_terms)
    return matches / len(query_terms)

