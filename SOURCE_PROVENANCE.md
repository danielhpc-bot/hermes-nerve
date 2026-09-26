# Source provenance

## Product baseline

Nerve `0.2.2.dev4`

- repository: `keeltrace/hermes-nerve`
- exact commit: `a3aeedc0006797c244ef29d7e085616a5253e627`
- verified public version at implementation start: `0.2.2.dev4`

There was no published `0.2.2.dev5` tree when this implementation began. This package is the dev5 candidate produced from that fixed point.

## Donor behavior

Hermes Outpost:
- commit `9764b4fd0fb7f7923b8c5796b0e17036046858f0`
- donated: named-host SSH security boundary, task-over-stdin, durable transport jobs, stream parsing, status/result/cancel semantics.

Hermes Kanban Labs:
- commit `acf73737673c6639ac59991d61e349456738b132`
- donated: single-authority rule, mixed local/remote spawn-adapter pattern, exact Git state transport, per-run workspaces, result refs, anti-sprawl/frontier concepts.

Hermes Kanban:
- canonical state remains in `hermes_cli.kanban_db`.
- integration uses existing claim/run identity, `complete_task`, and `request_review` semantics rather than introducing a second lifecycle state machine.

## Dev5 implementation boundary

New implementation lives primarily under:

- `hermes_nerve/work/`
- `hermes_nerve/remote/`

The plugin-level tool/hook composition lives in root `__init__.py`.


## dev6 derivation

`0.2.2.dev6` is implemented directly from the finalized local `0.2.2.dev5` product and the preserved 2026-09-20 A/B evidence. The tuning changes are intentionally scoped to Kanban token economics: headless worker registration, automatic DoD binding, per-API usage accounting, deterministic-first verification, ROI-gated hidden Jev decisions, compact directive injection, and benchmark instrumentation. No second task/scheduler authority was introduced.


## dev7 derivation

`0.2.2.dev7` is implemented directly from the finalized local `0.2.2.dev6` package plus the preserved Solar Pro 4 A/B evidence from 2026-09-21. That run proved the dev6 zero-schema headless worker path (`tools=0`) and live Jev provider integration, but the measured supervision database remained empty because dev6 attempted to open canonical Kanban state through the removed `hermes_cli.kanban_db.connect()` symbol. Hermes Agent v0.21.3 uses the split `hermes_cli.kanban_db_connect.connect_closing()` API.

Dev7 changes only the bootstrap/packaging seam needed to make the intended architecture real: it reads the dispatcher-pinned board/DB, validates canonical run and claim identity, binds the locked DoD during plugin startup before the first worker provider call, preserves zero model-visible Jev schemas, and includes the relative-import packaging correction discovered during the dev6 setup probe. Regression tests reproduce the split Hermes API shape and prove startup binding without requiring a model call. No second task/scheduler authority is introduced.


## dev8 derivation

`0.2.2.dev8` is implemented directly from the finalized local `0.2.2.dev7` package and the preserved Solar Pro 4 dev7 A/B evidence from 2026-09-21. That run proved startup binding, exact run/context state, zero worker-visible Jev tools, worker API accounting, evidence collection, and budget checkpoints, but made zero provider-backed Jev decisions across 89 measured Solar API calls.

The first broken edge was identified in the decision router: `SupervisionStore.events()` already parses `payload_json` into `row["payload"]`, while dev7 attempted to parse `row["payload_json"]`. Failure fingerprints were therefore always empty at routing time. Dev8 fixes that mismatch, keeps failure history across interleaved work events, fingerprints every failing pytest identity, propagates deterministic test failures into criterion state, wires native `pre_verify` to semantic completion verification, adds session-end fallback auditing, and enforces a cooldown after provider-backed trajectory decisions. No second task/scheduler authority is introduced.


## dev9 derivation

`0.2.2.dev9` is implemented directly from the finalized local `0.2.2.dev8` package and the measured Solar Pro 4 control/treatment A/B from 2026-09-21. Through the clean done-done boundary, treatment used 35 Solar calls and 1,056,481 worker-primary tokens; Jev used 33,498 supervisor tokens, for 1,089,979 combined versus 1,856,632 control primary tokens. The treatment nevertheless failed operationally after the solution was committed because the worker continued into a post-completion loop and ultimately exited without a valid terminal Kanban action.

Dev9 deliberately does not retune Jev prompts, thresholds, completion batching, or token policy. It fixes only lifecycle/authority edges exposed by that run: delegated children are fenced from completion supervision, a fresh completion verdict may supersede stale trajectory control before native `kanban_complete`, and fallback binding prefers canonical dispatcher task identity. Hermes Kanban remains the sole canonical lifecycle authority.

## dev10 derivation

`0.2.2.dev10` is implemented directly from the finalized local `0.2.2.dev9` package plus the live dev9 lifecycle reproduction on 2026-09-21. The run proved startup binding (`tools=0`, headless worker, exact task/run contract), real supervisor usage, trajectory assessment, 20/20 visible tests, and hidden acceptance. It then remained `running` for the full terminal-watch window and grew from 39 worker API-usage rows at the first all-green boundary to 77 while attempting to finish. After all eight DoD items were verified, the model attempted generic `tool_call`/`tool_search` paths for `kanban_complete`, then fell back toward direct `kanban_db.complete_task(...)` scripting instead of the required native terminal tool.

Dev10 changes only the post-verification lifecycle seam: a PASS at `pre_verify` arms a durable terminal-only `COMPLETE_READY` control and forces the next successful action to be the directly-listed native `kanban_complete`. Repeated pre-finish attempts reuse that latch without another Jev completion spend. No provider policy, routing threshold, completion prompt, token budget, or canonical Kanban authority is changed.

## dev11 derivation

`0.2.2.dev11` is derived from the verified local `0.2.2.dev10` package plus the live dev10 lifecycle reproduction on 2026-09-21. Dev10 materially improved verification: it rejected three premature completions and drove discovery of a real dead-letter idempotency defect. The final run nevertheless proved two remaining architecture faults: semantic completion evidence stayed false-negative (`DOD-06`/`DOD-07`/`DOD-08` remained missing even after machine-checkable proof), and the worker could bypass canonical lifecycle authority by writing and executing direct Kanban SQLite mutation code. The run eventually showed `done`, but only after that bypass, with 80 worker API rows and 174 tool calls.

Dev11 keeps Hermes Kanban as canonical authority but moves the final transition into the plugin harness using Hermes' documented `PluginContext.dispatch_tool()` API. A passing `pre_verify` result arms `COMPLETE_READY` and immediately invokes the registered native `kanban_complete` tool under the owning worker context. Deterministic completion evidence is expanded so the frozen event-delivery benchmark's interface compatibility, idempotency semantics, regression count, and final evidence summary can be proven locally. Generic CLI/SQLite lifecycle bypasses are fenced.



## dev12 live-smoke provenance

`0.2.2.dev12` is derived from the verified local `0.2.2.dev11` package plus the first clean dev11 live lifecycle smoke on 2026-09-21. That run proved the core dev11 authority path: the frozen baseline was 8 failed / 5 passed, Jev first returned REPLAN, then `completion_pre_verify allow=true`, then `completion_native_dispatch ok=true`, and Hermes canonically marked the task/run done/completed with `Nerve verified completion.` The strict release gate still observed one worker API row after PASS. Hermes source inspection proved `post_api_request` executes before the round-end `pre_verify` gate, so the row was a real subsequent provider call. The cause was Hermes' kanban text-stop guard: hook-owned `kanban_complete` is not represented in conversation messages, so the guard incorrectly emits a synthetic completion nudge. Dev12 suppresses that worker-local guard only after explicit native completion success.

## dev13 live-smoke provenance

`0.2.2.dev13` is derived from dev12 plus the failed dev12 live lifecycle smoke on 2026-09-21. The dev12 run started from the frozen 8-fail / 5-pass fixture and reached a clean committed implementation with 22 passing tests. The worker produced strong DOD-07 behavioral evidence (dead-event no-reattempt, never-redeliver, retry-then-success repeated-dispatch stability, and retry-then-success delivery), yet completion verification returned RETRY three times and still reported DOD-07/DOD-08 missing. Because no `allow=true` occurred, dev12 never reached its native terminal-tail suppression path. The worker then explored Kanban source/DB/tool mechanics; the authority fence blocked direct lifecycle bypasses, but API usage reached 67 rows before the worker disappeared and left the board stale-running.

Dev13 changes the completion evidence authority model rather than weakening the release gate: controller-observed deterministic PASS/FAIL is authoritative for machine-verifiable criteria; deterministic FAIL cannot be overwritten by semantic PASS; DOD-07 recognizes equivalent focused behavioral-test names and only clauses actually present in the locked criterion; and DOD-08 is generated by the harness from authoritative per-DoD verdicts plus the exact observed full-suite command/result. Jev remains available for trajectory advice and criteria that genuinely require semantic judgment.


## dev14 live-smoke provenance

`0.2.2.dev14` is derived from the verified local `0.2.2.dev13` package plus the failed dev13 live lifecycle smoke on 2026-09-21. The fresh dev13 run reproduced the frozen 8-fail / 5-pass baseline, bound headless supervision correctly, and reached a clean committed implementation whose visible suite reported 26 passing tests. Dev13's new authority model behaved correctly: the only completion verdict was deterministic, no semantic `completion_batch` usage occurred, and DOD-07 remained FAIL rather than being overridden by model prose.

The live postmortem then exposed the actual behavioral defect hidden by the worker's visible tests: after an event reached dead-letter state at attempt 2, dispatching it again returned `dead` but mutated the attempt counter from 2 to 3. An ad-hoc probe also showed the worker was beginning another completion-debug cycle after receiving only a generic DOD-07 failure. Hidden acceptance still passed that buggy implementation because it checked reaching dead state but not repeated dead-state dispatch.

Dev14 therefore moves DOD-07 proof one level deeper: the controller runs the required retry/dead-letter/idempotency behavior directly against the implementation rather than selecting worker-authored tests by name. Deterministic failure reasons are surfaced verbatim in the pre-verify RETRY directive and persisted in diagnostics, and hidden acceptance enforces the same dead-event redispatch stability.


## dev15b Laya/Reflex derivation

`0.2.2.dev15+dev15b` is derived directly from the user-supplied finalized `0.2.2.dev14` package after dev14 passed its initial smoke test. Dev15b is deliberately scoped below the existing completion-authority boundary: it does not weaken deterministic DoD verification, does not change native `kanban_complete` ownership, and does not modify the Hermes community catalog.

The new code introduces a provider-neutral Reflex factory beneath `DecisionEngine`, preserving Jev as the default backend while adding an opt-in local Laya backend and a Jev-authoritative/Laya-shadow mode. The core plugin remains dependency-free. Laya 0.3.5 and its torch/transformers stack are isolated in a separately launched, fixed-model sidecar that implements the same `system_one(state, questions)` shape already consumed by the engine. Shadow telemetry stores hashes plus bounded decision outputs, not full decision state, and Laya failures are fail-open in shadow mode.

The Laya API contract and package version used for dev15b were verified against the upstream `NandhaKishorM/laya` repository on 2026-09-21 at commit `573e5b62696ba441230cd6be71d593331b5d23af` (project version `0.3.5`). The integration targets the `convaiinnovations/laya` `typed-decisions` checkpoint. Offline tests use a real loopback HTTP server with a fake in-memory Laya-compatible agent; they prove transport/auth/model identity/provenance/shadow behavior without downloading model weights. A real-weight Laya smoke remains an explicit runtime acceptance gate for the parent dev15 merge.


## dev15 final controller-completion derivation

`0.2.2.dev15` is derived from the user-supplied finalized dev15b Laya integration artifact plus the live dev14 Pair-3 benchmark evidence captured on 2026-09-21. Pair 3 proved a distinct lifecycle failure after successful implementation: the worker reached a clean committed workspace with the full suite green and DOD-07 repaired, but then spent many additional model calls trying CLI, adapter, generated-script, generic-tool, and direct Kanban completion paths. The code was complete; terminal lifecycle authority was not reliably closed.

Dev15 resolves that seam without introducing a second task scheduler or canonical status store. Hermes Kanban remains canonical. The plugin captures Hermes' supported `PluginContext.dispatch_tool` capability and treats it as controller authority. Verified completion is persisted under the backward-compatible `COMPLETE_READY` run control with a lifecycle payload (`VERIFIED`, `COMPLETING`, `COMPLETED`, or `COMPLETION_RETRY`). Worker-originated completion intent is fenced and converted into controller verification/native dispatch. Native failures retry locally and may reconcile on session end; they do not return the worker to a completion-discovery loop.

The final package also incorporates the dev15b Reflex/Laya slice unchanged in authority ordering: deterministic completion evidence remains above semantic Jev/Laya decisions, Jev remains the default backend, and Laya is optional/local or shadow. The Hermes community catalog pin remains unchanged.


## 0.2.2.dev16 derivation

`0.2.2.dev16` is derived directly from the user-supplied finalized `0.2.2.dev15` artifact plus the full dev14/dev15 Solar Pro 4 A/B evidence from 2026-09-21. The release adds no new canonical scheduler or task authority. It extends the existing `CardSupervisor` with a local token-budget estimator, required `DOD-BUDGET`, a deterministic nerve observer, and a controller-owned `kanban_block` kill switch for confirmed runaway runs. The defaults were calibrated against the frozen eight-criterion event-delivery benchmark: 960k expected worker tokens, 1.10x completion tolerance, and a 1.75x hard observer tripwire with a minimum call-count guard.

The release also preserves the dev15 controller-owned completion repair and adds the rule that a post-verification provider call first triggers native completion reconciliation; an already completed run is never overwritten with watchdog BLOCK. Benchmark infrastructure findings (startup race, global concurrency contamination, abandoned ready cards, noncanonical board DBs, and Ctrl+C cleanup) are recorded in `docs/DEV16_SESSION_FINDINGS.md`, with a read-only `scripts/benchmark_preflight.py` helper.

## 0.2.2.dev17 derivation

`0.2.2.dev17` is derived directly from the finalized `0.2.2.dev16` Nerve release and freezes the dev16 controller-completion, token-budget, and Nerve thresholds while hardening release validation. The dev16 live Solar Pro 4 cohort established three valid Jev-supervised runs (719,634 / 495,493 / 588,465 combined tokens) with zero false-positive Nerve kills, while two of three controls crossed the 2.4M harness emergency ceiling and the remaining successful control used 2,355,073 primary tokens and required lingering-worker reap.

Dev17 adds an open Reflex compatibility layer, not a second scheduler or task authority. Laya remains an out-of-process LOCAL_ONLY sidecar and is updated to the published `laya==0.3.3` package with the standalone `convaiinnovations/laya-typed-decisions` checkpoint. OpenJev is integrated through its local Jev-compatible `/v1/systemone` helper surface with optional helper identity pinning. OpenJev model weights are not bundled. Operator scripts keep model runtimes outside the dependency-free Hermes plugin.

Release-validation infrastructure is rewritten around a crash-safe Jev/Laya/OpenJev matrix runner. It accepts Hermes `done` and `completed` as successful terminal task states, persists each arm before cleanup, distinguishes NERVE_KILL from HARNESS_KILL, reaps lingering workers, reports tail metrics, and survives cleanup/reporting errors without discarding completed measurements.
