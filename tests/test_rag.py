from pathlib import Path

from app.services.rag import KnowledgeBase


def test_retriever_ranks_relevant_document():
    kb = KnowledgeBase(Path("app/data/knowledge.json"))
    results = kb.search("Como funciona a antecipação de recebíveis?")
    assert results[0]["id"] == "antecipacao"
    assert results[0]["score"] > 0


def test_retriever_returns_empty_for_unrelated_query():
    kb = KnowledgeBase(Path("app/data/knowledge.json"))
    assert kb.search("ornitorrinco quântico lunar") == []

