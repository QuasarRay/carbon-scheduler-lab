# Investigation Report: Claims About Migration Roadmap v2

- Version: report-v2
- Status: independent source and roadmap audit; no implementation changes authorized or made
- Investigation date: 2026-08-16
- Roadmap reviewed: [`migration-roadmap/v2.md` at `eb9cd245290b9847a777a36fe93d353e2c5ffca6`](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md)
- Scheduler/Bevy Defer/async-executor source baseline: [`73629285578622cadd6994f0504e923262017f1e`](https://github.com/QuasarRay/carbon-scheduler/tree/73629285578622cadd6994f0504e923262017f1e)
- Downstream Carbon I/O source reviewed: [`carbonengine/io` at `5c4c669f6ebbda56996f1326315222dae9bf281e`](https://github.com/carbonengine/io/tree/5c4c669f6ebbda56996f1326315222dae9bf281e)

## 1. Scope and method

The ten submitted claims were treated as hypotheses, not as change instructions. Each was checked against:

- the exact wording and phase gates in roadmap v2;
- the pinned Carbon Scheduler implementation;
- the checked-in Bevy Defer and async-executor manifests and source;
- CPython reference/GC rules where an ownership claim depended on them; and
- the public Carbon I/O downstream repository for the integration-test claim.

This report adds no tests and does not run a sanitizer build. Findings marked **definite** follow directly from control flow or CPython's documented ownership contract. Findings marked **candidate** need a focused runtime/refcount probe to determine reachability or impact. No roadmap, source, test, manifest, or configuration file was changed.

## 2. Executive result

The factual core of all ten claims is supported. Claims 1, 2, 5, and 9 include evaluative language such as “grossly,” “meaningfully,” “cleanly,” or “more valuable”; their underlying facts are confirmed, while the evaluative conclusion is stated with the relevant scope qualification.

| # | Verdict | Confidence | Short result |
|---:|---|---|---|
| 1 | **Supported for an experimental-backend objective** | High | V2 makes production-grade contract/oracle work a gate before substantive Rust scheduling work and defines no shorter experiment lane. |
| 2 | **Mostly true; architectural characterization confirmed** | High | `carbon_core` is a bespoke Carbon runtime placed in the Bevy Defer workspace; reuse of Bevy Defer execution machinery is optional and downstream. |
| 3 | **True** | High | Local async-executor selection is mandatory even though v2 gives it no required Carbon responsibility. |
| 4 | **True** | Definite | `Receive()` sets `transfer_in_progress` before the channel callback; v2's ordered receive description omits/reverses that event. |
| 5 | **True as a phase-boundary criticism** | High | Phase 5 operations already execute Phase 7 callable, parent, and exception policy; v2 does not specify the bridge needed to split them. |
| 6 | **True** | High | Channel cleanup and kill/throw control are directly coupled while their ownership moves in separate phases without a defined mixed-state protocol. |
| 7 | **True** | Definite for several omissions | Multiple concrete reference leaks and GC/ownership defects are absent from D01–D18. |
| 8 | **True** | High | The taxonomy and exact-trace rule lack an equivalence class for specified operations with unspecified cross-object iteration order. |
| 9 | **True on the factual omission and integration value** | High | Carbon I/O is not a v2 gate despite directly exercising scheduler pumping and the native channel API. |
| 10 | **True** | High | V2 defines only the eventual migration gate, not a bounded opt-in experimental-PR milestone. |

The evidence supports a v3 revision. The most urgent correctness issue is claim 4; the most consequential planning issues are claims 1, 3, 8, 9, and 10.

## 3. Claim-by-claim findings

### Claim 1 — Phase 0–1 are oversized for an experimental implementation

**Verdict: Supported for the stated experimental objective.**

The workload described in the claim is substantially accurate:

- V2 requires every historical Python and native test to be classified before it can be used as an oracle ([§3.3, lines 198–213](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L198-L213)).
- Phase 0 requires an independent ABI manifest, legacy precompiled probes, decisions for D01–D18, an inventory of every public operation and ABI field, and no unnamed P0 defect ([lines 1026–1047](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1026-L1047)).
- Phase 1 requires a versioned trace schema, a non-observer-effect demonstration, C01–C35 “as applicable,” descriptive Hypothesis state machines, detailed ownership/concurrency observations, and frozen evidence digests ([lines 1049–1069](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1049-L1069)).
- The characterization section is explicitly a “Mandatory characterization backlog,” with 35 scenarios, 33 marked P0 and two marked P1 ([lines 978–1020](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L978-L1020)).
- The first package containing scheduling logic is Phase 3. Phase 2 only establishes packages, linkage, selection, and dependency-graph gates ([lines 1071–1115](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1071-L1115)).
- The final recommendation expressly says not to proceed until the contract and oracle phases are complete ([lines 1585–1591](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1585-L1591)).

There are two wording qualifications. C01–C35 are required only “as applicable,” and the standalone characterization text says Hypothesis state machines **SHOULD** run, although Phase 1 lists them as an action. Those qualifications do not alter the overall ordering: v2 has no route to learn from an opt-in Rust scheduler implementation before completing a large production-equivalence evidence program.

That ordering is defensible for a production cutover whose first promise is strict parity. It is disproportionate when the immediate deliverable is an experimental backend that explicitly makes no production-equivalence claim. The claim is therefore a valid scope criticism, not proof that the individual verification activities are intrinsically unnecessary.

### Claim 2 — V2 describes a bespoke Carbon scheduler more than a migration onto Bevy Defer

**Verdict: Mostly true; the architectural characterization is confirmed.**

V2 selects a separate `carbon_core` crate that owns scheduler state, tasklet axes, deterministic queue order, channels, budgets, identities, metrics, and lifecycle policy. It must have no Bevy dependency and make no CPython or Greenlet call. `carbon_ffi` depends directly on it rather than on the root `bevy_defer` package ([§9.1, lines 649–674](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L649-L674); [§9.4, lines 711–720](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L711-L720)). It also requires a dedicated Carbon queue and prohibits async-executor from deciding Carbon ordering ([§9.5–9.6, lines 722–750](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L722-L750)).

That differs materially from the existing Bevy Defer execution model:

- the root manifest has an unconditional Bevy dependency and a registry async-executor dependency ([`bevy_defer/Cargo.toml`, lines 39–54](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/bevy_defer/Cargo.toml#L39-L54));
- the root plugin initializes Bevy `World`-resident/non-send queues, executors, query caches, reactors, inspectors, signals, and schedules ([`bevy_defer/src/lib.rs`, lines 98–123](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/bevy_defer/src/lib.rs#L98-L123)); and
- its executor is a `LocalExecutor` used inside scoped `World`, `AssetServer`, `QueryQueue`, and `Reactors` contexts ([`bevy_defer/src/executor.rs`, lines 11–98](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/bevy_defer/src/executor.rs#L11-L98)).

Consequently, Carbon's authoritative runtime in v2 is not an adaptation of Bevy Defer's executor semantics. It is a new deterministic Carbon kernel located under the Bevy Defer checkout, with an optional Bevy adapter added later in Phase 10.

The qualification is that “migration to Bevy Defer” can mean repository ownership and future host integration rather than reuse of the existing executor. Under that broader definition, v2 still qualifies: it places the crates in the workspace and plans an optional Bevy plugin. Under the ordinary execution-architecture meaning, the claim is accurate.

### Claim 3 — Local async-executor integration is mandatory without a mandatory role

**Verdict: True.**

The contradiction is explicit:

- Phase 2 requires workspace membership, explicit local source selection, and metadata proof; its exit gate requires the local fork to be selected ([lines 1071–1091](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1071-L1091)).
- The Definition of Done again requires proven local async-executor selection ([lines 1519–1537](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1519-L1537)).
- Yet §9.6 prohibits using async-executor as the Carbon scheduler and says only that it **MAY** provide auxiliary I/O, timers, non-Carbon futures, wake signaling, or a completion primitive ([lines 739–750](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L739-L750)).
- The standalone `carbon_ffi` path bypasses the root package, so it need not inherit the root's async-executor dependency ([lines 659–674](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L659-L674)).

Nothing in v2 assigns the local fork a required Carbon responsibility. Selecting and maintaining it is therefore unrelated mandatory scope unless a separately approved experiment actually uses or modifies it. It may still be valuable for the existing Bevy Defer package or the optional host adapter; that is not a dependency of the experimental Carbon core described by v2.

### Claim 4 — The receive trace orders callback and transfer mutation incorrectly

**Verdict: True, definite.**

The implementation order is unambiguous. `Channel::Receive()` first calls `SetTransferInProgress(true)` on the current tasklet and only then calls `RunChannelCallback()` ([`src/Channel.cpp`, lines 147–157](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Channel.cpp#L147-L157)).

Send is deliberately different: `Channel::Send()` calls the channel callback first and then sets `transfer_in_progress` ([`src/Channel.cpp`, lines 34–43](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Channel.cpp#L34-L43)).

V2's ordered receive account begins with the callback and never records the preceding transfer mutation ([§6.3, lines 445–460](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L445-L460)). The generic channel event list also lists callback before transfer mutation ([§12.3, lines 926–937](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L926-L937)), while §12.5 prohibits normalizing event order.

This is not cosmetic. A reentrant channel callback can inspect the current tasklet and distinguish send from receive. A “lossless” oracle based on v2 would either emit the wrong receive sequence or omit an observable mutation point.

The correct source-level prefix is:

1. receive entry;
2. current tasklet `transfer_in_progress = true`;
3. channel callback, with `will_block` based on counterpart absence at entry;
4. unmatched-path waiter reference/list/balance mutations;
5. trap and closed checks with their respective rollback behavior.

### Claim 5 — Phase 5 cannot cleanly precede Phase 7 without a specified bridge

**Verdict: True as a phase-boundary criticism; separation is possible only with a more explicit adapter.**

Phase 5 says it will move bind/setup distinctions, tasklet metadata decisions, queue operations, `run`, and `switch` ([lines 1139–1160](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1139-L1160)). Phase 7 later moves callable policy, exceptions, kill/throw, and parent behavior ([lines 1187–1207](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1187-L1207)). The implementation does not expose those as independent families:

- `Tasklet::Bind()` performs CPython metadata introspection through `SetCallsiteData()`, branches on `m_dontRaise`, creates a Python `CallableWrapper`, sets its tasklet owner, stores Python args/kwargs, creates the Greenlet when arguments exist, and marks the tasklet alive ([`src/Tasklet.cpp`, lines 1122–1318](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Tasklet.cpp#L1122-L1318)).
- `Tasklet::SwitchImplementation()` pauses the caller, routes through manager `Run(this)`, and may yield through the parent path ([lines 223–289](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Tasklet.cpp#L223-L289)).
- `Tasklet::SwitchTo()` consumes pending exception state before first execution, commits current/parent-sensitive control, calls Greenlet, then examines the resumed current tasklet's exception state and decides liveness from blocked/transfer/paused/reschedule state ([lines 294–452](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Tasklet.cpp#L294-L452)).

Phase 4 does establish a continuation interface containing throw and parent operations, so the ordering is not logically impossible. A split could leave callable construction, Python metadata, parent updates, and exception storage in the legacy facade while Rust makes only selected decisions. V2, however, does not define that mixed-state API, ownership of each decision, the direction of callbacks, or the rollback protocol. Its Phase 5 bridge list names callbacks, counters, and manager ownership, but not these Phase 7 dependencies.

Thus “cannot cleanly precede” is accurate as written. The claim should not be read as proof that the phases must be identical; it establishes that an explicit legacy-policy bridge or a combined phase is required.

### Claim 6 — Phase 6 depends on Phase 7 kill/throw/control semantics

**Verdict: True.**

Phase 6 requires Rust channels to unlink blocked tasklets exactly once on match, kill, throw, clear, close, and teardown ([lines 1162–1185](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1162-L1185)). Phase 7 is where kill, throw, exceptions, and parent fallback move.

The baseline establishes direct two-way coupling:

- `Channel::ClearBlocked()` repeatedly calls `Tasklet::Kill()` on receive and send waiters ([`src/Channel.cpp`, lines 532–545](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Channel.cpp#L532-L545)).
- `Tasklet::Kill()` captures its blocked channel, changes blocked state, installs `TaskletExit`, schedules/runs the tasklet, and on the pending path calls `Channel::UnblockTaskletFromChannel()` ([`src/Tasklet.cpp`, lines 561–635](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Tasklet.cpp#L561-L635)).
- `Tasklet::ThrowException()` installs exception state and, for a blocked tasklet, changes blocked state and invokes `Run()`, with rollback on failure ([`src/Tasklet.cpp`, lines 806–900](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Tasklet.cpp#L806-L900)).
- `Channel::UnblockTaskletFromChannel()` mutates intrusive links, balance, and blocked direction ([`src/Channel.cpp`, lines 330–409](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Channel.cpp#L330-L409)).

A Phase 6 Rust channel cannot independently guarantee exactly-once unlinking for these operations unless Phase 7 control delivery calls into it through a defined protocol, or Phase 6 continues to call the complete legacy control path and mirrors the result. V2 states the exit condition but not that bridge, including who owns rollback if `Run()` or Greenlet transfer fails. The sequencing criticism is therefore substantiated.

### Claim 7 — D01–D18 is incomplete

**Verdict: True. Several omissions are definite from source alone.**

V2 says no listed item may remain hidden under generic “suspicious reference branch” or callback language and requires no unnamed P0 defect at the end of Phase 0 ([defect register, lines 852–877](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L852-L877); [Phase 0 exit, lines 1039–1045](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1039-L1045)). The following source-level issues are not named in D01–D18:

| Audit ID | Source finding | Status | Why it is distinct from D01–D18 |
|---|---|---|---|
| R2-X01 | `RunSchedulerCallback()` discards the return from `PyObject_Call()` without `Py_DECREF` | **Definite leak on a successful callback** | D04/D05 concern callback-slot replacement/ownership, not invocation-result ownership. |
| R2-X02 | `RunChannelCallback()` also discards the successful `PyObject_Call()` result | **Definite leak on a successful callback** | No D-row covers channel callback result ownership. |
| R2-X03 | `TaskletExceptionHandlerGet()` returns the stored pointer without `Py_INCREF` | **Definite new-reference contract violation** | No D-row covers this property getter. |
| R2-X04 | The exception-handler setter stores an owned reference, but `Tasklet::~Tasklet()` never decrefs `m_exceptionHandler` | **Definite retained reference when a handler remains installed** | Not covered by the future Rust-owned-edge GC rule or callback-slot rows. |
| R2-X05 | `TaskletTraverse()` visits only callable, positional args, and context-manager callable; `Tasklet::Clear()` clears only callable/args/kwargs | **Definite incomplete traverse/clear coverage; cycle impact requires probes** | V2 specifies a future Rust GC bridge but does not register the existing baseline GC omission. |
| R2-X06 | `CallableWrapperCall()` ignores successful `__enter__`, exception-handler, and `__exit__` call results and leaves `exitArgs` unreleased on normal paths | **Definite leaks on the corresponding successful paths** | No D-row audits callable-wrapper invocation ownership. |

Source evidence:

- scheduler callback call/result handling: [`src/ScheduleManager.cpp`, lines 659–690](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/ScheduleManager.cpp#L659-L690);
- channel callback call/result handling: [`src/Channel.cpp`, lines 411–432](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Channel.cpp#L411-L432);
- exception-handler getter/setter: [`src/PyTasklet.cpp`, lines 624–665](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/PyTasklet.cpp#L624-L665);
- destructor cleanup set: [`src/Tasklet.cpp`, lines 71–93](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Tasklet.cpp#L71-L93);
- tasklet traverse/clear: [`src/PyTasklet.cpp`, lines 1099–1145](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/PyTasklet.cpp#L1099-L1145) and [`src/Tasklet.cpp`, lines 1362–1373](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Tasklet.cpp#L1362-L1373);
- callable-wrapper call paths: [`src/PyTasklet.cpp`, lines 1315–1457](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/PyTasklet.cpp#L1315-L1457).

[`PyObject_Call()` returns a new reference on success](https://docs.python.org/3.12/c-api/call.html#c.PyObject_Call), and [CPython cyclic-GC container support](https://docs.python.org/3.12/c-api/gcsupport.html) requires traversal of directly contained Python references and a clear operation that drops cycle-forming references. The source is sufficient to add named investigation rows; subprocess tests, debug CPython, weakrefs, and ASan/LSan remain appropriate for measuring reachability and consequences.

This list is evidence of incompleteness, not a claim that it is exhaustive.

### Claim 8 — The differential model lacks a class for legitimate nondeterminism

**Verdict: True.**

V2's classes cover exact parity, pending/fixed defects, approved divergences, undefined or unstable behavior associated with UB/nonportable corruption, opt-in extensions, and unsupported boundaries ([§3.1, lines 167–181](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L167-L181)). It does not define “one of these permitted outcomes,” partial-order equivalence, or a happens-before contract. Its normalization rules expressly say never to normalize order ([§12.5, lines 957–975](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L957-L975)).

The baseline contains operations whose cross-object order follows `std::unordered_set` iteration:

- active channels are stored in `std::unordered_set<Channel*>` ([`src/Channel.h`, lines 117–128](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Channel.h#L117-L128));
- `UnblockAllActiveChannels()` copies channels in that iteration order, then clears each channel in that order ([`src/Channel.cpp`, lines 552–577](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/Channel.cpp#L552-L577));
- manager-owned tasklets are stored in `std::unordered_set<Tasklet*>` ([`src/ScheduleManager.h`, lines 157–165](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/ScheduleManager.h#L157-L165)); and
- teardown repeatedly selects `begin()` and disassociates that tasklet ([`src/ScheduleManager.cpp`, lines 744–765](https://github.com/QuasarRay/carbon-scheduler/blob/73629285578622cadd6994f0504e923262017f1e/src/ScheduleManager.cpp#L744-L765)).

`unordered_set` traversal is valid but its element order is not a portable semantic guarantee. Pointer values, allocation, hash-table growth, library implementation, and platform can change it. This is not C++ undefined behavior and should not be forced into v2's UB/corruption class.

Within each channel, receive/send wait-list order may still be exact FIFO. Across channels during global unblock, or across tasklets during manager teardown, an exact total trace is too strong unless the project deliberately elevates one implementation-specific order into a new public contract. The suitable oracle shape is an allowed outcome set or a partial order that preserves required per-object order and happens-before constraints while permitting unspecified sibling order.

### Claim 9 — Carbon I/O is absent as a mandatory integration gate

**Verdict: True on the factual omission and on its high integration value.**

`migration-roadmap/v2.md` contains no Carbon I/O or downstream-workload gate. It does include an explicit Phase 10 for an optional Bevy adapter ([lines 1256–1276](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1256-L1276)) and refers only generically to representative production workloads at controlled switchover ([lines 1278–1297](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1278-L1297)).

The downstream repository confirms the claim's technical premise:

- its custom unittest runner creates one Scheduler tasklet for the complete test run and repeatedly alternates `scheduler.run()` and `socket.dispatch()` until the result exists ([`carboniotests/__main__.py`, lines 77–93](https://github.com/carbonengine/io/blob/5c4c669f6ebbda56996f1326315222dae9bf281e/tests/python/carboniotests/__main__.py#L77-L93));
- its native channel shim obtains `SchedulerCAPI` and forwards channel new/receive/balance/send operations through it ([`src/c_channel.cpp`, lines 4–30](https://github.com/carbonengine/io/blob/5c4c669f6ebbda56996f1326315222dae9bf281e/src/c_channel.cpp#L4-L30)); and
- the socket implementation directly uses SchedulerCAPI for channel creation, preference, balance, send, receive, send-throw, current tasklet, block-trap, and main-tasklet checks throughout its I/O state machines (representative examples: [`src/carbonio.cpp`, lines 192–245](https://github.com/carbonengine/io/blob/5c4c669f6ebbda56996f1326315222dae9bf281e/src/carbonio.cpp#L192-L245) and [lines 829–904](https://github.com/carbonengine/io/blob/5c4c669f6ebbda56996f1326315222dae9bf281e/src/carbonio.cpp#L829-L904)).

This exercises exactly the experimental backend's important integration boundary: real cooperative tasklet pumping plus native channel calls from a downstream extension. It is more directly probative of Carbon Scheduler compatibility than an optional Bevy host adapter.

“Inexplicably” is not a fact that source inspection can establish; downstream build cost, platform availability, or repository ownership might explain deferral. But v2 records no such rationale and does not name Carbon I/O even as a later gate. The omission is real and material.

### Claim 10 — V2 lacks an experimental-PR Definition of Done

**Verdict: True.**

V2 has one Definition of Done, and it is the eventual migration-complete gate. It requires authoritative Rust crates, all classified public behavior, property suites, callback/metric/channel parity, GC coverage, ABI and precompiled consumers, no unclassified leak, Bevy constraints, zero unexplained mismatches, performance budgets, rollback, divergence documentation, and an observation window ([lines 1519–1543](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1519-L1543)).

Phase 11 does say Rust should be opt-in first, but promotion still waits on every platform and classified contract gate, production workload evidence, performance/safety budgets, and operational rollback ([lines 1278–1297](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1278-L1297)). The first two future work packages explicitly move no scheduler, tasklet, or channel decision to Rust ([lines 1545–1568](https://github.com/QuasarRay/carbon-scheduler/blob/eb9cd245290b9847a777a36fe93d353e2c5ffca6/migration-roadmap/v2.md#L1545-L1568)).

There is no bounded milestone equivalent to:

- an opt-in experimental Rust backend builds without changing the default;
- all unchanged Scheduler Python and native C++ tests run against it, with failures reported rather than normalized;
- Carbon I/O builds and runs against the unchanged SchedulerCAPI surface;
- the experiment demonstrates a vertical scheduling/channel slice; and
- the PR explicitly makes no production-equivalence or cutover claim.

Therefore the roadmap cannot distinguish “enough evidence to merge an isolated experiment” from “enough evidence to replace the production backend.” The claim is confirmed.

## 4. Cross-claim assessment

The ten findings cluster into four independent problems:

| Problem | Claims | Audit conclusion |
|---|---|---|
| Objective and milestone mismatch | 1, 10 | V2 is a production-parity/cutover plan applied to an experimental-backend milestone. |
| Architecture and dependency scope | 2, 3 | The Carbon runtime is bespoke and Bevy-free, while local async-executor selection remains mandatory without a required role. |
| Incorrect or incomplete semantic model | 4, 8 | Receive event order is wrong, and exact total traces cannot model valid unspecified cross-object ordering. |
| Migration-boundary and evidence gaps | 5, 6, 7, 9 | Phase boundaries omit required bridges, the named defect register is incomplete, and the strongest visible downstream integration suite is not a gate. |

Claims 4 and 7 are source-correctness findings independent of project strategy. Claims 5 and 6 do not prove that incremental migration is impossible; they prove that v2 has not yet specified the adapters needed to make its chosen phase boundaries executable. Claims 1, 2, 3, 9, and 10 establish that v2's plan is poorly aligned with an initial experimental PR even if it remains a useful inventory for eventual production parity.

## 5. Final conclusion

The submitted case for a v3 is substantiated. No claim was falsified by the pinned source. Four claims require wording qualifications because they contain product-strategy judgments, but their factual premises remain correct.

A v3 would need to resolve, at minimum, the experiment-versus-cutover milestone split, the optionality of async-executor, the exact receive trace, mixed Phase 5/6/7 ownership, the expanded defect inventory, nondeterministic equivalence, and Carbon I/O integration. This conclusion records audit results only; it does not modify or authorize modification of the roadmap or implementation.
