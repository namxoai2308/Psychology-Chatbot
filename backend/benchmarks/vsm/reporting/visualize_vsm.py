from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchmarks.vsm.reporting.sample_data import DISPLAY_NAMES, METRIC_DISPLAY, SYSTEMS


COLORS = {
    "ours_full": "#1b9e77",
    "ours_multi_agent": "#1b9e77",
    "ours_no_peer": "#66c2a5",
    "ours_no_validator": "#a6d854",
    "ours_no_safety_critic": "#ffd92f",
    "single_agent_stage_prompt": "#8da0cb",
    "single_agent_plain": "#b3b3b3",
    "prompt_1_1": "#377eb8",
    "soulchat": "#984ea3",
    "mindchat": "#ff7f00",
    "base_model": "#666666",
    "dry_run": "#999999",
    "ours_structural": "#4daf4a",
    "seallm": "#a65628",
    "camel": "#f781bf",
    "camel_cbt": "#e41a1c",
}


def generate_all_figures(summary: dict[str, Any], figures_dir: Path) -> list[Path]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        figures_dir / "fig_1_overall_radar.png",
        figures_dir / "fig_2_route_grouped_bar.png",
        figures_dir / "fig_3_safety_heatmap.png",
        figures_dir / "fig_4_yalom_dynamics.png",
        figures_dir / "fig_5_failure_stacked_bar.png",
        figures_dir / "fig_6_fallback_by_stage.png",
        figures_dir / "fig_7_cost_latency_scatter.png",
    ]
    _plot_overall_radar(summary, paths[0])
    _plot_route_grouped_bar(summary, paths[1])
    _plot_safety_heatmap(summary, paths[2])
    _plot_yalom_dynamics(summary, paths[3])
    _plot_failure_stacked_bar(summary, paths[4])
    _plot_fallback_by_stage(summary, paths[5])
    _plot_cost_latency_scatter(summary, paths[6])
    return paths


def _plot_overall_radar(summary: dict[str, Any], path: Path) -> None:
    metrics = list(METRIC_DISPLAY.keys())
    labels = [METRIC_DISPLAY[m] for m in metrics]
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw={"polar": True})
    for system in summary.get("systems", SYSTEMS):
        values = []
        data = summary.get("overall", {}).get(system, {})
        for metric in metrics:
            value = data.get(metric)
            values.append(0.0 if value is None else float(value))
        values += values[:1]
        ax.plot(angles, values, label=DISPLAY_NAMES.get(system, system), linewidth=2.0, color=COLORS.get(system))
        if system in {"ours_full", "ours_multi_agent"}:
            ax.fill(angles, values, alpha=0.18, color=COLORS.get(system))

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_title("Overall VSM Profile", fontsize=16, weight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.12), fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_route_grouped_bar(summary: dict[str, Any], path: Path) -> None:
    routes = ["CBT", "MBI", "BA"]
    systems = summary.get("systems", SYSTEMS)
    by_key = {(r["system"], r["route"]): r for r in summary.get("route_performance", [])}
    x = np.arange(len(routes))
    width = 0.14
    fig, ax = plt.subplots(figsize=(11, 6))
    for i, system in enumerate(systems):
        values = [float((by_key.get((system, route), {}) or {}).get("technique_fidelity") or 0.0) for route in routes]
        ax.bar(x + (i - len(systems) / 2) * width + width / 2, values, width, label=DISPLAY_NAMES.get(system, system), color=COLORS.get(system))
    ax.set_xticks(x)
    ax.set_xticklabels(routes)
    ax.set_ylabel("Technique Fidelity")
    ax.set_ylim(0, 100)
    ax.set_title("Route-Level Performance", fontsize=15, weight="bold")
    ax.legend(fontsize=8, ncol=3)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_safety_heatmap(summary: dict[str, Any], path: Path) -> None:
    systems = summary.get("systems", SYSTEMS)
    scenario_keys = ["crisis_safe_response", "medical_boundary", "dependency_boundary", "adversarial_pass_rate"]
    labels = ["Crisis", "Medical Boundary", "Dependency", "Adversarial"]
    matrix = np.array(
        [[float(summary.get("safety", {}).get(system, {}).get(key) or 0.0) for system in systems] for key in scenario_keys]
    )
    fig, ax = plt.subplots(figsize=(10, 5.6))
    im = ax.imshow(matrix, cmap="YlGnBu", vmin=0, vmax=100)
    ax.set_xticks(np.arange(len(systems)))
    ax.set_xticklabels([DISPLAY_NAMES.get(s, s) for s in systems], rotation=25, ha="right")
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, f"{matrix[i, j]:.1f}", ha="center", va="center", color="black", fontsize=8)
    ax.set_title("Safety and Adversarial Robustness", fontsize=15, weight="bold")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_yalom_dynamics(summary: dict[str, Any], path: Path) -> None:
    factors = summary.get("yalom_factors", {})
    labels = list(factors.keys())
    values = [float(v) for v in factors.values()]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(labels, values, color="#1b9e77")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Pass Rate")
    ax.set_title("Yalom Group Therapy Dynamics", fontsize=15, weight="bold")
    for y, value in enumerate(values):
        ax.text(value + 1, y, f"{value:.1f}", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_failure_stacked_bar(summary: dict[str, Any], path: Path) -> None:
    systems = summary.get("systems", SYSTEMS)
    selected = ["stage_mismatch", "route_bleed", "unsafe_advice", "generic_response", "wrong_peer", "fallback_used"]
    bottoms = np.zeros(len(systems))
    fig, ax = plt.subplots(figsize=(11, 6))
    cmap = plt.get_cmap("tab20")
    for idx, failure in enumerate(selected):
        values = np.array([summary.get("failure_taxonomy", {}).get(failure, {}).get(system, 0) for system in systems], dtype=float)
        ax.bar([DISPLAY_NAMES.get(s, s) for s in systems], values, bottom=bottoms, label=failure, color=cmap(idx))
        bottoms += values
    ax.set_ylabel("Failure Count")
    ax.set_title("Failure Distribution by System", fontsize=15, weight="bold")
    ax.tick_params(axis="x", rotation=25)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_fallback_by_stage(summary: dict[str, Any], path: Path) -> None:
    data = summary.get("fallback_by_stage", {})
    stages = list(data.keys())
    values = [float(v) for v in data.values()]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(stages, values, color="#d95f02")
    ax.set_ylabel("Fallback Rate (%)")
    ax.set_title("Fallback Rate by Stage", fontsize=15, weight="bold")
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def _plot_cost_latency_scatter(summary: dict[str, Any], path: Path) -> None:
    systems = summary.get("systems", SYSTEMS)
    fig, ax = plt.subplots(figsize=(8, 6))
    for system in systems:
        data = summary.get("overall", {}).get(system, {})
        latency = float(data.get("avg_latency_seconds") or 0.0)
        score = float(data.get("vsm_total") or 0.0)
        cost = float(data.get("token_cost_estimate") or 0.01)
        ax.scatter(latency, score, s=max(cost * 5000, 60), color=COLORS.get(system), alpha=0.75, label=DISPLAY_NAMES.get(system, system))
        ax.text(latency + 0.03, score, DISPLAY_NAMES.get(system, system), fontsize=8)
    ax.set_xlabel("Average Latency (seconds)")
    ax.set_ylabel("VSM Total")
    ax.set_title("Quality, Cost, and Latency Tradeoff", fontsize=15, weight="bold")
    ax.set_xlim(left=0)
    ax.set_ylim(0, 100)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
