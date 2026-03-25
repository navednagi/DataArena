"""
RPE Accuracy Analyzer

For each block and lift type:
  1. Find the final heavy top set (highest load in the last week)
  2. Use that set's e1RM as ground truth
  3. For every prior set in the block (same lift type), compute:
       - expected_rpe  = what Mike T's chart says RPE should have been
       - rated_rpe     = what was actually logged
       - deviation     = rated_rpe - expected_rpe  (positive = rated too hard)
  4. Aggregate: mean deviation, std deviation, count
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Optional

from .parser import LiftSet
from .mike_t_chart import calc_e1rm, expected_rpe as chart_expected_rpe


@dataclass
class SetAccuracy:
    lift_set: LiftSet
    e1rm_implied: float          # e1RM from this set's actual load/reps/rpe
    expected_rpe: float          # what Mike T chart expects given block e1RM
    rated_rpe: float             # what athlete logged
    deviation: float             # rated - expected  (+ve = rated harder than chart)


@dataclass
class BlockLiftSummary:
    block: str
    lift_type: str
    top_set: LiftSet             # final heavy top set (anchor)
    top_set_e1rm: float          # e1RM from the top set
    set_accuracies: list[SetAccuracy] = field(default_factory=list)

    # Stats
    n: int = 0
    mean_deviation: float = 0.0
    std_deviation: float = 0.0
    median_deviation: float = 0.0
    min_deviation: float = 0.0
    max_deviation: float = 0.0

    def compute_stats(self):
        devs = [s.deviation for s in self.set_accuracies]
        if not devs:
            return
        self.n = len(devs)
        self.mean_deviation = statistics.mean(devs)
        self.median_deviation = statistics.median(devs)
        self.min_deviation = min(devs)
        self.max_deviation = max(devs)
        self.std_deviation = statistics.stdev(devs) if len(devs) > 1 else 0.0


def find_top_set(sets: list[LiftSet]) -> Optional[LiftSet]:
    """
    Find the final heavy top set of a block:
    - Must have load, reps_actual, and rpe_actual
    - From the last week in the block
    - Highest load in that last week (as the 'top set')
    """
    valid = [s for s in sets if s.load_lbs and s.reps_actual and s.rpe_actual]
    if not valid:
        return None

    last_week = max(s.week_index for s in valid)
    last_week_sets = [s for s in valid if s.week_index == last_week]
    return max(last_week_sets, key=lambda s: s.load_lbs)


def analyze_block_lift(block_name: str, lift_type: str, sets: list[LiftSet]) -> Optional[BlockLiftSummary]:
    """
    Analyze RPE accuracy for one lift within one block.
    """
    lift_sets = [s for s in sets if s.lift_type == lift_type
                 and s.load_lbs and s.reps_actual and s.rpe_actual]
    if not lift_sets:
        return None

    top_set = find_top_set(lift_sets)
    if top_set is None:
        return None

    top_e1rm = calc_e1rm(top_set.load_lbs, top_set.rpe_actual, top_set.reps_actual)
    if top_e1rm is None or top_e1rm <= 0:
        return None

    summary = BlockLiftSummary(
        block=block_name,
        lift_type=lift_type,
        top_set=top_set,
        top_set_e1rm=top_e1rm,
    )

    for s in lift_sets:
        if s.load_lbs is None or s.reps_actual is None or s.rpe_actual is None:
            continue

        exp_rpe = chart_expected_rpe(s.load_lbs, top_e1rm, s.reps_actual)
        if exp_rpe is None:
            continue

        implied_e1rm = calc_e1rm(s.load_lbs, s.rpe_actual, s.reps_actual) or 0.0
        deviation = s.rpe_actual - exp_rpe

        summary.set_accuracies.append(SetAccuracy(
            lift_set=s,
            e1rm_implied=implied_e1rm,
            expected_rpe=exp_rpe,
            rated_rpe=s.rpe_actual,
            deviation=deviation,
        ))

    summary.compute_stats()
    return summary


def analyze_all(blocks: dict[str, list[LiftSet]]) -> list[BlockLiftSummary]:
    """
    Run analysis across all blocks and all lift types.
    Returns sorted list of BlockLiftSummary objects.
    """
    results = []
    for block_name, sets in blocks.items():
        for lift_type in ["SQ", "BN", "DL"]:
            summary = analyze_block_lift(block_name, lift_type, sets)
            if summary and summary.n > 0:
                results.append(summary)
    return results
