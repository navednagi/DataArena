"""
Weekly summary generator.

Produces a concise Telegram-friendly message covering:
  - The most recent block's summary stats per lift
  - Last 2 weeks of set-level RPE deviation detail
"""

from __future__ import annotations

import datetime
from .analyzer import BlockLiftSummary, SetAccuracy
from .parser import LiftSet

LIFT_LABELS = {"SQ": "Squat", "BN": "Bench", "DL": "Deadlift"}


def _trend(mean_dev: float) -> str:
    if abs(mean_dev) < 0.25:
        return "✅ calibrated"
    elif mean_dev > 1.0:
        return "🔺🔺 over-rating"
    elif mean_dev > 0:
        return "🔺 slightly over"
    elif mean_dev < -1.0:
        return "🔻🔻 under-rating"
    else:
        return "🔻 slightly under"


def build_weekly_message(summaries: list[BlockLiftSummary]) -> str:
    """
    Build a concise Telegram-ready weekly summary message.
    Uses the last block found in summaries.
    Shows last 2 weeks of deviation for each lift.
    """
    if not summaries:
        return "No RPE data found to summarise."

    # Find the most recent block (last in list order, which matches block sheet order)
    last_block_name = summaries[-1].block
    last_block = [s for s in summaries if s.block == last_block_name]

    # Find max week index across all lifts in this block
    all_weeks = set()
    for s in last_block:
        for acc in s.set_accuracies:
            all_weeks.add(acc.lift_set.week_index)
    if not all_weeks:
        return "No sets found in last block."

    max_week = max(all_weeks)
    last_2_weeks = {max_week - 1, max_week} if max_week > 0 else {max_week}

    lines = []
    lines.append(f"📊 *RPE Accuracy — Weekly Report*")
    lines.append(f"Block: *{last_block_name}*\n")

    lines.append("*Block Summary (all weeks)*")
    for s in last_block:
        label = LIFT_LABELS.get(s.lift_type, s.lift_type)
        top = s.top_set
        lines.append(
            f"  {label}: mean dev {s.mean_deviation:+.2f} RPE | "
            f"σ {s.std_deviation:.2f} | {_trend(s.mean_deviation)}"
        )
        lines.append(
            f"    Top set: {top.load_lbs:.0f} lbs × {top.reps_actual} @ RPE {top.rpe_actual} "
            f"→ e1RM ≈ {s.top_set_e1rm:.0f} lbs"
        )

    lines.append(f"\n*Last 2 Weeks (Wk {max_week} & {max_week+1}) — Set Detail*")

    for s in last_block:
        label = LIFT_LABELS.get(s.lift_type, s.lift_type)
        recent = sorted(
            [a for a in s.set_accuracies if a.lift_set.week_index in last_2_weeks],
            key=lambda a: (a.lift_set.week_index, -a.lift_set.load_lbs)
        )
        if not recent:
            continue

        lines.append(f"\n  *{label}*")
        lines.append(f"  {'Wk':>2}  {'Load':>6}  {'Reps':>4}  {'Rated':>6}  {'Exp':>5}  {'Dev':>5}")
        for acc in recent:
            lines.append(
                f"  {acc.lift_set.week_index+1:>2}  "
                f"{acc.lift_set.load_lbs:>6.0f}  "
                f"{acc.lift_set.reps_actual:>4}  "
                f"{acc.rated_rpe:>6.1f}  "
                f"{acc.expected_rpe:>5.1f}  "
                f"{acc.deviation:>+5.1f}"
            )

    lines.append(f"\n_Generated {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC_")
    return "\n".join(lines)
