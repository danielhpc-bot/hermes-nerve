# Nerve v0.2.2.dev16 — nerve observer + token-budget DoD

> **Historical dev16 note.** This document records the dev16 experiment and is not the current v0.2.3 setup or release guide. Use `docs/SETUP.md` for current setup and `bash scripts/verify_dev17.sh` for the canonical release gate.

Dev16 starts from the finalized dev15 controller-completion build and incorporates the failure modes and quality-of-life issues exposed by the dev14 Solar Pro 4 A/B sessions.

## What changed

### 1. "How many tokens should this take?" is now locked into the DoD

For automatically bound Kanban tasks, Jev estimates a conservative worker[REDACTED] from the structured Definition of Done before the first worker model call. The default estimator is local and free:

```text
estimate = safety_multiplier * (
    base_tokens
  + per_criterion_tokens * number_of_DOD_items
  + bounded_body_complexity
)
```

Defaults:

- base: `120,000`
- per DoD criterion: `75,000`
- task-body factor: `25 tokens / character-equivalent weight`, capped at 250k
- safety multiplier: `1.25x`
- floor: `work_default_task_budget_tokens` (70k)
- cap: 2,000,000

The estimator rounds to 10k for stable, readable contracts. The frozen 8-criterion event-delivery benchmark used in the dev14 A/B produces a **960,000[REDACTED]

Jev appends a required `DOD-BUDGET` criterion. It is controller-verifiable and cannot be waived by worker prose. A small default completion tolerance (`1.10x`) avoids false failures from normal estimate noise. With the frozen benchmark that gives a completion ceiling of **1,056,000 accounted worker tokens**.

### 2. Nerve observer

Every provider response updates a deterministic token-trajectory observer. It does not spend another model call.

The default escalation ladder is deliberately conservative:

```text
< 65% target              CONTINUE
>= 65% target             WATCH
>= 90% + corroboration    REPLAN advisory
>= 1.75x target + 12 calls KILL
>= 1.35x + repeated failures + sustained huge context KILL
post-verification call    controller completion first; kill only if terminal transition cannot close
```

Crossing the estimate by itself is **not** a kill condition. WATCH and REPLAN only inject one bounded directive on a state transition; they do not spam every turn. Automatic kill requires a high-confidence deterministic condition.

### 3. Controller-owned kill switch

A hard nerve trip is not handed back to the worker to reason about. Jev:

1. records a durable `BLOCK` control with `source=nerve_observer` and `kill_switch=true`;
2. uses the captured Hermes controller dispatcher to call canonical `kanban_block(reason=...)`;
3. fences worker implementation tools if canonical blocking cannot complete immediately;
4. preserves the workspace for controller/human inspection.

This specifically addresses the measured economics of Solar Pro 4 loops: one pathological run consumed 4.76M tokens, more than several healthy runs combined. On the frozen benchmark, the default hard ceiling is about **1.68M tokens**, which would have stopped that run millions of tokens earlier while leaving the 376k, 484k, and 968k valid runs untouched.

### 4. Post-PASS behavior is safer

If a provider call somehow occurs after deterministic verification, dev16 first retries controller-owned native `kanban_complete`. A successfully completed run is never overwritten with watchdog `BLOCK`. Only an unresolved terminal/lifecycle failure escalates to the kill path.

### 5. Session findings folded into dev16

Dev16 retains/finalizes:

- controller-owned completion from dev15;
- zero model-owned CLI/SQLite completion workarounds;
- deterministic DOD-07 behavioral authority;
- zero semantic override of deterministic failures;
- controller-authored completion summary;
- post-PASS API-call auditing;
- local completion retries without another worker turn;
- startup binding and global-run identity fencing;
- explicit benchmark launch retry handling;
- token accounting with deduplicated provider request IDs;
- low-overhead headless workers;
- Laya/Jev/shadow Reflex modes.

## New configuration

```yaml
work_auto_estimate_task_budget: true
work_budget_dod_required: true
work_budget_dod_tolerance: 1.10
work_budget_estimator_base_tokens: 120000
work_budget_estimator_per_criterion_tokens: 75000
work_budget_estimator_body_char_factor: 25.0
work_budget_estimator_safety_multiplier: 1.25
work_budget_estimator_max_tokens: 2000000

work_nerve_observer_enabled: true
work_nerve_auto_kill: false  # deprecated compatibility state; does not own stop authority
work_nerve_watch_fraction: 0.65
work_nerve_replan_fraction: 0.90
work_nerve_hard_budget_multiplier: 1.75
work_nerve_min_calls_before_kill: 12
work_nerve_repeated_failure_kill: 3
work_nerve_high_context_streak_kill: 3
```

`work_nerve_auto_kill` is retained only for compatibility with older configurations. Current Nerve does not use it to own economic stop authority: budget/trajectory escalation routes to the orchestrator/reviewer. Leave it `false`; WATCH/REPLAN and review telemetry remain available without granting Nerve a canonical kill switch.

## Install

```bash
cd hermes-nerve-v0.2.2.dev16-final
bash scripts/install_dev16_profile.sh abtest-jev-dev16
```

## Offline verification

```bash
bash scripts/verify_dev16.sh
```

Historical dev16-focused tests now map to the maintained files below:

```bash
python3 -m pytest -q \
  tests/test_dev16_nerve_budget.py \
  tests/test_dev15_controller_completion.py \
  tests/test_dev17_matrix_qol.py
```

For current release qualification, run the full canonical gate instead:

```bash
bash scripts/verify_dev17.sh
```

## Historical A/B record

The following checklist describes the original frozen event-delivery / Solar Pro 4 experiment. It is retained as historical benchmark context, not as the current release procedure. Record at minimum:

- valid completion;
- worker calls to first completion candidate;
- calls to deterministic PASS;
- calls after PASS (target: zero);
- target tokens / completion ceiling;
- consumed tokens at WATCH / REPLAN / KILL;
- maximum input context;
- repeated failure count;
- native completion attempts;
- terminal outcome.

The release target is not merely lower mean token use. The primary dev16 target is **tail compression**: no multi-million[REDACTED] spiral, no false-positive kill of a healthy run near the estimated budget, and zero model calls after verified PASS.