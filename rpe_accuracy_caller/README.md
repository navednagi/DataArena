# rpe-accuracy-caller

Analyses RPE accuracy across training blocks by comparing your rated RPEs to
what Mike Tuchscherer's RPE chart would have predicted, given your actual
performance at the final heavy top set of each block.

## What it does

For each **block × lift type** (Squat, Bench, Deadlift):

1. **Identifies the top set** — the heaviest set in the last week of the block
2. **Derives a ground-truth e1RM** from that top set using Mike T's percentage chart
3. **Back-calculates expected RPE** for every set in the block using that e1RM
4. **Computes deviation** = `rated_rpe − expected_rpe`
   - Positive → you rated the set *harder* than the chart predicts
   - Negative → you rated the set *easier* than the chart predicts
5. **Reports** mean, median, std deviation, and range per block × lift

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install openpyxl
```

## Usage

```bash
python rpe_accuracy_caller/main.py "Naved Training.xlsx"

# With CSV export:
python rpe_accuracy_caller/main.py "Naved Training.xlsx" --csv rpe_accuracy.csv
```

## Interpretation

| Mean Deviation | Meaning |
|---|---|
| < ±0.25 RPE | ✅ Well-calibrated |
| +0.25 to +1.0 | 🔺 Slightly over-rating effort |
| > +1.0 | 🔺🔺 Significantly over-rating (sets feel harder than they are) |
| −0.25 to −1.0 | 🔻 Slightly under-rating effort |
| < −1.0 | 🔻🔻 Significantly under-rating (sets feel easier than they are) |

## File structure

```
rpe_accuracy_caller/
├── main.py              # Entry point
├── README.md
└── src/
    ├── mike_t_chart.py  # Mike T RPE percentage lookup table + e1RM calcs
    ├── parser.py        # Excel workbook parser
    ├── analyzer.py      # Core accuracy analysis logic
    └── report.py        # Console report + CSV export
```
