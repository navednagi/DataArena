"""
Plot generator for RPE accuracy reports.

Produces two charts:
  1. Weekly deviation trend (line chart) — for the last block
  2. Cross-block mean deviation bar chart — all blocks, all lifts
"""

from __future__ import annotations

import io
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

from .analyzer import BlockLiftSummary

LIFT_LABELS = {"SQ": "Squat", "BN": "Bench", "DL": "Deadlift"}
LIFT_COLORS = {"SQ": "#4C9BE8", "BN": "#E87B4C", "DL": "#5DBD72"}

STYLE = {
    "bg":      "#1A1A2E",
    "panel":   "#16213E",
    "grid":    "#2A2A4A",
    "text":    "#E0E0E0",
    "subtext": "#8888AA",
    "zero":    "#555577",
}


def _apply_dark_style(fig, ax):
    fig.patch.set_facecolor(STYLE["bg"])
    ax.set_facecolor(STYLE["panel"])
    ax.tick_params(colors=STYLE["text"], labelsize=9)
    ax.xaxis.label.set_color(STYLE["text"])
    ax.yaxis.label.set_color(STYLE["text"])
    ax.title.set_color(STYLE["text"])
    for spine in ax.spines.values():
        spine.set_edgecolor(STYLE["grid"])
    ax.grid(color=STYLE["grid"], linestyle="--", linewidth=0.6, alpha=0.7)
    ax.axhline(0, color=STYLE["zero"], linewidth=1.2, linestyle="-", alpha=0.9)


def plot_weekly_deviation(summaries: list[BlockLiftSummary], block_name: str) -> bytes:
    """
    Line chart: weekly average RPE deviation for each lift in a block.
    Returns PNG bytes.
    """
    block_sums = [s for s in summaries if s.block == block_name]
    if not block_sums:
        return b""

    fig, ax = plt.subplots(figsize=(9, 4.5))
    _apply_dark_style(fig, ax)

    plotted = False
    for s in block_sums:
        week_groups: dict[int, list[float]] = {}
        for acc in s.set_accuracies:
            week_groups.setdefault(acc.lift_set.week_index, []).append(acc.deviation)

        if not week_groups:
            continue

        weeks = sorted(week_groups)
        avgs = [statistics.mean(week_groups[w]) for w in weeks]
        week_labels = [f"Wk {w+1}" for w in weeks]

        color = LIFT_COLORS.get(s.lift_type, "#AAAAAA")
        ax.plot(week_labels, avgs, marker="o", linewidth=2, markersize=6,
                color=color, label=LIFT_LABELS.get(s.lift_type, s.lift_type))
        plotted = True

    if not plotted:
        plt.close(fig)
        return b""

    ax.set_title(f"{block_name} — Weekly Avg RPE Deviation", fontsize=12, pad=12)
    ax.set_ylabel("Deviation (Rated − Expected RPE)", fontsize=9)
    ax.set_xlabel("Week", fontsize=9)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%+.1f"))

    # Shade comfort zone
    ax.axhspan(-0.25, 0.25, color="#334455", alpha=0.4, label="±0.25 calibrated zone")

    legend = ax.legend(fontsize=9, framealpha=0.3, facecolor=STYLE["panel"],
                       labelcolor=STYLE["text"], edgecolor=STYLE["grid"])

    plt.tight_layout(pad=1.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=STYLE["bg"])
    plt.close(fig)
    return buf.getvalue()


def plot_cross_block_deviation(summaries: list[BlockLiftSummary]) -> bytes:
    """
    Grouped bar chart: mean RPE deviation per block, grouped by lift type.
    Returns PNG bytes.
    """
    # Collect block names in order
    blocks = list(dict.fromkeys(s.block for s in summaries))
    lifts = ["SQ", "BN", "DL"]

    # Build matrix: blocks × lifts
    data: dict[str, list[float | None]] = {lt: [] for lt in lifts}
    for block in blocks:
        for lt in lifts:
            match = next((s for s in summaries if s.block == block and s.lift_type == lt), None)
            data[lt].append(match.mean_deviation if match else None)

    x = np.arange(len(blocks))
    bar_width = 0.25
    offsets = [-bar_width, 0, bar_width]

    fig, ax = plt.subplots(figsize=(11, 5))
    _apply_dark_style(fig, ax)

    # Cap y-axis at ±3 to prevent outliers from compressing the scale
    all_vals = [v for lt in lifts for v in data[lt] if v is not None]
    y_max = min(max(abs(v) for v in all_vals) + 0.5, 3.0) if all_vals else 3.0

    for i, lt in enumerate(lifts):
        vals = data[lt]
        heights = []
        for v in vals:
            heights.append(v if v is not None else 0)

        bars = ax.bar(x + offsets[i], heights, bar_width - 0.03,
                      color=LIFT_COLORS[lt], alpha=0.85,
                      label=LIFT_LABELS.get(lt, lt))

        # Value labels only on bars with |dev| >= 0.25 to reduce clutter
        for bar, v in zip(bars, vals):
            if v is not None and abs(v) >= 0.25:
                clamped = max(-y_max + 0.2, min(y_max - 0.2, v))
                y_pos = clamped + (0.08 if v >= 0 else -0.22)
                label = f"{v:+.1f}{'*' if abs(v) > y_max else ''}"
                ax.text(bar.get_x() + bar.get_width() / 2, y_pos,
                        label, ha="center", va="bottom",
                        fontsize=7.5, color=STYLE["text"])

    ax.set_title("Cross-Block RPE Calibration — Mean Deviation per Block", fontsize=12, pad=12)
    ax.set_ylabel("Mean Deviation (Rated − Expected RPE)", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([b.replace("Block ", "Blk ") for b in blocks], fontsize=8, rotation=15)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%+.1f"))
    ax.set_ylim(-y_max, y_max)

    # Calibrated band
    ax.axhspan(-0.25, 0.25, color="#334455", alpha=0.4)
    ax.text(len(blocks) - 0.4, 0.05, "calibrated zone", fontsize=7,
            color=STYLE["subtext"], va="bottom", ha="right")

    legend = ax.legend(fontsize=9, framealpha=0.3, facecolor=STYLE["panel"],
                       labelcolor=STYLE["text"], edgecolor=STYLE["grid"])

    plt.tight_layout(pad=1.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=STYLE["bg"])
    plt.close(fig)
    return buf.getvalue()
