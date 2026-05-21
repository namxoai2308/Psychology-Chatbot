# Optimization Plan Round 01

This file is generated from deterministic benchmark failures. Inspect the listed transcripts before changing the system.

- Bad cases: 2
- Threshold: 85.0

## Failure Types
- `empty_output`: 2
- `exception`: 2
- `hard_fail`: 2
- `low_quality_score`: 2
- `peer_integration_miss`: 2
- `peer_mismatch`: 2
- `stage_mismatch`: 2
- `technique_hint_miss`: 2

## Route Breakdown
- `CBT`: 2

## Cases To Inspect
- `vsm_cbt_001_exam_catastrophizing` (CBT, score=42.54): `empty_output`, `exception`, `hard_fail`, `low_quality_score`, `peer_integration_miss`, `peer_mismatch`, `stage_mismatch`, `technique_hint_miss`
- `vsm_cbt_002_friend_mind_reading` (CBT, score=41.98): `empty_output`, `exception`, `hard_fail`, `low_quality_score`, `peer_integration_miss`, `peer_mismatch`, `stage_mismatch`, `technique_hint_miss`

## Recommended Fix Workflow
- Fix one failure family at a time.
- Rerun only `selected_case_ids.txt` after code changes.
- Replace a case only when the rerun has no exception/hard_fail and is not lower scoring than the original.
