from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


DEFAULT_RESULTS_DIR = Path("backend/benchmarks/vsm/results/trace_vsm_core")

NAMES = {
    "ours_full": "TRACE-Full",
    "ours_no_peer": "NoPeer",
    "ours_no_safety_critic": "NoSafety",
    "ours_no_validator": "NoValidator",
    "single_agent_stage_prompt": "StagePrompt",
    "single_agent_plain": "Plain",
    "prompt_1_1": "Prompt1-1",
    "base_model": "Base",
    "camel_cbt": "CAMEL-CBT",
    "seallm": "SeaLLM",
}

COLORS = {
    "ours_full": "#13795b",
    "ours_no_peer": "#65a98f",
    "ours_no_safety_critic": "#d6a11d",
    "ours_no_validator": "#9db36b",
    "single_agent_stage_prompt": "#738cc6",
    "single_agent_plain": "#9a9a9a",
    "prompt_1_1": "#4978b7",
    "base_model": "#6e6e6e",
    "camel_cbt": "#c8564f",
    "seallm": "#8f6a4a",
}

METRICS = [
    ("clinical_safety", "Safety"),
    ("therapeutic_alliance", "Alliance"),
    ("technique_fidelity", "Technique"),
    ("conversation_progress", "Progress"),
    ("context_retention", "Context"),
    ("cultural_fit_vietnamese_student", "Culture"),
    ("actionability", "Action"),
    ("subtle_risk_detection", "Risk"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate short-name PNG visuals from frozen VSM paper results.")
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--out-dir", type=Path, default=Path("visuals"))
    args = parser.parse_args()

    score_rows = _read_csv(args.results_dir / "score_summary.csv")
    cape_rows = _read_csv(args.results_dir / "cape2_summary.csv")
    yalom_rows = _read_csv(args.results_dir / "yalom_summary.csv")
    _validate(score_rows, cape_rows, yalom_rows)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    _plot_rank(score_rows, args.out_dir / "rank.png")
    _plot_metrics(score_rows, args.out_dir / "metrics.png")
    _plot_ablate(score_rows, args.out_dir / "ablate.png")
    _plot_cape(cape_rows, args.out_dir / "cape.png")
    _plot_yalom(yalom_rows, args.out_dir / "yalom.png")

    for path in ["rank.png", "metrics.png", "ablate.png", "cape.png", "yalom.png"]:
        print(args.out_dir / path)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _validate(score_rows: list[dict[str, str]], cape_rows: list[dict[str, str]], yalom_rows: list[dict[str, str]]) -> None:
    score_systems = {row["system"] for row in score_rows}
    required = {"ours_full", "ours_no_peer", "ours_no_safety_critic", "ours_no_validator"}
    missing = sorted(required - score_systems)
    if missing:
        raise SystemExit(f"Missing systems in score_summary.csv: {missing}")
    if not cape_rows:
        raise SystemExit("cape2_summary.csv is empty")
    if not yalom_rows:
        raise SystemExit("yalom_summary.csv is empty")


def _float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    return default if value == "" or value is None else float(value)


def _label(system: str) -> str:
    return NAMES.get(system, system)


def _color(system: str) -> str:
    return COLORS.get(system, "#777777")


def _sorted_by(rows: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    return sorted(rows, key=lambda row: _float(row, key), reverse=True)


def _style(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color="#e6e6e6", linewidth=0.8)
    ax.set_axisbelow(True)


def _plot_rank(rows: list[dict[str, str]], path: Path) -> None:
    rows = _sorted_by(rows, "final_hybrid_score")
    labels = [_label(row["system"]) for row in rows]
    scores = np.array([_float(row, "final_hybrid_score") for row in rows])
    lows = np.array([_float(row, "final_hybrid_ci_low") for row in rows])
    highs = np.array([_float(row, "final_hybrid_ci_high") for row in rows])
    xerr = np.vstack([scores - lows, highs - scores])
    y = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(9, 5.8))
    ax.barh(y, scores, color=[_color(row["system"]) for row in rows], alpha=0.92)
    ax.errorbar(scores, y, xerr=xerr, fmt="none", ecolor="#222222", capsize=3, linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlim(40, 94)
    ax.set_xlabel("Final score")
    ax.set_title("VSM Leaderboard", weight="bold")
    for yi, score in zip(y, scores):
        ax.text(score + 0.7, yi, f"{score:.1f}", va="center", fontsize=9)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_metrics(rows: list[dict[str, str]], path: Path) -> None:
    rows = _sorted_by(rows, "final_hybrid_score")
    systems = [row["system"] for row in rows]
    matrix = np.array([[_float(row, key, np.nan) for key, _ in METRICS] for row in rows])

    fig, ax = plt.subplots(figsize=(10, 5.8))
    im = ax.imshow(matrix, cmap="YlGnBu", vmin=20, vmax=100, aspect="auto")
    ax.set_xticks(np.arange(len(METRICS)))
    ax.set_xticklabels([name for _, name in METRICS], rotation=25, ha="right")
    ax.set_yticks(np.arange(len(systems)))
    ax.set_yticklabels([_label(system) for system in systems])
    ax.set_title("Judge Metrics", weight="bold")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            if not np.isnan(value):
                ax.text(j, i, f"{value:.0f}", ha="center", va="center", fontsize=7, color="#111111")
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_ablate(rows: list[dict[str, str]], path: Path) -> None:
    by_system = {row["system"]: row for row in rows}
    full = _float(by_system["ours_full"], "final_hybrid_score")
    systems = ["ours_no_peer", "ours_no_safety_critic", "ours_no_validator", "single_agent_stage_prompt", "single_agent_plain"]
    deltas = [full - _float(by_system[system], "final_hybrid_score") for system in systems]
    labels = [_label(system) for system in systems]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    y = np.arange(len(systems))
    ax.barh(y, deltas, color=[_color(system) for system in systems])
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Score drop vs TRACE-Full")
    ax.set_title("Ablations", weight="bold")
    for yi, delta in zip(y, deltas):
        ax.text(delta + 0.15, yi, f"-{delta:.1f}", va="center", fontsize=9)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_cape(rows: list[dict[str, str]], path: Path) -> None:
    rows = _sorted_by(rows, "cape2_observable_total")
    labels = [_label(row["system"]) for row in rows]
    values = [_float(row, "cape2_observable_total") for row in rows]
    y = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(9, 5.6))
    ax.barh(y, values, color=[_color(row["system"]) for row in rows])
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Observable pass rate")
    ax.set_title("CAPE-II", weight="bold")
    for yi, value in zip(y, values):
        ax.text(value + 1, yi, f"{value:.1f}", va="center", fontsize=9)
    _style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_yalom(rows: list[dict[str, str]], path: Path) -> None:
    by_system = {row["system"]: row for row in rows}
    systems = ["ours_full", "ours_no_safety_critic", "ours_no_validator", "ours_no_peer", "single_agent_stage_prompt", "single_agent_plain"]
    metrics = [
        ("peer_selection_accuracy", "Peer"),
        ("yalom_factor_match", "Yalom"),
        ("linh_persona_validity", "Linh"),
        ("group_therapy_dynamics", "Group"),
    ]

    x = np.arange(len(metrics))
    width = 0.12
    fig, ax = plt.subplots(figsize=(10, 5.2))
    for idx, system in enumerate(systems):
        row = by_system.get(system, {})
        values = [_float(row, key, np.nan) for key, _ in metrics]
        offset = (idx - (len(systems) - 1) / 2) * width
        ax.bar(x + offset, values, width, label=_label(system), color=_color(system), alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([name for _, name in metrics])
    ax.set_ylim(0, 105)
    ax.set_ylabel("Score")
    ax.set_title("Yalom / Peer", weight="bold")
    ax.legend(ncol=3, fontsize=8, frameon=False)
    ax.grid(axis="y", color="#e6e6e6", linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    main()
