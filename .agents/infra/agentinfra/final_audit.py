from __future__ import annotations

"""Evidence-sealed FINAL_AUDIT contract.

The state machine decides when a task may enter FINAL_AUDIT.  This module
defines the exact observation set required to complete it.  Observation
producers are framework-controlled commands or verified/external boundaries;
manual assertions can never become a passing audit receipt.
"""

from collections import Counter
import hashlib
import json
import re


REQUIRED_FINAL_AUDIT_CHECKS = (
    "expected_repository_root",
    "boundary_snapshot_current",
    "governance_digest_unchanged",
    "no_agents_mutation",
    "no_governing_instruction_mutation",
    "no_unexpected_nested_repository_mutation",
    "no_overwritten_user_owned_dirty_file",
    "no_unexpected_generated_churn",
    "no_unexpected_lockfile_change",
    "no_unauthorized_dependency_change",
    "no_unauthorized_test_law_mutation",
    "no_reference_mutation",
    "write_scope_respected",
    "change_budget_respected_or_replanned",
    "semantic_budget_respected_or_replanned",
    "all_hard_gates_proven",
    "all_required_gates_proven_or_externally_waived",
    "advisory_omissions_justified",
    "mandatory_gate_families_present",
    "every_behavioral_production_change_has_tdd_cycle",
    "test_design_predates_implementation",
    "baseline_execution_predates_implementation",
    "required_red_legitimate_and_current",
    "characterization_present_where_required",
    "test_contract_frozen",
    "oracle_frozen",
    "green_same_frozen_contract",
    "green_current_implementation_epoch",
    "verification_current",
    "review_current",
    "review_lease_closed",
    "falsification_recorded",
    "no_unresolved_blocking_finding",
    "required_commands_executed",
    "no_secrets_introduced",
    "no_suspicious_test_aware_behavior",
    "no_fake_red",
    "no_fabricated_capability_claim",
    "final_workspace_fingerprint_recorded",
    "compiled_task_contract_current",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PROVENANCE = {"framework-command", "verified-observation", "external-source"}
_FINAL_STATUSES = {"PROVEN", "NOT_APPLICABLE"}


class FinalAuditError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def seal_audit_observation(
    *,
    check_id: str,
    status: str,
    evidence_digest: str,
    provenance: str,
    detail: str,
    justification: str | None = None,
) -> dict:
    if check_id not in REQUIRED_FINAL_AUDIT_CHECKS:
        raise FinalAuditError(f"unknown final-audit check: {check_id}")
    if status not in _FINAL_STATUSES:
        raise FinalAuditError("final-audit observation must be PROVEN or NOT_APPLICABLE")
    if not isinstance(evidence_digest, str) or not _SHA256_RE.fullmatch(evidence_digest):
        raise FinalAuditError("final-audit observation requires a canonical evidence digest")
    if provenance not in _PROVENANCE:
        raise FinalAuditError("manual or unknown provenance cannot prove final audit")
    if not isinstance(detail, str) or not detail.strip():
        raise FinalAuditError("final-audit observation requires execution detail")
    if status == "NOT_APPLICABLE" and (
        not isinstance(justification, str) or not justification.strip()
    ):
        raise FinalAuditError("NOT_APPLICABLE final-audit observation requires justification")
    body = {
        "schema": 1,
        "check_id": check_id,
        "status": status,
        "evidence_digest": evidence_digest,
        "provenance": provenance,
        "detail": detail.strip(),
        "justification": justification.strip() if isinstance(justification, str) else None,
    }
    body["observation_sha256"] = _digest(body)
    return body


def _validate_observation(record: object, expected_id: str) -> dict:
    if not isinstance(record, dict) or record.get("schema") != 1:
        raise FinalAuditError(f"invalid final-audit observation schema: {expected_id}")
    if record.get("check_id") != expected_id:
        raise FinalAuditError("final-audit observations are missing, duplicated, or reordered")
    claimed = record.get("observation_sha256")
    body = {key: value for key, value in record.items() if key != "observation_sha256"}
    if claimed != _digest(body):
        raise FinalAuditError(f"final-audit observation seal is invalid: {expected_id}")
    if record.get("status") not in _FINAL_STATUSES:
        raise FinalAuditError(f"final-audit check is not proven: {expected_id}")
    if record.get("provenance") not in _PROVENANCE:
        raise FinalAuditError(f"final-audit check has manual/unknown provenance: {expected_id}")
    if not _SHA256_RE.fullmatch(str(record.get("evidence_digest", ""))):
        raise FinalAuditError(f"final-audit evidence digest is invalid: {expected_id}")
    if not isinstance(record.get("detail"), str) or not record["detail"].strip():
        raise FinalAuditError(f"final-audit execution detail is missing: {expected_id}")
    if record.get("status") == "NOT_APPLICABLE" and (
        not isinstance(record.get("justification"), str) or not record["justification"].strip()
    ):
        raise FinalAuditError(f"final-audit NOT_APPLICABLE check is unjustified: {expected_id}")
    return record


def finalize_audit(
    observations: list[dict],
    *,
    expected_workspace_digest: str,
    current_workspace_digest: str,
) -> dict:
    if not isinstance(observations, list) or len(observations) != len(REQUIRED_FINAL_AUDIT_CHECKS):
        raise FinalAuditError(
            f"final audit requires exactly {len(REQUIRED_FINAL_AUDIT_CHECKS)} observations"
        )
    if not _SHA256_RE.fullmatch(str(expected_workspace_digest)) or not _SHA256_RE.fullmatch(
        str(current_workspace_digest)
    ):
        raise FinalAuditError("final audit requires canonical workspace digests")
    if expected_workspace_digest != current_workspace_digest:
        raise FinalAuditError("workspace changed during final audit")
    validated = [
        _validate_observation(record, check_id)
        for record, check_id in zip(observations, REQUIRED_FINAL_AUDIT_CHECKS)
    ]
    if [record["check_id"] for record in validated] != list(REQUIRED_FINAL_AUDIT_CHECKS):
        raise FinalAuditError("final-audit observation identity is not an exact contract bijection")
    counts = dict(sorted(Counter(record["status"] for record in validated).items()))
    body = {
        "schema": 1,
        "outcome": "PASS",
        "check_count": len(validated),
        "counts": counts,
        "workspace_sha256": current_workspace_digest,
        "observations": validated,
    }
    body["receipt_sha256"] = _digest(body)
    return body
