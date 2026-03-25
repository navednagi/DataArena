"""
Block drill-down report — deep week-by-week and session-by-session breakdown.

Triggered by: --blockX "Block N"

Covers:
  - Block overview: ensemble e1RM, calibration verdict per lift
  - Week-by-week table: sets, avg load, tonnage, avg rated RPE, avg dev, rolling avg dev
  - Session breakdown by day-of-week (when date data is available)
  - Rolling 3-week average deviation trend
  - ASCII plots: deviation trend by week, tonnage by week, load progression
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Optional

from .analyzer import BlockLiftSummary, SetAccuracy

LIFT_LABELS = {"SQ": "Squat", "BN": "Bench Press", "DL": "Deadlift"}
W = 80  # report width

DAY_NAMES = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bar_chart(values: list[float], labels: list[str], title: str, width: int = 40) -> list[str]:
    """
    Horizontal bar chart. Values can be positive or negative (deviation-style).
    For positive-only metrics (tonnage, load) all bars go right.
    """
    lines = [f"  {title}"]
    if not values:
        return lines

    all_positive = all(v >= 0 for v in values)
    max_abs = max(abs(v) for v in values) or 1.0

    for label, val in zip(labels, values):
        bar_len = int(abs(val) / max_abs * width)
        if all_positive:
            bar = "█" * bar_len
            lines.append(f"  {label:>6}  {bar:<{width}}  {val:.1f}")
        else:
            center = width // 2
            filled = int(abs(val) / max_abs * center)
            filled = min(filled, center)
            if val >= 0:
                bar = " " * center + "█" * filled + " " * (center - filled)
                marker = "▶"
            else:
                bar = " " * (center - filled) + "█" * filled + " " * (center + 1)
                marker = "◀"
            lines.append(f"  {label:>6}  {bar}  {val:+.2f}")
    return lines


def _rolling_avg(values: list[float], window: int = 3) -> list[Optional[float]]:
    """Compute rolling average, returning None for positions before window fills."""
    result: list[Optional[float]] = []
    for i, _ in enumerate(values):
        if i + 1 < window:
            result.append(None)
        else:
            result.append(statistics.mean(values[i + 1 - window: i + 1]))
    return result


def _section(title: str) -> str:
    pad = (W - len(title) - 4) // 2
    return f"\n{'═' * W}\n{'═' * pad}  {title}  {'═' * max(0, W - pad - len(title) - 4)}\n{'═' * W}"


def _sub(title: str) -> str:
    return f"\n  ── {title} {'─' * max(0, W - len(title) - 6)}"


def _trend_label(mean_dev: float) -> str:
    if abs(mean_dev) < 0.25:
        return "CALIBRATED ✅"
    elif mean_dev > 1.5:
        return "OVER-RATING 🔺🔺"
    elif mean_dev > 0:
        return "OVER-RATING 🔺 (slight)"
    elif mean_dev < -1.5:
        return "UNDER-RATING 🔻🔻"
    else:
        return "UNDER-RATING 🔻 (slight)"


# ── Main report ───────────────────────────────────────────────────────────────

def block_drill_report(
    summaries: list[BlockLiftSummary],
    block_name: str,
) -> str:
    """
    Generate a detailed drill-down report for a single block.

    Parameters
    ----------
    summaries : list[BlockLiftSummary]
        Full analysis output from analyze_all().
    block_name : str
        Target block name (e.g. "Block 5"). Case-insensitive match attempted.
    """
    # Case-insensitive match
    matched = [s for s in summaries if s.block.lower() == block_name.lower()]
    if not matched:
        available = sorted({s.block for s in summaries})
        return (
            f"Block '{block_name}' not found.\n"
            f"Available blocks: {', '.join(available)}"
        )

    lines = []
    lines.append("=" * W)
    lines.append(f"  BLOCK DRILL-DOWN: {matched[0].block}".center(W))
    lines.append("=" * W)
    lines.append(
        "\n  Deviation = Rated RPE − Expected RPE  (ensemble-anchored e1RM)\n"
        "  +ve = rated harder than chart predicts  |  −ve = rated easier\n"
    )

    for s in matched:
        label = LIFT_LABELS.get(s.lift_type, s.lift_type)

        # ── Lift header ──────────────────────────────────────────────────────
        lines.append(_section(f"{label} ({s.lift_type})"))

        top = s.top_set
        lines.append(f"  Ensemble e1RM:   ≈ {s.top_set_e1rm:.1f} lbs  ({s.top_set_e1rm * 0.453592:.1f} kg)")
        lines.append(f"  Ensemble sets:   {s.ensemble_size} high-stress sets (RPE ≥ 8.0)")
        lines.append(
            f"  Display top set: {top.load_lbs:.0f} lbs × {top.reps_actual} @ RPE {top.rpe_actual}"
            f"  (week {top.week_index + 1})"
        )
        lines.append(f"  Calibration:     {_trend_label(s.mean_deviation)}")
        lines.append(
            f"  Block stats:     mean {s.mean_deviation:+.2f} | "
            f"σ {s.std_deviation:.2f} | "
            f"median {s.median_deviation:+.2f} | "
            f"range [{s.min_deviation:+.2f}, {s.max_deviation:+.2f}]"
        )

        # ── Week-by-week table ───────────────────────────────────────────────
        lines.append(_sub("Week-by-Week Breakdown"))

        week_groups: dict[int, list[SetAccuracy]] = defaultdict(list)
        for acc in s.set_accuracies:
            week_groups[acc.lift_set.week_index].append(acc)

        sorted_weeks = sorted(week_groups.keys())
        wk_devs = []
        wk_labels = []
        wk_tonnage = []
        wk_loads = []

        lines.append(
            f"\n  {'Wk':>3}  {'Sets':>4}  {'AvgLoad':>8}  {'Tonnage':>8}  "
            f"{'AvgRPE':>7}  {'AvgDev':>7}  {'Roll3':>6}  {'Verdict'}"
        )
        lines.append(
            f"  {'──':>3}  {'────':>4}  {'───────':>8}  {'───────':>8}  "
            f"{'──────':>7}  {'──────':>7}  {'─────':>6}  {'───────'}"
        )

        for wk in sorted_weeks:
            accs = week_groups[wk]
            loads = [a.lift_set.load_lbs for a in accs]
            devs  = [a.deviation for a in accs]
            rpes  = [a.rated_rpe for a in accs]
            tonnage = sum(a.lift_set.load_lbs * a.lift_set.reps_actual for a in accs)

            avg_load    = statistics.mean(loads)
            avg_dev     = statistics.mean(devs)
            avg_rpe     = statistics.mean(rpes)

            wk_devs.append(avg_dev)
            wk_labels.append(f"Wk{wk+1}")
            wk_tonnage.append(tonnage)
            wk_loads.append(avg_load)

        roll3 = _rolling_avg(wk_devs, window=3)

        for i, wk in enumerate(sorted_weeks):
            accs = week_groups[wk]
            loads   = [a.lift_set.load_lbs for a in accs]
            devs    = [a.deviation for a in accs]
            rpes    = [a.rated_rpe for a in accs]
            tonnage = sum(a.lift_set.load_lbs * a.lift_set.reps_actual for a in accs)

            avg_load = statistics.mean(loads)
            avg_dev  = statistics.mean(devs)
            avg_rpe  = statistics.mean(rpes)
            r3       = f"{roll3[i]:+.2f}" if roll3[i] is not None else "  —  "
            verdict  = _trend_label(avg_dev)

            lines.append(
                f"  {wk+1:>3}  {len(accs):>4}  {avg_load:>8.1f}  "
                f"{tonnage:>8.0f}  {avg_rpe:>7.2f}  "
                f"{avg_dev:>+7.2f}  {r3:>6}  {verdict}"
            )

        # ── Session breakdown (day of week) ──────────────────────────────────
        dated_accs = [a for a in s.set_accuracies if a.lift_set.date is not None]
        if dated_accs:
            lines.append(_sub("Session Breakdown by Day-of-Week"))
            day_groups: dict[int, list[SetAccuracy]] = defaultdict(list)
            for acc in dated_accs:
                day_groups[acc.lift_set.date.weekday()].append(acc)

            lines.append(
                f"\n  {'Day':<5}  {'Sessions':>8}  {'Sets':>4}  "
                f"{'AvgLoad':>8}  {'Tonnage':>8}  {'AvgDev':>7}"
            )
            lines.append(
                f"  {'───':<5}  {'────────':>8}  {'────':>4}  "
                f"{'───────':>8}  {'───────':>8}  {'──────':>7}"
            )
            for day_idx in sorted(day_groups):
                accs_d = day_groups[day_idx]
                # Count unique dates as sessions
                sessions = len({a.lift_set.date for a in accs_d})
                devs   = [a.deviation for a in accs_d]
                loads  = [a.lift_set.load_lbs for a in accs_d]
                tonnage = sum(a.lift_set.load_lbs * a.lift_set.reps_actual for a in accs_d)
                lines.append(
                    f"  {DAY_NAMES.get(day_idx, '?'):<5}  {sessions:>8}  "
                    f"{len(accs_d):>4}  {statistics.mean(loads):>8.1f}  "
                    f"{tonnage:>8.0f}  {statistics.mean(devs):>+7.2f}"
                )

        # ── ASCII charts ─────────────────────────────────────────────────────
        if wk_labels:
            lines.append(_sub("Deviation Trend by Week"))
            lines.extend(_bar_chart(wk_devs, wk_labels, "Dev (Rated − Expected)", width=36))

            lines.append(_sub("Tonnage by Week"))
            lines.extend(_bar_chart(wk_tonnage, wk_labels, "Tonnage (lbs × reps)", width=36))

            lines.append(_sub("Avg Load Progression"))
            # Normalise load bars relative to min load for cleaner display
            min_load = min(wk_loads)
            load_delta = [v - min_load for v in wk_loads]
            lines.extend(_bar_chart(load_delta, wk_labels, "Load above block min (lbs)", width=36))
            # Also print absolute
            lines.append(f"\n  {'Wk':>6}  {'Avg Load (lbs)':>15}")
            for lbl, ld in zip(wk_labels, wk_loads):
                lines.append(f"  {lbl:>6}  {ld:>15.1f}")

    lines.append(f"\n{'=' * W}\n")
    return "\n".join(lines)
