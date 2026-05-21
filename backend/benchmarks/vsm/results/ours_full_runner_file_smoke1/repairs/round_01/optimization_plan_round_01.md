# Optimization Plan Round 01

This file is generated from deterministic benchmark failures. Inspect the listed transcripts before changing the system.

- Bad cases: 1
- Threshold: 85.0

## Failure Types
- `peer_integration_miss`: 1
- `peer_mismatch`: 1
- `stage_mismatch`: 1
- `technique_hint_miss`: 1

## Route Breakdown
- `BA`: 1

## Cases To Inspect
- `vsm_ba_001_low_energy_bed` (BA, score=95.01): `peer_integration_miss`, `peer_mismatch`, `stage_mismatch`, `technique_hint_miss`

## Recommended Fix Workflow
- Fix one failure family at a time.
- Rerun only `selected_case_ids.txt` after code changes.
- Replace a case only when the rerun has no exception/hard_fail and is not lower scoring than the original.
