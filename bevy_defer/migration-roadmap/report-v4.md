# Roadmap v4 Readiness Claim Audit

- Audit date: 2026-08-16
- Roadmap reviewed: `bevy_defer/migration-roadmap/v4.md`
- Published roadmap commit: `d091649a15cca17fe6d36b66d8b4aa469e08d809`
- Roadmap blob: `82e39cee351059615d923ec498a387498fef10bc`
- Legacy source baseline reviewed: `e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e`
- Repository: `QuasarRay/carbon-scheduler-lab`
- Scope: investigation only; this report does not amend v4 and does not authorize or implement code

## Executive verdict

The submitted conclusion is **substantially supported**, with two important
qualifications:

> V4 is ready to start a strictly bounded, disposable Phase 1A headless
> feasibility spike. It is not ready for Phase 1B or automatic continuation
> into the compatibility implementation.

The authorization boundary should be stated more precisely than “Phase 0 and
Phase 1A are GO”:

| Authorization | Verdict |
|---|---|
| Begin Phase 0 evidence capture and scope-guard work | **GO** |
| Declare Phase 0 reproducibility complete | **NO-GO until dependency/toolchain pinning is enforceable** |
| Implement Phase 1A only, then stop | **GO** |
| Treat Phase 1A as evidence that embedded mode works | **NO-GO** |
| Begin Phase 1B | **NO-GO until the bootstrap, artifact-mode, and abnormal-drop policies are fixed** |
| Begin Phase 2 automatically after Phase 1A | **NO-GO** |
| Begin Phase 3 cross-thread work | **NO-GO until the manager/host support matrix is fixed** |
| Implement v4 sequentially without another decision point | **NO-GO** |

V4 did fix the large v3 defects. Its binary-singleton design, driver-only
embedded entry, explicit executor run, suspended-poll-frame rules, retained
task handle, GIL-gated state, low-level FFI selection, and Phase-2
`useNestedTasklets` scope are all material improvements. The remaining gaps
are localized enough for a short v4.1 amendment rather than another complete
roadmap rewrite.

The numerical readiness scores in the submitted critique are opinions rather
than falsifiable measurements. This report evaluates the technical statements
under those scores, not the exact numbers.

## Claim verdict summary

| # | Claim | Verdict | Consequence |
|---:|---|---|---|
| 1 | V4 is not ready for unrestricted implementation | **Supported** | Keep an explicit stop after Phase 1A |
| 2 | Phase 0 and Phase 1A may begin now | **Mostly supported** | Phase 0 may start, but its reproducibility exit cannot pass yet |
| 3 | Phase 1B bootstrap order contradicts the embedded-host rule | **Supported; text-definite** | P0 relative to Phase 1B |
| 4 | Embedded cross-thread manager/host support is ambiguous | **Supported; source-definite** | Resolve before Phase 3; test the selected matrix |
| 5 | Abnormal live-host `Drop` still has no selected policy | **Supported** | Select one policy before Phase 1B teardown code |
| 6 | Intentionally leaking continuation state is automatically the safest fix | **Not established as written** | Retain the complete executor ownership closure or choose fail-stop abort |
| 7 | Cargo dependency pinning is not enforceable as written | **Supported** | Track a workspace lock and use `--locked`; pin non-Cargo inputs separately |
| 8 | Deployment-mode build selection remains unspecified | **Supported** | Freeze features/targets/commands before Phase 1B |
| 9 | V4's Greenlet/Future safety section is implementation-level strong | **Supported as a design contract, not yet as proof** | Phase 1A is a legitimate attempt |
| 10 | Normal driver lifecycle is sufficiently specified | **Mostly supported** | Only abnormal drop and interpreter teardown remain open |
| 11 | The Rust GIL/wake split is implementable | **Mostly supported** | Foreign manager topology is still missing |
| 12 | The phase decomposition is now sound | **Supported** | Preserve Phase 1A/1B as separate gates |
| 13 | The listed five amendments are the only remaining changes | **Mostly supported, but incomplete literally** | Add reverse CPython-finalization order to the bootstrap amendment |

## Evidence boundary

This is a source, manifest, test, and architecture audit. No `carbon_compat`
implementation exists, so no prospective runtime behavior could be executed.
The source-definite findings were checked against v4, the current Bevy Defer
manifest/source, Carbon's manager/channel tests, and repository ignore rules.

No Scheduler, Bevy Defer, Carbon I/O, sanitizer, or ABI test suite was run for
this report. Such execution cannot prove or disprove the not-yet-implemented
embedded topology. The report uses primary CPython and Cargo documentation for
the external API/build claims.

## 1. Embedded bootstrap ordering contradiction

**Verdict: supported and blocking for Phase 1B.**

V4's general embedded rule is unambiguous:

- `PyImport_AppendInittab` is called before `Py_Initialize` (v4 lines
  190–201); and
- attaching an embedded host after CPython initialization is unsupported and
  must fail before manager/Greenlet creation (v4 lines 214–218).

The second rule matters because the compatibility plugin is not an inert
label. It installs the owner-thread resources and driver and records the
runtime generation/runner marker (v4 lines 300–309).

Phase 1B then prescribes this literal order (v4 lines 1123–1134):

```text
create App
register PyInit__scheduler
initialize CPython
import scheduler
add CarbonCompatPlugin
submit Python to the driver's App
```

The plugin attachment therefore occurs after initialization and import, even
though §4.1 says such attachment is unsupported. The earlier registration of
the built-in module does not by itself install the plugin's App resources,
driver, executor run, or marker.

The contradiction cannot be dismissed as a wording detail. An implementer
must invent one of at least two materially different lifecycle models:

1. the plugin/bootstrap exists before CPython and owns registration; or
2. a pre-initialization bootstrap exists first, while the App plugin may
   attach after initialization but before any manager/Greenlet exists.

CPython independently confirms that `PyImport_AppendInittab` must precede
`Py_Initialize`; see the official
[import C API](https://docs.python.org/3/c-api/import.html#c.PyImport_AppendInittab).
That external rule validates v4's module-registration order, but it does not
decide the missing Bevy host/plugin order.

### Required correction

V4.1 should select one complete startup protocol. The cleanest interpretation
of v4's current “no post-init attachment” rule is:

```text
create App
create EmbeddedRuntimeBootstrap and generation
add CarbonCompatPlugin using that bootstrap
plugin installs CoreAsyncPlugin/resources/one runner/driver
register PyInit__scheduler from that same bootstrap
initialize CPython
import unchanged scheduler
verify built-in origin and generation identity
submit initial Python entry
```

It is also coherent to let `CarbonCompatPlugin::build` perform the inittab
registration, provided plugin addition is guaranteed to happen before
interpreter initialization and the plugin does not call ordinary CPython APIs
that require an initialized interpreter.

The alternative—allow plugin attachment after initialization when inittab
registration happened earlier and no manager exists—is viable, but it changes
the stated rule and needs an explicit bootstrap object that proves generation
identity across both steps.

### Missing inverse order

The same amendment should define teardown in reverse. V4 requires driver
shutdown before App destruction, but never places `Py_FinalizeEx` relative to
driver/manager cleanup. Carbon teardown can release Python references and run
CPython APIs, so the safe experimental order must be explicit:

```text
reject new entries
drive CarbonDriver to Dead while CPython/GIL remain usable
release Task and all compatibility-owned Python edges
finalize CPython
drop the now-dead Bevy compatibility resources/App
```

If another ordering is selected, it needs an ownership proof. “Create and
tear down the minimal module safely” is an acceptance goal, not a substitute
for specifying which runtime is alive during each teardown step.

## 2. Embedded cross-thread support matrix

**Verdict: supported; blocking for Phase 3, not for single-thread Phase 1B.**

V4 says all first manager creation and mutating/control-transferring embedded
Carbon operations must happen on the owner thread inside an active driver
entry (v4 lines 270–282). In the same contract, a foreign thread may commit a
permitted cross-thread channel transition under the GIL and wake the owner.

The logical-state design later assumes a rendezvous may release a tasklet
owned by “another manager,” commit it synchronously, and wake that manager's
owner (v4 lines 576–591). Phase 3 explicitly includes foreign logical
commitment and `WakeState` notification (v4 lines 1217–1236).

The baseline requires a manager on each participating Python thread:

- `ScheduleManager::GetThreadScheduleManager()` reads the current Python
  thread-state dictionary and creates/stores a manager when absent
  (`src/ScheduleManager.cpp` lines 85–128).
- `test_inter_thread_communication` constructs and runs a tasklet on a new
  Python thread while the original thread independently constructs and runs
  the receiver (`tests/python/scheduler/tests/test_channel.py` lines
  183–209).

The test's relevant topology is:

```text
Python thread A
    manager A
    tasklet A
    scheduler.run()

Python thread B
    manager B
    tasklet B
    scheduler.run()

shared channel links A and B
```

V4 does not say where manager B and its owner-only state live in embedded
mode. Three different designs are possible:

1. **Single embedded Carbon owner only.** Foreign threads cannot create or
   run Carbon tasklets; only a tightly defined non-executing wake/commit API
   is allowed.
2. **Embedded plus private headless workers.** The Bevy owner uses the App
   driver, while each other Python thread owns a standalone-style headless
   host/driver inside the same built-in module runtime.
3. **Multiple embedded owner hosts.** Each supported thread has a separately
   registered owner pump; this is a larger design not presently specified.

The phrase “a foreign thread may commit” does not select among these. In
particular, a normal Carbon `channel.send()` or `receive()` needs the current
tasklet, which normally implies that the foreign thread already has its own
manager.

### Required correction

V4.1 needs an explicit matrix such as:

| Deployment | Python-thread model | Managers/hosts | Cross-thread channel contract |
|---|---|---|---|
| Standalone experiment | Multiple GIL-enabled Python threads | One private headless host and manager per thread | Required by unchanged Scheduler tests |
| Embedded experiment | Exactly one Carbon-executing owner thread | One App driver/manager | Foreign Carbon tasklet execution unsupported; define whether any non-executing commit API remains |
| Embedded production | Decision deferred | To be designed | No implied support |

The embedded-plus-headless-worker design is also valid, but must say how the
built-in module chooses each thread's host, how process-global state is
shared, how each wake is pumped, and how all hosts shut down.

The unchanged Scheduler suite runs in standalone mode under v4, so this gap
does not invalidate Phase 1A. It does invalidate any claim that Phase 3's
embedded cross-thread architecture is already determined.

## 3. Abnormal live-host `Drop`

**Verdict: the missing policy claim is supported; the proposed leak policy is
only conditionally supported.**

V4's normal lifecycle is sufficiently concrete:

```text
Idle -> Requested -> ExecutingSegment -> Committing -> Idle
Idle/Requested -> ShuttingDown -> Dead
```

It retains the returned `Task<()>`, forbids detach, drives teardown while the
World remains alive, and releases the task only after `Dead` (v4 lines
437–482). This matches the current Bevy Defer API:

- `AsyncExecutor::spawn_task` returns a handle
  (`bevy_defer/src/executor.rs` lines 46–60); and
- Bevy Defer documents that dropping the handle drops the associated Future
  (`bevy_defer/src/spawn.rs` lines 61–76).

The unresolved branch appears at v4 lines 484–489. A live abnormal teardown
must “fail loudly or retain state according to a named safety policy.” Those
are different policies. A `Drop` implementation cannot leave the choice to
the implementer because panic, abort, leak, and best-effort cleanup have
different safety and observable behavior.

### Why “leak the continuation state” is not yet a complete answer

The submitted critique recommends intentionally retaining the
continuation-owning state and emitting a fatal diagnostic. The safety
motivation is sound: bounded leakage is preferable to cancelling a Future
whose native/Greenlet continuation can still resume.

However, the retained set must include the complete ownership closure, not
only a logical runtime or Greenlet object. `AsyncExecutor` is an
`Rc<LocalExecutor>` held as Bevy non-send state, and the driver Future belongs
to that executor. Dropping the surrounding App/World can drop the executor
and its runnable even if some separate logical state was forgotten. A safe
leak policy therefore has to retain, as one unit:

- the driver `Task`;
- an owning `AsyncExecutor`/`LocalExecutor` reference;
- the Future and every returnable native/Greenlet continuation;
- manager/tasklet logical state;
- all Python references whose destruction is deferred; and
- any host generation/wake state needed to keep stale access inert.

Whether that ownership closure can be extracted safely from a resource while
the outer App is itself being dropped is an implementation constraint that
v4 does not address.

### Required correction

V4.1 should choose exactly one experimental fallback. Two defensible choices
are:

1. **Fail-stop:** after a non-allocating diagnostic, abort the process if a
   live Greenlet-capable host reaches `Drop` before `Dead`. Test this in a
   subprocess. This is severe but does not unwind into cancellation.
2. **Whole-host retention:** deliberately retain the entire ownership closure
   above and continue only if no object in it can be implicitly dropped by
   the outer App teardown. Test that no destructor or Future cancellation
   runs.

A Rust panic is not equivalent to fail-stop: it unwinds unless the build
aborts, and unwinding may continue dropping the App and task. “Log and leak
some state” is also insufficient. Forced cancellation remains forbidden.

This decision belongs before Phase 1B because Phase 1B explicitly reviews
shutdown/cancellation in each lifecycle state and tears down a real App.

## 4. Reproducible Cargo resolution

**Verdict: supported, with a broader qualification.**

V4 Phase 0 says to pin Rust, C++, Python, Greenlet, Bevy, the source revision,
OS, and Carbon I/O revision, then requires reproducible baseline results (v4
lines 1053–1085). The current repository cannot enforce the Cargo portion of
that statement:

- `bevy_defer/Cargo.toml` uses ordinary version requirements such as
  `async-executor = "1.10.0"` and `bevy = "0.19.0"` (lines 39–54).
- Cargo interprets those as compatible ranges, not exact versions. For
  example, `1.10.0` permits later `1.x` releases, while `0.19.0` permits later
  `0.19.x` releases.
- No `Cargo.lock` is tracked in the workspace.
- `bevy_defer/.gitignore` explicitly ignores `Cargo.lock` (line 8).
- V4 says every experimental file other than the workspace-member edit should
  live under `bevy_defer/carbon_compat/` (v4 lines 90–94), while a workspace
  lock belongs at `bevy_defer/Cargo.lock`.
- `cargo metadata` and `cargo tree` report the graph resolved for one run;
  they do not constrain a clean checkout's future resolution.

Cargo's official documentation says the manifest contains version
requirements while the lock file records exact resolution; see
[Cargo.toml vs Cargo.lock](https://doc.rust-lang.org/cargo/guide/cargo-toml-vs-cargo-lock.html).
Cargo also documents that `--locked` fails if the lock is missing or would
change; see
[`cargo build --locked`](https://doc.rust-lang.org/cargo/commands/cargo-build.html#manifest-options).

### Required correction

V4.1 should explicitly permit and require:

```text
bevy_defer/Cargo.lock                    tracked workspace input
cargo generate-lockfile                 intentional lock creation/update
cargo metadata --locked                 dependency evidence
cargo tree --locked                     selected-source evidence
cargo build/test ... --locked            every compatibility gate
```

Because the ignore entry already exists and lines may not be removed, the
amendment must also select how the new lock becomes tracked: force-add the
file, or authorize one additive `!Cargo.lock` exception after the existing
ignore rule. It must add `bevy_defer/Cargo.lock` as an explicit exception to
the “all other files below `carbon_compat`” minimum-change rule.

The tracked lock is necessary for the Cargo graph, but it is not sufficient
for every item Phase 0 calls “pinned.” Rust toolchain selection, Python and
Greenlet build/wheel hashes, C++ compiler/toolchain, and the initial platform
also need versioned enforcement or a content-addressed environment recipe.
Recording their versions in a report is evidence of one run, not complete
reproducibility.

This gap does not make a disposable local Phase 1A experiment meaningless.
It does mean Phase 0 cannot honestly satisfy its reproducibility exit and a
Phase 1B safety result cannot be treated as repeatable until the lock/environment
policy exists.

## 5. Standalone versus embedded build selection

**Verdict: supported; fix before Phase 1B.**

V4 correctly says the package has two mutually exclusive deployment modes
(lines 20–34) and that the standalone extension must not be loaded into the
embedded process (lines 190–212). Its file map only promises “artifact
features” in the future package manifest (line 1430).

It does not specify:

- `[lib]` crate types;
- feature names or default features;
- whether exactly one mode must be selected;
- whether both `rlib` and `cdylib` are compiled while packaging chooses one;
- the exact Cargo commands for each artifact;
- how tests avoid accidentally enabling both modes; or
- how feature unification is detected.

This is material because the Phase 1B singleton proof depends on the
relationship between the library linked into the executable and the extension
artifact that must not enter the process.

The submitted feature sketch is a valid candidate:

```toml
[features]
default = []
standalone = []
embedded = []
```

with a compile-time rejection when both are enabled. Cargo's official feature
documentation confirms that dependency features are unified by union and
that a `compile_error!` guard is an accepted fallback for rare mutually
incompatible features; see
[Cargo feature unification](https://doc.rust-lang.org/cargo/reference/features.html#feature-unification)
and
[mutually exclusive features](https://doc.rust-lang.org/cargo/reference/features.html#mutually-exclusive-features).

Two qualifications matter:

1. Cargo recommends additive features. Mutually exclusive features make
   `--all-features` fail by design and require every dependency path to avoid
   enabling both. That may be desirable here, but it must be intentional.
2. Features select compiled code; they do not by themselves state which crate
   types are emitted or which artifact is packaged/loaded.

V4.1 must therefore choose one complete rule. For example:

```text
standalone build:
    cargo build -p carbon_compat --no-default-features \
        --features standalone --locked
    package only the _scheduler extension

embedded build/test:
    cargo test -p carbon_compat --no-default-features \
        --features embedded --locked
    link only the rlib into the executable
    verify _scheduler origin == built-in

both features:
    compile error

neither feature:
    either compile error, or an explicitly defined shared/test-only core mode
```

It is also valid to compile both crate types from one feature-neutral package
and make deployment the sole selector. If that option is chosen, the roadmap
must name the packaging commands and prove that the forbidden extension is
absent from embedded module search/load paths. Leaving the choice implicit is
not sufficient for Phase 1B.

## 6. Greenlet/Future poll-frame section

**Verdict: supported as an implementation-ready experiment contract.**

This part of the critique is accurate. V4 explicitly brings

```text
poll(self: Pin<&mut CarbonDriver>, cx: &mut Context<'_>)
```

inside the Greenlet safety boundary and requires that:

- reentrant Python cannot access the suspended driver borrow;
- no `Context`-derived reference crosses the switch;
- only a cloned Waker enters stable storage;
- nested Carbon entry cannot repoll the Future/executor;
- Greenlet returns to the same native switch invocation before that poll
  activation returns;
- no continuation can resume into an already-returned poll frame; and
- App, World, Task, and Future outlive the suspended switch.

V4 also defines a meaningful falsifier: if a returnable continuation must
outlive one poll activation, the selected architecture fails rather than
falling back to untracked raw pointers.

These statements do not prove the future code sound. Tests alone cannot prove
all aliasing or native stack-switch properties. They do define the right
unsafe proof obligations and a sufficiently narrow Phase 1A experiment.

No additional roadmap correction is needed in this section before Phase 1A.

## 7. Normal driver lifecycle

**Verdict: mostly supported.**

For ordinary operation, v4 is implementation-level enough:

- lifecycle states and allowed transitions are named;
- nested calls remain inside `ExecutingSegment`;
- shutdown during execution is deferred to a safe boundary;
- `Pending` is restricted to a point with no suspended returnable
  continuation;
- `Ready` follows cleanup;
- the host retains the non-detached task; and
- normal shutdown reaches `Dead` before releasing it.

The remaining holes are not reasons to redesign the state machine. They are:

1. abnormal live-host `Drop`, discussed above; and
2. the exact relationship between driver `Dead`, release of Python-owned
   edges, `Py_FinalizeEx`, and App destruction.

Once those are selected, the lifecycle is adequate for Phase 1B.

## 8. GIL-gated logical state and wake split

**Verdict: mostly supported.**

V4 now chooses an implementable Rust safety shape:

```text
process-visible logical state:
    GilRuntimeCell<RefCell<LogicalRuntime>>

owner-only non-Send state:
    App/World, driver Task, Greenlet, LocalExecutor relationship

foreign wake state:
    Arc<WakeState> with atomics and Waker mutex
```

It requires a held-GIL token for every logical access, releases `RefCell`
borrows before callback/decref/Greenlet entry, prevents owner-only pointers
from entering the wake cell, and commits logical queue state before wake.
Those are the central Rust safety invariants missing from v3.

The unresolved issue is topology rather than synchronization machinery. The
design has a way to wake “another manager,” but embedded mode does not say how
that manager acquired an owner host/driver. Selecting the support matrix in
Section 2 closes that gap without discarding the GIL/wake design.

## 9. Phase readiness

### Phase 0

**GO to begin; not yet eligible to pass its exit gate.**

Source/toolchain discovery, baseline tests, public-surface inventory, sentinel
probes, and the executable scope guard can all begin. The tracked lock and
non-Cargo environment-pin policy must be decided before claiming the results
are reproducible.

### Phase 1A

**GO, provided the authorization says “Phase 1A only, then stop.”**

The headless experiment does not depend on:

- the embedded App/plugin bootstrap order;
- foreign embedded manager topology; or
- a production multi-mode package.

It has a precise technical question:

```text
owned headless App
  -> CoreAsyncPlugin resources
  -> retained CarbonDriver Task
  -> run_before_async_executor
  -> run_async_executor
  -> one Greenlet/Python enter-yield-resume cycle
  -> return through the same poll activation
  -> normal shutdown to Dead
```

The dependency graph should still be captured, and a local lock should not be
silently regenerated between runs. But failure to have the final tracked-lock
policy today does not erase the learning value of this explicitly disposable
probe.

Phase 1A may not mark Phase 1B, the full embedded topology, or Phase 2 green.

### Phase 1B

**NO-GO as written.**

Before it starts, v4.1 must select:

- bootstrap/plugin/CPython initialization order;
- reverse shutdown/finalization order;
- exact standalone/embedded build commands and artifact selection;
- abnormal live-host Drop behavior; and
- the reproducible Cargo graph used by the proof.

### Phase 2

**NO-GO for automatic continuation.**

Phase 2's Carbon semantics are detailed enough, including the
`useNestedTasklets` correction. It must remain behind a successful corrected
Phase 1B, because tasklet/manager state would otherwise be built on an
unproven embedded runtime instance and lifecycle.

### Phase 3 and later

**NO-GO until the embedded/standalone manager-thread matrix is selected.**

The cross-thread state/wake mechanism is plausible, but the owner manager and
host topology must exist before the mechanism can be implemented or tested.

## 10. Minimal v4.1 amendment

The submitted critique is right that another 1,500-line rewrite is
unnecessary. Five correction topics are enough if the first and third are
made complete:

1. **Embedded lifecycle:** define App/bootstrap/plugin/inittab/CPython/import
   order and the inverse driver/Python/App teardown order.
2. **Thread support matrix:** define standalone multi-thread behavior and
   embedded single- or multi-owner behavior, including where every manager's
   driver lives.
3. **Abnormal Drop:** choose fail-stop abort or a proven whole-host retention
   policy; do not leave “fail or retain” to implementation.
4. **Reproducibility:** explicitly track `bevy_defer/Cargo.lock`, use
   `--locked`, permit the path/minimum-change exception, and pin non-Cargo
   toolchain inputs separately.
5. **Artifact selection:** define crate types, features/defaults, exact build
   commands, forbidden combinations, and packaging/module-origin checks.

The claim that these five topics are “all” that remain is therefore **mostly
supported**, not literally supported as originally worded. The proposed list
did not mention `Py_FinalizeEx` ordering, and its leak recommendation did not
name the complete executor ownership closure. Both fit naturally inside the
existing lifecycle/drop topics; neither requires a sixth architectural
redesign.

## Positive claims retained from v4

The audit found no reason to reopen the following v4 decisions:

- embedded `_scheduler` is a built-in module sharing the one linked runtime;
- ordinary external embedded Python does not synchronously reach into an
  application-owned `World`;
- the compatibility plugin, not `CoreAsyncPlugin`, owns one executor run;
- Carbon tasklets remain ordered by the Carbon compatibility queue, not by
  async-executor;
- running tasklets may remain linked in the runnable chain;
- tasklet state remains orthogonal rather than one clean enum;
- callback/current/switch-count and send/receive prefix ordering are explicit;
- channel control moves with kill/throw/close/teardown;
- native layout is produced through the unchanged C++ header;
- low-level `pyo3-ffi` is selected for exact CPython ownership/GC behavior;
- `useNestedTasklets` and both run branches are in Phase 2;
- original Scheduler and Carbon I/O suites remain unchanged gates; and
- experimental and production Definitions of Done remain separate.

## Final classification

The submitted high-level verdict is correct:

> **V4 has crossed the threshold for a useful Phase 1A code experiment, but
> not the threshold for unrestricted sequential implementation.**

The most accurate immediate authorization is:

```text
AUTHORIZED
    begin Phase 0
    implement Phase 1A
    stop after its evidence report

NOT AUTHORIZED
    mark Phase 0 reproducibility complete without enforceable pins
    begin Phase 1B from current text
    auto-continue into Phase 2+
```

After the compact five-topic v4.1 amendment above, Phase 1B can be attempted.
Only a green one-process embedded proof should unlock Phase 2, and only an
explicit manager/host thread matrix should unlock Phase 3.

No roadmap or implementation file was modified as part of this
investigation; this report is the sole new file.
