from __future__ import annotations

from .content import concise_summary, cosine_similarity, generate_embedding
from .models import SupportingDocument


def rank_supporting_documents(
    query_text: str,
    brief: str | None,
    documents: list[SupportingDocument],
    limit: int = 3,
) -> list[SupportingDocument]:
    if not documents:
        return []

    query_embedding = generate_embedding(f"{query_text}\n{brief or ''}")
    ranked = []
    for document in documents:
        embedding = document.embedding or generate_embedding(document.body)
        score = cosine_similarity(query_embedding, embedding)
        ranked.append((score, document.model_copy(update={"embedding": embedding})))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:limit]]


def summarize_supporting_documents(documents: list[SupportingDocument]) -> list[str]:
    summaries: list[str] = []
    for document in documents:
        summary = concise_summary(document.body, max_words=22)
        summaries.append(f"{document.title}: {summary}")
    return summaries

