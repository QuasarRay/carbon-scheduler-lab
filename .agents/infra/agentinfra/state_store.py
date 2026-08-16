from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import re
import uuid
from pathlib import Path

from .assurance import (
    AssuranceError,
    TDD_MODES as ASSURANCE_TDD_MODES,
    validate_falsification_receipt,
    validate_tdd_cycle,
)
from .atomic import atomic_write_json
from .controls import GATE_SEVERITIES, validate_gate_waiver
from .evidence import evidence_lock, load_evidence
from .locks import FileLock, LeaseLock
from .paths import leases_dir, persistent_dir, runtime_dir, tasks_dir
from .security import confined_path
from .review import ReviewError, review_receipt_digest, validate_review_receipt
from .state_machine import ALLOWED, STATES, TERMINAL_STATES, validate_transition
from .transaction import FileTransaction, Mutation
from .workspace import workspace_fingerprint


TASK_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
RECORD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
MODES = {"read", "write"}
COMPLEXITIES = {"S", "M", "L", "XL"}
RISKS = {"low", "medium", "high", "critical"}
GATE_STATUSES = {"OPEN", "PROVEN", "WAIVED"}
RISK_STATUSES = {"open", "resolved"}
WAIVER_AUTHORITY_RE = re.compile(r"^policy:[a-z0-9](?:[a-z0-9_.-]{0,62}[a-z0-9])?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TDD_MODES = {"RED_REQUIRED", "CHARACTERIZATION_REQUIRED", "NON_BEHAVIORAL_TEST_FIRST"}
EMPTY_EVIDENCE_SET_DIGEST = hashlib.sha256(b"").hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_tdd() -> dict:
    """Return an unprivileged TDD contract.

    Every field starts fail-closed.  A policy compiler / baseline recorder must
    populate the complete conjunction before a mutating transition is allowed.
    """

    return {
        "mode": None,
        "test_design_complete": False,
        "baseline_executed": False,
        "baseline_outcome": None,
        "required_baseline_outcome": None,
        "test_contract_digest": None,
        "frozen_test_contract_digest": None,
        "oracle_digest": None,
        "frozen_oracle_digest": None,
        "baseline_implementation_digest": None,
        "observed_implementation_digest": None,
        "harness_valid": False,
        "baseline_intact": False,
        "semantic_reason": "",
        "active_cycle_id": None,
        "green_epoch": None,
        "cycles": [],
    }


def slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()[:48]
    return text or "task"


def validate_task_id(task_id: str) -> str:
    if not isinstance(task_id, str) or not TASK_ID_RE.fullmatch(task_id):
        raise ValueError("task id must be 1-64 canonical lowercase letters/digits/hyphens")
    if task_id in {".", ".."}:
        raise ValueError("dot task ids are forbidden")
    return task_id


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _state_digest(task: dict) -> str:
    return hashlib.sha256(_canonical({key: value for key, value in task.items() if key != "integrity_sha256"})).hexdigest()


def _anchor_digest(anchor: dict) -> str:
    return hashlib.sha256(_canonical({key: value for key, value in anchor.items() if key != "anchor_sha256"})).hexdigest()


def _artifact_digest(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    digest = value.get("digest", value.get("sha256"))
    return digest if isinstance(digest, str) and SHA256_RE.fullmatch(digest) else None


def _evidence_set_digest(records: list[dict]) -> str:
    """Bind the ordered, verified ledger without inventing a non-empty sentinel."""

    encoded = b"".join(record["record_sha256"].encode("ascii") for record in records)
    return hashlib.sha256(encoded).hexdigest()


def _current_tdd_cycle(task: dict) -> dict | None:
    tdd = task.get("tdd")
    if not isinstance(tdd, dict):
        return None
    active = tdd.get("active_cycle_id")
    cycles = tdd.get("cycles", [])
    if not isinstance(active, str) or not isinstance(cycles, list):
        return None
    return next((cycle for cycle in cycles if isinstance(cycle, dict) and cycle.get("cycle_id") == active), None)


def _unique_ids(items: list, label: str) -> None:
    ids = [item.get("id") for item in items]
    if any(not isinstance(item, str) or not RECORD_ID_RE.fullmatch(item) for item in ids):
        raise RuntimeError(f"state schema: {label} id must be canonical and bounded")
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"state schema: duplicate {label} id")


def validate_task(task: dict, *, expected_id: str | None = None, verify_integrity: bool = True) -> None:
    if not isinstance(task, dict):
        raise RuntimeError("state schema: task must be an object")
    schema = task.get("schema")
    if schema not in {2, 3, 4}:
        raise RuntimeError(f"state schema: unsupported version {schema!r}")
    required = {
        "schema",
        "id",
        "title",
        "mode",
        "complexity",
        "risk",
        "state",
        "revision",
        "created",
        "updated",
        "precheck",
        "gates",
        "risks",
        "decisions",
        "child_history",
        "verification_evidence",
        "verification_epoch",
        "change_epoch",
        "final_audit_complete",
        "active_child",
        "previous_state",
        "transitions",
    }
    missing = sorted(required - set(task))
    if missing:
        raise RuntimeError("state schema: missing required fields: " + ", ".join(missing))
    if schema == 4 and "tdd" not in task:
        raise RuntimeError("state schema: missing required fields: tdd")
    task_id = validate_task_id(task["id"])
    if expected_id is not None and task_id != expected_id:
        raise RuntimeError("state file task id does not match owning task directory")
    if task.get("mode") not in MODES:
        raise RuntimeError("state schema: invalid mode")
    if task.get("complexity") not in COMPLEXITIES:
        raise RuntimeError("state schema: invalid complexity")
    if task.get("risk") not in RISKS:
        raise RuntimeError("state schema: invalid risk")
    if task.get("state") not in STATES:
        raise RuntimeError("state schema: invalid workflow state")
    if not isinstance(task.get("title"), str) or not task["title"].strip():
        raise RuntimeError("state schema: title must be a non-empty string")
    for field in ("created", "updated"):
        if not isinstance(task.get(field), str) or not task[field].strip():
            raise RuntimeError(f"state schema: {field} must be a timestamp string")
    for field in ("revision", "change_epoch"):
        value = task.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise RuntimeError(f"state schema: {field} must be a non-negative integer")
    for field in ("precheck",):
        if not isinstance(task.get(field), dict):
            raise RuntimeError(f"state schema: {field} must be an object")
    if "tdd" in task:
        tdd = task["tdd"]
        if not isinstance(tdd, dict):
            raise RuntimeError("state schema: tdd must be an object")
        expected_tdd_fields = set(_empty_tdd())
        missing_tdd = sorted(expected_tdd_fields - set(tdd))
        if missing_tdd:
            raise RuntimeError("state schema: incomplete tdd contract: " + ", ".join(missing_tdd))
        if tdd.get("mode") is not None and tdd.get("mode") not in TDD_MODES:
            raise RuntimeError("state schema: invalid tdd mode")
        for field in ("test_design_complete", "baseline_executed", "harness_valid", "baseline_intact"):
            if not isinstance(tdd.get(field), bool):
                raise RuntimeError(f"state schema: tdd {field} must be boolean")
        for field in (
            "test_contract_digest",
            "frozen_test_contract_digest",
            "oracle_digest",
            "frozen_oracle_digest",
            "baseline_implementation_digest",
            "observed_implementation_digest",
        ):
            value = tdd.get(field)
            if value is not None and (not isinstance(value, str) or not SHA256_RE.fullmatch(value)):
                raise RuntimeError(f"state schema: tdd {field} must be null or a canonical sha256")
        if tdd.get("baseline_outcome") not in {None, "RED", "CHARACTERIZED", "TEST_FIRST"}:
            raise RuntimeError("state schema: invalid tdd baseline outcome")
        if tdd.get("required_baseline_outcome") not in {None, "RED", "CHARACTERIZED", "TEST_FIRST"}:
            raise RuntimeError("state schema: invalid required tdd baseline outcome")
        if not isinstance(tdd.get("semantic_reason"), str) or not isinstance(tdd.get("cycles"), list):
            raise RuntimeError("state schema: invalid tdd semantic reason or cycle ledger")
        green_epoch = tdd.get("green_epoch")
        if green_epoch is not None and (
            not isinstance(green_epoch, int) or isinstance(green_epoch, bool) or green_epoch <= 0
        ):
            raise RuntimeError("state schema: tdd green_epoch must be null or a positive integer")
        cycle_ids: list[str] = []
        for cycle in tdd["cycles"]:
            try:
                validate_tdd_cycle(cycle)
            except AssuranceError as exc:
                raise RuntimeError(f"state schema: invalid TDD cycle: {exc}") from exc
            if cycle.get("task_id") != task_id:
                raise RuntimeError("state schema: TDD cycle belongs to another task")
            cycle_ids.append(cycle["cycle_id"])
        if len(cycle_ids) != len(set(cycle_ids)):
            raise RuntimeError("state schema: duplicate TDD cycle id")
        active_cycle_id = tdd.get("active_cycle_id")
        if active_cycle_id is not None and active_cycle_id not in cycle_ids:
            raise RuntimeError("state schema: active TDD cycle does not exist")
    for field in ("implementation_digest", "diff_digest", "evidence_set_digest"):
        value = task.get(field)
        if value is not None and (not isinstance(value, str) or not SHA256_RE.fullmatch(value)):
            raise RuntimeError(f"state schema: {field} must be null or a canonical sha256")
    falsification = task.get("falsification")
    if falsification is not None:
        if not validate_falsification_receipt(falsification, task_id=task_id, require_clean=False):
            raise RuntimeError("state schema: invalid falsification receipt")
    review_receipt = task.get("review_receipt")
    if review_receipt is not None:
        try:
            review_receipt_digest(review_receipt)
        except ReviewError as exc:
            raise RuntimeError("state schema: invalid review receipt") from exc
        if review_receipt.get("task_id") != task_id:
            raise RuntimeError("state schema: review receipt belongs to another task")
    for field in ("gates", "risks", "decisions", "child_history", "verification_evidence", "transitions"):
        if not isinstance(task.get(field), list):
            raise RuntimeError(f"state schema: {field} must be an array")
    _unique_ids(task["gates"], "gate")
    _unique_ids(task["risks"], "risk")
    _unique_ids(task["decisions"], "decision")
    handoff_ids = [item.get("handoff_id", item.get("lease_id")) for item in task["child_history"]]
    if len(handoff_ids) != len(set(handoff_ids)):
        raise RuntimeError("state schema: duplicate child handoff id")
    if any(not isinstance(value, str) or not value.startswith("E-") for value in task["verification_evidence"]):
        raise RuntimeError("state schema: invalid verification evidence id")
    if len(task["verification_evidence"]) != len(set(task["verification_evidence"])):
        raise RuntimeError("state schema: duplicate verification evidence id")
    verification_epoch = task.get("verification_epoch")
    if verification_epoch is not None and (not isinstance(verification_epoch, int) or isinstance(verification_epoch, bool) or verification_epoch < 0):
        raise RuntimeError("state schema: verification_epoch must be null or non-negative integer")
    for field in ("final_audit_complete", "material_claim"):
        if field in task and not isinstance(task[field], bool):
            raise RuntimeError(f"state schema: {field} must be boolean")
    for gate in task["gates"]:
        if gate.get("status") not in GATE_STATUSES or not isinstance(gate.get("description"), str) or not gate["description"].strip():
            raise RuntimeError("state schema: invalid acceptance gate")
        gate_severity = gate.get("severity", "high")
        if gate_severity not in RISKS:
            raise RuntimeError("state schema: invalid acceptance gate severity")
        constitutional_severity = gate.get("gate_severity")
        if constitutional_severity is not None and constitutional_severity not in GATE_SEVERITIES:
            raise RuntimeError("state schema: invalid HARD/REQUIRED/ADVISORY gate severity")
        evidence = gate.get("evidence", [])
        if not isinstance(evidence, list) or len(evidence) != len(set(evidence)) or any(not isinstance(item, str) or not item.startswith("E-") for item in evidence):
            raise RuntimeError("state schema: invalid gate evidence references")
        if gate.get("status") == "PROVEN" and not evidence:
            raise RuntimeError("state schema: a proven acceptance gate requires evidence")
        created_revision = gate.get("created_revision", 0)
        if not isinstance(created_revision, int) or isinstance(created_revision, bool) or created_revision < 0:
            raise RuntimeError("state schema: invalid gate creation revision")
        if gate.get("status") == "WAIVED" and constitutional_severity is None and (
            not isinstance(gate.get("waiver_reason"), str) or not gate["waiver_reason"].strip()
            or not isinstance(gate.get("waiver_authority"), str)
            or not WAIVER_AUTHORITY_RE.fullmatch(gate["waiver_authority"])
        ):
            # Schema-2/early-schema-3 records may predate explicit authority.  They
            # remain readable only until mutation migrates them; new CLI writes always bind authority.
            if schema >= 3 and gate.get("created_revision") is not None:
                raise RuntimeError("state schema: waived gate lacks reason/authority")
        if gate.get("status") == "WAIVED" and constitutional_severity is not None and (
            constitutional_severity != "REQUIRED"
            or not isinstance(gate.get("waiver_evidence"), str)
            or not gate["waiver_evidence"].startswith("E-")
        ):
            raise RuntimeError("state schema: REQUIRED gate waiver requires external waiver evidence; HARD and ADVISORY gates are not waivable")
        if gate.get("status") == "WAIVED" and gate_severity == "critical" and constitutional_severity is None:
            raise RuntimeError("state schema: critical acceptance gates cannot be waived by local policy")
    for risk in task["risks"]:
        if risk.get("severity") not in RISKS or risk.get("status") not in RISK_STATUSES or not isinstance(risk.get("description"), str) or not risk["description"].strip():
            raise RuntimeError("state schema: invalid risk record")
        if risk.get("status") == "resolved" and (not isinstance(risk.get("resolution"), str) or not risk["resolution"].strip()):
            raise RuntimeError("state schema: resolved risk lacks resolution")
    decision_ids: set[str] = set()
    for decision in task["decisions"]:
        if not isinstance(decision.get("statement"), str) or not decision["statement"].strip() or not isinstance(decision.get("rationale"), str) or not decision["rationale"].strip():
            raise RuntimeError("state schema: invalid decision record")
        if not isinstance(decision.get("evidence", []), list):
            raise RuntimeError("state schema: decision evidence must be an array")
        supersedes = decision.get("supersedes")
        if supersedes is not None and supersedes not in decision_ids:
            raise RuntimeError("state schema: decision supersedes unknown or future decision")
        decision_ids.add(decision["id"])
    for handoff in task["child_history"]:
        handoff_id = handoff.get("handoff_id", handoff.get("lease_id"))
        if not isinstance(handoff_id, str) or not handoff_id.strip() or handoff.get("outcome") not in {"accepted", "rejected", "partial", "recovered"}:
            raise RuntimeError("state schema: invalid child handoff")
        if not isinstance(handoff.get("summary"), str) or not handoff["summary"].strip() or not isinstance(handoff.get("evidence", []), list):
            raise RuntimeError("state schema: child handoff requires summary/evidence")
    active = task.get("active_child")
    if active is not None:
        if not isinstance(active, dict) or any(not isinstance(active.get(key), str) or not active[key].strip() for key in ("role", "opened", "lease_id")):
            raise RuntimeError("state schema: invalid active child")
        brief = active.get("context_brief")
        if brief is not None:
            if (
                not isinstance(brief, dict)
                or brief.get("schema") != 1
                or brief.get("task_id") != task.get("id")
                or brief.get("change_epoch") != task.get("change_epoch")
                or not isinstance(brief.get("evidence"), list)
            ):
                raise RuntimeError("state schema: invalid active child context brief")
            for fact in brief["evidence"]:
                if not isinstance(fact, dict) or not isinstance(fact.get("id"), str) or not fact["id"].startswith("E-") or not isinstance(fact.get("record_sha256"), str):
                    raise RuntimeError("state schema: invalid child context fact")
            encoded = json.dumps(brief, sort_keys=True, separators=(",", ":")).encode("utf-8")
            if len(encoded) > 16_384 or active.get("context_brief_sha256") != hashlib.sha256(encoded).hexdigest():
                raise RuntimeError("state schema: child context brief bound/digest limit failure")
    previous_to = "CREATED"
    last_revision = -1
    for index, transition in enumerate(task["transitions"]):
        if transition.get("from") != previous_to or transition.get("to") not in ALLOWED.get(previous_to, set()):
            raise RuntimeError(f"state schema: corrupted transition history at entry {index + 1}")
        if schema >= 3:
            revision = transition.get("revision")
            if not isinstance(revision, int) or revision <= last_revision:
                raise RuntimeError("state schema: transition revisions are not strictly monotonic")
            last_revision = revision
            if not isinstance(transition.get("epoch"), int):
                raise RuntimeError("state schema: transition epoch missing")
        if not isinstance(transition.get("reason"), str) or not transition["reason"].strip() or not isinstance(transition.get("at"), str):
            raise RuntimeError("state schema: transition reason/timestamp is invalid")
        previous_to = transition["to"]
    if task["transitions"] and task.get("state") != previous_to:
        raise RuntimeError("state schema: workflow state does not match transition history")
    if not task["transitions"] and task.get("state") != "CREATED":
        raise RuntimeError("state schema: non-created state has no transition history")
    if schema >= 3 and verify_integrity:
        if task.get("integrity_sha256") != _state_digest(task):
            raise RuntimeError("state integrity digest mismatch")


class StateStore:
    def __init__(self, root: Path):
        self.root = root.resolve(strict=True)
        self._loaded_identity: dict[int, str] = {}

    def _control_dir(self, relative: str | Path) -> Path:
        path = confined_path(self.root, relative, reject_symlinks=True)
        path.mkdir(parents=True, exist_ok=True)
        return confined_path(self.root, path, must_exist=True, reject_symlinks=True)

    def _runtime_root(self) -> Path:
        return self._control_dir(runtime_dir(self.root).relative_to(self.root))

    def _persistent_root(self) -> Path:
        return self._control_dir(persistent_dir(self.root).relative_to(self.root))

    def _leases_root(self) -> Path:
        return self._control_dir(leases_dir(self.root).relative_to(self.root))

    def _transaction_dir(self) -> Path:
        return self._control_dir(persistent_dir(self.root).relative_to(self.root) / "transactions")

    def _task_dir(self, task_id: str) -> Path:
        task_id = validate_task_id(task_id)
        base = self._control_dir(tasks_dir(self.root).relative_to(self.root))
        return confined_path(self.root, base / task_id, reject_symlinks=True)

    def _path(self, task_id: str) -> Path:
        return confined_path(self.root, self._task_dir(task_id) / "state.json", reject_symlinks=True)

    def _lock(self, task_id: str) -> FileLock:
        path = confined_path(self.root, self._task_dir(task_id) / ".state.lock", reject_symlinks=True)
        return FileLock(path, f"task:{task_id}")

    def _anchor_path(self, task_id: str) -> Path:
        task_id = validate_task_id(task_id)
        base = self._control_dir(persistent_dir(self.root).relative_to(self.root) / "task-anchors")
        return confined_path(self.root, base / f"{task_id}.json", reject_symlinks=True)

    def _anchor_history_dir(self, task_id: str, *, create: bool) -> Path:
        task_id = validate_task_id(task_id)
        base = self._control_dir(persistent_dir(self.root).relative_to(self.root) / "task-anchor-history")
        directory = confined_path(self.root, base / task_id, reject_symlinks=True)
        if create:
            directory.mkdir(parents=False, exist_ok=True)
            directory = confined_path(self.root, directory, must_exist=True, reject_symlinks=True)
        return directory

    def _anchor_history_path(self, anchor: dict) -> Path:
        revision = anchor.get("revision")
        digest = anchor.get("anchor_sha256")
        if not isinstance(revision, int) or revision < 0 or not isinstance(digest, str) or len(digest) != 64:
            raise RuntimeError("invalid task anchor history identity")
        directory = self._anchor_history_dir(anchor["task_id"], create=True)
        return confined_path(self.root, directory / f"{revision:020d}-{digest}.json", reject_symlinks=True)

    def current_path(self) -> Path:
        return confined_path(self.root, self._runtime_root() / "current-task", reject_symlinks=True)

    def _new_anchor(self, task: dict, previous: dict | None) -> dict:
        anchor = {
            "schema": 2,
            "task_id": task["id"],
            "revision": task["revision"],
            "state_sha256": task["integrity_sha256"],
            "previous_anchor_sha256": previous.get("anchor_sha256") if previous else None,
            "history_origin_revision": (
                previous.get("history_origin_revision", previous.get("revision", 0)) if previous else 0
            ),
        }
        anchor["anchor_sha256"] = _anchor_digest(anchor)
        return anchor

    def _validate_anchor_history(self, task_id: str, current: dict) -> None:
        directory = self._anchor_history_dir(task_id, create=False)
        if not directory.exists():
            if current.get("schema") == 2:
                raise RuntimeError("task anchor history is missing")
            return  # Legacy schema-1 anchors become a baseline on their next save.
        entries = sorted(directory.iterdir(), key=lambda item: item.name)
        if not entries:
            if current.get("schema") == 2:
                raise RuntimeError("task anchor history is empty")
            return
        anchors: list[dict] = []
        for raw_path in entries:
            path = confined_path(self.root, raw_path, must_exist=True, reject_symlinks=True)
            if not path.is_file() or path.suffix != ".json":
                raise RuntimeError(f"invalid task anchor history entry: {path.name}")
            try:
                anchor = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise RuntimeError(f"invalid task anchor history entry {path.name}: {exc}") from exc
            revision = anchor.get("revision") if isinstance(anchor, dict) else None
            digest_value = anchor.get("anchor_sha256") if isinstance(anchor, dict) else None
            if (
                not isinstance(anchor, dict)
                or anchor.get("schema") not in {1, 2}
                or anchor.get("task_id") != task_id
                or not isinstance(revision, int)
                or revision < 0
                or not isinstance(digest_value, str)
                or len(digest_value) != 64
                or digest_value != _anchor_digest(anchor)
                or path.name != f"{revision:020d}-{digest_value}.json"
            ):
                raise RuntimeError("task anchor history integrity failure")
            anchors.append(anchor)
        anchors.sort(key=lambda item: item["revision"])
        revisions = [item.get("revision") for item in anchors]
        if any(not isinstance(value, int) or value < 0 for value in revisions) or len(revisions) != len(set(revisions)):
            raise RuntimeError("task anchor history has invalid or duplicate revisions")
        origin = current.get("history_origin_revision", revisions[0])
        expected = list(range(origin, int(current.get("revision", -1)) + 1))
        if revisions != expected:
            raise RuntimeError("task anchor history was truncated, extended past state, or made non-contiguous")
        for previous, following in zip(anchors, anchors[1:]):
            if following.get("previous_anchor_sha256") != previous.get("anchor_sha256"):
                raise RuntimeError("task anchor history chain failure")
        if anchors[-1].get("anchor_sha256") != current.get("anchor_sha256"):
            raise RuntimeError("task anchor history head does not match current anchor")

    def _load_anchor(self, task_id: str, *, required: bool) -> dict | None:
        path = self._anchor_path(task_id)
        if not path.exists():
            if required:
                raise RuntimeError("task state anchor is missing")
            return None
        try:
            anchor = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"invalid task state anchor: {exc}") from exc
        if (
            not isinstance(anchor, dict)
            or anchor.get("schema") not in {1, 2}
            or anchor.get("task_id") != task_id
            or anchor.get("anchor_sha256") != _anchor_digest(anchor)
        ):
            raise RuntimeError("task state anchor integrity failure")
        if anchor.get("schema") == 2:
            origin = anchor.get("history_origin_revision")
            if not isinstance(origin, int) or origin < 0 or origin > int(anchor.get("revision", -1)):
                raise RuntimeError("task state anchor has invalid history origin")
        self._validate_anchor_history(task_id, anchor)
        return anchor

    def create(self, title: str, mode: str = "write", complexity: str = "M", risk: str = "medium") -> dict:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("task title must not be empty")
        if mode not in MODES or complexity not in COMPLEXITIES or risk not in RISKS:
            raise ValueError("invalid task mode, complexity, or risk")
        create_lock = FileLock(self._runtime_root() / ".task-create.lock", "task-create")
        create_lock.acquire()
        task_dir: Path | None = None
        try:
            task_id = validate_task_id(f"{slug(title)}-{uuid.uuid4().hex[:8]}")
            task_dir = self._task_dir(task_id)
            path = self._path(task_id)
            if path.exists():
                raise RuntimeError("task id collision")
            created = now()
            task = {
                "schema": 4,
                "id": task_id,
                "title": title.strip(),
                "mode": mode,
                "complexity": complexity,
                "risk": risk,
                "state": "CREATED",
                "revision": 0,
                "created": created,
                "updated": created,
                "precheck": {},
                "tdd": _empty_tdd(),
                "gates": [],
                "risks": [],
                "decisions": [],
                "child_history": [],
                "verification_evidence": [],
                "verification_epoch": None,
                "change_epoch": 0,
                "final_audit_complete": False,
                "active_child": None,
                "previous_state": None,
                "transitions": [],
                "material_claim": True,
                "evidence_head": None,
                "evidence_set_digest": EMPTY_EVIDENCE_SET_DIGEST,
                "implementation_digest": None,
                "diff_digest": None,
                "falsification": None,
                "review_receipt": None,
            }
            task["integrity_sha256"] = _state_digest(task)
            anchor = self._new_anchor(task, None)
            current = self.current_path()
            current_before = current.read_bytes() if current.exists() else None
            FileTransaction(
                self.root,
                [
                    Mutation(path, (json.dumps(task, indent=2, sort_keys=True) + "\n").encode("utf-8"), expected_sha256=None, expected_exists=False, mode=0o600),
                    Mutation(current, (task_id + "\n").encode("utf-8"), expected_sha256=hashlib.sha256(current_before).hexdigest() if current_before is not None else None, expected_exists=current_before is not None, mode=0o600),
                    Mutation(self._anchor_path(task_id), (json.dumps(anchor, indent=2, sort_keys=True) + "\n").encode("utf-8"), expected_sha256=None, expected_exists=False, mode=0o600),
                    Mutation(self._anchor_history_path(anchor), (json.dumps(anchor, indent=2, sort_keys=True) + "\n").encode("utf-8"), expected_sha256=None, expected_exists=False, mode=0o600),
                ],
                state_dir=self._transaction_dir(),
                name="task-create",
            ).commit(retain=False)
            self._loaded_identity[id(task)] = task_id
            return task
        except BaseException:
            if task_dir is not None and task_dir.exists() and not any(task_dir.iterdir()):
                task_dir.rmdir()
            raise
        finally:
            create_lock.release()

    def current_id(self) -> str:
        path = self.current_path()
        if path.is_symlink():
            raise RuntimeError("current task pointer must not be a symlink")
        try:
            task_id = path.read_text(encoding="utf-8").strip()
        except FileNotFoundError as exc:
            raise RuntimeError("no current task") from exc
        validate_task_id(task_id)
        task_path = self._path(task_id)
        if not task_path.is_file() or task_path.is_symlink():
            raise RuntimeError("current task pointer does not reference an existing real task state")
        return task_id

    def _load_unlocked(self, task_id: str, *, evidence_locked: bool = False) -> dict:
        path = self._path(task_id)
        if path.is_symlink():
            raise RuntimeError("state file must not be a symlink")
        try:
            task = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise
        except Exception as exc:
            raise RuntimeError(f"invalid task state JSON: {exc}") from exc
        validate_task(task, expected_id=task_id)
        if task.get("schema", 0) >= 3:
            anchor = self._load_anchor(task_id, required=True)
            if anchor.get("revision") != task.get("revision") or anchor.get("state_sha256") != task.get("integrity_sha256"):
                raise RuntimeError("task state does not match its durable task anchor")
        if task.get("state") == "FINALIZE":
            ledger_lock = None if evidence_locked else evidence_lock(self._task_dir(task_id))
            if ledger_lock is not None:
                ledger_lock.acquire()
            try:
                records = load_evidence(self._task_dir(task_id), verify=True)
            finally:
                if ledger_lock is not None:
                    ledger_lock.release()
            ledger_head = records[-1].get("record_sha256") if records else None
            if ledger_head != task.get("evidence_head"):
                raise RuntimeError("finalized task evidence head no longer matches its ledger")
            audited = task.get("final_audit_workspace")
            current = workspace_fingerprint(self.root)
            if (
                not isinstance(audited, dict)
                or audited.get("available") is not True
                or current.get("available") is not True
                or current.get("sha256") != audited.get("sha256")
            ):
                raise RuntimeError("finalized task workspace no longer matches its audited fingerprint")
        self._loaded_identity[id(task)] = task_id
        return task

    def load(self, task_id: str | None = None) -> dict:
        task_id = validate_task_id(task_id or self.current_id())
        return self._load_unlocked(task_id)

    def list_tasks(self) -> list[dict]:
        out = []
        base = self._control_dir(tasks_dir(self.root).relative_to(self.root))
        for directory in sorted(base.iterdir()):
            if not directory.is_dir() or directory.is_symlink():
                continue
            try:
                task_id = validate_task_id(directory.name)
                task = self._load_unlocked(task_id)
                out.append({key: task.get(key) for key in ("id", "title", "mode", "complexity", "risk", "state", "revision", "created", "updated")})
            except Exception as exc:
                out.append({"id": directory.name, "state": "CORRUPT", "error": str(exc)})
        return sorted(out, key=lambda item: (item.get("updated") or "", item.get("id") or ""), reverse=True)

    def _migrate(self, task: dict) -> dict:
        migrated = json.loads(json.dumps(task))
        if migrated.get("schema") != 4:
            migrated["schema"] = 4
        migrated.setdefault("material_claim", True)
        migrated.setdefault("evidence_head", None)
        migrated.setdefault("evidence_set_digest", EMPTY_EVIDENCE_SET_DIGEST)
        migrated.setdefault("implementation_digest", None)
        migrated.setdefault("diff_digest", None)
        migrated.setdefault("falsification", None)
        migrated.setdefault("review_receipt", None)
        migrated.setdefault("tdd", _empty_tdd())
        for field, default in _empty_tdd().items():
            migrated["tdd"].setdefault(field, json.loads(json.dumps(default)))
        epoch = 0
        for index, transition in enumerate(migrated.get("transitions", []), 1):
            if transition.get("to") in {"IMPLEMENT", "REMEDIATE"}:
                epoch += 1
            transition.setdefault("revision", index)
            transition.setdefault("epoch", epoch)
        migrated["integrity_sha256"] = _state_digest(migrated)
        return migrated

    def _validate_append_only(self, current: dict, updated: dict) -> None:
        for field in ("id", "title", "mode", "complexity", "risk", "created"):
            if updated.get(field) != current.get(field):
                raise RuntimeError(f"immutable task field changed: {field}")
        for field in ("decisions", "child_history", "transitions"):
            before = current.get(field, [])
            after = updated.get(field, [])
            if after[: len(before)] != before:
                raise RuntimeError(f"append-only task history was rewritten: {field}")
        before_cycles = current.get("tdd", {}).get("cycles", [])
        after_cycles = updated.get("tdd", {}).get("cycles", [])
        if len(after_cycles) < len(before_cycles):
            raise RuntimeError("TDD cycle history cannot be deleted")
        immutable_cycle_fields = (
            "schema",
            "task_id",
            "cycle_id",
            "mode",
            "remediation",
            "discovered_epoch",
            "designed_at_revision",
            "test_contract_digest",
            "oracle_digest",
            "baseline_epoch",
        )
        for old, new in zip(before_cycles, after_cycles):
            if any(new.get(field) != old.get(field) for field in immutable_cycle_fields):
                raise RuntimeError("TDD cycle identity or frozen contract was rewritten")
            old_events = old.get("events", [])
            new_events = new.get("events", [])
            if new_events[: len(old_events)] != old_events:
                raise RuntimeError("append-only TDD cycle evidence was rewritten")
            if old.get("status") in {"TDD_CYCLE_ABORTED", "TDD_CYCLE_COMPLETE"} and new != old:
                raise RuntimeError("terminal TDD cycle is immutable")
        if updated.get("change_epoch", 0) < current.get("change_epoch", 0) or updated.get("change_epoch", 0) > current.get("change_epoch", 0) + 1:
            raise RuntimeError("implementation epoch changed non-monotonically")
        before_gates = {item["id"]: item for item in current.get("gates", [])}
        after_gate_ids = {item["id"] for item in updated.get("gates", [])}
        if not set(before_gates) <= after_gate_ids:
            raise RuntimeError("acceptance gate history cannot be deleted")
        for gate in updated.get("gates", []):
            old = before_gates.get(gate["id"])
            if old and (
                gate.get("description") != old.get("description")
                or gate.get("severity", "high") != old.get("severity", "high")
                or gate.get("gate_severity") != old.get("gate_severity")
                or gate.get("created_revision") != old.get("created_revision")
            ):
                raise RuntimeError("acceptance gate identity/history was rewritten")
        before_risks = {item["id"]: item for item in current.get("risks", [])}
        after_risk_ids = {item["id"] for item in updated.get("risks", [])}
        if not set(before_risks) <= after_risk_ids:
            raise RuntimeError("risk history cannot be deleted")
        for risk in updated.get("risks", []):
            old = before_risks.get(risk["id"])
            if old and (
                risk.get("description") != old.get("description")
                or risk.get("severity") != old.get("severity")
            ):
                raise RuntimeError("risk history was rewritten")

    @staticmethod
    def _falsification_bindings(task: dict) -> tuple[object, ...]:
        cycle = _current_tdd_cycle(task)
        return (
            task.get("id"),
            cycle.get("cycle_sha256") if cycle else None,
            task.get("change_epoch"),
            task.get("implementation_digest"),
            task.get("diff_digest"),
        )

    @staticmethod
    def _review_bindings(task: dict) -> tuple[object, ...]:
        cycle = _current_tdd_cycle(task)
        return (
            task.get("id"),
            cycle.get("cycle_sha256") if cycle else None,
            task.get("change_epoch"),
            task.get("implementation_digest"),
            task.get("diff_digest"),
            _artifact_digest(task.get("precheck", {}).get("compiled_policy")),
            task.get("evidence_set_digest"),
            _artifact_digest(task.get("precheck", {}).get("test_law_baseline")),
        )

    @staticmethod
    def _validate_bound_falsification(task: dict, *, require_clean: bool) -> None:
        receipt = task.get("falsification")
        cycle = _current_tdd_cycle(task)
        if receipt is None or cycle is None or not validate_falsification_receipt(
            receipt,
            task_id=task.get("id"),
            current_tdd_cycle_digest=cycle.get("cycle_sha256"),
            current_epoch=task.get("change_epoch"),
            current_diff_digest=task.get("diff_digest"),
            require_clean=require_clean,
        ):
            raise RuntimeError("falsification receipt is missing, stale, contains a counterexample, or is invalid")

    @staticmethod
    def _validate_bound_review(task: dict) -> None:
        receipt = task.get("review_receipt")
        cycle = _current_tdd_cycle(task)
        if receipt is None or cycle is None or receipt.get("task_id") != task.get("id"):
            raise RuntimeError("independent review receipt is missing or belongs to another task")
        reviewer_role = str(receipt.get("reviewer_role", "")).casefold()
        if not any(marker in reviewer_role for marker in ("adversarial", "security")):
            raise RuntimeError("independent review receipt lacks an adversarial/security role")
        matching_handoff = any(
            item.get("lease_id", item.get("handoff_id")) == receipt.get("reviewer_lease")
            and item.get("role") == receipt.get("reviewer_role")
            and item.get("outcome") in {"accepted", "partial"}
            for item in task.get("child_history", [])
        )
        if not matching_handoff:
            raise RuntimeError("review receipt is not bound to a closed accepted child lease")
        if not validate_review_receipt(
            receipt,
            current_epoch=task.get("change_epoch"),
            current_diff_digest=task.get("diff_digest"),
            current_requirements_digest=_artifact_digest(task.get("precheck", {}).get("compiled_policy")),
            current_evidence_set_digest=task.get("evidence_set_digest"),
            current_tdd_cycle_digest=cycle.get("cycle_sha256"),
            current_test_law_baseline_digest=_artifact_digest(task.get("precheck", {}).get("test_law_baseline")),
        ):
            raise RuntimeError("independent review receipt is stale, rejected, or invalid")

    def _save_locked(
        self,
        current: dict,
        updated: dict,
        expected_revision: int,
        *,
        evidence_locked: bool = False,
    ) -> dict:
        if not evidence_locked:
            ledger_lock = evidence_lock(self._task_dir(current["id"]))
            ledger_lock.acquire()
            try:
                return self._save_locked(
                    current,
                    updated,
                    expected_revision,
                    evidence_locked=True,
                )
            finally:
                ledger_lock.release()
        if current["revision"] != expected_revision:
            raise RuntimeError(f"stale task revision: expected {expected_revision}, found {current['revision']}")
        migrated_current = self._migrate(current)
        updated = self._migrate(updated)
        if updated.get("id") != current.get("id"):
            raise RuntimeError("task id mutation cannot redirect state storage")
        records = load_evidence(self._task_dir(current["id"]), verify=True)
        records_by_id = {record["id"]: record for record in records}
        for gate in updated.get("gates", []):
            if gate.get("status") == "WAIVED" and gate.get("gate_severity") is not None and not validate_gate_waiver(
                gate,
                records_by_id,
                task_id=current["id"],
                current_epoch=int(updated.get("change_epoch", 0)),
            ):
                raise RuntimeError("REQUIRED gate waiver lacks current external trusted waiver evidence")
        ledger_head = records[-1].get("record_sha256") if records else None
        if ledger_head != updated.get("evidence_head"):
            raise RuntimeError("task evidence head is not the verified ledger head")
        if updated.get("evidence_head") != current.get("evidence_head"):
            if current.get("evidence_head") is not None and updated.get("evidence_head") is None:
                raise RuntimeError("task evidence head cannot move backwards to null")
            if current.get("evidence_head") is not None and not any(
                record.get("record_sha256") == current.get("evidence_head") for record in records[:-1]
            ):
                raise RuntimeError("evidence ledger rewrite does not extend the prior task-bound head")
        updated["evidence_set_digest"] = _evidence_set_digest(records)
        if (
            current.get("falsification") is not None
            and updated.get("falsification") == current.get("falsification")
            and self._falsification_bindings(migrated_current) != self._falsification_bindings(updated)
        ):
            updated["falsification"] = None
        if (
            current.get("review_receipt") is not None
            and updated.get("review_receipt") == current.get("review_receipt")
            and self._review_bindings(migrated_current) != self._review_bindings(updated)
        ):
            updated["review_receipt"] = None
        self._validate_append_only(migrated_current, updated)
        if updated.get("falsification") is not None:
            self._validate_bound_falsification(updated, require_clean=False)
        if updated.get("review_receipt") is not None:
            self._validate_bound_review(updated)
        claim_fields = ("gates", "risks", "verification_evidence", "verification_epoch", "evidence_head", "decisions")
        if current.get("final_audit_complete") and any(updated.get(field) != current.get(field) for field in claim_fields):
            updated["final_audit_complete"] = False
            updated.pop("final_audit_workspace", None)
        updated["revision"] = expected_revision + 1
        updated["updated"] = now()
        updated["integrity_sha256"] = _state_digest(updated)
        validate_task(updated, expected_id=current["id"])
        prior_anchor = self._load_anchor(current["id"], required=current.get("schema", 0) >= 3)
        if prior_anchor is None:
            # Schema-2 tasks predate task anchors.  Their currently validated
            # state becomes an explicit migration baseline before revision N+1.
            prior_anchor = self._new_anchor(migrated_current, None)
        anchor = self._new_anchor(updated, prior_anchor)
        state_path = self._path(current["id"])
        anchor_path = self._anchor_path(current["id"])
        mutations = [
            Mutation(state_path, (json.dumps(updated, indent=2, sort_keys=True) + "\n").encode("utf-8"), expected_sha256=hashlib.sha256(state_path.read_bytes()).hexdigest(), expected_exists=True, mode=0o600),
            Mutation(anchor_path, (json.dumps(anchor, indent=2, sort_keys=True) + "\n").encode("utf-8"), expected_sha256=hashlib.sha256(anchor_path.read_bytes()).hexdigest() if anchor_path.exists() else None, expected_exists=anchor_path.exists(), mode=0o600),
        ]
        prior_history_path = self._anchor_history_path(prior_anchor)
        if not prior_history_path.exists():
            mutations.append(
                Mutation(
                    prior_history_path,
                    (json.dumps(prior_anchor, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                    expected_exists=False,
                    mode=0o600,
                )
            )
        mutations.append(
            Mutation(
                self._anchor_history_path(anchor),
                (json.dumps(anchor, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                expected_exists=False,
                mode=0o600,
            )
        )
        FileTransaction(
            self.root,
            mutations,
            state_dir=self._transaction_dir(),
            name="task-state",
        ).commit(retain=False)
        self._loaded_identity[id(updated)] = current["id"]
        return updated

    def save(self, task: dict, expected_revision: int) -> dict:
        storage_id = self._loaded_identity.get(id(task))
        if storage_id is None:
            raise RuntimeError("state object was not loaded by this store; storage identity is unknown")
        if task.get("id") != storage_id:
            raise RuntimeError("task id mutation cannot redirect state storage")
        lock = self._lock(storage_id)
        lock.acquire()
        try:
            current = self._load_unlocked(storage_id)
            return self._save_locked(current, task, expected_revision)
        finally:
            lock.release()

    def mutate(
        self,
        fn,
        task_id: str | None = None,
        *,
        expected_revision: int | None = None,
        allow_active_child: bool = False,
        hold_evidence_lock: bool = False,
        on_failure=None,
    ):
        task_id = validate_task_id(task_id or self.current_id())
        lock = self._lock(task_id)
        lock.acquire()
        ledger_lock = evidence_lock(self._task_dir(task_id)) if hold_evidence_lock else None
        if ledger_lock is not None:
            ledger_lock.acquire()
        try:
            current = self._load_unlocked(task_id, evidence_locked=hold_evidence_lock)
            if current.get("state") in TERMINAL_STATES:
                raise RuntimeError(f"terminal task state {current.get('state')} rejects further mutation")
            if expected_revision is not None and current["revision"] != expected_revision:
                raise RuntimeError(f"stale task revision: expected {expected_revision}, found {current['revision']}")
            if current.get("active_child") and not allow_active_child:
                raise RuntimeError("active child blocks canonical task mutation outside handoff control")
            updated = json.loads(json.dumps(current))
            try:
                fn(updated)
                return self._save_locked(
                    current,
                    updated,
                    current["revision"],
                    evidence_locked=hold_evidence_lock,
                )
            except BaseException as exc:
                if on_failure is not None:
                    try:
                        on_failure()
                    except BaseException as rollback_exc:
                        raise RuntimeError(
                            f"task mutation failed and its evidence side effect could not be rolled back: {rollback_exc}"
                        ) from exc
                raise
        finally:
            if ledger_lock is not None:
                ledger_lock.release()
            lock.release()

    def record_tdd_cycle(self, cycle: dict, task_id: str | None = None) -> dict:
        """Append or extend one validated TDD cycle without replacing its identity."""

        validate_tdd_cycle(cycle)
        task_id = validate_task_id(task_id or self.current_id())
        if cycle.get("task_id") != task_id:
            raise AssuranceError("TDD cycle belongs to another task")
        expected_outcome, observed_status = ASSURANCE_TDD_MODES[cycle["mode"]]

        def apply(task: dict) -> None:
            cycles = task["tdd"]["cycles"]
            index = next((position for position, item in enumerate(cycles) if item.get("cycle_id") == cycle["cycle_id"]), None)
            if index is None:
                cycles.append(json.loads(json.dumps(cycle)))
            else:
                cycles[index] = json.loads(json.dumps(cycle))
            baseline_event = next(
                (event for event in cycle["events"] if event.get("status") == "BASELINE_EXECUTED"),
                None,
            )
            tdd = task["tdd"]
            tdd.update(
                mode=cycle["mode"],
                test_design_complete=True,
                baseline_executed=baseline_event is not None and cycle.get("status") != "TDD_CYCLE_ABORTED",
                baseline_outcome=baseline_event.get("outcome") if baseline_event else None,
                required_baseline_outcome=expected_outcome,
                test_contract_digest=cycle["test_contract_digest"],
                frozen_test_contract_digest=cycle.get("frozen_test_contract_digest"),
                oracle_digest=cycle["oracle_digest"],
                frozen_oracle_digest=cycle.get("frozen_oracle_digest"),
                baseline_implementation_digest=cycle.get("baseline_implementation_digest"),
                observed_implementation_digest=cycle.get("baseline_implementation_digest"),
                harness_valid=bool(baseline_event and baseline_event.get("harness_valid") is True),
                baseline_intact=bool(baseline_event and baseline_event.get("baseline_intact") is True),
                semantic_reason=str(baseline_event.get("semantic_reason", "")) if baseline_event else "",
                active_cycle_id=cycle["cycle_id"],
                green_epoch=cycle.get("green_epoch"),
            )
            if baseline_event is not None and cycle.get("status") not in {
                observed_status,
                "GREEN_PROVEN",
                "TDD_CYCLE_COMPLETE",
            }:
                raise AssuranceError("TDD cycle status contradicts its recorded baseline")
            if cycle.get("status") in {"GREEN_PROVEN", "TDD_CYCLE_COMPLETE"}:
                task["implementation_digest"] = cycle.get("green_implementation_digest")
                task["diff_digest"] = cycle.get("green_diff_digest")

        return self.mutate(apply, task_id)

    def record_falsification(self, receipt: dict, task_id: str | None = None) -> dict:
        task_id = validate_task_id(task_id or self.current_id())

        def apply(task: dict) -> None:
            if task.get("state") != "FALSIFY":
                raise RuntimeError("falsification evidence may be recorded only in FALSIFY")
            cycle = _current_tdd_cycle(task)
            if cycle is None or not validate_falsification_receipt(
                receipt,
                task_id=task_id,
                current_tdd_cycle_digest=cycle.get("cycle_sha256"),
                current_epoch=task.get("change_epoch"),
                current_diff_digest=task.get("diff_digest"),
                require_clean=False,
            ):
                raise AssuranceError("falsification receipt is invalid or stale")
            task["falsification"] = json.loads(json.dumps(receipt))

        return self.mutate(apply, task_id)

    def record_review(self, receipt: dict, task_id: str | None = None) -> dict:
        task_id = validate_task_id(task_id or self.current_id())

        def apply(task: dict) -> None:
            if task.get("state") != "ADVERSARIAL_REVIEW":
                raise RuntimeError("review evidence may be recorded only in ADVERSARIAL_REVIEW")
            task["review_receipt"] = json.loads(json.dumps(receipt))
            self._validate_bound_review(task)

        return self.mutate(apply, task_id)

    def _validate_proofs(self, task: dict, *, finalizing: bool) -> None:
        records = load_evidence(self._task_dir(task["id"]), verify=True)
        by_id = {record["id"]: record for record in records}
        ledger_head = records[-1].get("record_sha256") if records else None
        if ledger_head != task.get("evidence_head"):
            raise RuntimeError("task evidence anchor does not match evidence ledger")
        proof_ids = list(task.get("verification_evidence", []))
        for gate in task.get("gates", []):
            if gate.get("status") == "PROVEN":
                proof_ids.extend(gate.get("evidence", []))
        missing = sorted({proof for proof in proof_ids if proof not in by_id})
        if missing:
            raise RuntimeError("task references missing evidence: " + ", ".join(missing))
        epoch = int(task.get("change_epoch", 0))
        for proof_id in proof_ids:
            record = by_id[proof_id]
            if record.get("schema", 1) != 2 or record.get("task_id") != task["id"]:
                raise RuntimeError(f"proof is not task-bound framework evidence: {proof_id}")
            if record.get("change_epoch") != epoch:
                raise RuntimeError(f"proof is stale for current implementation epoch: {proof_id}")
            if record.get("provenance") not in {"framework-command", "verified-observation", "external-source"}:
                raise RuntimeError(f"manual/fabricated evidence cannot satisfy verification: {proof_id}")
            command = record.get("details", {}).get("command")
            if record.get("provenance") == "framework-command" and (not isinstance(command, dict) or command.get("success") is not True):
                raise RuntimeError(f"failed/unexecuted command cannot satisfy verification: {proof_id}")
            if record.get("provenance") == "external-source":
                details = record.get("details", {})
                source_identity = details.get("source_identity")
                source_fingerprint = details.get("source_fingerprint")
                observed_at = details.get("observed_at")
                ttl_seconds = details.get("ttl_seconds")
                if (
                    not isinstance(source_identity, str) or not source_identity.strip()
                    or not isinstance(source_fingerprint, str) or not source_fingerprint.strip()
                    or not isinstance(observed_at, str)
                    or not isinstance(ttl_seconds, (int, float)) or isinstance(ttl_seconds, bool)
                    or not math.isfinite(float(ttl_seconds)) or float(ttl_seconds) <= 0
                ):
                    raise RuntimeError(f"external-source proof lacks bound source identity/fingerprint/freshness: {proof_id}")
                try:
                    observed = datetime.fromisoformat(observed_at)
                    if observed.tzinfo is None:
                        raise ValueError("timezone is required")
                except ValueError as exc:
                    raise RuntimeError(f"external-source proof has invalid observation timestamp: {proof_id}") from exc
                age = (datetime.now(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds()
                if age < -300 or age > float(ttl_seconds):
                    raise RuntimeError(f"external-source proof is stale or future-dated: {proof_id}")
            if finalizing:
                audited = task.get("final_audit_workspace")
                observed = record.get("details", {}).get("workspace")
                if not isinstance(audited, dict) or not audited.get("available"):
                    raise RuntimeError("final audit has no available workspace fingerprint")
                if not isinstance(observed, dict) or observed.get("sha256") != audited.get("sha256"):
                    raise RuntimeError(f"proof workspace does not match final audit: {proof_id}")
        for gate in task.get("gates", []):
            if gate.get("status") != "PROVEN":
                continue
            for proof_id in gate.get("evidence", []):
                record = by_id[proof_id]
                if gate["id"] not in record.get("details", {}).get("gate_ids", []):
                    raise RuntimeError(f"gate proof lacks explicit relevance binding: {gate['id']}/{proof_id}")
                created_revision = int(gate.get("created_revision", 0))
                if int(record.get("details", {}).get("task_revision", -1)) < created_revision:
                    raise RuntimeError(f"gate proof predates gate definition: {gate['id']}/{proof_id}")

    def transition(self, target: str, reason: str, task_id: str | None = None):
        target = target.upper()
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("transition reason must not be empty")
        task_id = validate_task_id(task_id or self.current_id())
        existing = self.load(task_id)
        if existing.get("state") == target == "FINALIZE":
            return existing

        def apply(task: dict) -> None:
            validate_transition(task, target, reason=reason)
            if target in {"FINAL_AUDIT", "FINALIZE"}:
                lease = LeaseLock(self._leases_root() / "subagent-lease.json", "single-active-subagent").inspect()
                if lease.get("exists"):
                    raise RuntimeError("global subagent lease blocks final audit/finalization")
            if target in {"FINAL_AUDIT", "FINALIZE"}:
                self._validate_proofs(task, finalizing=target == "FINALIZE")
            if target == "FINALIZE":
                first = workspace_fingerprint(self.root)
                second = workspace_fingerprint(self.root)
                audited = task.get("final_audit_workspace")
                if not first.get("available") or first.get("sha256") != second.get("sha256"):
                    raise RuntimeError("workspace fingerprint was unavailable or changed during finalization")
                if not isinstance(audited, dict) or first.get("sha256") != audited.get("sha256"):
                    raise RuntimeError("workspace changed after final audit; re-verify and re-audit")
            old = task["state"]
            if target == "BLOCKED":
                task["previous_state"] = old
                task["block_reason"] = reason.strip()
            elif old == "BLOCKED":
                task["previous_state"] = None
                task.pop("block_reason", None)
            task["state"] = target
            if target in {"IMPLEMENT", "REMEDIATE"}:
                task["change_epoch"] = int(task.get("change_epoch", 0)) + 1
                task["verification_evidence"] = []
                task["verification_epoch"] = None
                task["falsification"] = None
                task["review_receipt"] = None
                task["final_audit_complete"] = False
                task.pop("final_audit_workspace", None)
                for gate in task.get("gates", []):
                    if gate.get("status") == "PROVEN":
                        gate["status"] = "OPEN"
                        gate["evidence"] = []
                for risk in task.get("risks", []):
                    if risk.get("status") == "resolved" and risk.get("reopen_on_change", True):
                        risk["status"] = "open"
                        risk.pop("resolution", None)
            elif target == "TEST_DESIGN":
                task["falsification"] = None
                task["review_receipt"] = None
                task["final_audit_complete"] = False
                task.pop("final_audit_workspace", None)
            task.setdefault("transitions", []).append(
                {
                    "at": now(),
                    "from": old,
                    "to": target,
                    "reason": reason.strip(),
                    "revision": int(task.get("revision", 0)) + 1,
                    "epoch": int(task.get("change_epoch", 0)),
                }
            )

        updated = self.mutate(apply, task_id)
        return self.load(task_id) if target == "FINALIZE" else updated

    def audit_complete(self, task_id: str | None = None) -> dict:
        task_id = validate_task_id(task_id or self.current_id())

        def apply(task: dict) -> None:
            if task.get("state") != "FINAL_AUDIT":
                raise RuntimeError("audit-complete requires task state FINAL_AUDIT")
            self._validate_proofs(task, finalizing=False)
            lease = LeaseLock(self._leases_root() / "subagent-lease.json", "single-active-subagent").inspect()
            if lease.get("exists"):
                raise RuntimeError("global subagent lease blocks final-audit completion")
            fingerprint = workspace_fingerprint(self.root)
            if not fingerprint.get("available"):
                raise RuntimeError("cannot complete final audit without an available workspace fingerprint")
            task["final_audit_workspace"] = fingerprint
            task["final_audit_complete"] = True

        return self.mutate(apply, task_id)
