"""
Mike Tuchscherer RPE Chart

Percentage of 1RM lookup table indexed by RPE and rep count.
Source: Reactive Training Systems (RTS) - Mike T RPE percentages.
"""

# RPE → {reps: percentage_of_1rm}
# Rows = RPE (10.0 down to 0.5 in 0.5 steps)
# Cols = Reps (1 through 12)
_CHART = {
    10.0: {1: 1.000, 2: 0.955, 3: 0.922, 4: 0.892, 5: 0.863, 6: 0.837, 7: 0.811, 8: 0.786, 9: 0.762, 10: 0.739, 11: 0.707, 12: 0.680},
     9.5: {1: 0.978, 2: 0.939, 3: 0.907, 4: 0.878, 5: 0.850, 6: 0.824, 7: 0.799, 8: 0.774, 9: 0.751, 10: 0.723, 11: 0.694, 12: 0.667},
     9.0: {1: 0.955, 2: 0.922, 3: 0.892, 4: 0.863, 5: 0.837, 6: 0.811, 7: 0.786, 8: 0.762, 9: 0.739, 10: 0.707, 11: 0.680, 12: 0.653},
     8.5: {1: 0.939, 2: 0.907, 3: 0.878, 4: 0.850, 5: 0.824, 6: 0.799, 7: 0.774, 8: 0.751, 9: 0.723, 10: 0.694, 11: 0.667, 12: 0.640},
     8.0: {1: 0.922, 2: 0.892, 3: 0.863, 4: 0.837, 5: 0.811, 6: 0.786, 7: 0.762, 8: 0.739, 9: 0.707, 10: 0.680, 11: 0.653, 12: 0.626},
     7.5: {1: 0.907, 2: 0.878, 3: 0.850, 4: 0.824, 5: 0.799, 6: 0.774, 7: 0.751, 8: 0.723, 9: 0.694, 10: 0.667, 11: 0.640, 12: 0.613},
     7.0: {1: 0.892, 2: 0.863, 3: 0.837, 4: 0.811, 5: 0.786, 6: 0.762, 7: 0.739, 8: 0.707, 9: 0.680, 10: 0.653, 11: 0.626, 12: 0.599},
     6.5: {1: 0.878, 2: 0.850, 3: 0.824, 4: 0.799, 5: 0.774, 6: 0.751, 7: 0.723, 8: 0.694, 9: 0.667, 10: 0.640, 11: 0.613, 12: 0.586},
     6.0: {1: 0.863, 2: 0.837, 3: 0.811, 4: 0.786, 5: 0.762, 6: 0.739, 7: 0.707, 8: 0.680, 9: 0.653, 10: 0.626, 11: 0.599, 12: 0.572},
     5.5: {1: 0.850, 2: 0.824, 3: 0.799, 4: 0.774, 5: 0.751, 6: 0.723, 7: 0.694, 8: 0.667, 9: 0.640, 10: 0.613, 11: 0.586, 12: 0.559},
     5.0: {1: 0.837, 2: 0.811, 3: 0.786, 4: 0.762, 5: 0.739, 6: 0.707, 7: 0.680, 8: 0.653, 9: 0.626, 10: 0.599, 11: 0.572, 12: 0.545},
     4.5: {1: 0.824, 2: 0.799, 3: 0.774, 4: 0.751, 5: 0.723, 6: 0.694, 7: 0.667, 8: 0.640, 9: 0.613, 10: 0.586, 11: 0.559, 12: 0.532},
     4.0: {1: 0.811, 2: 0.786, 3: 0.762, 4: 0.739, 5: 0.707, 6: 0.680, 7: 0.653, 8: 0.626, 9: 0.599, 10: 0.572, 11: 0.545, 12: 0.518},
     3.5: {1: 0.799, 2: 0.774, 3: 0.751, 4: 0.723, 5: 0.694, 6: 0.667, 7: 0.640, 8: 0.613, 9: 0.586, 10: 0.559, 11: 0.532, 12: 0.505},
     3.0: {1: 0.786, 2: 0.762, 3: 0.739, 4: 0.707, 5: 0.680, 6: 0.653, 7: 0.626, 8: 0.599, 9: 0.572, 10: 0.545, 11: 0.518, 12: 0.491},
     2.5: {1: 0.774, 2: 0.751, 3: 0.723, 4: 0.694, 5: 0.667, 6: 0.640, 7: 0.613, 8: 0.586, 9: 0.559, 10: 0.532, 11: 0.505, 12: 0.478},
     2.0: {1: 0.762, 2: 0.739, 3: 0.707, 4: 0.680, 5: 0.653, 6: 0.626, 7: 0.599, 8: 0.572, 9: 0.545, 10: 0.518, 11: 0.491, 12: 0.464},
     1.5: {1: 0.751, 2: 0.723, 3: 0.694, 4: 0.667, 5: 0.640, 6: 0.613, 7: 0.586, 8: 0.559, 9: 0.532, 10: 0.505, 11: 0.478, 12: 0.451},
     1.0: {1: 0.739, 2: 0.707, 3: 0.680, 4: 0.653, 5: 0.626, 6: 0.599, 7: 0.572, 8: 0.545, 9: 0.518, 10: 0.491, 11: 0.464, 12: 0.437},
     0.5: {1: 0.723, 2: 0.694, 3: 0.667, 4: 0.640, 5: 0.613, 6: 0.586, 7: 0.559, 8: 0.532, 9: 0.505, 10: 0.478, 11: 0.451, 12: 0.424},
}

# Sorted RPE values for nearest-match lookups
_RPE_LEVELS = sorted(_CHART.keys(), reverse=True)


def get_percentage(rpe: float, reps: int) -> float | None:
    """
    Return the Mike T chart percentage for a given RPE and rep count.
    Clamps reps to 1-12 range. Returns None if RPE is out of range.
    """
    rpe = round(rpe * 2) / 2  # snap to nearest 0.5
    reps = max(1, min(12, int(reps)))
    row = _CHART.get(rpe)
    if row is None:
        return None
    return row.get(reps)


def calc_e1rm(load: float, rpe: float, reps: int) -> float | None:
    """
    Calculate estimated 1RM from load, RPE, and reps using Mike T's chart.
    e1RM = load / percentage
    """
    pct = get_percentage(rpe, reps)
    if pct is None or pct == 0:
        return None
    return load / pct


def expected_rpe(load: float, e1rm: float, reps: int) -> float | None:
    """
    Given a known e1RM, load, and rep count — find the RPE that the
    Mike T chart would predict for that set.
    Returns the closest RPE level (to 0.5 precision), or None if out of range.
    """
    if e1rm <= 0:
        return None
    target_pct = load / e1rm
    reps = max(1, min(12, int(reps)))

    best_rpe = None
    best_diff = float("inf")
    for rpe_level in _RPE_LEVELS:
        chart_pct = _CHART[rpe_level].get(reps)
        if chart_pct is None:
            continue
        diff = abs(chart_pct - target_pct)
        if diff < best_diff:
            best_diff = diff
            best_rpe = rpe_level
    return best_rpe
