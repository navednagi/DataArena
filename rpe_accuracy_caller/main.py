#!/usr/bin/env python3
"""
rpe-accuracy-caller
───────────────────
Parses a training Excel workbook, analyses RPE accuracy block by block,
and reports how your rated RPEs compare to what Mike T's chart would predict
given your actual top-set performance.

Usage:
    python main.py <path_to_workbook.xlsx> [--csv <output.csv>]

Example:
    python main.py "Naved Training.xlsx"
    python main.py "Naved Training.xlsx" --csv rpe_accuracy.csv
"""

import argparse
import sys
from pathlib import Path

# Allow running as script or as module
if __name__ == "__main__" and __package__ is None:
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from src.parser import parse_workbook
    from src.analyzer import analyze_all
    from src.report import format_console_report, export_csv
else:
    from .src.parser import parse_workbook
    from .src.analyzer import analyze_all
    from .src.report import format_console_report, export_csv


def main():
    parser = argparse.ArgumentParser(
        description="RPE Accuracy Caller — compare rated RPEs to Mike T chart expectations."
    )
    parser.add_argument("workbook", help="Path to the training Excel workbook (.xlsx)")
    parser.add_argument("--csv", metavar="OUTPUT_CSV", help="Optional: export per-set data to CSV")
    args = parser.parse_args()

    workbook_path = Path(args.workbook)
    if not workbook_path.exists():
        print(f"Error: file not found: {workbook_path}", file=sys.stderr)
        sys.exit(1)

    print(f"📂 Parsing workbook: {workbook_path.name} ...")
    blocks = parse_workbook(workbook_path)
    total_sets = sum(len(s) for s in blocks.values())
    print(f"✅ Loaded {len(blocks)} block(s), {total_sets} total sets\n")

    if total_sets == 0:
        print("No sets found. Check that the workbook matches the expected format.")
        sys.exit(1)

    print("🔍 Analysing RPE accuracy ...")
    summaries = analyze_all(blocks)
    print(f"✅ Analysed {len(summaries)} block × lift combinations\n")

    report = format_console_report(summaries)
    print(report)

    if args.csv:
        csv_data = export_csv(summaries)
        Path(args.csv).write_text(csv_data)
        print(f"📊 CSV exported to: {args.csv}")


if __name__ == "__main__":
    main()
