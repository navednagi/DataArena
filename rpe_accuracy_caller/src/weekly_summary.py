"""
Weekly RPE accuracy summary — analyst-style Telegram message.

Sections:
  1. Last block summary table (lift | n | mean dev | σ | verdict)
  2. Last 2 weeks — set-level detail table per lift
  3. Images: weekly deviation trend + cross-block calibration bar chart
"""

from __future__ import annotations

import datetime
import statistics
from .analyzer import BlockLiftSummary, SetAccuracy

LIFT_LABELS = {"SQ": "Squat", "BN": "Bench", "DL": "Deadlift"}


def _verdict(mean_dev: float, std: float) -> str:
    if abs(mean_dev) < 0.25:
        return "✅ on"
    elif mean_dev > 1.0:
        return "🔺 over"
    elif mean_dev > 0:
        return "↑ slight"
    elif mean_dev < -1.0:
        return "🔻 under"
    else:
        return "↓ slight"


def build_weekly_message(summaries: list[BlockLiftSummary]) -> str:
    if not summaries:
        return "No RPE data found."

    last_block_name = summaries[-1].block
    last_block = [s for s in summaries if s.block == last_block_name]

    # Max week in this block
    all_weeks = {acc.lift_set.week_index
                 for s in last_block for acc in s.set_accuracies}
    if not all_weeks:
        return "No sets in last block."

    max_week = max(all_weeks)
    last_2 = {max_week - 1, max_week} if max_week > 0 else {max_week}

    date_str = datetime.datetime.utcnow().strftime("%d %b %Y")
    lines = []

    # ── Header ──
    lines.append(f"📊 *RPE Accuracy Report — {date_str}*")
    lines.append(f"Block: *{last_block_name}*\n")

    # ── Block summary table ──
    lines.append("*Block Summary*")
    lines.append("```")
    lines.append(f"{'Lift':<8} {'N':>3}  {'Mean':>6}  {'σ':>5}  {'e1RM':>7}  {'Call'}")
    lines.append(f"{'─'*8} {'─'*3}  {'─'*6}  {'─'*5}  {'─'*7}  {'─'*8}")
    for s in last_block:
        label = LIFT_LABELS.get(s.lift_type, s.lift_type)
        verdict = _verdict(s.mean_deviation, s.std_deviation)
        lines.append(
            f"{label:<8} {s.n:>3}  {s.mean_deviation:>+6.2f}  "
            f"{s.std_deviation:>5.2f}  "
            f"{s.top_set_e1rm:>6.0f}lb  {verdict}"
        )
    lines.append("```")

    # ── Last 2 weeks detail ──
    lines.append(f"\n*Last 2 Weeks (Wk {max_week} & {max_week+1})*")

    for s in last_block:
        recent = sorted(
            [a for a in s.set_accuracies if a.lift_set.week_index in last_2],
            key=lambda a: (a.lift_set.week_index, -a.lift_set.load_lbs)
        )
        if not recent:
            continue

        label = LIFT_LABELS.get(s.lift_type, s.lift_type)

        # compute weekly avg dev for these 2 weeks
        devs = [a.deviation for a in recent]
        avg_dev = statistics.mean(devs)
        verdict = _verdict(avg_dev, statistics.stdev(devs) if len(devs) > 1 else 0)

        lines.append(f"\n*{label}* — avg dev {avg_dev:+.2f} {verdict}")
        lines.append("```")
        lines.append(f"{'Wk':>2}  {'Load':>5}  {'×':>1}{'Reps':<4}  {'Rated':>5}  {'Exp':>5}  {'Dev':>5}")
        lines.append(f"{'──':>2}  {'─────':>5}  {'─'*5}  {'─────':>5}  {'─────':>5}  {'─────':>5}")
        for acc in recent:
            lines.append(
                f"{acc.lift_set.week_index+1:>2}  "
                f"{acc.lift_set.load_lbs:>5.0f}  "
                f"×{acc.lift_set.reps_actual:<4}  "
                f"{acc.rated_rpe:>5.1f}  "
                f"{acc.expected_rpe:>5.1f}  "
                f"{acc.deviation:>+5.1f}"
            )
        lines.append("```")

    lines.append(f"\n_Anchored to top set per lift. Dev = Rated − Expected (Mike T chart)._")
    return "\n".join(lines)
