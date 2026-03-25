"""
Weekly RPE accuracy summary — analyst-style Telegram message.

Shows the current week vs prior 2 weeks with delta callouts.
Sections:
  1. Block summary table (ensemble-anchored e1RM, lift | n | mean dev | σ | verdict)
  2. Week-over-week comparison: this week / week-1 / week-2 per lift
     — avg dev, tonnage, avg load, delta trend
  3. Calibration drift callout if week-over-week deviation is shifting
"""

from __future__ import annotations

import datetime
import statistics
from .analyzer import BlockLiftSummary, SetAccuracy

LIFT_LABELS = {"SQ": "Squat", "BN": "Bench", "DL": "Deadlift"}


def _verdict(mean_dev: float, std: float = 0.0) -> str:
    if abs(mean_dev) < 0.25:
        return "✅ on"
    elif mean_dev > 1.0:
        return "🔺🔺 over"
    elif mean_dev > 0:
        return "🔺 slight+"
    elif mean_dev < -1.0:
        return "🔻🔻 under"
    else:
        return "🔻 slight−"


def _delta_arrow(current: float, prior: float) -> str:
    """Return a directional indicator for drift between two mean deviations."""
    diff = current - prior
    if abs(diff) < 0.1:
        return "→"
    elif diff > 0:
        return f"↑{diff:+.1f}"
    else:
        return f"↓{diff:+.1f}"


def _week_stats(accs: list[SetAccuracy]) -> dict:
    """Compute summary stats for a list of set accuracies."""
    if not accs:
        return {}
    devs = [a.deviation for a in accs]
    loads = [a.lift_set.load_lbs for a in accs]
    tonnage = sum(
        (a.lift_set.load_lbs * a.lift_set.reps_actual * (a.lift_set.lift_set.sets or 1))
        if hasattr(a.lift_set, 'lift_set') else
        a.lift_set.load_lbs * a.lift_set.reps_actual
        for a in accs
    )
    return {
        "n": len(devs),
        "mean_dev": statistics.mean(devs),
        "std_dev": statistics.stdev(devs) if len(devs) > 1 else 0.0,
        "avg_load": statistics.mean(loads),
        "tonnage": tonnage,
    }


def _week_stats_simple(accs: list[SetAccuracy]) -> dict:
    """Compute summary stats for a list of set accuracies (simple tonnage)."""
    if not accs:
        return {}
    devs = [a.deviation for a in accs]
    loads = [a.lift_set.load_lbs for a in accs]
    # Simple tonnage: sum of load * reps per set row
    tonnage = sum(a.lift_set.load_lbs * a.lift_set.reps_actual for a in accs)
    return {
        "n": len(devs),
        "mean_dev": statistics.mean(devs),
        "std_dev": statistics.stdev(devs) if len(devs) > 1 else 0.0,
        "avg_load": statistics.mean(loads),
        "tonnage": tonnage,
    }


def build_weekly_message(summaries: list[BlockLiftSummary]) -> str:
    if not summaries:
        return "No RPE data found."

    last_block_name = summaries[-1].block
    last_block = [s for s in summaries if s.block == last_block_name]

    all_weeks = {
        acc.lift_set.week_index
        for s in last_block
        for acc in s.set_accuracies
    }
    if not all_weeks:
        return "No sets in last block."

    max_week = max(all_weeks)
    # Current = max_week, prior1 = max_week-1, prior2 = max_week-2
    cur_wk   = max_week
    prior1   = max_week - 1
    prior2   = max_week - 2

    date_str = datetime.datetime.utcnow().strftime("%d %b %Y")
    lines = []

    # ── Header ──
    lines.append(f"📊 *RPE Accuracy Report — {date_str}*")
    lines.append(f"Block: *{last_block_name}*  |  Week {max_week + 1} of block\n")

    # ── Block summary table ──
    lines.append("*Block Summary (ensemble-anchored)*")
    lines.append("```")
    lines.append(f"{'Lift':<8} {'N':>3}  {'Mean':>6}  {'σ':>5}  {'e1RM':>7}  {'Ens':>3}  {'Call'}")
    lines.append(f"{'─'*8} {'─'*3}  {'─'*6}  {'─'*5}  {'─'*7}  {'─'*3}  {'─'*10}")
    for s in last_block:
        label = LIFT_LABELS.get(s.lift_type, s.lift_type)
        verdict = _verdict(s.mean_deviation, s.std_deviation)
        lines.append(
            f"{label:<8} {s.n:>3}  {s.mean_deviation:>+6.2f}  "
            f"{s.std_deviation:>5.2f}  "
            f"{s.top_set_e1rm:>6.0f}lb  "
            f"{s.ensemble_size:>3}  {verdict}"
        )
    lines.append("```")

    # ── Week-over-week comparison ──
    lines.append(f"\n*Week-over-Week  (Wk{prior2+1} → Wk{prior1+1} → Wk{cur_wk+1})*")

    for s in last_block:
        label = LIFT_LABELS.get(s.lift_type, s.lift_type)

        wk_map: dict[int, list[SetAccuracy]] = {}
        for acc in s.set_accuracies:
            wk_map.setdefault(acc.lift_set.week_index, []).append(acc)

        cur_stats   = _week_stats_simple(wk_map.get(cur_wk, []))
        prior1_stats = _week_stats_simple(wk_map.get(prior1, []))
        prior2_stats = _week_stats_simple(wk_map.get(prior2, []))

        if not cur_stats:
            continue

        # Build delta indicators
        delta_cur_p1 = (
            _delta_arrow(cur_stats["mean_dev"], prior1_stats["mean_dev"])
            if prior1_stats else "—"
        )
        delta_p1_p2 = (
            _delta_arrow(prior1_stats["mean_dev"], prior2_stats["mean_dev"])
            if (prior1_stats and prior2_stats) else "—"
        )

        lines.append(f"\n*{label}*")
        lines.append("```")
        lines.append(f"{'Wk':<4}  {'Sets':>4}  {'AvgLoad':>8}  {'Tonnage':>8}  {'AvgDev':>7}  {'Drift'}")
        lines.append(f"{'──':<4}  {'────':>4}  {'───────':>8}  {'───────':>8}  {'──────':>7}  {'─────'}")

        for wk_idx, stats, drift in [
            (prior2, prior2_stats, ""),
            (prior1, prior1_stats, delta_p1_p2),
            (cur_wk, cur_stats, delta_cur_p1),
        ]:
            if not stats:
                lines.append(f"Wk{wk_idx+1:<2}  {'—':>4}  {'—':>8}  {'—':>8}  {'—':>7}  {drift}")
                continue
            lines.append(
                f"Wk{wk_idx+1:<2}  {stats['n']:>4}  "
                f"{stats['avg_load']:>8.1f}  "
                f"{stats['tonnage']:>8.0f}  "
                f"{stats['mean_dev']:>+7.2f}  "
                f"{drift}"
            )
        lines.append("```")

        # Drift callout
        if cur_stats and prior1_stats:
            diff = cur_stats["mean_dev"] - prior1_stats["mean_dev"]
            if abs(diff) >= 0.5:
                direction = "worsening (more over-rating)" if diff > 0 else "improving (less over-rating)"
                lines.append(
                    f"⚠️ {label} calibration drifting {direction}: "
                    f"{diff:+.1f} RPE vs last week"
                )

    lines.append(
        f"\n_e1RM anchored to ensemble of top {last_block[0].ensemble_size if last_block else 'N'} "
        f"high-stress sets (RPE ≥ 8.0). Dev = Rated − Expected (Mike T chart)._"
    )
    return "\n".join(lines)
