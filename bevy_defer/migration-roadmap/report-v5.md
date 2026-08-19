# Roadmap v5 Readiness Claim Audit

- Audit date: 2026-08-19
- Roadmap reviewed: `bevy_defer/migration-roadmap/v5.md`
- Published roadmap commit: `144504ac56232a4aac2b406ecd7e08cf0d0d6f5f`
- Roadmap Git blob: `d2dc837211616dd6016a9c37c332a91c0b99d22d`
- Roadmap SHA-256: `06473f3144b27d8384e8139f92cbbb0c700fefb41f00b26b30c3b2cbb46430fe`
- Legacy source baseline: `e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e`
- Current upstream Scheduler head checked: `c646f49b12ba2ae784548b242e0cd2051c5550f9`
- Repository: `QuasarRay/carbon-scheduler-lab`
- Scope: investigation only; this report does not amend v5, authorize implementation, or add implementation code

## Executive verdict

The submitted high-level conclusion is **substantially supported**, but one
important part of its Phase-0 rationale is overstated.

> Do not give an autonomous coding agent the unrestricted instruction
> “implement v5.”

V5 is architecturally coherent enough to authorize a deliberately bounded
Phase 0 followed by Phase 1A and a mandatory stop. It is not yet an execution
specification from which an agent should proceed automatically through
Phases 1B–6. The remaining gaps are principally work-package decomposition,
one interpreter-lifecycle policy, an exact cross-thread wake protocol, and
human-owned production acceptance inputs. They are not evidence that the
selected Carbon-on-Bevy-Defer architecture is fundamentally unsound.

The submitted Cargo claim needs correction:

- V5's two deployment features do create awkward or failing generic
  **workspace-wide** commands unless those commands select a mode or exclude
  `carbon_compat`.
- They do **not** make ordinary root `cargo test` or `cargo clippy` fail in the
  current non-virtual workspace: with a root package and no
  `default-members`, Cargo selects the root package by default.
- Phase 0 does not yet add `carbon_compat` as a workspace member; that happens
  in Phase 1A. Therefore the feature policy is not a blocker to beginning
  Phase 0.
- Adding `default-members` would not repair an explicit `--workspace` command.

The corrected authorization boundary is:

| Scope | Independent verdict |
|---|---|
| Begin Phase 0 evidence, lock, and scope-guard work | **GO** |
| Add `carbon_compat` and begin Phase 1A | **GO after Phase 0 and a frozen workspace-command policy** |
| Continue beyond Phase 1A automatically | **NO-GO; publish evidence and stop** |
| Begin Phase 1B | **Conditional GO after Phase-1A review and a CPython reinitialization policy** |
| Execute Phase 2 as one autonomous-agent transaction | **NO-GO; split it first** |
| Execute Phase 3 as one autonomous-agent transaction | **NO-GO; split it and freeze the wake algorithm first** |
| Complete the experimental backend through Phase 5 | **Architecturally plausible, subject to every preceding stop gate** |
| Claim production equivalence after Phase 5 | **NO-GO** |
| Let an implementation agent choose performance/platform/workload policy in Phase 6 | **NO-GO; those are human acceptance inputs** |
| “Implement all of v5 now” | **NO-GO** |

The numerical readiness scores in the submitted critique are opinions, not
reproducible measurements. This audit assesses the technical propositions
under those scores rather than attempting to validate the numbers themselves.

## Claim verdict summary

| # | Submitted proposition | Verdict | Qualification or consequence |
|---:|---|---|---|
| 1 | V5 should not be handed to an agent as one unrestricted implementation job | **Supported** | Mandatory review/stop gates remain necessary |
| 2 | V5 is sound enough for Phase 0 → Phase 1A, then stop | **Supported with a boundary correction** | Phase 0 may begin now; freeze build-command policy before Phase 1A adds the member |
| 3 | V5's Bevy Defer executor premises are accurate | **Supported; source-definite** | `CoreAsyncPlugin`, runner, scoped world, and retained task claims match source |
| 4 | V5's difficult Carbon queue/callback/channel/ABI premises are accurate | **Supported; source-definite** | All audited ordering claims match the implementation |
| 5 | The audited core Scheduler snapshot is current rather than stale | **Supported, more strongly than submitted** | Five audited files, not only two, match current upstream Git blobs |
| 6 | V5 contains a Cargo feature/workspace contradiction that blocks Phase 0 | **Partly supported; severity overstated** | There is a workspace-command policy gap, not a Phase-0 correctness blocker |
| 7 | Phase 2 and Phase 3 are too large for one autonomous-agent transaction | **Supported as execution-risk analysis** | Split each into immutable-test, mandatory-stop subphases |
| 8 | CPython same-process reinitialization policy must be resolved before Phase 1B | **Supported** | The answer changes module/global/generation design, not merely late teardown tests |
| 9 | The lost-wakeup algorithm and memory ordering must be frozen before cross-thread work | **Supported; v5 admits the gap** | Blocks the cross-thread subphase of Phase 3, not earlier phases |
| 10 | V5 lacks a defined production performance admission gate | **Partly supported** | V5 already requires approved budgets; it lacks a frozen benchmark manifest, thresholds, and approver |
| 11 | Production platform/toolchain policy must be human-approved | **Supported** | Upstream CI evidence is not itself a supported-platform contract |
| 12 | Eventual upstream/integration policy remains underdefined | **Partly supported** | It is a production/product gate, not a Phase-1 architecture blocker |
| 13 | V5 is architecture-ready but not whole-roadmap autonomous-agent-ready | **Supported** | This is the most accurate overall classification |
| 14 | A small v5.1 amendment is sufficient | **Supported** | No Carbon scheduler redesign is justified by the evidence in this audit |

## Evidence boundary and method

This investigation compared:

1. the complete published v5 roadmap;
2. the local Carbon Scheduler, Bevy Defer, and test sources at the pinned
   baseline;
3. the current public `carbonengine/scheduler` main branch as of the audit
   date;
4. Cargo's official workspace/package-selection documentation;
5. CPython's official initialization and extension-isolation documentation;
   and
6. current upstream Scheduler change and CI history relevant to performance
   and platform claims.

The audit checked exact Git blob identities where a staleness claim depended
on content equality. It did not infer identity from filenames or commit dates.

No compatibility implementation exists, so there was no prospective runtime
to build or execute. No Scheduler, Bevy Defer, Carbon I/O, sanitizer, ABI, or
benchmark suite was run for this report. The result is a source/documentation
and roadmap-readiness audit, not runtime proof.

## 1. The positive architectural premises are sound

### 1.1 Bevy Defer executor behavior

**Verdict: supported; source-definite.**

V5 accurately distinguishes Bevy Defer resource installation from executor
polling:

- `CoreAsyncPlugin` is documented as the core plugin that does not run its
  executors and initializes the relevant resources and schedules
  (`bevy_defer/src/lib.rs`, lines 98–112).
- `AsyncPlugin` adds `CoreAsyncPlugin` and installs
  `run_before_async_executor.before(run_async_executor)` in its configured
  schedules (`bevy_defer/src/lib.rs`, lines 197–222).
- `AsyncExecutor` contains a crate-private `Rc<LocalExecutor>`, and
  `spawn_task` returns an `async_executor::Task<T>`
  (`bevy_defer/src/executor.rs`, lines 46–60).
- `run_async_executor(&mut World)` installs scoped `SPAWNER`, `QUERY_QUEUE`,
  `REACTORS`, and `WORLD` context and drains the executor through
  `try_tick()` (`bevy_defer/src/executor.rs`, lines 77–95).
- Bevy Defer's public spawn documentation says that dropping the returned
  handle drops the associated future (`bevy_defer/src/spawn.rs`, lines
  61–76).

Those facts support v5's decisions to install an explicit runner, execute the
driver in a real Bevy `World` scope, retain the driver task, and treat an
accidental live-task drop as cancellation rather than normal retirement.

They do not by themselves prove that Greenlet switching from a suspended Rust
`Future::poll` is safe. V5 correctly assigns that proof to Phase 1A/1B rather
than treating the executor source as sufficient evidence.

### 1.2 Carbon runnable-chain behavior

**Verdict: supported; source-definite.**

The baseline manager chooses `baseTasklet->Next()`, switches to that tasklet,
and removes or reschedules it only after `SwitchTo()` returns. During the
tasklet's execution, the current tasklet can therefore still be linked in the
runnable chain. The relevant sequence is visible in current upstream
[`ScheduleManager.cpp`](https://github.com/carbonengine/scheduler/blob/c646f49b12ba2ae784548b242e0cd2051c5550f9/src/ScheduleManager.cpp#L450-L553).

V5's linked-while-running law and its orthogonal tasklet flags are faithful to
that representation. A cleaner mutually exclusive `Ready → Running → Paused`
enum would not be an isomorphic legacy model.

### 1.3 Callback, current-tasklet, and switch-count timing

**Verdict: supported; source-definite.**

`Tasklet::SwitchTo()` increments the target's `m_timesSwitchedTo` before it
calls `SetCurrentTasklet()` in current upstream
[`Tasklet.cpp`](https://github.com/carbonengine/scheduler/blob/c646f49b12ba2ae784548b242e0cd2051c5550f9/src/Tasklet.cpp#L382-L385).
`SetCurrentTasklet()` then invokes switch accounting and callbacks before it
assigns `m_currentTasklet` in
[`ScheduleManager.cpp`](https://github.com/carbonengine/scheduler/blob/c646f49b12ba2ae784548b242e0cd2051c5550f9/src/ScheduleManager.cpp#L141-L150).

Consequently a reentrant callback can observe the incremented target counter
while `getcurrent()` still exposes the previous tasklet. V5 preserves that
non-obvious ordering rather than reducing it to a generic “transition event.”

### 1.4 Send/receive callback asymmetry

**Verdict: supported; source-definite.**

The implementation deliberately has different prefixes:

- send invokes the channel callback and then marks transfer-in-progress; and
- receive marks transfer-in-progress and then invokes the channel callback.

Both sequences are directly visible in current upstream
[`Channel.cpp`](https://github.com/carbonengine/scheduler/blob/c646f49b12ba2ae784548b242e0cd2051c5550f9/src/Channel.cpp#L34-L42)
and
[`Channel.cpp`](https://github.com/carbonengine/scheduler/blob/c646f49b12ba2ae784548b242e0cd2051c5550f9/src/Channel.cpp#L147-L156).
V5's asymmetric trace contract is therefore correct.

### 1.5 Native capsule shape

**Verdict: supported; source-definite.**

The native API contains `PyObject **TaskletExit`, not `PyObject *TaskletExit`.
That is visible in current upstream
[`Scheduler.h`](https://github.com/carbonengine/scheduler/blob/c646f49b12ba2ae784548b242e0cd2051c5550f9/include/Scheduler.h#L109-L133).
V5 is right to preserve the unchanged C++ header and verify the identity of
`*TaskletExit`; a manually approximated Rust struct would create avoidable ABI
risk.

## 2. Snapshot staleness claim

**Verdict: supported, more strongly than submitted.**

The submitted critique says the critical `Tasklet.cpp` and
`ScheduleManager.cpp` files in the snapshot match current upstream main. That
is true. The audit compared exact Git blobs and found the following five core
files identical between the pinned lab baseline and current upstream
[`c646f49b12ba2ae784548b242e0cd2051c5550f9`](https://github.com/carbonengine/scheduler/commit/c646f49b12ba2ae784548b242e0cd2051c5550f9):

| File | Exact Git blob in both trees |
|---|---|
| `src/Tasklet.cpp` | `493c7c12a092a04bf171cfdee8ae187f4871fce5` |
| `src/ScheduleManager.cpp` | `0ec50a45b31b185aa709136c6f57ecb17b9dde0b` |
| `src/Channel.cpp` | `754a59087d4322a57eb8ffcb7e397cb305a16541` |
| `include/Scheduler.h` | `21d01ce43e82a74ff7f67977bcc86c90e3d4d51c` |
| `src/SchedulerModule.cpp` | `9262bf066cbd57d1a9a92f83433424231f90e27a` |

This materially reduces the risk that v5's core queue, callback, channel,
module, and capsule decisions were derived from obsolete private code.

It does not freeze future upstream behavior. Phase 0 should retain the local
baseline digest as the compatibility authority and separately record the
upstream comparison commit. A later upstream change is an input to a deliberate
rebase decision, not an unreviewed moving oracle.

## 3. Cargo modes and workspace behavior

**Submitted claim: V5's exactly-one-mode guards contradict workspace use and
must be corrected before Phase 0.**

**Verdict: partly supported; the operational gap is real, but the stated
Phase-0 blocker and `default-members` rationale are incorrect.**

### 3.1 What v5 actually specifies

V5 proposes:

```toml
[features]
default = []
standalone = []
embedded = []
```

It then rejects both `standalone + embedded` and `neither`, intentionally
rejects `--all-features`, and freezes explicit package builds for each mode.
That is internally coherent for deployment artifacts: every artifact must
have one unambiguous topology.

### 3.2 What fails

After Phase 1A adds `carbon_compat` to the workspace, these generic command
families would fail unless adjusted:

```text
cargo check --workspace
cargo test --workspace
cargo clippy --workspace
cargo check --workspace --all-features
```

The first three compile `carbon_compat` with neither mode unless a mode is
selected. The last compiles it with both modes. This is poor generic workspace
ergonomics and must be an explicit CI/tooling policy rather than an accidental
failure.

### 3.3 What does not fail for the stated reason

`bevy_defer/Cargo.toml` is a non-virtual workspace root that also defines the
root `bevy_defer` package. Cargo's official
[workspace package-selection rules](https://doc.rust-lang.org/cargo/reference/workspaces.html#package-selection)
state that, when no package options are supplied, a root package is selected
by default; `default-members` is relevant when defining a different default
set. Therefore plain root commands such as:

```text
cargo test
cargo clippy
```

continue to select the root package. The absence of `default-members` does not
make them select every member.

Moreover, `default-members` does not constrain an explicit `--workspace`, so
adding it alone would not solve the submitted failure mode.

Finally, v5 adds the workspace member in Phase 1A, not Phase 0. Phase 0's lock,
baseline, scope-guard, and environment work can begin before this issue is
reachable.

### 3.4 Required v5.1 decision

Before Phase 1A adds the member, v5.1 should choose one of these policies:

1. **Common validation mode:** allow `carbon_compat` to compile with neither
   deployment mode for mode-independent library checks, while still rejecting
   both and requiring exactly one mode for artifacts and integration tests.
2. **Default standalone:** make `standalone` the package default, override it
   explicitly for embedded builds, and continue rejecting both.
3. **Explicit workspace matrix:** keep the current guards, document that
   generic `--workspace`/`--all-features` are unsupported, run the root package
   separately, and run `carbon_compat` once per explicit mode.

Option 1 usually gives the best generic tooling behavior without silently
choosing a deployment topology. The roadmap may select another option, but it
must freeze the exact `check`, `test`, `clippy`, documentation, and packaging
commands.

This correction is required before Phase 1A manifest work, not before Phase 0
evidence capture.

## 4. Phase 2 and Phase 3 execution granularity

**Verdict: supported as an autonomous-agent execution concern.**

The exact phrase “grossly oversized” is judgment rather than a source fact,
but the dependency and rollback risk is observable. V5 Phase 2 combines:

- the process runtime and per-thread manager model;
- main-tasklet ownership;
- Python objects, generational handles, tombstones, GC traversal, and clear;
- Greenlet creation and parent chains;
- the intrusive runnable chain;
- bind/setup/run/schedule/switch;
- nested-tasklet modes;
- callback and exception timing; and
- budgets and counters.

Phase 3 likewise combines channel object semantics, same-thread rendezvous,
blocking queues, callback prefixes, trap/closed rollback, kill/throw/clear/
teardown coupling, foreign-manager commitment, wakeup races, and embedded
foreign-context rejection.

Those are reasonable architecture chapters. They are not safe atomic coding
transactions: a failure would leave too many possible causes, and a large
patch could make tests pass through mutually compensating mistakes.

### 4.1 Recommended gated split for Phase 2

| Subphase | Scope | Required stop evidence |
|---|---|---|
| 2A — object and ownership shells | FFI/type shells, generational handles, tombstones, Python ownership ledger, `tp_traverse`/`tp_clear`; no Greenlet switch | GC/refcount/type-identity tests; stale-handle and clear idempotence |
| 2B — minimal runnable vertical slice | manager/main ownership, Greenlet bootstrap and required parent/exception carrier, intrusive queue, one `schedule`/`run` path | linked-while-running trace; same-poll return; deterministic queue tests |
| 2C — tasklet control completion | bind/setup/run/switch variants, `useNestedTasklets`, reschedule, traps, callback/current/counter ordering, budgets | unchanged focused Python/C++ tests plus exact ordering traces |

The split must respect real dependencies. In particular, Greenlet parent and
minimal exception state cannot be postponed past the first tasklet switch just
to make the table look cleaner.

### 4.2 Recommended gated split for Phase 3

| Subphase | Scope | Required stop evidence |
|---|---|---|
| 3A — same-thread rendezvous | channel object/API, callback prefixes, balance/preference, immediate same-thread send/receive matching | exact send/receive prefix and FIFO traces |
| 3B — blocked channel/control unit | wait queues, block/switch traps, close/clear, kill/throw, unlink and teardown | rollback, ownership, blocked-control, and teardown tests |
| 3C — standalone cross-thread commitment | second manager/headless host, logical commit, generation-safe wake, owner-thread execution; embedded rejection | adversarial barrier/stress tests and no-lost-wakeup proof |

Each subphase should be a separately authorized work package with immutable
tests and an explicit stop. This is an execution-plan amendment, not a reason
to replace v5's architecture.

## 5. CPython initialization/finalization generations

**Verdict: supported; decide before Phase 1B.**

V5 specifies one coherent embedded lifecycle:

```text
bootstrap/plugin registration
Py_Initialize
driver operation
driver Dead
release Python edges
Py_FinalizeEx
drop App
```

It later asks to repeat startup/shutdown, but it does not say whether repetition
means:

1. multiple `Py_Initialize`/`Py_FinalizeEx` cycles in one OS process; or
2. one interpreter generation per subprocess, with repetition performed by a
   test harness spawning fresh processes.

That is not merely late test wording. It affects the ownership of runtime
registries, Python types, the capsule table, `TaskletExit`, built-in-module
state, generation counters, and any `OnceLock` or C++ static used in Phase 1B
and Phase 2.

The baseline raises the concern directly. `SchedulerModule.cpp` uses a static
module definition with `m_size = -1` and static/global module/API state in
current upstream
[`SchedulerModule.cpp`](https://github.com/carbonengine/scheduler/blob/c646f49b12ba2ae784548b242e0cd2051c5550f9/src/SchedulerModule.cpp#L1162-L1178).
That does not prove repeated initialization currently fails, but it does mean
generation isolation cannot be assumed.

CPython's official
[`Py_FinalizeEx` documentation](https://docs.python.org/3.13/c-api/init.html#c.Py_FinalizeEx)
notes that extension modules are not unloaded and that some extensions may not
work correctly when Python is initialized more than once. CPython's official
[extension-isolation guidance](https://docs.python.org/3.13/howto/isolating-extensions.html)
explains why process-global state is hazardous across sequential interpreter
lifetimes and recommends per-module state or an explicit restriction.

### Required v5.1 decision

The smallest safe experimental policy is:

> Standalone and embedded experiments support one CPython initialization/
> finalization generation per process. Repetition uses fresh subprocesses.
> Same-process reinitialization is detected/rejected and remains a separate
> production design decision.

If same-process reinitialization is instead required, Phase 1B must prove it
with generation-owned module/type/API state before Phase 2 relies on global
cells. An implementation agent must not choose between those contracts while
writing teardown code.

## 6. Cross-thread lost-wakeup exactness

**Verdict: supported; text-definite and concurrency-critical.**

V5 selects a plausible state shape:

```text
requested: AtomicBool
waker: Mutex<Option<Waker>>
generation: RuntimeGeneration
```

It also explicitly says that the exact lost-wakeup algorithm must be specified
and tested before Phase 3. The submitted critique is therefore not discovering
a contradiction; it is identifying a roadmap-owned prerequisite that has not
yet been discharged.

Data shape and prose laws are insufficient because these races must all work:

1. a request occurs before any waker is registered;
2. a request occurs while the owner replaces a waker;
3. a request occurs after the owner's final request check but before it returns
   `Pending`;
4. a stale generation retains a cloned wake handle during shutdown; and
5. multiple requests collapse without losing the logical runnable commitment.

### Protocol that must be frozen before subphase 3C

At minimum, the roadmap must define:

- the foreign-side order of logical commit, request publication, waker clone,
  lock release, and `wake()`;
- the owner-side order of request consumption, waker registration, mandatory
  post-registration recheck, and transition to `Pending`;
- exact Rust atomic orderings and the state they publish/observe;
- how a wake is tied to one immutable runtime generation;
- how shutdown closes the wake target without allowing a stale task/Greenlet
  continuation to resume;
- that neither the GIL-gated runtime borrow nor the waker mutex is held across
  callbacks, decrefs, Greenlet switches, or `Waker::wake`; and
- deterministic race tests plus prolonged stress/model checking appropriate
  to the selected primitive.

A conventional candidate is release publication by the requester and an
acquire/release consume–register–recheck loop by the owner. That is only a
design sketch; v5.1 must freeze and review the actual pseudocode and invariants
rather than tell the coding agent to derive them from this report.

This gap blocks only standalone cross-thread subphase 3C. It does not block
Phase 0, the single-owner Phase 1 experiments, or same-thread channel work.

## 7. Performance admission

**Submitted claim: performance is only a later consideration and must become
a defined production gate.**

**Verdict: partly supported. V5 already makes performance a production gate,
but the gate is not executable yet.**

V5 Phase 6 explicitly requires measured latency, throughput, and memory
budgets, and its Production Definition of Done requires approved budgets. It
therefore does not treat performance as optional or allow an experimental
backend to claim production equivalence without it.

What is missing is the externally supplied acceptance manifest:

- benchmark workloads and datasets;
- legacy and Rust build profiles/toolchains;
- warm-up, sample count, variance, and machine controls;
- absolute and relative thresholds;
- long-duration memory/refcount slope criteria;
- who has authority to approve or change the thresholds; and
- which regressions are release-blocking versus approved divergences.

The submitted hot-path example is factual. Upstream Scheduler PR
[#38](https://github.com/carbonengine/scheduler/pull/38), merged on 2026-08-14,
fixed a reference leak on the tasklet-switch hot path whose memory effect grew
with server uptime. The merge is current upstream commit
[`c646f49b12ba2ae784548b242e0cd2051c5550f9`](https://github.com/carbonengine/scheduler/commit/c646f49b12ba2ae784548b242e0cd2051c5550f9).
This supports a long-duration memory/refcount-slope gate at least as strongly
as a throughput gate.

### Required production input

Before Phase 6 is authorized, a human owner should freeze a benchmark manifest
covering at least:

- tasklet switches per second and per-switch allocation/refcount slope;
- `scheduler.run()` latency distribution;
- same-thread and standalone cross-thread channel throughput/wake latency;
- idle and active Bevy frame overhead;
- startup, shutdown, and repeated-subprocess lifecycle cost;
- RSS/object-count behavior in a long soak; and
- representative Carbon I/O workloads.

The implementation agent may automate and execute those measurements. It must
not invent the production threshold or approve its own regression.

This is a Phase-6 admission prerequisite, not a reason to block Phase 1A.

## 8. Supported platform and toolchain policy

**Verdict: supported as a human-owned production decision.**

V5 correctly requires one pinned environment for reproducible feasibility
work and separately requires an approved matrix for production. It does not,
however, list that matrix, and an implementation agent has no authority to
infer it.

Current upstream contains platform-specific TeamCity configurations for
[`macOS`](https://github.com/carbonengine/scheduler/blob/c646f49b12ba2ae784548b242e0cd2051c5550f9/.teamcity/MacOS/Project.kt)
and
[`Windows`](https://github.com/carbonengine/scheduler/blob/c646f49b12ba2ae784548b242e0cd2051c5550f9/.teamcity/Windows/Project.kt),
including multiple configurations. That is evidence that those platforms are
actively represented in upstream build/test automation. It is not by itself a
formal Carbon ecosystem or Fenris production support promise, and it cannot
establish the required Python, Greenlet, compiler, architecture, or Bevy
version combinations.

Before Phase 6, a human/product owner must approve a table containing:

- operating system and CPU architecture;
- Rust toolchain and Bevy/Bevy-Defer version;
- C/C++ compiler and standard-library ABI;
- CPython and Greenlet versions/build modes;
- debug/release/sanitizer configurations;
- standalone versus embedded support per row; and
- required Scheduler, ABI, Carbon I/O, soak, and packaging evidence per row.

Phase 0 should pin one feasibility environment. It should not pretend that
environment is the eventual production matrix.

## 9. Upstream and product integration

**Verdict: partly supported; this is a product/production gap, not a runtime
architecture defect.**

V5 includes external packaging, rollout, rollback, and representative workload
evidence in its production program. It does not choose an eventual upstream
delivery topology or maintainer acceptance path. That omission is harmless for
the lab experiment but material before a production claim.

Human owners must eventually decide, for example:

- whether the target is a lab-only alternative backend, a maintained Carbon
  package option, a Bevy Defer upstream feature, or another distribution;
- where backend selection occurs without modifying import-time public behavior;
- which project owns the C++ shim, wheels/native packages, compatibility
  matrix, and security updates;
- how changes are reviewed and released; and
- how a deployment rolls back to the legacy scheduler.

The public repositories cannot establish a private Fenris production bar, so
this audit cannot verify the submitted claim that v5 is sufficient or
insufficient for that internal bar. It can verify only that v5 does not supply
those human acceptance inputs and must not let an agent invent them.

## 10. Corrected readiness assessment

### 10.1 Phase 0

**GO.** Phase 0 may capture digests, pin the environment, track the workspace
lock, and create the executable add-only scope guard. The deployment-mode
workspace policy must be documented before Phase 1A adds the package member,
but it is not necessary to block the preceding evidence work.

### 10.2 Phase 1A

**GO after Phase 0 and the build-command decision.** Phase 1A is deliberately
disposable and single-owner. It is the right place to test:

- real headless Bevy `App`/`World` context;
- explicit executor-run installation;
- retained driver task ownership;
- one Greenlet → Python → nested Carbon yield → same native switch return;
- no borrow/lock/`Context` reference across the Greenlet switch; and
- deterministic `Dead` shutdown.

Passing Phase 1A must still end in a published evidence checkpoint and manual
review. It proves neither embedded singleton topology nor Carbon parity.

### 10.3 Phase 1B

**Conditional GO only.** Before authorization:

1. Phase 1A evidence must be reviewed;
2. same-process CPython reinitialization must be required or explicitly
   unsupported; and
3. the one-process embedded fixture/build selection must remain frozen.

V5 otherwise defines the embedded singleton, bootstrap order, owner-thread
entry, poll-frame safety, no nested repoll, driver lifecycle, and fail-stop
drop policy strongly enough for the experiment.

### 10.4 Phase 2

**Architecture-ready, not ready as one autonomous work package.** Split 2A,
2B, and 2C (or an equivalently dependency-correct sequence), authorize one at
a time, and require focused unchanged tests plus new ownership/ordering tests
at each stop.

### 10.5 Phase 3

**Architecture-ready, not ready as one autonomous work package.** Split
same-thread rendezvous, blocked-control coupling, and cross-thread wake. Freeze
the exact generation-safe request/register/recheck algorithm before the last
subphase.

### 10.6 Phases 4 and 5

**Conditionally plausible.** Phase 4 depends on completed ownership/control
nuclei. Phase 5 is a legitimate experimental gate because it includes Carbon
I/O and a real one-process Bevy workload. Neither authorizes a production
equivalence claim.

### 10.7 Phase 6

**Not autonomously executable as written, by design.** Production
certification requires external decisions: supported platforms, performance
thresholds, representative workloads, packaging/integration ownership,
rollout, and rollback. These are acceptance authority, not missing Rust code.

## 11. Minimal v5.1 amendment set

V5 does not need another architectural rewrite. A focused v5.1 should add:

1. **Workspace command policy.** Specify how generic root/workspace
   `check`/`test`/`clippy`/docs commands coexist with mutually exclusive
   deployment builds. Do not claim `default-members` alone fixes
   `--workspace`.
2. **Interpreter generation policy.** Require same-process
   initialize/finalize support or explicitly use one generation per process
   and fresh-subprocess repetition.
3. **Phase 2 subphases.** Freeze small, dependency-correct, separately
   authorized work packages and exit tests.
4. **Phase 3 subphases.** Separate same-thread rendezvous, blocked control,
   and standalone cross-thread wake.
5. **Exact wake protocol.** Before cross-thread coding, freeze pseudocode,
   atomic orderings, generation close behavior, and race/model tests.
6. **Human production prerequisites.** Name the external approvers and required
   manifests for performance, supported platforms/toolchains, workloads, and
   integration/rollout policy.

The first four affect implementation sequencing. The last two prevent an AI
agent from silently converting unresolved policy into code or self-approved
production evidence.

## 12. Final classification

The submitted bottom line is correct after narrowing its Cargo rationale:

> **Architecture: essentially ready. Phase 0/1A implementation: ready with a
> small pre-Phase-1A workspace-command decision. Whole-roadmap autonomous
> implementation: not ready. Production equivalence: requires human-approved
> Phase-6 inputs and evidence.**

The appropriate future instruction is not “implement v5.” It is:

```text
Authorize Phase 0.
Freeze the workspace command/mode matrix.
Authorize Phase 1A only.
Publish evidence and stop.
```

After review, Phase 1B may be separately authorized once interpreter-generation
policy is explicit. Phases 2 and 3 must first be split into smaller gated work
packages. Nothing in this audit authorizes code, modifies v5, or supports a
production-equivalence claim.
