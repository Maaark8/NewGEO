from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from .content import first_paragraph, keyword_overlap, tokenize
from .models import EngineObservation, QueryCluster, RunKind, VisibilityMetrics


@dataclass
class CandidatePage:
    page_id: str
    title: str
    content: str
    url: str | None = None


@dataclass
class ConnectorArtifactPayload:
    query_text: str
    prompt_text: str
    raw_response: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkExecution:
    observations: list[EngineObservation]
    artifacts: list[ConnectorArtifactPayload]
    prompt_version: str
    connector_kind: str
    comparable: bool


class EngineConnector(Protocol):
    name: str
    run_kind: RunKind
    comparable: bool
    connector_kind: str

    def run_benchmark(
        self,
        query_cluster: QueryCluster,
        candidate_pages: list[CandidatePage],
        prompt_version: str = "newgeo-benchmark-v1",
    ) -> BenchmarkExecution:
        ...


def _stable_noise(key: str, amplitude: float) -> float:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return (((digest[0] / 255) * 2) - 1) * amplitude


def _structure_score(content: str) -> float:
    lines = content.splitlines()
    headings = sum(1 for line in lines if line.strip().startswith("#"))
    bullets = sum(1 for line in lines if line.strip().startswith(("- ", "* ")))
    quick_answer = 1 if "## quick answer" in content.lower() else 0
    return min(1.0, (headings * 0.18) + (bullets * 0.06) + (quick_answer * 0.24))


def _authority_score(content: str) -> float:
    lower = content.lower()
    digits = sum(1 for char in content if char.isdigit())
    cues = [
        "because",
        "benchmark",
        "evidence",
        "guide",
        "definition",
        "comparison",
        "step",
        "how",
        "why",
    ]
    cue_score = sum(1 for cue in cues if cue in lower) * 0.07
    digit_score = min(0.35, digits * 0.02)
    return min(1.0, cue_score + digit_score)


def _token_share(query_text: str, content: str) -> float:
    early_window = " ".join(content.split()[:120])
    terms = [term for term in tokenize(query_text) if len(term) > 2]
    if not terms:
        return 0.0
    matches = sum(1 for term in terms if term in tokenize(early_window))
    return matches / len(terms)


def _quote_coverage(content: str) -> float:
    lines = content.splitlines()
    feature_lines = sum(
        1
        for line in lines
        if any(marker in line for marker in ['"', "%", ":"]) or line.strip().startswith(("- ", "* "))
    )
    return min(1.0, feature_lines / max(5, len(lines) or 1))


def _raw_score(engine_name: str, query_text: str, candidate: CandidatePage, noise_amplitude: float) -> tuple[float, VisibilityMetrics]:
    content = candidate.content
    coverage = keyword_overlap(query_text, f"{candidate.title}\n{content}")
    early = _token_share(query_text, content)
    structure = _structure_score(content)
    authority = _authority_score(content)
    density = min(1.0, keyword_overlap(query_text, first_paragraph(content)) + 0.15)
    variance = abs(_stable_noise(f"{engine_name}:{query_text}:{candidate.page_id}", noise_amplitude))
    raw = (coverage * 0.40) + (early * 0.22) + (structure * 0.16) + (authority * 0.12) + (density * 0.10)
    raw = max(0.0, raw + _stable_noise(f"rank:{engine_name}:{query_text}:{candidate.page_id}", noise_amplitude))
    metrics = VisibilityMetrics(
        mention_rate=round(min(1.0, coverage + 0.15), 4),
        citation_share=0.0,
        answer_position=0.0,
        token_share=round(early, 4),
        quote_coverage=round(_quote_coverage(content), 4),
        run_variance=round(variance, 4),
        overall_score=0.0,
    )
    return raw, metrics


def _average_metrics(metrics_list: list[VisibilityMetrics]) -> VisibilityMetrics:
    if not metrics_list:
        return VisibilityMetrics()

    count = len(metrics_list)
    return VisibilityMetrics(
        mention_rate=round(sum(item.mention_rate for item in metrics_list) / count, 4),
        citation_share=round(sum(item.citation_share for item in metrics_list) / count, 4),
        answer_position=round(sum(item.answer_position for item in metrics_list) / count, 4),
        token_share=round(sum(item.token_share for item in metrics_list) / count, 4),
        quote_coverage=round(sum(item.quote_coverage for item in metrics_list) / count, 4),
        run_variance=round(sum(item.run_variance for item in metrics_list) / count, 4),
        overall_score=round(sum(item.overall_score for item in metrics_list) / count, 4),
    )


def _candidate_excerpt(candidate: CandidatePage, limit: int = 240) -> str:
    text = " ".join(candidate.content.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _build_prompt(prompt_version: str, query_text: str, candidate_pages: list[CandidatePage], connector_config: dict[str, Any]) -> str:
    page_blocks = []
    for candidate in candidate_pages:
        page_blocks.append(
            "\n".join(
                [
                    f"Page ID: {candidate.page_id}",
                    f"Title: {candidate.title}",
                    f"URL: {candidate.url or 'n/a'}",
                    f"Excerpt: {_candidate_excerpt(candidate)}",
                ]
            )
        )
    config_json = json.dumps(connector_config, ensure_ascii=False, sort_keys=True)
    return (
        f"Prompt version: {prompt_version}\n"
        f"Query: {query_text}\n"
        f"Connector config: {config_json}\n\n"
        "Candidate pages:\n"
        + "\n\n".join(page_blocks)
    )


class HeuristicEngineConnector:
    def __init__(
        self,
        name: str = "newgeo-benchmark-v1",
        connector_kind: str = "heuristic",
        connector_config: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.connector_kind = connector_kind
        self.connector_config = connector_config or {}
        self.run_kind = RunKind.benchmark
        self.comparable = connector_kind == "heuristic"

    def run_benchmark(
        self,
        query_cluster: QueryCluster,
        candidate_pages: list[CandidatePage],
        prompt_version: str = "newgeo-benchmark-v1",
    ) -> BenchmarkExecution:
        rollups: dict[str, list[VisibilityMetrics]] = {page.page_id: [] for page in candidate_pages}
        artifacts: list[ConnectorArtifactPayload] = []

        for query in query_cluster.queries:
            raw_rows: list[tuple[CandidatePage, float, VisibilityMetrics]] = []
            for candidate in candidate_pages:
                raw_score, metrics = _raw_score(self.name, query.text, candidate, 0.025)
                raw_rows.append((candidate, raw_score, metrics))

            raw_rows.sort(key=lambda row: row[1], reverse=True)
            total_raw = sum(row[1] for row in raw_rows) or 1.0
            page_count = max(1, len(raw_rows))

            for rank, (candidate, raw_score, metrics) in enumerate(raw_rows, start=1):
                citation_share = raw_score / total_raw
                position_score = 1.0 - ((rank - 1) / max(1, page_count - 1))
                overall_score = (
                    (metrics.mention_rate * 0.24)
                    + (citation_share * 0.28)
                    + (position_score * 0.20)
                    + (metrics.token_share * 0.16)
                    + (metrics.quote_coverage * 0.12)
                )
                rollups[candidate.page_id].append(
                    metrics.model_copy(
                        update={
                            "citation_share": round(citation_share, 4),
                            "answer_position": round(float(rank), 4),
                            "overall_score": round(overall_score, 4),
                        }
                    )
                )
            prompt_text = _build_prompt(prompt_version, query.text, candidate_pages, self.connector_config)
            raw_response = {
                "engine_name": self.name,
                "connector_kind": self.connector_kind,
                "query_text": query.text,
                "rankings": [
                    {
                        "page_id": candidate.page_id,
                        "title": candidate.title,
                        "raw_score": round(raw_score, 6),
                    }
                    for candidate, raw_score, _ in raw_rows
                ],
            }
            artifacts.append(
                ConnectorArtifactPayload(
                    query_text=query.text,
                    prompt_text=prompt_text,
                    raw_response=json.dumps(raw_response, ensure_ascii=False, indent=2),
                    metadata={"candidate_count": len(candidate_pages)},
                )
            )

        observations: list[EngineObservation] = []
        for candidate in candidate_pages:
            aggregate = _average_metrics(rollups[candidate.page_id])
            notes = []
            if aggregate.token_share >= 0.5:
                notes.append("Strong early query coverage.")
            if aggregate.quote_coverage >= 0.4:
                notes.append("Content is highly scannable for quoted snippets.")
            if aggregate.answer_position <= 2:
                notes.append("Likely to appear near the top of generated answers.")
            observations.append(
                EngineObservation(
                    page_id=candidate.page_id,
                    engine_name=self.name,
                    query_text=query_cluster.name,
                    metrics=aggregate,
                    notes=notes
                    + (
                        []
                        if self.connector_kind == "heuristic"
                        else [f"Connector kind `{self.connector_kind}` used heuristic scoring as a preview."]
                    ),
                )
            )
        return BenchmarkExecution(
            observations=observations,
            artifacts=artifacts,
            prompt_version=prompt_version,
            connector_kind=self.connector_kind,
            comparable=self.comparable,
        )


class LiveSpotCheckConnector(HeuristicEngineConnector):
    def __init__(self, name: str = "newgeo-live-spot-check", connector_config: dict[str, Any] | None = None) -> None:
        super().__init__(name=name, connector_kind="live_spot_check", connector_config=connector_config)
        self.run_kind = RunKind.live_spot_check
        self.comparable = False

    def run_benchmark(
        self,
        query_cluster: QueryCluster,
        candidate_pages: list[CandidatePage],
        prompt_version: str = "newgeo-benchmark-v1",
    ) -> BenchmarkExecution:
        parent_execution = super().run_benchmark(query_cluster, candidate_pages, prompt_version=prompt_version)
        observations = []
        for observation in parent_execution.observations:
            noisy_metrics = observation.metrics.model_copy(
                update={
                    "run_variance": round(min(1.0, observation.metrics.run_variance + 0.08), 4),
                    "overall_score": round(max(0.0, observation.metrics.overall_score - 0.03), 4),
                }
            )
            observations.append(
                observation.model_copy(
                    update={
                        "engine_name": self.name,
                        "metrics": noisy_metrics,
                        "notes": observation.notes + ["Spot-check result is observational and not directly comparable."],
                    }
                )
            )
        artifacts = [
            ConnectorArtifactPayload(
                query_text=artifact.query_text,
                prompt_text=artifact.prompt_text,
                raw_response=artifact.raw_response,
                metadata={**artifact.metadata, "observational": True},
            )
            for artifact in parent_execution.artifacts
        ]
        return BenchmarkExecution(
            observations=observations,
            artifacts=artifacts,
            prompt_version=prompt_version,
            connector_kind=self.connector_kind,
            comparable=False,
        )


class ApiPreviewConnector(HeuristicEngineConnector):
    def __init__(self, name: str, connector_config: dict[str, Any] | None = None) -> None:
        super().__init__(name=name, connector_kind="api_preview", connector_config=connector_config)
        self.comparable = False


def connector_for_run(
    engine_name: str,
    run_kind: RunKind,
    connector_kind: str = "heuristic",
    connector_config: dict[str, Any] | None = None,
) -> EngineConnector:
    if run_kind == RunKind.live_spot_check:
        return LiveSpotCheckConnector(name=engine_name, connector_config=connector_config)
    if connector_kind != "heuristic":
        return ApiPreviewConnector(name=engine_name, connector_config=connector_config)
    return HeuristicEngineConnector(name=engine_name, connector_kind=connector_kind, connector_config=connector_config)
