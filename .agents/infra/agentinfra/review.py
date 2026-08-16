from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OUTCOMES = {"ACCEPTED", "REJECTED", "PARTIAL"}
_REQUIRED_CHALLENGE_FIELDS = (
    "assumptions_tested",
    "counterexamples_attempted",
    "boundary_cases",
    "potential_failures",
)


class ReviewError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _receipt_digest(receipt: dict) -> str:
    body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    return hashlib.sha256(_canonical(body)).hexdigest()


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewError(f"{label} must be non-empty")
    return value.strip()


def _require_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ReviewError(f"{label} must be a canonical sha256")
    return value


def _require_string_list(value: object, label: str, *, nonempty: bool) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ReviewError(f"{label} must be an array of non-empty strings")
    if nonempty and not value:
        raise ReviewError(f"rubber-stamp review: {label} is empty")
    return [item.strip() for item in value]


def build_review_receipt(
    *,
    task_id: str,
    reviewer_lease: str,
    reviewer_role: str,
    reviewer_identity: str,
    implementer_identity: str,
    epoch: int,
    diff_digest: str,
    requirements_digest: str,
    evidence_set_digest: str,
    tdd_cycle_digest: str,
    test_law_baseline_digest: str,
    assumptions_tested: list[str],
    counterexamples_attempted: list[str],
    boundary_cases: list[str],
    potential_failures: list[str],
    unexpected_scope: list[str],
    findings: list[dict],
    outcome: str,
) -> dict:
    reviewer = _require_text(reviewer_identity, "reviewer identity")
    implementer = _require_text(implementer_identity, "implementer identity")
    if reviewer.casefold() == implementer.casefold():
        raise ReviewError("implementer cannot independently accept their own change")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        raise ReviewError("review epoch must be a non-negative integer")
    if outcome not in _OUTCOMES:
        raise ReviewError("invalid review outcome")
    if not isinstance(findings, list) or any(not isinstance(item, dict) for item in findings):
        raise ReviewError("findings must be an array of objects")
    blocking = [item for item in findings if item.get("severity") in {"HARD", "CRITICAL", "HIGH"} and item.get("status", "OPEN") != "RESOLVED"]
    if outcome == "ACCEPTED" and blocking:
        raise ReviewError("accepted review contains unresolved blocking findings")
    receipt = {
        "schema": 1,
        "task_id": _require_text(task_id, "task id"),
        "reviewer_lease": _require_text(reviewer_lease, "reviewer lease"),
        "reviewer_role": _require_text(reviewer_role, "reviewer role"),
        "reviewer_identity": reviewer,
        "implementer_identity": implementer,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "epoch": epoch,
        "diff_digest": _require_digest(diff_digest, "diff digest"),
        "requirements_digest": _require_digest(requirements_digest, "requirements digest"),
        "evidence_set_digest": _require_digest(evidence_set_digest, "evidence-set digest"),
        "tdd_cycle_digest": _require_digest(tdd_cycle_digest, "TDD-cycle digest"),
        "test_law_baseline_digest": _require_digest(test_law_baseline_digest, "test/law baseline digest"),
        "assumptions_tested": _require_string_list(assumptions_tested, "assumptions_tested", nonempty=True),
        "counterexamples_attempted": _require_string_list(counterexamples_attempted, "counterexamples_attempted", nonempty=True),
        "boundary_cases": _require_string_list(boundary_cases, "boundary_cases", nonempty=True),
        "potential_failures": _require_string_list(potential_failures, "potential_failures", nonempty=True),
        "unexpected_scope": _require_string_list(unexpected_scope, "unexpected_scope", nonempty=False),
        "findings": findings,
        "outcome": outcome,
    }
    receipt["receipt_sha256"] = _receipt_digest(receipt)
    return receipt


def validate_review_receipt(
    receipt: dict,
    *,
    current_epoch: int,
    current_diff_digest: str,
    current_requirements_digest: str,
    current_evidence_set_digest: str,
    current_tdd_cycle_digest: str,
    current_test_law_baseline_digest: str,
) -> bool:
    if not isinstance(receipt, dict) or receipt.get("schema") != 1:
        return False
    if receipt.get("receipt_sha256") != _receipt_digest(receipt):
        return False
    if receipt.get("outcome") != "ACCEPTED":
        return False
    if any(not isinstance(receipt.get(field), list) or not receipt[field] for field in _REQUIRED_CHALLENGE_FIELDS):
        return False
    if any(
        item.get("severity") in {"HARD", "CRITICAL", "HIGH"} and item.get("status", "OPEN") != "RESOLVED"
        for item in receipt.get("findings", [])
        if isinstance(item, dict)
    ):
        return False
    expected = {
        "epoch": current_epoch,
        "diff_digest": current_diff_digest,
        "requirements_digest": current_requirements_digest,
        "evidence_set_digest": current_evidence_set_digest,
        "tdd_cycle_digest": current_tdd_cycle_digest,
        "test_law_baseline_digest": current_test_law_baseline_digest,
    }
    return all(receipt.get(field) == value for field, value in expected.items())


def review_receipt_digest(receipt: dict) -> str:
    if not isinstance(receipt, dict) or receipt.get("receipt_sha256") != _receipt_digest(receipt):
        raise ReviewError("review receipt integrity failure")
    return receipt["receipt_sha256"]
