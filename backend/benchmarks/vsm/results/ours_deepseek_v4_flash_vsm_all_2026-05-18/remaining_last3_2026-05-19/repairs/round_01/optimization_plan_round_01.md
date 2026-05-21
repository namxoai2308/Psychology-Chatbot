# Optimization Plan Round 01

This file is generated from deterministic benchmark failures. Inspect the listed transcripts before changing the system.

- Bad cases: 3
- Threshold: 85.0

## Failure Types
- `low_quality_score`: 3
- `peer_integration_miss`: 3
- `peer_mismatch`: 3
- `stage_mismatch`: 3
- `technique_hint_miss`: 3

## Route Breakdown
- `CBT`: 3

## Cases To Inspect
- `vsm_stress_yalom_001_universality_dorm_loneliness` (CBT, score=80.28): `low_quality_score`, `peer_integration_miss`, `peer_mismatch`, `stage_mismatch`, `technique_hint_miss`
- `vsm_stress_yalom_002_catharsis_family_pressure` (CBT, score=77.95): `low_quality_score`, `peer_integration_miss`, `peer_mismatch`, `stage_mismatch`, `technique_hint_miss`
- `vsm_stress_yalom_003_hope_after_failure` (CBT, score=80.82): `low_quality_score`, `peer_integration_miss`, `peer_mismatch`, `stage_mismatch`, `technique_hint_miss`

## Recommended Fix Workflow
- Fix one failure family at a time.
- Rerun only `selected_case_ids.txt` after code changes.
- Replace a case only when the rerun has no exception/hard_fail and is not lower scoring than the original.
