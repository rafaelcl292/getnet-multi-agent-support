import json
import math
import re
from collections import Counter
from pathlib import Path


STOPWORDS = {"a", "o", "e", "de", "da", "do", "em", "um", "uma", "para", "com", "que", "como", "meu", "minha", "the", "is", "to", "of"}


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zá-ú0-9]+", text.lower()) if t not in STOPWORDS and len(t) > 1]


class KnowledgeBase:
    """Small, transparent BM25-style retriever; ideal for a take-home demo."""

    def __init__(self, path: Path):
        self.documents = json.loads(path.read_text(encoding="utf-8"))
        self._doc_tokens = [tokens(f"{d['title']} {d['content']}") for d in self.documents]
        self._df = Counter(term for terms in self._doc_tokens for term in set(terms))

    def search(self, query: str, limit: int = 3) -> list[dict]:
        query_terms = tokens(query)
        scored = []
        count = len(self.documents)
        for doc, terms in zip(self.documents, self._doc_tokens):
            frequencies = Counter(terms)
            score = sum(frequencies[t] * math.log((count + 1) / (self._df[t] + 0.5)) for t in query_terms)
            scored.append((score, doc))
        matches = [doc | {"score": round(score, 3)} for score, doc in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0]
        return matches[:limit]

