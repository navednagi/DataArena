"""
Parser for Naved's training Excel workbook.

Each block sheet (Block 1 through Block 8, Meet Prep) contains multiple
weeks laid out side-by-side. Each week has the same repeating column
structure:

  col+0  = lift type (SQ / BN / DL)
  col+1  = exercise name
  col+2  = (skip)
  col+3  = sets (prescribed)
  col+4  = reps (prescribed)
  col+5  = RPE/% prescribed
  col+6  = load (lbs, actual)
  col+7  = load (kg, formula — skip)
  col+8  = reps (actual)
  col+9  = RPE (actual/rated)
  col+10 = e1RM (formula — skip)
  col+11 = e1RM (kg, formula — skip)
  col+12 = remarks

The pattern repeats every ~18 columns across the sheet for each week.
Week headers (dates / "Monday" labels) appear around row 5.
Data rows start around row 7.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import openpyxl
from openpyxl.utils import get_column_letter


BLOCK_SHEETS = ["Block 1", "Block 2", "Block 3", "Block 4",
                "Block 5", "Block 6", "Block 7", "Block 8", "Meet Prep"]

LIFT_TYPES = {"SQ", "BN", "DL"}

# Column offsets within a week's column group (0-indexed from week anchor col)
COL_LIFT_TYPE      = 0
COL_EXERCISE       = 1
COL_SETS           = 3
COL_REPS_PRESCRIBED = 4
COL_RPE_PRESCRIBED = 5
COL_LOAD_LBS       = 6
COL_REPS_ACTUAL    = 8
COL_RPE_ACTUAL     = 9

# Week anchor columns (1-indexed) — the column where 'lift type' (SQ/BN/DL) lives
# Discovered empirically: weeks repeat every ~18 columns starting from col B (2)
# We detect them dynamically by scanning for LIFT_TYPES in col B-ish
WEEK_COL_STEP = 18  # approximate; detected dynamically below
HEADER_ROW = 6       # row with "Exercise", "Sets", etc.
DATA_ROW_START = 7   # first actual data row


@dataclass
class LiftSet:
    block: str
    week_index: int          # 0-based week within the block
    date: Optional[datetime.date]
    lift_type: str           # SQ / BN / DL
    exercise: str
    sets: Optional[int]
    reps_prescribed: Optional[int]
    rpe_prescribed: Optional[float]
    load_lbs: Optional[float]
    reps_actual: Optional[int]
    rpe_actual: Optional[float]


def _to_float(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v) -> Optional[int]:
    f = _to_float(v)
    return int(f) if f is not None else None


def _to_date(v) -> Optional[datetime.date]:
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.date() if isinstance(v, datetime.datetime) else v
    return None


def _detect_week_anchor_cols(ws, max_col: int) -> list[int]:
    """
    Scan the header rows to find all week anchor columns.
    A week anchor is a column where data rows contain 'SQ', 'BN', or 'DL'.
    We scan row DATA_ROW_START to DATA_ROW_START+20 for LIFT_TYPE values.
    """
    anchors = []
    # Sample a few data rows
    sample_rows = list(ws.iter_rows(
        min_row=DATA_ROW_START,
        max_row=min(DATA_ROW_START + 20, ws.max_row),
        values_only=True
    ))

    for col_idx in range(1, max_col + 1):
        hits = 0
        for row in sample_rows:
            cell_val = row[col_idx - 1] if col_idx - 1 < len(row) else None
            if isinstance(cell_val, str) and cell_val.strip().upper() in LIFT_TYPES:
                hits += 1
        if hits >= 2:  # at least 2 lift-type entries in this column
            anchors.append(col_idx)

    # Deduplicate anchors that are too close together (< 5 cols apart)
    filtered = []
    for a in sorted(anchors):
        if not filtered or a - filtered[-1] >= 5:
            filtered.append(a)
    return filtered


def _find_week_date(ws, week_col: int) -> Optional[datetime.date]:
    """
    Look in rows 1-6 near week_col for a date value.
    """
    for row_idx in range(1, HEADER_ROW + 1):
        for col_offset in range(-2, 6):
            c = week_col + col_offset
            if c < 1:
                continue
            cell = ws.cell(row=row_idx, column=c)
            d = _to_date(cell.value)
            if d is not None:
                return d
    return None


def parse_block(ws, block_name: str) -> list[LiftSet]:
    """Parse all lift sets from a single block worksheet."""
    sets: list[LiftSet] = []
    max_col = ws.max_column
    max_row = ws.max_row

    week_anchors = _detect_week_anchor_cols(ws, max_col)
    if not week_anchors:
        return sets

    for week_idx, anchor_col in enumerate(week_anchors):
        week_date = _find_week_date(ws, anchor_col)

        for row_idx in range(DATA_ROW_START, max_row + 1):
            def cell_val(col_offset):
                c = anchor_col + col_offset
                if c < 1 or c > max_col:
                    return None
                return ws.cell(row=row_idx, column=c).value

            lift_type_raw = cell_val(COL_LIFT_TYPE)
            if not isinstance(lift_type_raw, str):
                continue
            lift_type = lift_type_raw.strip().upper()
            if lift_type not in LIFT_TYPES:
                continue

            exercise_raw = cell_val(COL_EXERCISE)
            exercise = str(exercise_raw).strip() if exercise_raw else lift_type

            sets_val = _to_int(cell_val(COL_SETS))
            reps_prescribed = _to_int(cell_val(COL_REPS_PRESCRIBED))
            rpe_prescribed_raw = cell_val(COL_RPE_PRESCRIBED)
            rpe_prescribed = _to_float(rpe_prescribed_raw) if not isinstance(rpe_prescribed_raw, str) else None
            load_lbs = _to_float(cell_val(COL_LOAD_LBS))
            reps_actual = _to_int(cell_val(COL_REPS_ACTUAL))
            rpe_actual = _to_float(cell_val(COL_RPE_ACTUAL))

            # Skip rows with no meaningful data
            if load_lbs is None or rpe_actual is None or reps_actual is None:
                continue
            if load_lbs <= 0:
                continue

            sets.append(LiftSet(
                block=block_name,
                week_index=week_idx,
                date=week_date,
                lift_type=lift_type,
                exercise=exercise,
                sets=sets_val,
                reps_prescribed=reps_prescribed,
                rpe_prescribed=rpe_prescribed,
                load_lbs=load_lbs,
                reps_actual=reps_actual,
                rpe_actual=rpe_actual,
            ))

    return sets


def parse_workbook(path: str | Path) -> dict[str, list[LiftSet]]:
    """
    Parse all block sheets from the workbook.
    Returns dict of {block_name: [LiftSet, ...]}
    """
    wb = openpyxl.load_workbook(str(path), data_only=True)
    result = {}
    for sheet_name in BLOCK_SHEETS:
        if sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            result[sheet_name] = parse_block(ws, sheet_name)
    return result
