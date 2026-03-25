"""
RPE Accuracy Analyzer

For each block and lift type:
  1. Build an ensemble e1RM anchor from the top high-stress sets in the block
     (RPE >= 8.0, top-N by implied e1RM, trimmed mean — more robust than a
     single top set which can be misrated).
  2. For every set in the block (same lift type), compute:
       - expected_rpe  = what Mike T's chart says RPE should have been
       - rated_rpe     = what was actually logged
       - deviation     = rated_rpe − expected_rpe  (positive = rated too hard)
  3. Aggregate: mean deviation, std deviation, count

The legacy single-top-set path is preserved via find_top_set() for reference
and for callers that need the representative "anchor set" displayed in reports.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Optional

from .parser import LiftSet
from .mike_t_chart import calc_e1rm, expected_rpe as chart_expected_rpe

# ── Ensemble tuning constants ──────────────────────────────────────────────────
ENSEMBLE_MIN_RPE = 8.0      # Only consider sets at or above this RPE
ENSEMBLE_TOP_N   = 5        # Take up to this many sets by implied e1RM
ENSEMBLE_TRIM    = 1        # Drop this many from each tail when averaging
#  (trim=1 with top_n=5 → drop highest + lowest → mean of middle 3)
# ──────────────────────────────────────────────────────────────────────────────


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
    top_set: LiftSet             # representative high-stress set (for display)
    top_set_e1rm: float          # ensemble e1RM (robust anchor, not just top set)
    ensemble_size: int = 0       # number of sets used in ensemble
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
    Find the single heaviest set in the last week of the block.
    Used as the representative display anchor in reports.
    """
    valid = [s for s in sets if s.load_lbs and s.reps_actual and s.rpe_actual]
    if not valid:
        return None
    last_week = max(s.week_index for s in valid)
    last_week_sets = [s for s in valid if s.week_index == last_week]
    return max(last_week_sets, key=lambda s: s.load_lbs)


def ensemble_e1rm(
    sets: list[LiftSet],
    min_rpe: float = ENSEMBLE_MIN_RPE,
    top_n: int = ENSEMBLE_TOP_N,
    trim: int = ENSEMBLE_TRIM,
) -> Optional[float]:
    """
    Derive a robust e1RM anchor for a block-lift by ensembling high-stress sets.

    Algorithm:
      1. Filter to sets with rpe_actual >= min_rpe (high-stress threshold).
      2. Compute implied e1RM for each via Mike T's chart.
      3. Keep the top_n sets by implied e1RM (highest effort).
      4. Apply symmetric trim (drop `trim` from each tail).
      5. Return the trimmed mean of the remaining e1RMs.

    Falls back to the single top-set e1RM if fewer than (2*trim + 1) sets remain.
    """
    valid = [
        s for s in sets
        if s.load_lbs and s.reps_actual and s.rpe_actual
        and s.rpe_actual >= min_rpe
    ]
    if not valid:
        # Fallback: relax RPE filter and use single top set
        top = find_top_set(sets)
        if top is None:
            return None
        return calc_e1rm(top.load_lbs, top.rpe_actual, top.reps_actual)

    # Compute implied e1RM for each candidate
    candidates: list[tuple[float, LiftSet]] = []
    for s in valid:
        e1rm = calc_e1rm(s.load_lbs, s.rpe_actual, s.reps_actual)
        if e1rm and e1rm > 0:
            candidates.append((e1rm, s))

    if not candidates:
        return None

    # Sort descending by implied e1RM, take top_n
    candidates.sort(key=lambda x: x[0], reverse=True)
    top_candidates = candidates[:top_n]

    e1rms = [e for e, _ in top_candidates]

    # Trimmed mean — drop `trim` from each tail if enough samples
    min_required = 2 * trim + 1
    if len(e1rms) >= min_required:
        trimmed = sorted(e1rms)[trim: len(e1rms) - trim]
    else:
        trimmed = e1rms  # not enough for trimming, use all

    return statistics.mean(trimmed)


def analyze_block_lift(block_name: str, lift_type: str, sets: list[LiftSet]) -> Optional[BlockLiftSummary]:
    """
    Analyze RPE accuracy for one lift within one block.
    Uses an ensemble e1RM anchor for robustness.
    """
    lift_sets = [
        s for s in sets
        if s.lift_type == lift_type
        and s.load_lbs and s.reps_actual and s.rpe_actual
    ]
    if not lift_sets:
        return None

    # Representative display set (heaviest in last week — unchanged for reports)
    top_set = find_top_set(lift_sets)
    if top_set is None:
        return None

    # Robust ensemble e1RM anchor
    anchor_e1rm = ensemble_e1rm(lift_sets)
    if anchor_e1rm is None or anchor_e1rm <= 0:
        return None

    # Count how many sets contributed to ensemble
    high_stress = [
        s for s in lift_sets
        if s.rpe_actual >= ENSEMBLE_MIN_RPE
    ]
    used_in_ensemble = min(len(high_stress), ENSEMBLE_TOP_N)

    summary = BlockLiftSummary(
        block=block_name,
        lift_type=lift_type,
        top_set=top_set,
        top_set_e1rm=anchor_e1rm,
        ensemble_size=used_in_ensemble,
    )

    for s in lift_sets:
        exp_rpe = chart_expected_rpe(s.load_lbs, anchor_e1rm, s.reps_actual)
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
