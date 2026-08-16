from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from hypothesis import given, strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from .hypothesis_profiles import settings  # noqa: F401
from agentinfra.assurance import (
    AssuranceError,
    build_falsification_receipt,
    new_tdd_cycle,
    record_baseline,
    record_green,
)
from agentinfra.controls import validate_gate_waiver
from agentinfra.review import build_review_receipt
from agentinfra.state_machine import TransitionError
from agentinfra.state_store import StateStore
from agentinfra.workspace import workspace_fingerprint


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64
SHA_F = "f" * 64
EMPTY_EVIDENCE = hashlib.sha256(b"").hexdigest()


class StateAssuranceIntegrationProperties(unittest.TestCase):
    def test_state_store_rejects_caller_labelled_required_gate_waiver(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".agents").mkdir()
            (root / ".agents" / "framework.toml").write_text("[framework]\nversion='4.0.0'\n", encoding="utf-8")
            store = StateStore(root)
            store.create("waiver provenance", mode="write", risk="low")
            store.mutate(
                lambda task: task["gates"].append(
                    {
                        "id": "G1",
                        "description": "required external decision",
                        "severity": "high",
                        "gate_severity": "REQUIRED",
                        "status": "OPEN",
                        "evidence": [],
                        "created_revision": task["revision"] + 1,
                    }
                )
            )

            def forge(task: dict) -> None:
                task["gates"][0].update(
                    status="WAIVED",
                    waiver_reason="caller supplied",
                    waiver_authority="policy:caller",
                )

            with self.assertRaisesRegex(RuntimeError, "external.*waiver|waiver.*external"):
                store.mutate(forge)

    @given(
        severity=st.sampled_from(("HARD", "REQUIRED", "ADVISORY")),
        provenance=st.sampled_from(("manual", "verified-observation", "external-source")),
        epoch=st.integers(min_value=0, max_value=2),
        trusted=st.booleans(),
    )
    def test_gate_waiver_requires_current_external_trusted_provenance(
        self,
        severity: str,
        provenance: str,
        epoch: int,
        trusted: bool,
    ) -> None:
        gate = {
            "id": "G1",
            "description": "constitutional gate",
            "gate_severity": severity,
            "status": "WAIVED",
            "waiver_reason": "explicitly requested exception",
            "waiver_evidence": "E-1",
        }
        evidence = {
            "E-1": {
                "schema": 2,
                "id": "E-1",
                "task_id": "task-1",
                "change_epoch": epoch,
                "provenance": provenance,
                "details": {
                    "gate_ids": ["G1"],
                    "waiver_authority": {
                        "kind": "user",
                        "identity": "external-user",
                        "trusted": trusted,
                    },
                },
            }
        }
        expected = severity == "REQUIRED" and provenance == "external-source" and epoch == 1 and trusted
        self.assertEqual(
            validate_gate_waiver(
                gate,
                evidence,
                task_id="task-1",
                current_epoch=1,
            ),
            expected,
        )

    def store_at_plan(self, root: Path) -> tuple[StateStore, str]:
        (root / ".agents").mkdir()
        (root / ".agents" / "framework.toml").write_text("[framework]\nversion='4.0.0'\n", encoding="utf-8")
        store = StateStore(root)
        task = store.create("integrated assurance", mode="write", risk="low")
        store.transition("DISCOVER", "repository discovery")
        store.transition("PRECHECK", "artifact compilation")
        store.mutate(
            lambda value: value["precheck"].update(
                governance_snapshot={"digest": SHA_A},
                constitution={"digest": SHA_B},
                instruction_provenance={"digest": SHA_C},
                repository_discovery={"digest": SHA_D},
                workspace_snapshot=workspace_fingerprint(root),
                test_law_baseline={"digest": SHA_E},
                tdd_plan={"digest": SHA_F},
                compiled_policy={"digest": SHA_A},
                mandatory_gates={"digest": SHA_B},
                write_scope={"digest": SHA_C},
                budgets={"digest": SHA_D},
                command_matrix={"digest": SHA_E},
                review_requirements={"digest": SHA_F},
            )
        )
        store.transition("TRIAGE", "precheck verified")
        store.transition("PLAN", "bounded plan")
        return store, task["id"]

    def observed_cycle(self, task_id: str, *, cycle_id: str = "TDD-1") -> dict:
        designed = new_tdd_cycle(
            task_id=task_id,
            cycle_id=cycle_id,
            mode="RED_REQUIRED",
            designed_at_revision=5,
            test_contract_digest=SHA_A,
            oracle_digest=SHA_B,
        )
        return record_baseline(
            designed,
            outcome="RED",
            observed_implementation_digest=SHA_C,
            command=["python", "contract.py"],
            environment_digest=SHA_D,
            output_digest=SHA_E,
            semantic_reason="required behavior absent",
            harness_valid=True,
            baseline_intact=True,
        )

    def test_green_falsification_and_review_are_enforced_as_current_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store, task_id = self.store_at_plan(root)
            store.transition("TEST_DESIGN", "property designed")
            store.record_tdd_cycle(self.observed_cycle(task_id))
            store.transition("BASELINE", "legitimate RED captured")
            store.transition("IMPLEMENT", "implementation authorized")
            with self.assertRaises(TransitionError):
                store.transition("GREEN", "self-reported green")
            cycle = record_green(
                store.load()["tdd"]["cycles"][0],
                current_epoch=1,
                current_test_contract_digest=SHA_A,
                current_oracle_digest=SHA_B,
                current_implementation_digest=SHA_D,
                diff_digest=SHA_E,
                command=["python", "contract.py"],
                environment_digest=SHA_F,
                output_digest=SHA_C,
                passed=True,
            )
            store.record_tdd_cycle(cycle)
            store.transition("GREEN", "frozen contract green")
            with self.assertRaises(TransitionError):
                store.transition("ADVERSARIAL_REVIEW", "skip falsification")
            store.transition("FALSIFY", "search for counterexamples")
            falsification = build_falsification_receipt(
                task_id=task_id,
                tdd_cycle_digest=cycle["cycle_sha256"],
                epoch=1,
                diff_digest=SHA_E,
                methods=["Hypothesis state machine"],
                attempts=["stale epoch"],
                boundary_cases=["empty evidence ledger"],
                counterexamples=[],
                outcome="NO_COUNTEREXAMPLE",
            )
            store.record_falsification(falsification)
            store.transition("ADVERSARIAL_REVIEW", "current falsification complete")
            store.mutate(lambda task: task["child_history"].append({"role": "adversarial-reviewer", "lease_id": "lease-1", "outcome": "accepted", "summary": "independent review", "evidence": []}))
            receipt = build_review_receipt(
                task_id=task_id,
                reviewer_lease="lease-1",
                reviewer_role="adversarial-reviewer",
                reviewer_identity="reviewer",
                implementer_identity="implementer",
                epoch=1,
                diff_digest=SHA_E,
                requirements_digest=SHA_A,
                evidence_set_digest=EMPTY_EVIDENCE,
                tdd_cycle_digest=cycle["cycle_sha256"],
                test_law_baseline_digest=SHA_E,
                assumptions_tested=["scope closed"],
                counterexamples_attempted=["stale epoch"],
                boundary_cases=["empty evidence ledger"],
                potential_failures=["post-review mutation"],
                unexpected_scope=[],
                findings=[],
                outcome="ACCEPTED",
            )
            store.record_review(receipt)
            self.assertEqual(store.load()["review_receipt"]["receipt_sha256"], receipt["receipt_sha256"])
            store.mutate(lambda task: task.__setitem__("diff_digest", SHA_F))
            self.assertIsNone(store.load()["review_receipt"])

    @given(field=st.sampled_from(("test", "oracle")))
    def test_recorded_cycle_identity_cannot_be_replaced_after_baseline(self, field: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store, task_id = self.store_at_plan(Path(directory))
            store.transition("TEST_DESIGN", "property designed")
            store.record_tdd_cycle(self.observed_cycle(task_id))
            replacement = new_tdd_cycle(
                task_id=task_id,
                cycle_id="TDD-1",
                mode="RED_REQUIRED",
                designed_at_revision=5,
                test_contract_digest=SHA_F if field == "test" else SHA_A,
                oracle_digest=SHA_F if field == "oracle" else SHA_B,
            )
            with self.assertRaises((AssuranceError, RuntimeError)):
                store.record_tdd_cycle(replacement)

    @given(counterexamples=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=3))
    def test_falsification_cannot_claim_clean_when_counterexamples_exist(self, counterexamples: list[str]) -> None:
        with self.assertRaises(AssuranceError):
            build_falsification_receipt(
                task_id="task-1",
                tdd_cycle_digest=SHA_A,
                epoch=1,
                diff_digest=SHA_B,
                methods=["property"],
                attempts=["hostile input"],
                boundary_cases=["empty"],
                counterexamples=counterexamples,
                outcome="NO_COUNTEREXAMPLE",
            )


if __name__ == "__main__":
    unittest.main()
