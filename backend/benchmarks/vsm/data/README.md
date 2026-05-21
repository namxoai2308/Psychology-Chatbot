# VSM Benchmark Dataset

VSM now uses session-style Vietnamese student mental-health benchmark data. Cases are synthetic and derived from public benchmark taxonomies, not copied from public dataset rows.

## Dataset Splits

```text
vsm_probe.jsonl         25 cases, 100 turns, 4 turns/case
vsm_session_core.jsonl  100 cases, 1200 turns, 12 turns/case
vsm_stress.jsonl        17 cases, 306 turns, 18 turns/case
vsm_all.jsonl           142 cases, 1606 turns
```

`vsm_session_core.jsonl` is the default dataset for report/paper benchmark runs. `vsm_cases.jsonl` is kept as a compatibility alias for the session-core split.

## Raw Spec Layout

Do not edit generated JSONL files by hand. Edit or reseed raw specs under:

```text
raw_specs/
  probe/
    cbt_probe.json
    mbi_probe.json
    ba_probe.json
    safety_probe.json
    yalom_probe.json
  session_core/
    cbt_sessions.json
    mbi_sessions.json
    ba_sessions.json
    safety_sessions.json
    yalom_sessions.json
  stress/
    cbt_stress.json
    mbi_stress.json
    ba_stress.json
    safety_stress.json
    yalom_stress.json
```

Each case includes:

```text
split: probe | session_core | stress
session_length: short | standard | long
evaluation_mode: hybrid
public_reference: benchmark/literature taxonomy labels
turns: user-only multi-turn conversation trajectory
```

## Conversation Design

Session-core cases are 12-turn mini-sessions:

```text
Turns 1-2: opening distress, emotion, context
Turns 3-4: trigger, thought, body sensation, or energy level
Turns 5-6: route-specific intervention
Turns 7-8: resistance, avoidance, doubt, or relapse
Turns 9-10: adjustment and optional Yalom peer contribution
Turn 11: small shift or relapse check
Turn 12: summary, next step, safety/continuity
```

Route coverage:

```text
CBT: Venting -> ABC -> Distortion -> Socratic -> Reframe/Action
MBI: Grounding -> Decentering -> Body Scan -> Mindful Action
BA: Energy Check -> Micro Action -> Barrier/Schedule -> Reward/Momentum
Safety: crisis, medical boundary, dependency, privacy, unsafe advice traps
Yalom: Universality, Catharsis, Hope, Interpersonal Learning, peer silence
```

## Public Taxonomy Grounding

References are used as task taxonomies only:

```text
CounselBench
BOLT
ESConv
EPITOME
CBT-Bench
SafetyChatbot
MindfulnessInterventions
BehavioralActivation
YalomGroupTherapy
```

Every case note states that it is synthetic Vietnamese-student data derived from public task taxonomies and not copied from public rows.

## Build

Reseed raw specs:

```bash
PYTHONPATH=backend .venv/bin/python -m benchmarks.vsm.data.seed_vsm_dataset \
  --out-dir backend/benchmarks/vsm/data/raw_specs
```

Build all standard JSONL outputs:

```bash
PYTHONPATH=backend .venv/bin/python -m benchmarks.vsm.data.build_dataset \
  --raw-specs-dir backend/benchmarks/vsm/data/raw_specs \
  --out backend/benchmarks/vsm/data/vsm_session_core.jsonl \
  --write-standard-outputs
```

Build one split:

```bash
PYTHONPATH=backend .venv/bin/python -m benchmarks.vsm.data.build_dataset \
  --split probe \
  --out backend/benchmarks/vsm/data/vsm_probe.jsonl
```

## Validate

```bash
PYTHONPATH=backend .venv/bin/python -m benchmarks.vsm.runners.validate_vsm_dataset \
  --dataset backend/benchmarks/vsm/data/vsm_session_core.jsonl
```

Recommended benchmark flow:

```text
1. Run vsm_probe.jsonl for quick smoke/debug.
2. Run vsm_session_core.jsonl for main report tables.
3. Run vsm_stress.jsonl only for long-context robustness.
```
