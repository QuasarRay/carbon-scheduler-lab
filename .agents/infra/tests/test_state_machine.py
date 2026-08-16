import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentinfra.assurance import build_falsification_receipt, new_tdd_cycle, record_baseline, record_green
from agentinfra.evidence import _append_verified_observation, append_evidence, load_evidence, rollback_last_evidence
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


class TestState(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / ".agents").mkdir()
        (self.root / ".agents" / "framework.toml").write_text(
            "[framework]\nversion='4.0.0'\n", encoding="utf-8"
        )
        self.s = StateStore(self.root)

    def tearDown(self):
        self.td.cleanup()

    def _task_dir(self, task_id):
        return self.root / ".aegis" / "tasks" / task_id

    def _precheck(self):
        self.s.transition("DISCOVER", "repository discovery")
        self.s.transition("PRECHECK", "compile artifacts")
        artifacts = {
            "governance_snapshot": {"digest": SHA_A},
            "constitution": {"digest": SHA_B},
            "instruction_provenance": {"digest": SHA_C},
            "repository_discovery": {"digest": SHA_D},
            "workspace_snapshot": workspace_fingerprint(self.root),
            "test_law_baseline": {"digest": SHA_E},
            "tdd_plan": {"digest": SHA_F},
            "compiled_policy": {"digest": SHA_A},
            "mandatory_gates": {"digest": SHA_B},
            "write_scope": {"digest": SHA_C},
            "budgets": {"digest": SHA_D},
            "command_matrix": {"digest": SHA_E},
            "review_requirements": {"digest": SHA_F},
        }
        self.s.mutate(lambda task: task["precheck"].update(artifacts))
        return self.s.transition("TRIAGE", "precheck current")

    def _baseline_cycle(self, *, remediation=False):
        task = self.s.load()
        cycle = new_tdd_cycle(
            task_id=task["id"],
            cycle_id=f"TDD-{task['change_epoch'] + 1}",
            mode="RED_REQUIRED",
            designed_at_revision=task["revision"],
            test_contract_digest=SHA_A,
            oracle_digest=SHA_B,
            remediation=remediation,
            discovered_epoch=task["change_epoch"] if remediation else None,
        )
        cycle = record_baseline(
            cycle,
            outcome="RED",
            observed_implementation_digest=SHA_C,
            command=["python", "contract.py"],
            environment_digest=SHA_D,
            output_digest=SHA_E,
            semantic_reason="required behavior absent",
            harness_valid=True,
            baseline_intact=True,
        )
        self.s.record_tdd_cycle(cycle)

    def _implement(self):
        self._precheck()
        self.s.transition("PLAN", "bounded plan")
        self.s.transition("TEST_DESIGN", "test first")
        self._baseline_cycle()
        self.s.transition("BASELINE", "legitimate RED")
        return self.s.transition("IMPLEMENT", "implementation authorized")

    def _remediate(self):
        self.s.transition("TEST_DESIGN", "regression first")
        self._baseline_cycle(remediation=True)
        self.s.transition("BASELINE", "remediation RED")
        return self.s.transition("REMEDIATE", "remediation authorized")

    def _green(self, *, verify=False):
        task = self.s.load()
        cycle = next(item for item in task["tdd"]["cycles"] if item["cycle_id"] == task["tdd"]["active_cycle_id"])
        cycle = record_green(
            cycle,
            current_epoch=task["change_epoch"],
            current_test_contract_digest=SHA_A,
            current_oracle_digest=SHA_B,
            current_implementation_digest=SHA_D,
            diff_digest=SHA_E,
            command=["python", "contract.py"],
            environment_digest=SHA_F,
            output_digest=SHA_C,
            passed=True,
        )
        self.s.record_tdd_cycle(cycle)
        result = self.s.transition("GREEN", "frozen contract green")
        return self.s.transition("VERIFY", "verification") if verify else result

    def _review_current(self):
        self.s.transition("FALSIFY", "seek counterexamples")
        task = self.s.load()
        cycle = next(item for item in task["tdd"]["cycles"] if item["cycle_id"] == task["tdd"]["active_cycle_id"])
        receipt = build_falsification_receipt(
            task_id=task["id"],
            tdd_cycle_digest=cycle["cycle_sha256"],
            epoch=task["change_epoch"],
            diff_digest=task["diff_digest"],
            methods=["boundary analysis"],
            attempts=["stale epoch"],
            boundary_cases=["empty ledger"],
            counterexamples=[],
            outcome="NO_COUNTEREXAMPLE",
        )
        self.s.record_falsification(receipt)
        self.s.transition("ADVERSARIAL_REVIEW", "independent review")
        lease = f"review-{task['change_epoch']}"
        self.s.mutate(lambda value: value["child_history"].append({
            "role": "adversarial-reviewer",
            "lease_id": lease,
            "outcome": "accepted",
            "summary": "independent review complete",
            "evidence": [],
        }))
        task = self.s.load()
        review = build_review_receipt(
            task_id=task["id"],
            reviewer_lease=lease,
            reviewer_role="adversarial-reviewer",
            reviewer_identity="reviewer",
            implementer_identity="implementer",
            epoch=task["change_epoch"],
            diff_digest=task["diff_digest"],
            requirements_digest=SHA_A,
            evidence_set_digest=task["evidence_set_digest"],
            tdd_cycle_digest=cycle["cycle_sha256"],
            test_law_baseline_digest=SHA_E,
            assumptions_tested=["scope closed"],
            counterexamples_attempted=["stale epoch"],
            boundary_cases=["empty ledger"],
            potential_failures=["post-review mutation"],
            unexpected_scope=[],
            findings=[],
            outcome="ACCEPTED",
        )
        return self.s.record_review(review)

    def test_precheck_fails_closed(self):
        self.s.create("x", mode="write")
        self.s.transition("DISCOVER", "discover")
        self.s.transition("PRECHECK", "start")
        with self.assertRaises(TransitionError):
            self.s.transition("TRIAGE", "too soon")

    def test_valid_precheck(self):
        self.s.create("x", mode="write")
        self._precheck()
        self.assertEqual(self.s.load()["state"], "TRIAGE")

    def test_transition_history_is_atomic_state(self):
        task = self.s.create("x")
        self.s.transition("DISCOVER", "start")
        current = self.s.load()
        self.assertEqual(current["transitions"][-1]["to"], "DISCOVER")
        self.assertFalse((self._task_dir(task["id"]) / "transitions.jsonl").exists())

    def test_blocked_only_resumes_previous_state(self):
        self.s.create("x")
        self.s.transition("DISCOVER", "start")
        self.s.transition("BLOCKED", "external")
        with self.assertRaises(TransitionError):
            self.s.transition("IMPLEMENT", "skip")
        self.assertEqual(self.s.transition("DISCOVER", "resume")["state"], "DISCOVER")

    def test_implementation_invalidates_stale_proof(self):
        self.s.create("x")
        self._implement()

        def proven(task):
            task["verification_evidence"] = ["E-old"]
            task["verification_epoch"] = task["change_epoch"]
            task["gates"] = [
                {"id": "G1", "description": "proof gate", "status": "PROVEN", "evidence": ["E-old"]},
                {"id": "G2", "description": "waived gate", "status": "WAIVED", "evidence": [], "waiver_reason": "not applicable", "waiver_authority": "policy:test-policy"},
            ]
            task["final_audit_complete"] = True
            task["final_audit_workspace"] = {"available": False}

        self.s.mutate(proven)
        epoch = self.s.load()["change_epoch"]
        self.s.transition("DIAGNOSE", "issue")
        self._remediate()
        task = self.s.load()
        self.assertFalse(task["final_audit_complete"])
        self.assertNotIn("final_audit_workspace", task)
        self.assertEqual(task["verification_evidence"], [])
        self.assertIsNone(task["verification_epoch"])
        self.assertEqual(task["change_epoch"], epoch + 1)
        self.assertEqual(task["gates"][0]["status"], "OPEN")
        self.assertEqual(task["gates"][0]["evidence"], [])
        self.assertEqual(task["gates"][1]["status"], "WAIVED")

    def test_final_audit_requires_resolved_gates_and_critical_risks(self):
        self.s.create("x")
        self._implement()
        self._green(verify=True)
        task = self.s.load()
        record = _append_verified_observation(
            self._task_dir(task["id"]), "observation", "current verified observation",
            task_id=task["id"], change_epoch=task["change_epoch"], task_revision=task["revision"],
            workspace=workspace_fingerprint(self.root), gate_ids=["G1"],
        )

        def setup(value):
            value["verification_evidence"] = [record["id"]]
            value["verification_epoch"] = value["change_epoch"]
            value["evidence_head"] = record["record_sha256"]
            value["gates"] = [{"id": "G1", "description": "current proof", "status": "OPEN", "evidence": []}]
            value["risks"] = [{"id": "R1", "description": "critical risk", "severity": "critical", "status": "open"}]

        self.s.mutate(setup)
        self._review_current()
        with self.assertRaises(TransitionError):
            self.s.transition("FINAL_AUDIT", "too soon")
        self.s.mutate(lambda value: value["gates"][0].update(status="PROVEN", evidence=[record["id"]]))
        with self.assertRaises(TransitionError):
            self.s.transition("FINAL_AUDIT", "risk still open")
        self.s.mutate(lambda value: value["risks"][0].update(status="resolved", resolution="verified mitigation"))
        self.assertEqual(self.s.transition("FINAL_AUDIT", "ready")["state"], "FINAL_AUDIT")

    def test_finalize_rejects_evidence_from_prior_epoch_even_if_state_is_tampered(self):
        task = self.s.create("x")
        task_dir = self._task_dir(task["id"])
        old = append_evidence(task_dir, "test", "old proof", change_epoch=0)
        path = task_dir / "state.json"
        forged = json.loads(path.read_text())
        forged["state"] = "FINAL_AUDIT"
        forged["change_epoch"] = 1
        forged["verification_epoch"] = 1
        forged["verification_evidence"] = [old["id"]]
        forged["gates"] = [{"id": "G1", "description": "gate", "status": "PROVEN", "evidence": [old["id"]]}]
        forged["final_audit_complete"] = True
        path.write_text(json.dumps(forged))
        with self.assertRaisesRegex(RuntimeError, "state (?:schema|integrity)"):
            self.s.transition("FINALIZE", "must reject forged stale proof")

    def test_failed_state_save_rolls_back_its_evidence_append(self):
        task = self.s.create("x")
        task_dir = self._task_dir(task["id"])
        attached = {}

        def mutate_with_bad_state(state):
            record = append_evidence(task_dir, "test", "must roll back", task_revision=state["revision"], lock_held=True)
            attached["record"] = record
            state["evidence_head"] = record["record_sha256"]
            state["title"] = "illegal immutable rewrite"

        def rollback():
            record = attached.get("record")
            if record:
                rollback_last_evidence(task_dir, record["record_sha256"], lock_held=True)

        with self.assertRaisesRegex(RuntimeError, "immutable task field changed"):
            self.s.mutate(mutate_with_bad_state, hold_evidence_lock=True, on_failure=rollback)
        self.assertEqual(load_evidence(task_dir), [])
        current = self.s.load()
        self.assertEqual(current["revision"], 0)
        self.assertIsNone(current["evidence_head"])

    def test_unbound_direct_append_blocks_canonical_state_mutation(self):
        task = self.s.create("x")
        task_dir = self._task_dir(task["id"])
        append_evidence(task_dir, "test", "orphan")
        with self.assertRaisesRegex(RuntimeError, "evidence head is not the verified ledger head"):
            self.s.mutate(lambda state: state["precheck"].__setitem__("x", True))

    def test_critical_gate_cannot_be_waived_by_a_caller_supplied_policy_string(self):
        self.s.create("x")
        self.s.mutate(lambda state: state["gates"].append({
            "id": "G1", "description": "critical proof", "severity": "critical",
            "status": "OPEN", "evidence": [], "created_revision": state["revision"] + 1,
        }))

        def forge_waiver(state):
            state["gates"][0].update({
                "status": "WAIVED", "waiver_reason": "caller says so",
                "waiver_authority": "policy:caller-controlled",
            })

        with self.assertRaisesRegex(RuntimeError, "critical acceptance gates cannot be waived"):
            self.s.mutate(forge_waiver)

    def test_finalized_load_fails_closed_after_workspace_mutation(self):
        self.s.create("x", mode="write", risk="low")
        self._implement()
        self._green(verify=True)
        task = self.s.load()
        task_dir = self._task_dir(task["id"])
        record = _append_verified_observation(
            task_dir, "observation", "current proof",
            task_id=task["id"], change_epoch=task["change_epoch"], task_revision=task["revision"],
            workspace=workspace_fingerprint(self.root), gate_ids=["G1"],
        )

        def bind(state):
            state["evidence_head"] = record["record_sha256"]
            state["verification_evidence"] = [record["id"]]
            state["verification_epoch"] = state["change_epoch"]
            state["gates"] = [{
                "id": "G1", "description": "proof", "severity": "high", "status": "PROVEN",
                "evidence": [record["id"]], "created_revision": 0,
            }]

        self.s.mutate(bind)
        self._review_current()
        self.s.transition("FINAL_AUDIT", "ready")
        self.s.audit_complete()
        finalized = self.s.transition("FINALIZE", "done")
        self.assertEqual(finalized["state"], "FINALIZE")
        with self.assertRaisesRegex(RuntimeError, "terminal task state FINALIZE rejects evidence append"):
            append_evidence(task_dir, "observation", "must not append", task_id=task["id"], change_epoch=task["change_epoch"])
        self.assertEqual(self.s.load()["state"], "FINALIZE")
        (self.root / "post-finalize.txt").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "workspace no longer matches"):
            self.s.load()

    def test_state_and_current_anchor_rollback_is_rejected_by_anchor_history(self):
        task = self.s.create("rollback")
        state_path = self._task_dir(task["id"]) / "state.json"
        anchor_path = self.root / ".aegis" / "state" / "task-anchors" / f"{task['id']}.json"
        old_state = state_path.read_bytes()
        old_anchor = anchor_path.read_bytes()
        self.s.mutate(lambda state: state["precheck"].__setitem__("newer", True))
        state_path.write_bytes(old_state)
        anchor_path.write_bytes(old_anchor)
        with self.assertRaisesRegex(RuntimeError, "anchor history"):
            self.s.load(task["id"])

    def test_gate_and_risk_history_cannot_be_deleted_or_replaced(self):
        self.s.create("append-only claims")
        self.s.mutate(lambda state: (
            state["gates"].append({"id": "G1", "description": "real gate", "severity": "high", "status": "OPEN", "evidence": [], "created_revision": state["revision"] + 1}),
            state["risks"].append({"id": "R1", "description": "real risk", "severity": "high", "status": "open"}),
        ))
        with self.assertRaisesRegex(RuntimeError, "gate history cannot be deleted"):
            self.s.mutate(lambda state: state.__setitem__("gates", [{"id": "Gfake", "description": "replacement", "severity": "low", "status": "OPEN", "evidence": [], "created_revision": state["revision"] + 1}]))
        with self.assertRaisesRegex(RuntimeError, "risk history cannot be deleted"):
            self.s.mutate(lambda state: state.__setitem__("risks", []))

    def test_proven_gate_requires_nonempty_evidence(self):
        self.s.create("empty proof")
        with self.assertRaisesRegex(RuntimeError, "proven acceptance gate requires evidence"):
            self.s.mutate(lambda state: state["gates"].append({"id": "G1", "description": "fake", "severity": "low", "status": "PROVEN", "evidence": [], "created_revision": state["revision"] + 1}))

    @unittest.skipUnless(os.name == "nt", "Windows junction behavior")
    def test_runtime_junction_cannot_redirect_state_reads_outside_project(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside_directory:
            root = Path(td)
            outside = Path(outside_directory)
            (root / ".agents").mkdir()
            store = StateStore(root)
            task = store.create("junction")
            tasks = root / ".aegis" / "tasks"
            target = outside / "redirected-tasks"
            shutil.copytree(tasks, target)
            shutil.rmtree(tasks)
            result = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(tasks), str(target)],
                capture_output=True,
                text=True,
            )
            if result.returncode:
                self.skipTest("host cannot create a directory junction")
            try:
                with self.assertRaisesRegex(RuntimeError, "(?:escapes root|redirected control path)"):
                    StateStore(root).load(task["id"])
            finally:
                tasks.rmdir()
