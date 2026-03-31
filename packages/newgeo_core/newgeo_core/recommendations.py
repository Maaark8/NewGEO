from __future__ import annotations

from .benchmarking import CandidatePage, HeuristicEngineConnector
from .constraints import assess_source_claim_preservation, evaluate_constraints
from .content import first_paragraph, normalize_markdown
from .diffing import markdown_diff
from .models import (
    ConstraintType,
    ContextPack,
    Page,
    QueryCluster,
    RecommendationBundle,
    RecommendationPreview,
    SupportingDocument,
    VisibilityMetrics,
)
from .retrieval import rank_supporting_documents, summarize_supporting_documents


def _preview_metrics(page_id: str, observations: list) -> VisibilityMetrics:
    for observation in observations:
        if observation.page_id == page_id:
            return observation.metrics
    return VisibilityMetrics()


def _build_rewritten_markdown(
    page: Page,
    original_markdown: str,
    context_pack: ContextPack,
    query_cluster: QueryCluster,
    ranked_documents: list[SupportingDocument],
) -> tuple[str, list[str]]:
    original = normalize_markdown(original_markdown)
    rationale: list[str] = []
    sections: list[str] = []

    if not original.startswith("#"):
        sections.append(f"# {page.title}")

    quick_answer_lines: list[str] = []
    primary_query = query_cluster.queries[0].text if query_cluster.queries else query_cluster.name
    lead_paragraph = first_paragraph(original)
    if lead_paragraph:
        quick_answer_lines.append(lead_paragraph)
    if context_pack.brief:
        quick_answer_lines.append(f"Context: {context_pack.brief.strip()}")
    required_terms = [
        constraint.value
        for constraint in context_pack.constraints
        if constraint.kind == ConstraintType.required_term and constraint.value.lower() not in original.lower()
    ]
    if required_terms:
        quick_answer_lines.append(f"Important search terms to surface clearly: {', '.join(required_terms)}.")
    quick_answer_lines.append(f"Primary query cluster: {primary_query}.")
    sections.append("## Quick answer\n" + " ".join(line for line in quick_answer_lines if line))
    rationale.append("Added a high-signal quick answer block aligned to the tracked query cluster.")

    locked_facts = [
        constraint.value for constraint in context_pack.constraints if constraint.kind == ConstraintType.locked_fact
    ]
    if locked_facts:
        facts_block = "\n".join(f"- {fact}" for fact in locked_facts)
        sections.append("## Locked facts to preserve\n" + facts_block)
        rationale.append("Surfaced locked facts explicitly so meaning-critical details stay visible during review.")

    related_context = summarize_supporting_documents(ranked_documents)
    if related_context:
        sections.append("## Related internal context\n" + "\n".join(f"- {item}" for item in related_context))
        rationale.append("Brought in read-only supporting context from related internal pages without editing those pages.")

    sections.append("## Suggested page body\n" + original)
    rationale.append("Kept the original page body intact inside the draft to minimize semantic drift.")

    if context_pack.voice_rules:
        rationale.append("Applied voice guidance during draft assembly without turning voice rules into publishable copy.")

    return "\n\n".join(section.strip() for section in sections if section.strip()), rationale


def generate_recommendation_bundle(
    page: Page,
    original_markdown: str,
    context_pack: ContextPack,
    query_cluster: QueryCluster,
    candidate_pages: list[CandidatePage],
) -> RecommendationBundle:
    ranked_documents = rank_supporting_documents(query_cluster.name, context_pack.brief, context_pack.supporting_documents)
    rewritten_markdown, rationale = _build_rewritten_markdown(
        page=page,
        original_markdown=original_markdown,
        context_pack=context_pack,
        query_cluster=query_cluster,
        ranked_documents=ranked_documents,
    )

    checks = evaluate_constraints(rewritten_markdown, context_pack.constraints)
    checks.extend(assess_source_claim_preservation(original_markdown, rewritten_markdown))
    failed = sum(1 for check in checks if check.status == "fail")
    warned = sum(1 for check in checks if check.status == "warn")
    confidence = max(0.35, 0.92 - (failed * 0.18) - (warned * 0.05))

    connector = HeuristicEngineConnector()
    baseline_execution = connector.run_benchmark(query_cluster, candidate_pages)
    projected_candidates = [
        CandidatePage(
            page_id=candidate.page_id,
            title=candidate.title,
            content=rewritten_markdown if candidate.page_id == page.id else candidate.content,
            url=candidate.url,
        )
        for candidate in candidate_pages
    ]
    projected_execution = connector.run_benchmark(query_cluster, projected_candidates)

    baseline_metrics = _preview_metrics(page.id, baseline_execution.observations)
    projected_metrics = _preview_metrics(page.id, projected_execution.observations)

    return RecommendationBundle(
        rewritten_markdown=rewritten_markdown,
        diff_markdown=markdown_diff(original_markdown, rewritten_markdown),
        rationale=rationale,
        confidence=round(confidence, 4),
        supporting_context_used=[document.title for document in ranked_documents],
        constraint_checks=checks,
        preview=RecommendationPreview(
            baseline=baseline_metrics,
            projected=projected_metrics,
            score_delta=round(projected_metrics.overall_score - baseline_metrics.overall_score, 4),
        ),
    )
