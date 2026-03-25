"""
Full CLI breakdown report — on-demand, verbose, schedulable.

Covers every block, every lift, every set.
Includes:
  - Per-block/lift stats
  - Week-by-week progression tables
  - Overall calibration summary
  - Cross-block drift analysis (how your calibration changes block to block)
"""

from __future__ import annotations

import datetime
from .analyzer import BlockLiftSummary, SetAccuracy

LIFT_LABELS = {"SQ": "Squat", "BN": "Bench Press", "DL": "Deadlift"}
W = 80  # report width


def _bar(value: float, scale: float = 3.0, width: int = 20) -> str:
    """Simple ASCII deviation bar. Center = 0."""
    center = width // 2
    filled = int(abs(value) / scale * center)
    filled = min(filled, center)
    if value >= 0:
        return " " * center + "█" * filled + " " * (width - center - filled)
    else:
        return " " * (center - filled) + "█" * filled + " " * (center + 1)


def _trend_label(mean_dev: float) -> str:
    if abs(mean_dev) < 0.25:
        return "CALIBRATED    ✅"
    elif mean_dev > 1.5:
        return "OVER-RATING   🔺🔺 (sets feel harder than they are)"
    elif mean_dev > 0:
        return "OVER-RATING   🔺 (slight)"
    elif mean_dev < -1.5:
        return "UNDER-RATING  🔻🔻 (sets feel easier than they are)"
    else:
        return "UNDER-RATING  🔻 (slight)"


def _section(title: str) -> str:
    pad = (W - len(title) - 4) // 2
    return f"\n{'═' * W}\n{'═' * pad}  {title}  {'═' * (W - pad - len(title) - 4)}\n{'═' * W}"


def _sub(title: str) -> str:
    return f"\n{'─' * W}\n  {title}\n{'─' * W}"


def full_cli_report(summaries: list[BlockLiftSummary]) -> str:
    lines = []

    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines.append("=" * W)
    lines.append(f"  RPE ACCURACY — FULL BREAKDOWN REPORT".center(W))
    lines.append(f"  Generated: {now}".center(W))
    lines.append("=" * W)
    lines.append(
        "\n  Deviation = Rated RPE − Expected RPE (from Mike T chart, anchored to block top set)\n"
        "  +ve = you rated the set harder than the chart predicts\n"
        "  −ve = you rated the set easier than the chart predicts\n"
    )

    current_block = None

    for s in summaries:
        # Block header
        if s.block != current_block:
            lines.append(_section(f"BLOCK: {s.block}"))
            current_block = s.block

        label = LIFT_LABELS.get(s.lift_type, s.lift_type)
        lines.append(_sub(f"{label}  ({s.lift_type})"))

        top = s.top_set
        lines.append(f"  Ensemble e1RM anchor:")
        lines.append(
            f"    ≈ {s.top_set_e1rm:.1f} lbs  ({s.top_set_e1rm * 0.453592:.1f} kg)"
            f"  ←  {s.ensemble_size} high-stress sets (RPE ≥ 8.0)"
        )
        lines.append(f"  Display top set:")
        lines.append(
            f"    {top.load_lbs:.0f} lbs × {top.reps_actual} reps @ RPE {top.rpe_actual}"
            f"  (week {top.week_index + 1})"
        )
        lines.append(f"\n  Calibration stats ({s.n} sets):")
        lines.append(f"    Verdict:          {_trend_label(s.mean_deviation)}")
        lines.append(f"    Mean deviation:   {s.mean_deviation:+.3f} RPE")
        lines.append(f"    Std deviation:    {s.std_deviation:.3f} RPE")
        lines.append(f"    Median deviation: {s.median_deviation:+.3f} RPE")
        lines.append(f"    Range:            {s.min_deviation:+.2f} to {s.max_deviation:+.2f} RPE")

        # Deviation bar chart
        lines.append(f"\n  Deviation distribution (each █ ≈ 0.15 RPE):")
        lines.append(f"  {'Under ←':>10}  {'0':^{20}}  {'→ Over':6}")
        lines.append(f"  {'-'*10}  {'-'*20}  {'-'*6}")

        for acc in sorted(s.set_accuracies, key=lambda a: (a.lift_set.week_index, -a.lift_set.load_lbs)):
            bar = _bar(acc.deviation, scale=4.0, width=20)
            lines.append(
                f"  Wk{acc.lift_set.week_index+1:>2} {acc.lift_set.load_lbs:>6.0f}lbs "
                f"×{acc.lift_set.reps_actual:<2} @{acc.rated_rpe:<4.1f}  "
                f"|{bar}|  {acc.deviation:>+5.1f}"
            )

        # Week-by-week summary
        lines.append(f"\n  Week-by-week averages:")
        lines.append(f"  {'Wk':>3}  {'Sets':>4}  {'Avg Load':>9}  {'Avg Rated':>10}  {'Avg Expect':>11}  {'Avg Dev':>8}")
        lines.append(f"  {'--':>3}  {'----':>4}  {'-'*9}  {'-'*10}  {'-'*11}  {'-'*8}")

        week_groups: dict[int, list[SetAccuracy]] = {}
        for acc in s.set_accuracies:
            week_groups.setdefault(acc.lift_set.week_index, []).append(acc)

        for wk_idx in sorted(week_groups):
            accs = week_groups[wk_idx]
            avg_load = sum(a.lift_set.load_lbs for a in accs) / len(accs)
            avg_rated = sum(a.rated_rpe for a in accs) / len(accs)
            avg_exp = sum(a.expected_rpe for a in accs) / len(accs)
            avg_dev = sum(a.deviation for a in accs) / len(accs)
            lines.append(
                f"  {wk_idx+1:>3}  {len(accs):>4}  {avg_load:>9.1f}  {avg_rated:>10.2f}  "
                f"{avg_exp:>11.2f}  {avg_dev:>+8.2f}"
            )

    # ── Cross-block drift ──
    lines.append(_section("CROSS-BLOCK CALIBRATION DRIFT"))
    lines.append(
        "  How your RPE calibration has evolved across blocks.\n"
        "  Positive drift = over-rating trending worse. Negative = improving accuracy.\n"
    )

    for lift_type in ["SQ", "BN", "DL"]:
        label = LIFT_LABELS.get(lift_type, lift_type)
        lift_sums = [s for s in summaries if s.lift_type == lift_type]
        if not lift_sums:
            continue

        lines.append(f"\n  {label}:")
        lines.append(f"  {'Block':<16} {'N':>4}  {'Mean Dev':>9}  {'Std':>6}  {'Verdict'}")
        lines.append(f"  {'-'*16} {'----':>4}  {'-'*9}  {'-'*6}  {'-'*20}")
        for s in lift_sums:
            lines.append(
                f"  {s.block:<16} {s.n:>4}  {s.mean_deviation:>+9.2f}  "
                f"{s.std_deviation:>6.2f}  {_trend_label(s.mean_deviation)}"
            )

    # ── Overall summary ──
    lines.append(_section("OVERALL SUMMARY"))
    all_devs = [acc.deviation for s in summaries for acc in s.set_accuracies]
    if all_devs:
        import statistics
        overall_mean = statistics.mean(all_devs)
        overall_std = statistics.stdev(all_devs) if len(all_devs) > 1 else 0.0
        overall_median = statistics.median(all_devs)
        lines.append(f"\n  Total sets analysed:  {len(all_devs)}")
        lines.append(f"  Overall mean dev:     {overall_mean:+.3f} RPE")
        lines.append(f"  Overall std dev:      {overall_std:.3f} RPE")
        lines.append(f"  Overall median dev:   {overall_median:+.3f} RPE")
        lines.append(f"  Verdict:              {_trend_label(overall_mean)}")

    lines.append(f"\n{'=' * W}\n")
    return "\n".join(lines)
