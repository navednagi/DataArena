"""
Report generator for RPE accuracy analysis.

Outputs a human-readable console report + optionally a CSV.
"""

from __future__ import annotations

import csv
import io

from .analyzer import BlockLiftSummary, SetAccuracy


LIFT_LABELS = {"SQ": "Squat", "BN": "Bench Press", "DL": "Deadlift"}


def _trend_emoji(mean_dev: float) -> str:
    if abs(mean_dev) < 0.25:
        return "✅"
    elif mean_dev > 0:
        return "🔺"
    else:
        return "🔻"


def format_console_report(summaries: list[BlockLiftSummary]) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("  RPE ACCURACY REPORT  —  Rated RPE vs Mike T Chart Expected RPE")
    lines.append("=" * 72)
    lines.append(
        f"  Deviation = Rated RPE − Expected RPE\n"
        f"  +ve → you rated the set HARDER than the chart predicts\n"
        f"  −ve → you rated the set EASIER than the chart predicts\n"
        f"  ✅ well-calibrated (|mean| < 0.25)  🔺 over-rating  🔻 under-rating\n"
        f"  e1RM anchor = ensemble of top high-stress sets (RPE ≥ 8.0)\n"
    )

    current_block = None
    for s in summaries:
        if s.block != current_block:
            lines.append(f"\n{'─' * 72}")
            lines.append(f"  BLOCK: {s.block}")
            lines.append(f"{'─' * 72}")
            current_block = s.block

        lift_label = LIFT_LABELS.get(s.lift_type, s.lift_type)
        top = s.top_set
        trend = _trend_emoji(s.mean_deviation)

        lines.append(f"\n  {lift_label} ({s.lift_type})  {trend}")
        lines.append(
            f"    e1RM anchor (ensemble):  ≈ {s.top_set_e1rm:.1f} lbs  "
            f"({s.ensemble_size} high-stress sets)"
        )
        lines.append(
            f"    Display top set:         {top.load_lbs:.0f} lbs × {top.reps_actual} reps "
            f"@ RPE {top.rpe_actual}"
        )
        lines.append(f"    Sets analysed:           {s.n}")
        lines.append(f"    Mean deviation:          {s.mean_deviation:+.2f} RPE")
        lines.append(f"    Std deviation:           {s.std_deviation:.2f} RPE")
        lines.append(f"    Median deviation:        {s.median_deviation:+.2f} RPE")
        lines.append(f"    Range:                   {s.min_deviation:+.2f} to {s.max_deviation:+.2f} RPE")

        # Weekly progression table
        lines.append(f"\n    {'Wk':>3}  {'Load':>6}  {'Reps':>4}  {'Rated':>6}  {'Expect':>6}  {'Dev':>6}")
        lines.append(f"    {'--':>3}  {'------':>6}  {'----':>4}  {'------':>6}  {'------':>6}  {'------':>6}")
        for acc in sorted(s.set_accuracies, key=lambda a: (a.lift_set.week_index, -a.lift_set.load_lbs)):
            lines.append(
                f"    {acc.lift_set.week_index + 1:>3}  "
                f"{acc.lift_set.load_lbs:>6.0f}  "
                f"{acc.lift_set.reps_actual:>4}  "
                f"{acc.rated_rpe:>6.1f}  "
                f"{acc.expected_rpe:>6.1f}  "
                f"{acc.deviation:>+6.1f}"
            )

    lines.append(f"\n{'=' * 72}")
    lines.append("  OVERALL SUMMARY")
    lines.append(f"{'=' * 72}\n")
    lines.append(f"  {'Block':<14} {'Lift':<12} {'N':>4}  {'Mean Dev':>9}  {'Std':>6}  {'e1RM':>7}  {'Cal.'}")
    lines.append(f"  {'-'*14} {'-'*12} {'----':>4}  {'-'*9}  {'-'*6}  {'-'*7}  {'-'*12}")
    for s in summaries:
        trend = _trend_emoji(s.mean_deviation)
        lines.append(
            f"  {s.block:<14} {LIFT_LABELS.get(s.lift_type, s.lift_type):<12} "
            f"{s.n:>4}  {s.mean_deviation:>+9.2f}  {s.std_deviation:>6.2f}  "
            f"{s.top_set_e1rm:>6.0f}  {trend}"
        )
    lines.append("")
    return "\n".join(lines)


def export_csv(summaries: list[BlockLiftSummary]) -> str:
    """Return CSV string of per-set accuracy data."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "block", "lift_type", "week", "load_lbs", "reps_actual",
        "rpe_rated", "rpe_expected", "deviation",
        "e1rm_implied_lbs", "block_ensemble_e1rm_lbs", "ensemble_size"
    ])
    for s in summaries:
        for acc in sorted(s.set_accuracies, key=lambda a: (a.lift_set.week_index, -a.lift_set.load_lbs)):
            writer.writerow([
                s.block,
                acc.lift_set.lift_type,
                acc.lift_set.week_index + 1,
                acc.lift_set.load_lbs,
                acc.lift_set.reps_actual,
                acc.rated_rpe,
                acc.expected_rpe,
                round(acc.deviation, 2),
                round(acc.e1rm_implied, 1),
                round(s.top_set_e1rm, 1),
                s.ensemble_size,
            ])
    return output.getvalue()
