# Roadmap v3 Architecture Claim Audit

- Audit date: 2026-08-16
- Roadmap reviewed: `bevy_defer/migration-roadmap/v3.md`
- Published roadmap commit: `f2f202b0a48069432392f3e2dfd357cdaf5d665c`
- Roadmap blob: `594842bcc2d973380deb3bbd7fedc83113b02bc6`
- Source baseline reviewed: `e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e`
- Repository: `QuasarRay/carbon-scheduler-lab`
- Scope: investigation only; this report does not amend v3 and does not authorize or implement code

## Executive verdict

The critique's central conclusion is **supported**:

> V3 is not ready to authorize the stated embedded implementation or to advance into Phase 2 as written.

V3's Carbon semantic model is materially sound. The newly raised defects are mostly in a different layer: binary identity, initial entry into an embedded host, executor installation, and lifetime/synchronization around a Greenlet-suspended Rust `Future::poll` call. Those are real architectural gaps, not cosmetic omissions.

There is one important qualification. A narrowly defined, disposable **headless-only Greenlet/Bevy Defer probe** can still be useful before every embedded decision is finalized. It must not be allowed to satisfy the current Phase-1 exit, because it cannot prove that an embedded Rust plugin and an imported Python module share one compatibility runtime or that embedded `scheduler.run()` has a legal synchronous entry path.

The numerical readiness scores in the submitted critique are opinions, not independently falsifiable measurements. This audit therefore accepts or rejects the underlying technical claims, not the exact scores.

| # | Claim | Verdict | Consequence |
|---:|---|---|---|
| 1 | The Rust plugin and `_scheduler` can become two runtime instances | **Supported** | P0 topology decision before Phase 1 may pass |
| 2 | Embedded synchronous `scheduler.run()` has no defined initial entry | **Supported** | P0 host contract before Phase 1 may pass |
| 3 | `CoreAsyncPlugin` does not poll executors | **Supported; source-definite** | P0 executor-run policy for embedded mode |
| 4 | The Greenlet safety proof omits the suspended Rust poll frame | **Mostly supported** | Strengthen the Phase-1 soundness proof |
| 5 | Driver task ownership, wake state, and shutdown are underspecified | **Supported** | Specify before treating the vertical slice as reusable runtime code |
| 6 | GIL serialization is not yet a concrete Rust sharing model | **Supported with qualification** | Choose/prove the model before cross-thread Phase 3 |
| 7 | `useNestedTasklets` is a Phase-2 dependency | **Supported; source-definite** | Move the flag, both branches, and accessors into Phase 2 |
| 8 | The in-tree Phase-0 CI guard cannot be a GitHub workflow | **Supported with qualification** | Define an executable guard plus an external invoker, or allow a root workflow |
| 9 | The CPython/Rust FFI strategy needs an explicit early decision | **Supported as a gate** | Decide before Phase 2; preferably as a Phase-1 exit |
| 10 | A one-process embedded integration test is the missing discriminator | **Supported** | Make it a Phase-1 acceptance test after topology is selected |

## Evidence boundary

This is a source and architecture audit. No `carbon_compat` artifact exists to execute, so claims about its prospective runtime topology are explicit inferences from the proposed build shape and platform linkage rules. The source-definite claims were checked directly in the pinned repository. No Scheduler, Bevy Defer, or Carbon I/O test suite was run for this report because the requested claims concern a not-yet-implemented architecture.

## 1. Duplicate `carbon_compat` runtime instances

**Verdict: supported, with the word “can” being essential.**

V3 explicitly makes one package both a Rust library and a Python/native extension ([v3 lines 167–176](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L167-L176)). It never selects a crate type, a final link topology, a built-in-module arrangement, a shared state provider, or a C ABI between independently loaded artifacts. “One Cargo package” is a source/build organization decision; it is not a process-wide singleton guarantee.

The natural embedded build has two final artifacts:

```text
Rust/Bevy executable
  <- statically incorporates carbon_compat from an rlib

CPython import
  <- dynamically loads _scheduler from a cdylib/shared object
```

Rust's linkage reference defines an `rlib` as an intermediate static Rust library used to produce statically linked executables and a `cdylib` as a separate dynamic system library loaded from another language. It guarantees uniqueness within one artifact's dependency graph; it does not merge a copy already incorporated in an executable with another copy later introduced by `dlopen`. Therefore, ordinary Rust statics, thread locals, registries, and allocator/runtime-adjacent state in those two final artifacts must be treated as distinct unless the design deliberately supplies one shared instance. This is a high-confidence linkage inference, not an observed `carbon_compat` failure. See the [Rust Reference: Linkage](https://doc.rust-lang.org/reference/linkage.html).

V3 also prohibits relying on symbol interposition ([v3 line 74](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L74)), so accidental platform symbol coalescing cannot be its answer.

The proposed built-in-module solution is viable **when the embedded executable controls CPython initialization**: link `carbon_compat` once, register `PyInit__scheduler` with `PyImport_AppendInittab()` before Python initialization, and import that built-in module. CPython documents that mechanism directly in [Extending Embedded Python](https://docs.python.org/3/extending/extending.html#extending-embedded-python). The unchanged wrapper imports top-level `_scheduler` ([`python/scheduler/__init__.py` lines 1–12](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/python/scheduler/__init__.py#L1-L12)), so the baseline import name is compatible with such a design.

That proposal is conditional, not universally sufficient:

- `PyImport_AppendInittab()` must happen before interpreter initialization;
- an application attaching to an already initialized interpreter needs another mechanism; and
- standalone Python still needs the dynamically loaded extension path.

An explicit stable C ABI to one shared host registry, or another deliberately single shared-library topology, can also work. V3 need not be forced to use the built-in-module option, but it must select and test one single-instance mechanism.

The existing Phase-1 condition that “the same driver runs in both minimal headless and existing-App tests” ([v3 lines 679–685](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L679-L685)) is not enough. Two independent tests can each create a valid driver while never exercising both linkage paths in one process.

## 2. Missing synchronous initial entry in embedded mode

**Verdict: supported.**

V3 defines the standalone path precisely: the compatibility layer owns a minimal `App`/`World` and synchronously pumps until the requested Carbon API boundary completes ([v3 lines 189–201](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L189-L201)). It does not define the equivalent first entry for an application-owned `App`.

The embedded section says the plugin registers state, ordering, affinity, and a wake path while leaving `scheduler.run()` available ([v3 lines 203–216](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L203-L216)). The reentrancy section then asserts that an outer call submits a request and pumps the driver ([v3 lines 218–230](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L218-L230)). It never identifies who owns the mutable `App`/`World` at that instant or what legal API performs the pump.

The current Bevy Defer API makes that omission material:

- `run_async_executor` requires `&mut World` and performs the actual `try_tick()` loop ([`executor.rs` lines 77–98](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/bevy_defer/src/executor.rs#L77-L98));
- `AsyncExecutor` contains `Rc<LocalExecutor>` behind a crate-private field; and
- its public compatibility-facing operations spawn work but do not expose `try_tick()` ([`executor.rs` lines 46–75](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/bevy_defer/src/executor.rs#L46-L75)).

Queueing a request and waiting is not by itself a synchronous solution. If arbitrary Python is executing on the owner thread outside the Bevy run and blocks waiting for the next App tick, it can prevent that same owner thread from ticking. Retaining an arbitrary `&mut World`, recursively calling `App::update()`, or reaching through the private executor field would each introduce a different unsoundness or compatibility problem.

The critique's proposed contract—embedded Python begins through a Carbon host/driver entry, so later scheduler calls are nested—is coherent and deserves evaluation. It is not the only possible answer. A separately specified owner-thread synchronous host callback could also work. The required pre-implementation decision is the supported contract:

1. embedded Python may start only through the driver; or
2. arbitrary external Python may call synchronous Carbon APIs, in which case v3 must define a legal owner-thread pump and its borrow/reentrancy rules.

Without that choice, the embedded portion is not implementable from the text.

## 3. `CoreAsyncPlugin` does not run the executor

**Verdict: supported and source-definite.**

The Bevy Defer source describes `CoreAsyncPlugin` as the plugin “that does not run its executors” ([`lib.rs` lines 96–103](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/bevy_defer/src/lib.rs#L96-L103)). Its build method initializes resources and supporting schedules/systems, but does not install `run_async_executor` ([`lib.rs` lines 103–124](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/bevy_defer/src/lib.rs#L103-L124)).

`AsyncPlugin` owns executor-run configuration. `empty()` installs no run, `default_settings()` chooses `Update`, and `run_in`/`run_in_set` add schedules ([`lib.rs` lines 139–195](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/bevy_defer/src/lib.rs#L139-L195)). Its `Plugin::build` is what adds `run_async_executor` to those schedules ([`lib.rs` lines 197–223](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/bevy_defer/src/lib.rs#L197-L223)).

Consequently, “require or install `CoreAsyncPlugin`” plus a spawned driver can leave the driver forever unpolled. The Phase-1 headless test can avoid that by calling the public runner directly, but doing so does not close the embedded hole.

V3 must assign responsibility for installing or validating an executor run, choose the schedule/set, specify ordering, and prevent accidental duplicate runners when an application already configured `AsyncPlugin`. The critique's options A–C are valid design candidates; this report does not select among them.

## 4. Greenlet suspension includes the Rust `Future::poll` frame

**Verdict: mostly supported.**

V3 already contains strong rules: stable heap storage, no reentrant compatibility borrow or lock across a switch, and reentry through stable handles rather than aliases to the suspended Rust stack ([v3 lines 218–230](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L218-L230), [v3 lines 497–510](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L497-L510)). The critique is therefore identifying an incomplete proof boundary, not an absence of safety awareness.

Greenlet explicitly supports switching with native functions on the call stack and warns that native frames must be reentrant-safe. Its conceptual model is a stack of suspended frames that resumes at the prior switch point. See [Greenlet concepts](https://greenlet.readthedocs.io/en/stable/greenlet.html) and [Greenlet native-function caveats](https://greenlet.readthedocs.io/en/stable/caveats.html#native-functions-should-be-re-entrant).

A Rust Future is entered through:

```rust
fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output>
```

as documented by [`Future::poll`](https://doc.rust-lang.org/std/future/trait.Future.html). If `PyGreenlet_Switch` occurs inside this call, that native Rust frame—including its pinned receiver and context—is suspended until control returns.

The mere existence of `Pin<&mut CarbonDriver>` and `Context` is **not automatically unsound**. The actual obligations are:

- reentrant code cannot alias or mutate memory covered by a still-live exclusive driver borrow;
- the driver cannot be polled recursively;
- no `cx`-derived borrowed reference is retained for reentrant use;
- pinned driver storage remains valid; and
- teardown/cancellation cannot destroy a continuation that a Greenlet can still resume into.

The critique's suggested “small driver handle plus stable heap state” is a plausible way to meet those obligations, but it remains a proposed design, not a proven unique solution. Phase 1 should explicitly name the poll receiver, executor task, and native return continuation in its safety argument and tests.

## 5. Driver task ownership, wake state, and shutdown

**Verdict: supported.**

V3 says one `CarbonDriver` Future represents a scheduling domain and mentions host wakes and generation validation, but it does not say which object owns the spawned task, whether it is detached, when it is cancelled, or how stale wakeups are rejected during teardown.

That choice is observable in the current API:

- `AsyncExecutor::spawn_any` detaches the task;
- `AsyncExecutor::spawn_task` returns a `Task<T>` handle ([`executor.rs` lines 51–60](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/bevy_defer/src/executor.rs#L51-L60)); and
- Bevy Defer's own documentation states that dropping a returned task handle causes the associated Future to be dropped by the executor ([`spawn.rs` lines 61–77](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/bevy_defer/src/spawn.rs#L61-L77)). Upstream `async-task` likewise documents cancellation on `Task` drop and explicit `detach()` for background survival ([`async_task::Task`](https://docs.rs/async-task/latest/async_task/struct.Task.html)).

For a driver that owns or can resume a Greenlet continuation, casual detachment is not an acceptable unspecified default. At minimum the architecture needs named ownership, request/idle/executing/shutdown/dead transitions, a generation or equivalent stale-wake barrier, and a rule for deterministic task retirement after every resumable Greenlet has returned to a safe boundary. The exact enum names in the critique are optional; the lifecycle invariants are not.

## 6. Cross-thread Rust sharing model

**Verdict: supported with qualification.**

V3 correctly separates GIL-serialized logical state from owner-only `Rc<LocalExecutor>`, `App`/`World`, and Greenlet state ([v3 lines 234–249](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L234-L249)). That is the right semantic boundary.

It is not yet a concrete Rust representation. Rust requires a shared immutable static's type to implement `Sync`, while `Rc` and `RefCell` deliberately are not thread-safe; unsafe `Send`/`Sync` assertions become proof obligations. See the [Rust Reference on static items](https://doc.rust-lang.org/reference/items/static-items.html#statics--sync) and the [Rustonomicon on `Send` and `Sync`](https://doc.rust-lang.org/nomicon/send-and-sync.html).

The critique is right that “the GIL serializes access” does not by itself make an arbitrary Rust global compile or make an unsafe wrapper sound. V3 must eventually choose one of these classes of implementation:

- an ordinary thread-safe shared container such as `Arc` plus a synchronization primitive;
- a purpose-built GIL-token-guarded container with a documented `unsafe` boundary; or
- another representation that proves the same exclusivity and lifetime properties.

`Arc<Mutex<LogicalManager>>` is an example, not a required answer. A lock must not remain held across callbacks, finalizer-capable decrefs, or Greenlet switches, consistent with v3. Conversely, a GIL-only wrapper must prove every access holds the GIL and must remain outside the free-threaded-Python target. The owner-only host can remain thread-local/non-`Send`; only the committed logical state and wake primitive need safe foreign-thread access.

This choice need not block a strictly single-thread Phase-1 probe. It must be made and tested before Phase 3 claims cross-thread channel commitment.

## 7. `useNestedTasklets` is required in Phase 2

**Verdict: supported and source-definite.**

The baseline declares `ScheduleManager::s_useNestedTasklets` as process-global state ([`ScheduleManager.h` lines 113–123](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/src/ScheduleManager.h#L113-L123)). `Tasklet::Run()` immediately branches on it and implements materially different scheduling behavior in the true and false branches ([`Tasklet.cpp` lines 503–559](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/src/Tasklet.cpp#L503-L559)). The module exports public setters/getters ([`SchedulerModule.cpp` lines 408–427](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/src/SchedulerModule.cpp#L408-L427)).

V3 Phase 2 moves tasklet `run()` and the run/reschedule machinery ([v3 lines 689–706](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L689-L706)), while Phase 4 defers completion of module-level exports ([v3 lines 764–778](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L764-L778)). As written, that postpones a direct dependency of the migrated operation.

Phase 2 must include the process-global flag, its two public accessors, both `Tasklet::Run()` branches, and their queue/reschedule tests. The only alternative would be to explicitly narrow Phase 2 to the default-true subset and weaken its exit claim; v3 does neither.

## 8. Phase-0 CI guard under the path restriction

**Verdict: supported specifically for GitHub Actions; qualified for generic external CI.**

V3 requires every write to remain below `bevy_defer/` and asks Phase 0 to create an add-only/path-scope CI guard ([v3 lines 30–74](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L30-L74), [v3 lines 640–659](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L640-L659)). The repository has workflows under `bevy_defer/.github/workflows/`, but no repository-root `.github/workflows/` directory at the pinned baseline.

GitHub searches only the `.github/workflows` directory at the **repository root** when triggering workflows. A nested `bevy_defer/.github/workflows/rust.yml` is not a workflow for this monorepo. See [GitHub's workflow discovery description](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows#workflow-triggers).

An executable scope-check script or test can be added below `bevy_defer/`. It becomes a CI guard only if some already-authorized external CI definition invokes it. This audit found no root GitHub workflow that does so, and the current path rule prevents adding one. Therefore the acceptance item must either:

- say “executable scope guard” and identify how existing external CI invokes it; or
- permit one repository-root workflow/configuration exception.

This is a Phase-0 process inconsistency, not a scheduler architecture blocker.

## 9. Explicit CPython/Rust FFI strategy

**Verdict: supported as an early gate.**

V3 chooses a small C++ Greenlet/capsule shim and panic-contained `extern "C"` Rust entrypoints ([v3 lines 285–313](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L285-L313), [v3 lines 484–510](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L484-L510)). It does not choose how Rust implements CPython module/type/GC/GIL operations: high-level PyO3, low-level `pyo3-ffi`, raw CPython bindings, or a broader C++ bridge.

That decision affects:

- module initialization and the single-instance built-in-module option;
- type object construction and subclass flags;
- `tp_traverse`, `tp_clear`, weakrefs, and deallocation;
- owned versus borrowed Python references;
- GIL proof tokens and static/shared state; and
- panic and exception translation.

A minimal Phase-1 experiment could use a deliberately tiny raw/C++ bridge without settling the entire wrapper implementation. Phase 2, which introduces Python wrappers and GC edges, must not begin until the FFI stack and unsafe-boundary policy are selected. Making that a Phase-1 exit decision is therefore well founded.

## 10. One-process embedded topology test

**Verdict: supported.**

The suggested one-executable test closes the most important false-green path. It must exercise in one OS process:

1. the Rust-facing `CarbonCompatPlugin`;
2. a real application-owned Bevy `App`;
3. embedded CPython importing the unchanged `scheduler` package and `_scheduler` module;
4. the selected initial Python-entry contract;
5. the exact owner OS thread;
6. the exact driver task installed in that App's `AsyncExecutor`;
7. nested scheduler reentry without a recursive executor tick; and
8. deterministic shutdown after every Greenlet has returned to a safe continuation boundary.

It should expose a test-only runtime identity/generation token through both Rust and Python paths and assert equality. It should also verify the loaded module mechanism/origin appropriate to the selected topology; two independently passing host tests are insufficient evidence of singleton identity.

Two qualifications apply:

- The exact `scheduler.run()` assertion must follow the chosen embedded-entry contract. If all Python begins inside the driver, `scheduler.run()` is tested as nested synchronous behavior, not as an unsupported outside-the-App pump.
- One happy-path teardown test cannot by itself prove the absence of all dangling continuations. The ownership invariant, adversarial teardown cases, and later sanitizer coverage remain necessary.

Despite those qualifications, this is the correct mandatory Phase-1 integration discriminator.

## Positive Carbon-semantic claims in the critique

The critique also says v3 got several difficult baseline semantics right. Those statements were independently checked and are supported.

### Active tasklets remain linked while executing — supported

`ScheduleManager::Run()` selects `baseTasklet->Next()`, calls `currentTasklet->SwitchTo()`, and removes it only after that call returns ([`ScheduleManager.cpp` lines 464–548](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/src/ScheduleManager.cpp#L464-L548)). V3's active-linked state and queue law match that behavior ([v3 lines 350–370](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L350-L370)).

### Callback and `times_switched_to` ordering — supported

`Tasklet::SwitchTo()` increments `m_timesSwitchedTo` before calling `SetCurrentTasklet()` ([`Tasklet.cpp` lines 352–401](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/src/Tasklet.cpp#L352-L401)). `SetCurrentTasklet()` runs the switch hook and callbacks before assigning `m_currentTasklet` ([`ScheduleManager.cpp` lines 141–150](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/src/ScheduleManager.cpp#L141-L150)). V3 records the same observable order ([v3 lines 393–407](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L393-L407)).

### Send/receive callback asymmetry — supported

Send invokes the channel callback before setting transfer-in-progress ([`Channel.cpp` lines 34–44](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/src/Channel.cpp#L34-L44)). Receive sets transfer-in-progress before invoking the callback ([`Channel.cpp` lines 147–165](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/src/Channel.cpp#L147-L165)). V3's separate prefixes are correct ([v3 lines 409–430](https://github.com/QuasarRay/carbon-scheduler-lab/blob/f2f202b0a48069432392f3e2dfd357cdaf5d665c/bevy_defer/migration-roadmap/v3.md#L409-L430)).

### Orthogonal tasklet state — supported

The baseline stores Greenlet, scheduled, alive, queue links, blocked links/direction, paused, first-run, reschedule, removal, parent, exception, transfer, and other state independently ([`Tasklet.h` lines 246–315](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/src/Tasklet.h#L246-L315)). V3 is correct not to collapse these into one mutually exclusive enum.

### Native capsule shape — supported

`SchedulerCAPI` is C++-only, uses typed function-pointer aliases, stores type pointers, and declares `TaskletExit` as `PyObject **` ([`Scheduler.h` lines 25–133](https://github.com/QuasarRay/carbon-scheduler-lab/blob/e736c2b8d20e8f6ff5409aa2f2b3f81781e8e58e/include/Scheduler.h#L25-L133)). V3's unchanged-header C++ shim is a sound way to avoid manually guessing that layout.

These confirmations explain why v3 should be amended rather than discarded: its compatibility model has addressed the major Carbon-specific errors, while the remaining blockers sit at the host/binary boundary.

## Readiness classification

| Authorization target | Verdict |
|---|---|
| Implement v3 exactly as written and accept current Phase 1 | **NO-GO** |
| Begin Phase 2 scheduler/tasklet migration | **NO-GO** |
| Begin Phase 3 cross-thread channels | **NO-GO** |
| Run a disposable, headless-only Greenlet/Bevy Defer learning probe that cannot mark Phase 1 complete | **GO, narrowly scoped** |
| Amend Phase 1 around topology, entry, executor-run ownership, and poll/driver lifetime | **GO** |

The current Phase 1 can produce a false green because its headless and existing-App tests may exercise separate final artifacts or may invoke `run_async_executor` directly in test-only code without proving the real embedded import/entry path. Phase 2 must remain blocked until that is repaired.

## Minimum decisions needed before Phase 1 can pass

These are findings from the audit, not edits made to v3:

1. Select and document the embedded single-instance binary topology.
2. Select the embedded initial Python-entry/synchronous-run contract.
3. Assign executor-run installation, schedule/set selection, ordering, and duplicate-run prevention.
4. Extend the Greenlet proof to the suspended `Pin<&mut CarbonDriver>`, `Context`, executor task, and return continuation.
5. Define driver task ownership, wake/generation state, cancellation, and shutdown.
6. Add the one-process Rust-plugin/embedded-CPython identity and entry test.

Before Phase 2, also select the CPython/Rust FFI strategy and include `useNestedTasklets`. Before Phase 3, choose and prove the concrete cross-thread Rust state/wake representation. Phase 0 must describe a scope guard that can actually be invoked under the repository path restriction.

## Final classification

The submitted conclusion is substantially right:

> **V3 is Carbon-semantically strong but one host/linkage revision short of implementation-ready.**

It is not necessary to redesign the Carbon queue, tasklet axes, callback order, channel entry order, or native table strategy again. It is necessary to close the runtime-instance, embedded-entry, executor-run, and suspended-driver-lifetime gaps before a Phase-1 pass can authorize broader code-level work.

No roadmap or implementation file was modified as part of this investigation.
