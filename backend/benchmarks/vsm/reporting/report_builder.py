from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from benchmarks.vsm.reporting.sample_data import DISPLAY_NAMES, METRIC_DISPLAY, SYSTEMS, demo_summary
from benchmarks.vsm.reporting.visualize_vsm import generate_all_figures


def build_vsm_report(summary: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = out_dir / "tables"
    figures_dir = out_dir / "figures"
    tables_dir.mkdir(exist_ok=True)
    figures_dir.mkdir(exist_ok=True)

    table_paths = {
        "overall": tables_dir / "table_1_overall_leaderboard.csv",
        "route": tables_dir / "table_2_route_performance.csv",
        "safety": tables_dir / "table_3_safety.csv",
        "yalom": tables_dir / "table_4_yalom_group.csv",
        "failure": tables_dir / "table_5_failure_taxonomy.csv",
        "confidence": tables_dir / "table_6_confidence_intervals.csv",
        "audit": tables_dir / "table_7_human_audit.csv",
        "ablation": tables_dir / "table_8_ablation_deltas.csv",
    }

    overall_rows = _overall_rows(summary)
    route_rows = _route_rows(summary)
    safety_rows = _safety_rows(summary)
    yalom_rows = _yalom_rows(summary)
    failure_rows = _failure_rows(summary)
    confidence_rows = _confidence_rows(summary)
    audit_rows = _audit_rows(summary)
    ablation_rows = _ablation_rows(summary)

    _write_csv(table_paths["overall"], overall_rows)
    _write_csv(table_paths["route"], route_rows)
    _write_csv(table_paths["safety"], safety_rows)
    _write_csv(table_paths["yalom"], yalom_rows)
    _write_csv(table_paths["failure"], failure_rows)
    _write_csv(table_paths["confidence"], confidence_rows)
    _write_csv(table_paths["audit"], audit_rows)
    _write_csv(table_paths["ablation"], ablation_rows)

    figure_paths = generate_all_figures(summary, figures_dir)

    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(_report_markdown(summary, table_paths, figure_paths), encoding="utf-8")

    return {
        "summary": out_dir / "summary.json",
        "report": out_dir / "report.md",
        "tables_dir": tables_dir,
        "figures_dir": figures_dir,
        "failures": out_dir / "failures.jsonl",
        "per_case_results": out_dir / "per_case_results.jsonl",
        "judge_results": out_dir / "judge_results.jsonl",
        "human_audit_template": out_dir / "human_audit_template.csv",
    }


def _overall_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for system in summary.get("systems", SYSTEMS):
        m = summary.get("overall", {}).get(system, {})
        rows.append(
            {
                "System": DISPLAY_NAMES.get(system, system),
                "VSM Total": _fmt(m.get("vsm_total")),
                "Clinical Safety": _fmt(m.get("clinical_safety")),
                "Therapeutic Quality": _fmt(m.get("therapeutic_quality")),
                "Modality Fidelity": _fmt(m.get("modality_fidelity")),
                "Group Therapy Dynamics": _fmt(m.get("group_therapy_dynamics")),
                "Reliability": _fmt(m.get("system_reliability")),
                "Fallback Rate": _pct(m.get("fallback_rate")),
                "Avg Latency": _seconds(m.get("avg_latency_seconds")),
            }
        )
    return rows


def _confidence_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for system in summary.get("systems", SYSTEMS):
        m = summary.get("confidence_intervals", {}).get(system, {})
        rows.append(
            {
                "System": DISPLAY_NAMES.get(system, system),
                "Metric": m.get("metric", "final_hybrid_score"),
                "Mean": _fmt(m.get("mean")),
                "Std": _fmt(m.get("std")),
                "95% CI Low": _fmt(m.get("ci_low")),
                "95% CI High": _fmt(m.get("ci_high")),
                "Turns": m.get("n_turns", "N/A"),
            }
        )
    return rows


def _audit_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    audit = summary.get("human_audit", {})
    agreement = audit.get("agreement_summary", {}) if isinstance(audit, dict) else {}
    if not agreement:
        return [
            {
                "Audit File": audit.get("template", "human_audit_template.csv") if isinstance(audit, dict) else "human_audit_template.csv",
                "Audited Turns": audit.get("audited_turns", 0) if isinstance(audit, dict) else 0,
                "Safety Agreement": "Pending",
                "Technique Agreement": "Pending",
                "Empathy Agreement": "Pending",
            }
        ]
    return [
        {
            "Audit File": audit.get("template", "human_audit_template.csv"),
            "Audited Turns": audit.get("audited_turns", 0),
            "Safety Agreement": _fmt(agreement.get("safety")),
            "Technique Agreement": _fmt(agreement.get("technique")),
            "Empathy Agreement": _fmt(agreement.get("empathy")),
        }
    ]


def _ablation_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in summary.get("ablation_deltas", []):
        baseline = row.get("baseline")
        variant = row.get("variant")
        rows.append(
            {
                "Baseline": DISPLAY_NAMES.get(baseline, baseline),
                "Variant": DISPLAY_NAMES.get(variant, variant),
                "Final Hybrid Δ": _fmt(row.get("final_hybrid_delta")),
                "Clinical Safety Δ": _fmt(row.get("clinical_safety_delta")),
                "Technique Fidelity Δ": _fmt(row.get("technique_fidelity_delta")),
                "Group Dynamics Δ": _fmt(row.get("group_therapy_dynamics_delta")),
                "Latency Δ": _seconds(row.get("latency_delta_seconds")),
            }
        )
    return rows


def _route_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "System": DISPLAY_NAMES.get(row.get("system"), row.get("system")),
            "Route": row.get("route"),
            "Cases": row.get("cases"),
            "Stage Accuracy": _fmt(row.get("stage_accuracy")),
            "Technique Fidelity": _fmt(row.get("technique_fidelity")),
            "Route Bleed Count": row.get("route_bleed_count"),
            "Validator Pass": _fmt(row.get("validator_pass")),
            "Fallback Rate": _pct(row.get("fallback_rate")),
        }
        for row in summary.get("route_performance", [])
    ]


def _safety_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for system in summary.get("systems", SYSTEMS):
        m = summary.get("safety", {}).get(system, {})
        rows.append(
            {
                "System": DISPLAY_NAMES.get(system, system),
                "Crisis Safe Response": _fmt(m.get("crisis_safe_response")),
                "Unsafe Advice Violation": m.get("unsafe_advice_violation", "N/A"),
                "Medical Boundary": _fmt(m.get("medical_boundary")),
                "Dependency Boundary": _fmt(m.get("dependency_boundary")),
                "Adversarial Pass Rate": _fmt(m.get("adversarial_pass_rate")),
                "Safety Gate Failures": m.get("safety_gate_failures", "N/A"),
            }
        )
    return rows


def _yalom_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for system in summary.get("systems", SYSTEMS):
        m = summary.get("yalom_group", {}).get(system, {})
        rows.append(
            {
                "System": DISPLAY_NAMES.get(system, system),
                "Peer Selection Accuracy": _fmt(m.get("peer_selection_accuracy")),
                "Yalom Factor Match": _fmt(m.get("yalom_factor_match")),
                "Nam Persona Validity": _fmt(m.get("nam_persona_validity")),
                "Linh Persona Validity": _fmt(m.get("linh_persona_validity")),
                "Peer Silence Accuracy": _fmt(m.get("peer_silence_accuracy")),
                "Repetition Penalty": _fmt(m.get("repetition_penalty")),
            }
        )
    return rows


def _failure_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    failures = summary.get("failure_taxonomy", {})
    for failure_type, by_system in failures.items():
        row = {"Failure Type": failure_type}
        for system in summary.get("systems", SYSTEMS):
            row[system] = by_system.get(system, 0)
        rows.append(row)
    return rows


def _report_markdown(summary: dict[str, Any], table_paths: dict[str, Path], figure_paths: list[Path]) -> str:
    overall = _overall_rows(summary)
    route = _route_rows(summary)
    safety = _safety_rows(summary)
    yalom = _yalom_rows(summary)
    failures = _failure_rows(summary)
    ablation = _ablation_rows(summary)
    lines = [
        "# VSM Benchmark Report",
        "",
        "## Evaluation Groups",
        "",
        *[f"- **{display}** (`{key}`)" for key, display in METRIC_DISPLAY.items()],
        "",
        "## Table 1. Overall Benchmark Leaderboard",
        "",
        _md_table(overall),
        "",
        "## Table 2. Route-Level Performance",
        "",
        _md_table(route),
        "",
        "## Table 3. Safety and Adversarial Robustness",
        "",
        _md_table(safety),
        "",
        "## Table 4. Yalom Group Dynamics",
        "",
        _md_table(yalom),
        "",
        "## Table 5. Failure Taxonomy",
        "",
        _md_table(failures),
        "",
        "## Table 6. Confidence Intervals",
        "",
        _md_table(_confidence_rows(summary)),
        "",
        "## Table 7. Human Audit Status",
        "",
        _md_table(_audit_rows(summary)),
        "",
        "## Table 8. Ablation Deltas",
        "",
        _md_table(ablation),
        "",
        "## Figures",
        "",
    ]
    for path in figure_paths:
        rel = path.relative_to(path.parents[1])
        title = path.stem.replace("_", " ").title()
        lines.extend([f"### {title}", "", f"![{title}]({rel.as_posix()})", ""])
    lines.extend(
        [
            "## Generated Files",
            "",
            *[f"- `{path.relative_to(path.parents[1]).as_posix()}`" for path in table_paths.values()],
        ]
    )
    return "\n".join(lines).replace("Axis", "Evaluation Dimension")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _md_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No data._"
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (int, float)):
        return f"{value:.1f}"
    return str(value)


def _pct(value: Any) -> str:
    return "N/A" if value is None else f"{float(value):.1f}%"


def _seconds(value: Any) -> str:
    return "N/A" if value is None else f"{float(value):.1f}s"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary-json", default="")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.summary_json:
        summary = json.loads(Path(args.summary_json).read_text(encoding="utf-8"))
    else:
        summary = demo_summary()
    build_vsm_report(summary, Path(args.out_dir))


if __name__ == "__main__":
    main()
