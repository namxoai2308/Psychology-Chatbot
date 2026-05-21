# Test Logs

Active test runs should write a small, named log here only while they are being inspected.

Archive old logs by date:

```text
backend/tests/logs/archive/YYYY-MM-DD/
```

Recommended naming:

```text
<scope>_<dataset_or_case>_<model_or_mode>_YYYY-MM-DD.log
```

Examples:

```text
vsm_probe_ours_deepseek_2026-05-17.log
vsm_structural_all_ours_structural_2026-05-17.log
```

Do not store benchmark source data in this folder. Use `backend/benchmarks/vsm/results/` for structured outputs such as `per_case_results.jsonl`, `score_summary.json`, `judge_results.jsonl`, and generated reports.
