from __future__ import annotations

from .content import extract_numeric_claims, tokenize
from .models import Constraint, ConstraintCheck, ConstraintType


def evaluate_constraints(candidate_text: str, constraints: list[Constraint]) -> list[ConstraintCheck]:
    checks: list[ConstraintCheck] = []
    candidate_lower = candidate_text.lower()

    for constraint in constraints:
        value_lower = constraint.value.lower()
        if constraint.kind == ConstraintType.locked_fact:
            status = "pass" if value_lower in candidate_lower else "fail"
            checks.append(
                ConstraintCheck(
                    constraint_id=constraint.id,
                    constraint_kind=constraint.kind.value,
                    status=status,
                    message="Locked fact preserved." if status == "pass" else f"Locked fact missing: {constraint.value}",
                )
            )
        elif constraint.kind == ConstraintType.forbidden_claim:
            status = "fail" if value_lower in candidate_lower else "pass"
            checks.append(
                ConstraintCheck(
                    constraint_id=constraint.id,
                    constraint_kind=constraint.kind.value,
                    status=status,
                    message="Forbidden claim avoided." if status == "pass" else f"Forbidden claim introduced: {constraint.value}",
                )
            )
        elif constraint.kind == ConstraintType.required_term:
            status = "pass" if value_lower in candidate_lower else "warn"
            checks.append(
                ConstraintCheck(
                    constraint_id=constraint.id,
                    constraint_kind=constraint.kind.value,
                    status=status,
                    message="Required term surfaced." if status == "pass" else f"Required term not surfaced clearly: {constraint.value}",
                )
            )
        elif constraint.kind == ConstraintType.voice_rule:
            checks.append(
                ConstraintCheck(
                    constraint_id=constraint.id,
                    constraint_kind=constraint.kind.value,
                    status="pass",
                    message=f"Voice rule noted during generation: {constraint.value}",
                )
            )

    return checks


def _claim_preserved(claim: str, candidate_text: str) -> bool:
    candidate_lower = candidate_text.lower()
    numeric_tokens = [token for token in claim.split() if any(char.isdigit() for char in token)]
    if numeric_tokens and not all(token.lower() in candidate_lower for token in numeric_tokens):
        return False

    tokens = [token for token in tokenize(claim) if len(token) > 3]
    if not tokens:
        return True

    overlap = sum(1 for token in tokens if token in candidate_lower)
    return (overlap / len(tokens)) >= 0.45


def assess_source_claim_preservation(original_text: str, candidate_text: str) -> list[ConstraintCheck]:
    claims = extract_numeric_claims(original_text)
    if not claims:
        return [
            ConstraintCheck(
                constraint_id="source_claims",
                constraint_kind="source_claims",
                status="pass",
                message="No numeric source claims required special preservation checks.",
            )
        ]

    missing = [claim for claim in claims if not _claim_preserved(claim, candidate_text)]
    if not missing:
        return [
            ConstraintCheck(
                constraint_id="source_claims",
                constraint_kind="source_claims",
                status="pass",
                message="Source claims with numeric details were preserved.",
            )
        ]

    return [
        ConstraintCheck(
            constraint_id="source_claims",
            constraint_kind="source_claims",
            status="fail",
            message=f"Potential semantic drift detected for {len(missing)} source claim(s).",
        )
    ]

