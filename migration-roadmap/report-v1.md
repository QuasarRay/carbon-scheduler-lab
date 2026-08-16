# Investigation Report: Migration Roadmap v1

Status: read-only investigation; no roadmap or production/test code was changed

Repository branch: dev-rs-v2

Carbon/Bevy Defer source baseline: 73629285578622cadd6994f0504e923262017f1e

Roadmap reviewed: migration-roadmap/v1.md as committed in 7b2a0d6dd9db560b8e61a4282e6e36f9922df35f

Investigation date: 2026-08-16

## 1. Executive verdict

The submitted critique is materially correct. None of the 43 claims is false.

| Verdict | Count | Claim numbers |
|---|---:|---|
| Confirmed | 35 | 2–8, 10–11, 13–18, 21–29, 31–36, 38–39, 41–43 |
| Confirmed with qualification | 8 | 1, 9, 12, 19, 20, 30, 37, 40 |
| False | 0 | — |
| Not determinable from the repository | 0 | — |

“Confirmed with qualification” means the core correction is valid but one part of its wording is broader than the evidence:

- Claim 1: main wait-list membership is source-proven and exercised by deadlock/progress tests; the specifically named successful native main-send test usually matches an already-blocked receiver and is not, by itself, proof of main send-wait membership.
- Claim 9: v1 strongly implies per-manager/per-scope counters, but has not yet implemented them; “relocates” describes the prescribed design rather than a completed change.
- Claim 12: receive mutates and rolls back before returning, but the intermediate state is normally hidden by the GIL. The roadmap is wrong about implementation order even if a Rust preflight can ultimately prove observationally equivalent.
- Claim 19: v1 already mentions a separate workspace crate as an option, but Phase 2 never selects or wires that option.
- Claim 20: a mutex can be justified as an opt-in host extension; it is not a fact inferred from the Python 3.12 compatibility baseline.
- Claim 30: “C API” is an established CPython-extension label, but the actual external consumer language and header are C++.
- Claim 37: the parser bug is confirmed, but reading the uninitialized delta is C++ undefined behavior, not a stable legacy result that can sensibly be preserved.
- Claim 40: the unconditional reference acquisition before the duplicate check is confirmed; reachability of that duplicate branch through a supported public operation still needs a focused test.

The roadmap should not authorize implementation in its current form. Its principal structural problem is that it combines three different contracts:

1. descriptive legacy behavior;
2. desired Rust safety invariants; and
3. intentional, product-approved divergences from legacy defects.

Those contracts must be separated before Phase 1. The correct acceptance rule is **zero unclassified differential mismatches**, not zero mismatches of every kind.

## 2. Method and evidence limits

This investigation traced every claim against the pinned roadmap, C++ implementation, Python facade, Python tests, native tests, Rust manifests, and relevant official documentation. Important source paths are linked inline below.

No scheduler extension binary, Cargo executable, or CMake executable is present in this workspace, so this pass did not execute the runtime test suites. Claims about exact source order, field ownership, queue mutation, manifest resolution, and test construction are nevertheless directly decidable from the repository. Claims involving undefined behavior, dangling pointers, or leak manifestation are reported as source-confirmed defects whose exact crash/leak symptom must be characterized in an isolated subprocess and sanitizer build.

Verdict meanings:

- **Confirmed**: the claim follows directly from repository code/tests or from an authoritative toolchain/API rule.
- **Confirmed with qualification**: its requested roadmap correction is necessary, but a supporting example or strength-of-wording needs narrowing.
- **False**: contradicted by the reviewed baseline.

## 3. State model required by the baseline

Before the individual findings, the source establishes that Carbon’s public state cannot be faithfully represented by v1’s single mutually exclusive enum. At minimum the compatibility oracle must record orthogonal facts:

- callable bound;
- Greenlet initialized;
- alive;
- paused;
- scheduled flag;
- intrusive runnable links;
- current identity;
- channel direction and wait links;
- transfer-in-progress;
- reschedule/tagged-removal flags;
- owner manager/thread; and
- parent continuation.

Reachable configurations include:

| Configuration | Callable | Greenlet | Alive | Paused | Runnable-linked/scheduled | Channel wait |
|---|---:|---:|---:|---:|---:|---:|
| Fresh with no callable | No | No | No | No | No | No |
| Bound, not initialized | Yes | No | No | No | No | No |
| Bound with args, paused | Consumed into Greenlet | Yes | Yes | Yes | No | No |
| Ready | Consumed into Greenlet | Yes | Yes | Usually no | Yes | No |
| Executing baseline tasklet | Consumed into Greenlet | Yes | Yes | No | Yes until switch returns | No |
| Channel-blocked ordinary tasklet | Consumed into Greenlet | Yes | Yes | Varies by path | No | Yes |
| Main blocked on channel | Main continuation | Yes | Yes | Varies | Main sentinel plus channel membership | Yes |
| Trapped run of paused tasklet | Consumed into Greenlet | Yes | Yes | Yes | Yes | No |

Rust may later derive a cleaner target state machine, but the differential adapter needs a lossless legacy snapshot and an explicit mapping. It must not normalize away combinations that the baseline actually exposes.

## 4. Findings 1–10: tasklet state, queue execution, and run limits

### 1. Main can enter a channel wait queue

**Verdict: Confirmed with qualification.**

[Channel::Send](../src/Channel.cpp#L34-L145) adds the current tasklet to the sender FIFO at lines 70–75. [Channel::Receive](../src/Channel.cpp#L147-L237) increments the current tasklet and adds it to the receiver FIFO at lines 165–168. Neither path excludes main. [ScheduleManager::Yield](../src/ScheduleManager.cpp#L298-L375) explicitly detects a blocked main tasklet and runs other runnable tasklets until main is released or a deadlock is declared.

The native tests [test_main_tasklet_receive_deadlock_after_running_child_tasklets and test_main_tasklet_send_deadlock_after_running_child_tasklets](../tests/python/scheduler/tests/test_channel.py#L141-L181) prove that main blocks while other tasklets make progress in both directions. [QueueChannel.test_blocking_receive_on_main_tasklet](../tests/python/scheduler/tests/test_queuechannel.py#L196-L215) supplies a successful main receive in which the underlying channel has no waiting sender at entry and must yield to the ready sender.

Qualification: [test_blocking_send_on_main_tasklet](../tests/python/scheduler/tests/test_channel.py#L439-L462) starts by running the receiver until it is already waiting. Each main send therefore finds a counterpart; that test name alone does not prove that main joined the send FIFO. The source and the send-deadlock/progress test still prove that it can.

The invariant in [v1 §11.2](v1.md#112-invariants-for-property-tests) saying main is never in a channel wait queue is false. Replace it with a descriptive law: main may temporarily join exactly one channel FIFO; Yield must either rendezvous and remove it exactly once or roll it back on deadlock/error.

### 2. Running-without-queue-membership is not baseline-isomorphic

**Verdict: Confirmed.**

[ScheduleManager::Run](../src/ScheduleManager.cpp#L423-L628) selects baseTasklet->Next at line 464 and calls SwitchTo at line 527. It does not remove that tasklet from the intrusive chain until control returns, at lines 547–553. [Tasklet::SwitchTo](../src/Tasklet.cpp#L294-L453) sets current and switches the Greenlet while those links and the scheduled flag still exist.

Python running inside the tasklet can therefore observe itself as current while its next/previous links and scheduled flag still describe runnable membership. v1’s canonical Running row, which says “Not a waiting queue node,” and the proposal to derive scheduled solely from the enum are not faithful to the baseline.

Required correction: distinguish **logical execution state** from **legacy runnable linkage**. The parity model should allow ActiveLinked. A cleaner dequeue-before-run target is an approved divergence only if next/prev, scheduled, callback reentrancy, refcounts, and ordering are proven unchanged.

### 3. Bound-but-not-runnable is a missing lifecycle state

**Verdict: Confirmed.**

[Tasklet::Bind](../src/Tasklet.cpp#L1205-L1320) validates and stores the callable at lines 1214–1255. It initializes a Greenlet and marks alive only if args or kwargs were supplied, at lines 1298–1314. Construction through [TaskletInit](../src/PyTasklet.cpp#L42-L101) calls Bind with null args and kwargs.

The resulting object has a callable but no Greenlet, is not alive, and is not scheduled. It is neither v1’s Unbound (“No executable callable/arguments”) nor Ready. The transition “construct/bind/setup → Ready” is therefore false.

Required correction: add at least a BoundDormant state or retain separate binding, continuation, liveness, and membership axes in the compatibility layer.

### 4. Bind with arguments creates alive-but-paused, while Setup enqueues

**Verdict: Confirmed.**

Bind with args/kwargs calls Initialise and SetAlive but never inserts. [Tasklet::Initialise](../src/Tasklet.cpp#L170-L188) sets paused true. By contrast, [Tasklet::Setup](../src/Tasklet.cpp#L1069-L1118) initializes, marks alive, and then inserts the tasklet.

[test_switch_paused](../tests/python/scheduler/tests/test_scheduler.py#L494-L502), [test_run_paused](../tests/python/scheduler/tests/test_scheduler.py#L591-L601), and [test_bind_args_not_runnable](../tests/python/scheduler/tests/test_tasklet.py#L1031-L1041) exercise the distinction.

Required correction: Bind and Setup need separate transition rows and oracle events. A shared canonical transition loses public lifecycle behavior.

### 5. Paused plus scheduled is reachable

**Verdict: Confirmed.**

[Tasklet::Run](../src/Tasklet.cpp#L503-L559) directly asks the manager to insert an unscheduled tasklet at lines 525–532; it does not pass through Tasklet::Insert, which would clear paused. [Tasklet::SwitchTo](../src/Tasklet.cpp#L294-L453) checks switch_trap at lines 352–357 and returns before setting paused false. [ScheduleManager::Run](../src/ScheduleManager.cpp#L578-L600) returns from that failure path without removing the newly inserted tasklet unless RequiresRemoval is set.

[test_run_paused](../tests/python/scheduler/tests/test_scheduler.py#L591-L601) asserts that the tasklet remains paused after the trapped run, then proves scheduler.run later executes the queued tasklet. This is a reachable paused + scheduled combination.

Required correction: do not derive paused and scheduled from a mutually exclusive enum during parity. If the target removes this combination, classify and test that change as an approved divergence.

### 6. tasklet.switch is routed through ScheduleManager::Run

**Verdict: Confirmed.**

[Tasklet::SwitchImplementation](../src/Tasklet.cpp#L223-L292) calls ScheduleManager::Run(this) for an already scheduled tasklet, then yields through the parent. For a detached live tasklet it first inserts the target and then also calls Run(this). This is not an isolated direct PyGreenlet_Switch operation.

Required correction: replace v1’s statement that switch bypasses normal queue traversal with an exact algorithm: validate target; insert when detached; establish parent/boundary through Run(this); perform continuation switch; then follow the parent/yield behavior. Queue and callback traces must distinguish switch from ordinary unbounded run without pretending it bypasses the manager.

### 7. switch_trap does not increment the timeout switched counter

**Verdict: Confirmed.**

Tasklet::SwitchTo tests IsSwitchTrapped and returns at lines 352–357 before incrementing times_switched_to at line 382 or calling SetCurrentTasklet at line 385. [ScheduleManager::SetCurrentTasklet](../src/ScheduleManager.cpp#L141-L150) calls OnSwitch; [OnSwitch](../src/ScheduleManager.cpp#L630-L639) is the only increment of the timeout switched counter.

The comment at lines 635–636 claiming a trapped attempt increments the counter is stale. v1 copied that comment despite its own implementation-over-comments authority.

Required correction: define the metric from the executed ordering, add a trapped-timeout characterization, and call the counter actual current-tasklet transitions during a time-limited run unless further tests reveal another path.

### 8. The timeout “completed” counter counts dequeue cycles

**Verdict: Confirmed.**

In ScheduleManager::Run, cleanupCurrentTasklet becomes true when RemoveTasklet succeeds. The same still-alive tasklet may immediately be reinserted because RequiresReschedule is BACK or FRONT_PLUS_ONE. The time-limited counter is nevertheless incremented at lines 614–622.

The existing native test [PyScheduler_GetTaskletsCompletedLastRunWithTimeout](../tests/capiTest/Scheduler.cpp#L452-L474) uses only three one-shot lambdas. It proves the one-shot case, not the meaning for yielding tasklets.

Required correction: rename the internal semantic to successful runnable-removal/dequeue cycles until characterized. Add a time-limited tasklet that repeatedly calls schedule and verify the exact count before deciding whether the public getter may continue to be described as “completed tasklets.”

### 9. Timeout counters are global, not per manager

**Verdict: Confirmed with qualification.**

[ScheduleManager.h](../src/ScheduleManager.h#L137-L165) declares both timeout counters static inline. [RunTaskletsForTime](../src/ScheduleManager.cpp#L377-L403) resets the process-global values, and the getters at lines 720–727 return them without a manager argument.

v1 says each ManagerCore needs timeout counters and each RunScope contains deltas. That strongly prescribes per-manager state, although no code has yet “relocated” it. A per-manager publication would change which result is visible after another Python thread performs a later timed run.

Required correction: characterize two-thread last-writer visibility. Preserve global last-timed-run counters in the parity facade, even if a scope calculates local deltas internally, unless a compatibility break is approved.

### 10. A RunScope stack fixes rather than reproduces nested budget corruption

**Verdict: Confirmed.**

[RunTaskletsForTime and RunNTasklets](../src/ScheduleManager.cpp#L377-L421) overwrite ambient manager fields and unconditionally reset m_runType to STANDARD and limits to defaults after the nested call. An inner limited run can therefore erase an outer limited run’s mode and budget.

v1 explicitly proposes a scope stack so the inner call cannot corrupt the outer call. That is a sound target design, but not automatic parity.

Required correction: first add nested limited-run oracle cases. Then choose either legacy-compatible corruption in compatibility mode or an approved divergence with explicit expected trace differences and release notes.

## 5. Findings 11–17: channels, traps, and oracle quality

### 11. Python channel preference ignores ordinary out-of-range values

**Verdict: Confirmed.**

[ChannelPreferenceSet](../src/PyChannel.cpp#L96-L141) calls SetPreferenceFromInt only when the converted value is -1, 0, or 1. An ordinary in-range C long outside that set returns success and leaves the old preference unchanged. The native capsule function [PyChannel_SetPreference](../src/SchedulerModule.cpp#L681-L699) instead clamps below -1 and above 1.

Required correction: specify two entrypoint contracts. The Python property setter ignores ordinary out-of-range integers; the native C++ API clamps. Do not route both through one clamping Rust setter. Also characterize PyLong_AsLong overflow: it returns -1 with an exception, after which the current code can set preference to -1 and return success with an exception still pending.

### 12. Unmatched receive mutates before block_trap and then rolls back

**Verdict: Confirmed with qualification.**

Channel::Receive increments the current tasklet and adds it to the receive FIFO at lines 167–168. AddTaskletToWaitingToReceive updates direction and balance. Only afterward does Receive check block_trap at lines 169–180, remove the node, reset transfer state, and release the acquired tasklet reference.

The final balance tested by [test_attempting_receive_on_block_trapped_tasklet_does_not_change_balance](../tests/python/scheduler/tests/test_channel.py#L874-L883) is unchanged. Under the normal GIL-held path, no Python code runs between insertion and rollback, so a target preflight may prove observationally equivalent. But “preflight before mutation” is not a descriptive baseline law.

Required correction: record two separate statements: **legacy sequence is mutate then rollback**; **target invariant may preflight** if callback order, refcount lifetime, trace observation, and all public state remain equivalent.

### 13. send sets transfer-in-progress before trap and closed validation

**Verdict: Confirmed.**

Channel::Send invokes the channel callback and then sets current->SetTransferInProgress(true) at lines 40–42. The no-receiver branch checks current, block_trap, and closed/closing only afterward. The early returns at lines 47–68 do not restore the flag.

This is potentially observable beyond an internal boolean: [Tasklet::SwitchTo](../src/Tasklet.cpp#L426-L432) refuses to mark a non-main tasklet dead while transfer-in-progress is true. A tasklet that catches the send error and later returns can therefore follow a different liveness path.

Required correction: add trapped-send and closed-send scenarios in which the tasklet catches the exception, returns, and has alive/scheduled/paused/refcount state inspected. Treat validate-then-mutate as a defect fix or approved divergence if it changes those results.

### 14. switch_trap is not globally pre-mutation

**Verdict: Confirmed.**

The paused-run path inserts before SwitchTo reaches the trap check, as established by finding 5. Channel match paths can pop and unblock a counterpart, attach a transfer packet, and insert the counterpart into its owner queue before preference scheduling eventually attempts a trapped switch.

Required correction: remove the general law that switch_trap prevents all prior queue/channel mutation. Specify trap points operation by operation, and separately state any transactional target behavior as a proposed divergence.

### 15. The Phase 1 property suite mixes false baseline invariants with target invariants

**Verdict: Confirmed.**

Phase 1 requires no legacy invariant failures except documented defects, while v1 §11.2 includes:

- main never in a channel wait queue, contradicted by finding 1;
- exclusive canonical state/membership assumptions, contradicted by findings 2–5; and
- restoration of outer run mode/budget on every exit, contradicted by finding 10.

Required correction: create two named suites.

| Suite | Purpose | May fail on legacy? |
|---|---|---|
| Legacy descriptive properties | Learn and freeze reachable behavior and externally visible ordering | No, except a separately enumerated unstable/undefined case |
| Target safety invariants | Prove the Rust design’s chosen guarantees | Yes, where an approved divergence says legacy is defective |

Each divergence needs a mapping from one expected legacy trace to one expected target trace. The differential harness must never “normalize” the difference away.

### 16. Existing tests cannot be authority number one until audited

**Verdict: Confirmed.**

[test_tasklet.py](../tests/python/scheduler/tests/test_tasklet.py#L306-L389) contains:

- self.assertRaises(RuntimeError, t.switch())
- self.assertRaises(RuntimeError, t.kill())
- self.assertRaises(RuntimeError, t.bind())

Python evaluates each method call before assertRaises is entered. The exception therefore escapes the worker target. Python’s documented assertRaises callable form requires passing the callable itself, while an unhandled Thread.run exception is sent to threading.excepthook and join only waits for termination. The later assertions in each worker are skipped, and ordinary unittest does not turn the worker exception into the intended assertion result.

The setup test at lines 391–419 correctly passes t.setup and demonstrates the intended form.

Required correction: audit every Python test for assertion construction, worker exception capture, skipped post-exception assertions, order dependence, and cleanup. Keep the old tests unchanged as historical inputs, but do not mark a contract row trusted until a reliable parallel characterization reproduces its intended assertion.

Official references: [unittest.assertRaises](https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertRaises) and [threading.Thread exception/join behavior](https://docs.python.org/3/library/threading.html#thread-objects).

### 17. Native tests contain reference-ownership errors

**Verdict: Confirmed.**

In [tests/capiTest/Tasklet.cpp](../tests/capiTest/Tasklet.cpp#L12-L37), PyObject_GetAttrString returns a new reference to fooCallable. PyTuple_SetItem steals that reference. Cleanup later decrements both taskletArgs and fooCallable. The same pattern recurs in later tasklet tests. CPython documents PyObject_GetAttrString as returning a new reference and PyTuple_SetItem as stealing one.

The callback tests add another inconsistency. [PyScheduler_SetChannelCallback](../tests/capiTest/Scheduler.cpp#L177-L253) passes a new reference to the native setter, later decrements it, and does not first clear the global slot. The implementation stores that pointer without incrementing it and later decrements the old slot on replacement.

Required correction: perform a line-by-line native-test ownership audit before freezing the suite as an ownership oracle. Run the corrected parallel probes under debug CPython and ASan/LSan. “All current tests pass” remains useful behavioral evidence, but it is not proof of sound reference conventions.

Official references: [PyObject_GetAttrString](https://docs.python.org/3/c-api/object.html#c.PyObject_GetAttrString) and [PyTuple_SetItem](https://docs.python.org/3/c-api/tuple.html#c.PyTuple_SetItem).

## 6. Findings 18–22: Cargo, Bevy boundaries, synchronization, and thread affinity

### 18. Workspace membership does not select a local dependency source

**Verdict: Confirmed.**

[bevy_defer/Cargo.toml](../bevy_defer/Cargo.toml#L1-L59) declares async-executor = "1.10.0", which is a registry dependency. Merely adding bevy_defer/async-executor to workspace.members changes package grouping, command selection, the lockfile, and target sharing; it does not rewrite that dependency declaration to a local source.

Cargo’s official documentation separately defines [workspace members](https://doc.rust-lang.org/cargo/reference/workspaces.html), [path dependencies](https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html), and [patch overrides](https://doc.rust-lang.org/cargo/reference/overriding-dependencies.html).

Required correction: Phase 0 must require either:

- async-executor = { path = "./async-executor", version = "1.14.0" } or the exact compatible local version; or
- a root [patch.crates-io] override whose version participates in resolution.

Then verify cargo metadata resolve.nodes and packages show the local manifest path and no registry instance is selected for Bevy Defer. Workspace membership can be added for workspace operations, but is not a substitute.

### 19. A Bevy-free module is not a Bevy-free dependency graph

**Verdict: Confirmed with qualification.**

The root Bevy Defer manifest has an unconditional Bevy dependency with bevy_state, bevy_log, and bevy_asset enabled. [bevy_defer/src/lib.rs](../bevy_defer/src/lib.rs#L1-L85) imports Bevy types unconditionally. A carbon_core module that happens not to import bevy::World would still live in a crate whose dependency graph contains Bevy.

v1’s recommended layout already says “bevy_defer::carbon_core, or a workspace crate,” so it recognizes one valid option. Phase 2 does not choose it or explain how the root manifest becomes Bevy-optional.

Required correction: choose one enforceable architecture:

1. preferred: a separate workspace crate with no Bevy dependency, consumed by the root crate only through an optional adapter; or
2. a material root-crate feature refactor in which the Bevy dependency is optional and every Bevy-using module/export is gated.

The gate must inspect cargo metadata/cargo tree for the core package. An import lint alone is insufficient.

### 20. The channel mutex is a target extension, not a baseline necessity

**Verdict: Confirmed with qualification.**

The current Python methods execute under CPython’s GIL. Native capsule wrappers acquire it through [GILRAII](../src/GILRAII.cpp#L1-L11). [Channel.h](../src/Channel.h) and Channel.cpp contain no independent channel mutex. v1 explicitly excludes free-threaded Python from the compatibility promise.

A mutex may be necessary if a future Bevy host mutates channel state outside the GIL or if free-threaded Python becomes a goal. It introduces new lock ordering, callback reentrancy, destruction, and deadlock behavior and therefore cannot be presented as inferred legacy semantics.

Required correction: define a compatibility mode in which all canonical channel mutation remains GIL-serialized. If an opt-in host path needs a lock, state the new concurrency contract, lock order, reentrancy rules, and proof that standalone Python traces are unchanged. No lock may cross Python code, a callback, decref that can finalize user objects, or a Greenlet switch.

### 21. Cross-thread command commitment is underspecified

**Verdict: Confirmed.**

On rendezvous, Channel::Send and Channel::Receive synchronously call the released tasklet owner’s InsertTasklet or InsertTaskletToRunNext before returning from the operation. The owner manager’s queue, scheduled flag, links, and run count are therefore logically changed while the matching caller still holds the GIL.

If Rust only enqueues a command that a later owner-host pump consumes, an intervening getruncount, next/prev read, callback, close/kill, or second rendezvous can see a different state and order.

Required correction: define a linearization point. The safest parity design is:

1. synchronously commit the owner-manager scheduling mutation under the same GIL-held operation;
2. use a command/wake only to notify the owner thread that already-committed work exists; and
3. perform Greenlet switching only on that owner thread.

If mutation itself is deferred, every observable manager read must specify whether and how it incorporates pending commands, and differential tests must cover the interval between enqueue and pump.

### 22. A Bevy pump may execute only on the exact Greenlet owner thread

**Verdict: Confirmed.**

[Tasklet::BelongsToCurrentThread](../src/Tasklet.cpp#L1384-L1393) ties tasklet operations to its ScheduleManager. v1 Phase 4 correctly says Greenlet calls stay on the owning Python thread, but Phase 10 merely says a Bevy schedule can pump a selected manager or command queue.

Greenlet’s own documentation is stronger: [greenlets belonging to different threads cannot be mixed or switched](https://greenlet.readthedocs.io/en/stable/python_threads.html). A Bevy schedule thread, including an exclusive/main Bevy thread, is not automatically the Python owner of every Carbon manager.

Required correction: a pump may resume a manager only when the current Python thread-state/manager identity exactly equals that manager’s recorded owner. Any other Bevy worker may enqueue and wake only. Add wrong-thread pump rejection tests and owner-thread handoff tests; do not permit “selected manager” to bypass affinity.

## 7. Findings 23–29: callback order and phase dependencies

### 23. A schedule callback sees the previous tasklet as current

**Verdict: Confirmed.**

[ScheduleManager::SetCurrentTasklet](../src/ScheduleManager.cpp#L141-L150) performs:

1. OnSwitch;
2. RunSchedulerCallback(previous, next); and only then
3. m_currentTasklet = next.

A reentrant Python or fast callback that calls scheduler.getcurrent therefore sees previous, not next.

Required correction: make “current transition” a multi-point protocol, not one generic event. The trace must capture callback entry while current == previous and the later commit to next. A Rust implementation that commits current before invoking the callback is incompatible even if the callback argument pair is correct.

### 24. times_switched_to is incremented before the callback

**Verdict: Confirmed.**

Tasklet::SwitchTo increments the target’s m_timesSwitchedTo at line 382, then calls SetCurrentTasklet at line 385. During the callback, the target already reports the incremented count while scheduler.getcurrent still returns previous.

Required correction: Phase 1 needs a callback that inspects both next.times_switched_to and scheduler.getcurrent. The required ordering is:

1. target times_switched_to increment;
2. timeout switch accounting;
3. Python schedule callback;
4. fast native callback;
5. current pointer assignment; and
6. Greenlet switch.

The callback-exception cases must record which later points still occur.

### 25. Python and native callback setters do not share one ownership contract

**Verdict: Confirmed.**

The Python setters [SetChannelCallback](../src/SchedulerModule.cpp#L26-L66) and [SchedulerSetScheduleCallback](../src/SchedulerModule.cpp#L250-L291) increment a callable before passing it to storage. The native setters at lines 894–904 and 921–933 pass the incoming pointer without incrementing it. Storage in [Channel::SetChannelCallback](../src/Channel.cpp#L497-L507) and [ScheduleManager::SetSchedulerCallback](../src/ScheduleManager.cpp#L651-L657) decrements the old slot and stores the new pointer.

In effect, storage expects an owned/transferred reference. Python entrypoints prepare one; native entrypoints do not. The native tests then treat their local reference as still owned by the caller, making the current contract internally inconsistent.

Required correction: the ownership ledger must have separate Python-setter and native-setter rows. Characterize existing consumers, then explicitly choose borrowed-plus-INCREF or transferred-reference semantics for the capsule function. Preserve the public result only after the old/native ownership expectation is frozen.

### 26. Python callback setters can return a decref’d previous pointer

**Verdict: Confirmed.**

Both Python setters save a raw previousCallback pointer, replace the slot, and then return the saved pointer. Replacement decrements the old slot. There is no compensating increment before replacement or return. If the slot held the last strong reference, the returned object pointer may already be freed.

Required correction: add an explicit defect-decision row and a subprocess test:

1. install a callback;
2. delete every external strong reference and collect;
3. replace or clear the callback;
4. inspect the returned object and weakref/finalizer outcome under debug CPython and ASan.

Because returning a dangling PyObject is memory-unsafe, the recommended decision is fix identically in legacy and Rust before relying on setter-return parity.

### 27. Callback exceptions leave a pending exception and do not suppress the fast callback

**Verdict: Confirmed.**

[RunSchedulerCallback](../src/ScheduleManager.cpp#L659-L698) ignores the return from PyObject_Call, decrements the args tuple, and then attempts the fast callback regardless. It does not clear or immediately propagate the Python exception. [RunChannelCallback](../src/Channel.cpp#L411-L433) likewise ignores PyObject_Call’s result.

Required correction: callback failure is part of every scheduler/channel transition from Phase 1 onward, not a late Phase 8 detail. Record:

- Python callback entered/returned or raised;
- whether a Python exception is pending;
- fast callback invocation and result;
- whether current was committed;
- whether Greenlet switching was attempted;
- final queue/channel state; and
- public return/exception.

### 28. channel callback will_block means “no counterpart at callback entry”

**Verdict: Confirmed.**

Channel::Send computes willBlock from m_lastBlockedOnReceive == nullptr and invokes the callback before checking block_trap or closed state. Receive does the symmetric calculation from the sender queue. The callback can itself reenter and change queues before the original operation resumes.

The callback therefore runs for operations that later fail, and its will_block value is a pre-validation, pre-reentrancy snapshot—not a prediction that the operation ultimately blocks.

Required correction: name the trace field counterpart_absent_at_callback_entry or document the historical will_block meaning exactly. Preserve callback-before-validation order unless a separately approved divergence changes it.

### 29. Phases 5/6 need an explicit legacy callback and metric bridge

**Verdict: Confirmed.**

Phase 5 moves scheduler/tasklet decisions to Rust and requires all Python/native tests plus callback traces, counters, and lifetimes to match. Phase 6 does the same for channels. Phase 8 is where v1 says callback storage and timeout metrics move. The roadmap does not specify who invokes the still-legacy slots, at which exact points, or who publishes the counters during the mixed state.

Required correction: add a phase dependency contract:

| Moving decision family | Temporary bridge required until Phase 8 |
|---|---|
| Rust scheduler/current transition | Call legacy Python and fast schedule callback storage with findings 23–27 ordering |
| Rust timed run | Publish to legacy static global counters with findings 7–10 semantics |
| Rust channel attempt | Call legacy global channel callback with finding 28 timing |
| Rust tasklet count/lifecycle | Continue updating legacy global counts until ownership moves |

The bridge itself belongs in differential tests. Phase 8 should change storage ownership, not silently introduce callback/counter behavior that Phase 5 already promised.

## 8. Findings 30–34: native API and ABI proof

### 30. The public capsule header is C++-only

**Verdict: Confirmed with qualification.**

[include/Scheduler.h](../include/Scheduler.h#L22-L159) includes type_traits, uses using aliases, std::add_pointer_t, and reinterpret_cast. The repository’s consumers are .cpp GoogleTest files. A C compiler cannot consume this header as written.

“C API” remains a conventional name for a CPython capsule interface, so the label does not need to be globally renamed. The specific Phase 9 and definition-of-done language must say **native C++ consumer**. A real C consumer is a new feature requiring an extern "C" compatible shim and separate ABI.

### 31. PyCapsule byte layout is not a meaningful compatibility target

**Verdict: Confirmed.**

CPython defines [PyCapsule as an opaque value carrying a void pointer](https://docs.python.org/3/c-api/capsule.html). The implementation creates one with pointer &api and name scheduler._C_API at [SchedulerModule.cpp lines 1340–1343](../src/SchedulerModule.cpp#L1340-L1343).

Required compatibility facts are:

- import name scheduler._C_API;
- successful PyCapsule_Import;
- the stored pointer value points to the intended SchedulerCAPI table;
- SchedulerCAPI total size and every field offset;
- function signatures, calling conventions, and semantic ownership;
- type/exception pointer representation and identity; and
- capsule lifetime/destructor behavior.

Remove “capsule byte layout.” Byte-comparing an opaque PyObject is non-portable and can vary across CPython builds.

### 32. Recompiling a new consumer does not prove old binary compatibility

**Verdict: Confirmed.**

An external project freshly compiled against the new header proves source compatibility and agreement between that header and the new implementation. It does not prove that a binary produced earlier against the baseline table continues to work.

Required correction: preserve at least one precompiled legacy probe/object/library per supported ABI/toolchain, especially MSVC Windows, and load it against the replacement. Where artifact retention is impractical, freeze baseline sizeof/offsetof/alignment/calling-convention constants and exported-symbol records independently of the new header; this is weaker than a precompiled probe and should be labeled accordingly.

### 33. Assertions derived from the current header can be tautological

**Verdict: Confirmed.**

If both the “expected” offsets and implementation are compiled from an accidentally changed Scheduler.h, they can agree while breaking old clients.

Required correction: generate and commit a baseline ABI manifest keyed by commit, platform, architecture, compiler ABI, Python ABI, sizeof, alignof, every offsetof, field type spelling, and calling convention. Phase 9 tests must compare the current build to those frozen values, not regenerate expectations from the file under test.

### 34. TaskletExit is a pointer-to-pointer field

**Verdict: Confirmed.**

[SchedulerCAPI](../include/Scheduler.h#L124-L133) declares PyObject** TaskletExit. Module initialization assigns &TaskletExit at [SchedulerModule.cpp line 1295](../src/SchedulerModule.cpp#L1288-L1297).

Required correction: freeze the field’s PyObject ** representation and offset. The runtime test must separately assert:

1. api->TaskletExit is non-null;
2. *api->TaskletExit is non-null; and
3. *api->TaskletExit is identical to scheduler.TaskletExit.

“Stable TaskletExit pointer” is too ambiguous to cover both levels.

## 9. Findings 35–42: lifetime, GC, explicit defects, and instrumentation

### 35. The ownership ledger omits the thread-state dictionary’s manager edge

**Verdict: Confirmed.**

[ScheduleManager::GetThreadScheduleManager](../src/ScheduleManager.cpp#L84-L139) looks up SCHEDULE_MANAGER in PyThreadState_GetDict. On creation, PyDict_SetItem makes the thread-state dictionary an owner of the Python manager wrapper, after which the creation reference is released. Manager destruction registers a temporary raw pointer in s_closingScheduleManagers so recursive cleanup lookup does not create a replacement.

Required correction: add these ledger rows:

| Owner | Edge | Acquire | Release/exception path |
|---|---|---|---|
| Python thread-state dictionary | manager wrapper under SCHEDULE_MANAGER | successful PyDict_SetItem | thread-state dictionary clear/destruction |
| Manager wrapper | native/Rust ManagerCore handle | wrapper init | tp_clear/tp_dealloc |
| Closing-manager registry | non-owning manager pointer keyed by thread ID | manager destructor entry | destructor exit, including failure containment |
| Manager | main tasklet wrapper/implementation | CreateSchedulerTasklet | manager destruction |

Also audit the PyDict_SetItem failure path, which currently releases the manager and then appears to release it again.

### 36. Rust-owned Python references require an explicit GC traversal/clear protocol

**Verdict: Confirmed.**

[TaskletType](../src/PyTasklet.cpp#L1251-L1290) is GC-tracked. [TaskletTraverse](../src/PyTasklet.cpp#L1099-L1130) currently visits callable, bind args, and context-manager callable only. [TaskletClear](../src/PyTasklet.cpp#L1132-L1145) calls Tasklet::Clear, which clears callable, args, and kwargs. Other current Tasklet fields include Greenlet, transfer values, exception state/arguments, handler, parent, and manager relationships with varying strong/weak status.

If any strong PyObject edge moves behind a Rust handle, CPython cannot discover it unless tp_traverse calls through FFI and visits it. CPython’s [GC protocol](https://docs.python.org/3/c-api/gcsupport.html) requires traversal to visit every directly contained object without side effects and tp_clear to drop cycle-forming references while leaving the wrapper valid.

Required correction: define two panic-contained FFI operations:

- carbon_tasklet_traverse(handle, visitproc, arg): under the GIL, enumerate each currently strong Python edge exactly once; do not incref/decref, allocate Python objects, invoke user code, or mutate state.
- carbon_tasklet_clear(handle): under the GIL, atomically detach and release every cycle-forming Rust-owned Python edge, make repeated calls idempotent, and leave deallocation-safe tombstone state.

Equivalent protocols are needed for any other GC-tracked wrapper that gains Rust-owned edges. Add cycles through callable, args, kwargs, handler, context getter, transfer packet, exception, Greenlet frames, and parent.

### 37. switch_trap argument parsing continues with an uninitialized delta

**Verdict: Confirmed with qualification.**

[SchedulerSwitchTrap](../src/SchedulerModule.cpp#L344-L362) declares int delta without initialization. If PyArg_ParseTuple fails, it sets another error but does not return; it then reads delta and writes originalSwitchTrap + delta before returning a PyLong while an exception may remain pending.

Qualification: the uninitialized read is C++ undefined behavior. There is no deterministic numeric “legacy result” to preserve across compilers/builds.

Required correction: name this defect explicitly and run malformed-argument probes only in isolated subprocesses with UBSan/debug builds. Recommended disposition: fix the parser return path identically in legacy and Rust before migration, with the intended exception and no trap-level mutation.

### 38. Tasklet::SetParent leaks references on failure and has an ambiguous main-parent edge

**Verdict: Confirmed.**

[Tasklet::SetParent](../src/Tasklet.cpp#L921-L961) increments a non-null proposed parent before PyGreenlet_SetParent and returns false without balancing that increment if the call fails. For a null logical parent, it increments main before setting the Greenlet parent; failure also returns without release. On success it stores m_taskletParent = parent, which remains null for the main-parent path, so the extra main increment has no corresponding stored edge visible in this function.

Required correction: add explicit parent ownership cases for ordinary parent success/failure, replacement, reset-to-main success/failure, tasklet death, and manager teardown. Determine whether the main increment is deliberate permanent retention or a leak; do not infer it from the null Tasklet pointer convention.

### 39. Closed unmatched receive omits the tasklet decref used by trap rollback

**Verdict: Confirmed.**

In Channel::Receive, the unmatched path increments current and inserts it into the wait FIFO. The block_trap rollback removes the node and decrements current. The immediately following closed/closing rollback removes the node and resets transfer state but returns without the corresponding current->Decref. [RemoveTaskletFromBlocked](../src/Channel.cpp#L355-L409) only unlinks and updates balance/direction; it does not release a tasklet reference.

Required correction: add a direct closed-receive refcount/weakref/finalizer test under debug CPython. Record this branch separately in the defect ledger; generic “suspicious reference-count branches” is not sufficient.

### 40. InsertTaskletToRunNext increments before checking duplicate scheduling

**Verdict: Confirmed with qualification.**

[InsertTaskletToRunNext](../src/ScheduleManager.cpp#L158-L188) calls tasklet->Incref first. If IsScheduled is true, it sets a BACK reschedule request and returns without releasing the newly acquired reference.

Qualification: current ordinary call sites generally remove or unblock the tasklet before this operation. The source defect is definite, but this audit did not prove a supported public sequence that reaches the already-scheduled branch. Callback reentrancy and exceptional queue states make reachability worth testing.

Required correction: add a focused call-site/reentrancy characterization and an internal assertion test. If reachable, freeze the observed refcount effect for the decision log; if unreachable, remove or hard-fail the branch during a separately tested legacy cleanup and keep the target API duplicate-safe.

### 41. Greenlet module import retention is absent from the ownership inventory

**Verdict: Confirmed.**

[module initialization](../src/SchedulerModule.cpp#L1272-L1286) obtains a new reference from PyImport_ImportModule("greenlet"), marks it “TODO cleanup,” and never decrements or stores that reference in module state. It is also absent from error cleanup after later initialization steps.

Required correction: add module -> imported greenlet module/C API state to the baseline ledger and test repeated import, subinterpreter probe, module teardown, and interpreter finalization. Decide whether the module reference is intentionally retained for process lifetime or should be balanced in both implementations.

### 42. Trace instrumentation needs a strict non-observer-effect invariant

**Verdict: Confirmed.**

The roadmap says the adapter must not alter decisions, but refcount/GC-sensitive Carbon behavior requires a stronger construction rule. A trace system can accidentally retain wrappers, delay finalizers, invoke repr/equality/hash/property code, allocate at a GC-sensitive point, change timeout outcomes through overhead, or alter thread ordering through locks/I/O.

Required trace invariants:

- IDs are numeric sidecar values or non-owning pointer/generation mappings; no persistent Python strong references.
- Snapshots read native/Rust primitive fields only; no repr, str, equality, hashing, descriptors, weakref callbacks, or arbitrary Python calls.
- An event never holds a PyObject beyond the lifetime already guaranteed at that trace point.
- The hot path uses a preallocated/nonblocking sink; file I/O and Python serialization occur after the scenario.
- Sequence numbers, not wall-clock calls, define event order. Timed-run scenarios compare traced and untraced outcomes and account for instrumentation overhead.
- Trace disablement produces identical return values, exceptions, queue/channel state, refcounts, weakref/finalizer order, and deterministic callback order.
- Trace traversal cannot acquire locks in an order different from the runtime or run during partially destroyed state without a tombstone-safe path.

Add a metamorphic test that runs each refcount/GC and timeout scenario with tracing disabled and enabled, comparing all non-trace observations.

## 10. Finding 43: parity versus approved divergence

### 43. v1’s equivalence gates conflict with intentional fixes

**Verdict: Confirmed.**

v1 correctly recognizes apparent defects and supplies a decision list, but it still repeatedly promises behaviorally indistinguishable traces and “zero unexplained differential mismatches” while prescribing changes that deliberately differ:

- scoped run-budget restoration instead of ambient nested corruption;
- transactional channel preflight instead of mutate/rollback and stale transfer state;
- independent synchronization/command routing not present in the GIL baseline; and
- bounded teardown instead of the potentially unbounded loop documented in [ClearThreadTasklets](../src/ScheduleManager.cpp#L744-L766).

Required correction: make every contract row one of these categories:

| Category | Oracle | Acceptance rule |
|---|---|---|
| Baseline parity | Reproducible, defined legacy behavior | Exact match |
| Baseline defect, decision pending | Legacy trace plus safety/ownership evidence | No implementation until disposition approved |
| Approved divergence | One expected legacy trace and one expected target trace | Exact match to the side under test; mismatch is named, not normalized |
| Undefined/unstable legacy behavior | Sanitizer/source evidence, not a portable output oracle | Replace with an approved defined result |
| Opt-in host extension | Standalone parity trace plus extension-specific contract | No effect when disabled; extension invariants when enabled |
| Unsupported boundary | Explicit rejection/error contract | No accidental partial behavior |

The global switchover gate should be **zero unexplained or unclassified mismatches**. Approved divergences remain visible in reports and release documentation.

## 11. Minimum roadmap revisions required before implementation

The following are documentation/design prerequisites. They do not authorize source changes.

| Priority | Required roadmap revision | Claims addressed | Exit evidence |
|---|---|---|---|
| P0 | Split legacy descriptive properties, target safety invariants, and approved divergences | 2–5, 10, 12–15, 43 | Three separately named suites and a mismatch-classification schema |
| P0 | Replace the single parity state enum with a lossless legacy state vector plus an explicit target mapping | 1–5, 15 | Every reachable baseline snapshot maps without normalization |
| P0 | Correct switch/run algorithms and trap points | 5–7, 14 | Direct traces for ready, detached, paused, trapped, blocked, current, and cross-thread targets |
| P0 | Define timeout metrics at their actual scope and increment points | 7–10 | Yielding, trapped, nested, and two-thread metric traces |
| P0 | Audit tests before promoting them to trusted oracles | 16–17 | Per-test trusted/suspect/broken classification and corrected parallel probes |
| P0 | Correct Cargo source selection and choose a genuinely Bevy-free crate boundary | 18–19 | cargo metadata/tree output showing local async-executor and no Bevy in core |
| P0 | Specify exact callback transition order and mixed-phase bridges | 23–29 | Reentrant/raising callback traces in legacy, shadow, and Rust-decision modes |
| P0 | Replace capsule-byte checks with frozen native C++ ABI evidence | 30–34 | Baseline ABI manifest plus precompiled legacy probe where supported |
| P0 | Expand ownership/GC and defect ledgers to named edges/branches | 25–26, 35–41 | Debug-CPython/sanitizer results for every listed edge |
| P0 | Define cross-thread scheduling linearization and Greenlet owner-thread rule | 20–22 | Barrier-controlled visibility and wrong-thread rejection traces |
| P1 | Strengthen trace non-observer-effect requirements | 42 | Tracing-on/off metamorphic equivalence |
| P1 | Reconcile all phase gates with the divergence taxonomy | 29, 43 | No phase requires parity for a feature it has not yet bridged or migrated |

### 11.1 Recommended baseline/target representation

For Phase 1 and shadow mode, use a descriptive snapshot such as:

- tasklet ID and manager ID;
- is_main and is_current;
- callable_bound and continuation_present;
- alive, paused, scheduled, blocked, transfer_in_progress;
- runnable previous/next IDs;
- channel ID, direction, blocked previous/next IDs;
- parent ID;
- reschedule/tagged-removal/pending-control values;
- times_switched_to; and
- Python ownership-edge counters used only by debug probes.

The target may then map those snapshots to clean internal states, but mapping must be explicit:

- exact parity mapping;
- temporary compatibility state;
- approved divergence; or
- invalid only in the target suite.

### 11.2 Required callback transition protocol

At minimum, the versioned trace schema needs separate events for:

1. target selected;
2. target times_switched_to incremented;
3. timeout switched counter incremented, if applicable;
4. Python schedule callback enter/exit and pending-exception state;
5. fast callback enter/exit;
6. current pointer committed;
7. Greenlet switch attempted/completed/failed;
8. return-to-parent current transition;
9. queue removal/reinsertion; and
10. timeout dequeue-cycle counter increment.

For channel attempts, separately record:

1. entry queue snapshot and counterpart-present decision;
2. channel callback enter/exit;
3. transfer-in-progress mutation;
4. trap/closed validation;
5. waiter insertion/removal and balance update;
6. match/pop/unblock;
7. owner-manager scheduling commit;
8. optional host wake; and
9. preference-triggered schedule attempt.

These events are not permission to expose intermediate details as new public behavior. They are the fidelity needed to compare old and new ordering.

## 12. Characterization backlog

These tests should be designed before production logic. They may initially live as isolated oracle probes rather than edits to the historical suite.

| ID | Priority | Scenario | Required observations | Claims |
|---|---|---|---|---|
| C01 | P0 | Main calls receive with a ready sender that has not run | During a schedule callback, main is channel.queue, balance is -1, then exactly one rollback/match removes it | 1 |
| C02 | P0 | Main calls send with a ready receiver that has not run | Main joins send FIFO, child progresses, transfer succeeds, no residual ref/link | 1 |
| C03 | P0 | Main send/receive deadlock after N no-op tasklets | All N progress while main is waiting; error class/message; final queue/balance/refcount restored | 1, 12 |
| C04 | P0 | Construct, bind callable only, bind args, setup | callable/Greenlet/alive/paused/scheduled/runcount snapshots after every call | 3–4 |
| C05 | P0 | Running tasklet inspects itself and neighbors | is_current, scheduled, next/prev while Python body is executing | 2 |
| C06 | P0 | Paused bound tasklet run under switch_trap | paused + scheduled + runcount after failure, then later execution | 5, 14 |
| C07 | P0 | switch to ready and detached targets with queued neighbors | queue order, parent, callbacks, current, links before/during/after | 6 |
| C08 | P0 | Timed run whose first selected tasklet is switch-trapped | switched counter remains unchanged; queue and completed/dequeue counter outcome | 7 |
| C09 | P0 | Timed run of a tasklet that calls schedule repeatedly | public “completed” count per yield/dequeue cycle versus terminal death | 8 |
| C10 | P0 | Timed runs in two Python threads, read getters after each barrier | process-global reset/last-writer visibility | 9 |
| C11 | P0 | Outer timed/count-limited run invokes inner limited run | outer mode/budget corruption and exact overshoot/order | 10 |
| C12 | P0 | Python property sets -2, 2, large fitting ints, and overflow int; native setter does same | prior value retention versus clamp, pending exceptions | 11 |
| C13 | P0 | block-trapped receive with trace enabled/disabled | final equality plus no trace exposure/lifetime perturbation | 12, 42 |
| C14 | P0 | Non-main catches block-trapped or closed send and returns | transfer flag consequence, alive/dead/paused/scheduled/refcount | 13 |
| C15 | P0 | Rendezvous mutates counterpart and later hits switch_trap | transfer delivery, counterpart queue state, caller error, retry behavior | 14 |
| C16 | P0 | Reliable cross-thread switch/kill/bind/setup tests | worker captures exception into a synchronized result; all postconditions run | 16 |
| C17 | P0 | Native test ownership audit | per-pointer new/borrowed/stolen ledger and debug-refcount cleanup | 17, 25 |
| C18 | P0 | cargo metadata after dependency wiring | Bevy Defer’s async-executor package source is local path, no registry duplicate | 18 |
| C19 | P0 | cargo tree for core-only build | no Bevy package in the core dependency closure | 19 |
| C20 | P0 | Cross-thread rendezvous paused between match and owner pump | owner getruncount, scheduled, next/prev, callback visibility at the linearization barrier | 20–21 |
| C21 | P0 | Bevy worker attempts to pump foreign manager | no Greenlet call; deterministic rejection/enqueue-only behavior | 22 |
| C22 | P0 | Schedule callback calls getcurrent and inspects next.times_switched_to | previous remains current; target counter is already incremented | 23–24 |
| C23 | P0 | Python schedule callback raises with fast callback installed | fast callback still runs; pending exception/current commit/switch outcome exactly traced | 27 |
| C24 | P0 | Channel callback under block_trap, closed channel, and callback reentrancy | callback always occurs at legacy point; will_block reflects entry counterpart state | 28 |
| C25 | P0 | Drop all external refs to installed callback, then replace/clear | returned previous object safety, weakref/finalizer, no dangling pointer | 26 |
| C26 | P0 | Legacy-precompiled capsule consumer | imports exact name and exercises every table field without recompilation | 30–34 |
| C27 | P0 | Thread creation/destruction and manager dictionary removal | manager wrapper lifetime, closing registry, no resurrection/double release | 35 |
| C28 | P0 | Cycles through every Rust-owned PyObject edge in shadow prototype | tp_traverse visibility, tp_clear idempotence, collection/finalizer order | 36 |
| C29 | P0 | switch_trap malformed/no/extra/wrong-type arguments | subprocess result, sanitizer output, trap level unchanged after approved fix | 37 |
| C30 | P0 | Force SetParent failure and reset-to-main repeatedly | exact parent/main refcount delta on every success/failure | 38 |
| C31 | P0 | Closed unmatched receive loop | tasklet/channel refcounts, weakrefs, active counts, no accumulation | 39 |
| C32 | P1 | Exercise/reject already-scheduled run-next insertion | branch reachability, reschedule effect, exact refcount delta | 40 |
| C33 | P1 | Repeated module import/interpreter teardown | greenlet module references and module-state retention | 41 |
| C34 | P0 | Adversarial tasklet repeatedly catches TaskletExit during teardown | legacy nontermination boundary and separately approved target bound | 43 |
| C35 | P0 | Every scenario with tracing off/on | identical non-trace behavior, refcounts, finalizer order, and deterministic timing class | 42 |

## 13. Defect and divergence decision recommendations

These are recommendations for the future decision log, not code changes in this report.

| Finding | Recommended category | Reason |
|---|---|---|
| Broken assertRaises calls in worker threads | Test defect; repair oracle before use | The current test does not assert what its author intended |
| Native test stolen-reference misuse | Test defect; repair oracle before use | Passing tests cannot validate ownership while the test itself violates it |
| switch_trap uninitialized delta | Undefined legacy behavior; fix both | UB is not a portable compatibility contract |
| Callback setter dangling return | Memory-safety defect; fix both | Returning a freed PyObject cannot be a supported contract |
| SetParent failure/main reference paths | Defect pending characterization, then fix both | Reference imbalance is not intended scheduling semantics |
| Closed-receive missing decref | Defect pending refcount confirmation, then fix both | Likely isolated ownership leak |
| Duplicate run-next pre-incref | Defect/reachability pending | Branch exists; supported reachability is not yet proven |
| Greenlet import retention | Ownership decision pending | May be intentional process-lifetime retention, but must be explicit |
| send transfer flag on early error | Observable defect decision pending | Can affect liveness after caught exceptions |
| Mutate-then-rollback receive | Baseline order plus target invariant | Preflight may be parity-preserving if observer/refcount tests prove it |
| Nested limited-run corruption | Approved divergence or compatibility-mode quirk | Scope restoration deliberately changes nested behavior |
| Global timeout counter scope | Baseline parity first | Per-manager isolation is an API change |
| Channel mutex/host command queue | Opt-in host extension | Not required by the GIL-held compatibility baseline |
| Bounded teardown | Approved divergence | Deliberately replaces a possible infinite loop with a defined safety bound |

## 14. External authoritative references

- [Cargo workspaces](https://doc.rust-lang.org/cargo/reference/workspaces.html)
- [Cargo dependency source specification](https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html)
- [Cargo dependency overrides](https://doc.rust-lang.org/cargo/reference/overriding-dependencies.html)
- [CPython PyCapsule API](https://docs.python.org/3/c-api/capsule.html)
- [CPython object attribute API](https://docs.python.org/3/c-api/object.html)
- [CPython tuple API and stolen references](https://docs.python.org/3/c-api/tuple.html)
- [CPython cyclic-GC support for extension types](https://docs.python.org/3/c-api/gcsupport.html)
- [Python unittest.assertRaises](https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertRaises)
- [Python Thread exception and join behavior](https://docs.python.org/3/library/threading.html#thread-objects)
- [Greenlets and Python threads](https://greenlet.readthedocs.io/en/stable/python_threads.html)

## 15. Final assessment

All 43 submitted concerns should be carried into the next roadmap revision. Eight need the qualifications recorded in §1; none should be rejected.

The most urgent corrections are not implementation details. They are contract corrections:

1. model the actual legacy state combinations;
2. audit and stratify the test oracle;
3. separate parity from target invariants and approved divergences;
4. specify callback and cross-thread linearization points;
5. freeze the real native C++ ABI and ownership rules; and
6. make the Cargo/Bevy-free dependency graph mechanically provable.

Until those corrections and P0 characterizations exist, starting scheduler code would risk encoding the roadmap’s desired model as if it were Carbon’s baseline behavior.
