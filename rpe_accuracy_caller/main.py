#!/usr/bin/env python3
"""
rpe-accuracy-caller
───────────────────
Compares your rated RPEs against Mike T's chart expectations,
anchored to an ensemble of high-stress sets per block (RPE ≥ 8.0, top 5 by
implied e1RM, trimmed mean). More robust than a single top-set anchor.

Modes
─────
  (default)          Concise console report + summary table
  --full             Full verbose breakdown: per-set bars, weekly averages,
                     cross-block drift analysis
  --weekly           Telegram-ready weekly summary: current week vs prior 2 weeks,
                     drift callouts, block-level calibration table
  --blockX <name>    Deep drill-down for a single block: week-by-week table,
                     session-by-day breakdown, rolling 3-week avg, ASCII charts
                     e.g. --blockX "Block 5"
  --csv <file>       Export per-set data to CSV (combinable with any mode)

Usage
─────
  python main.py <workbook.xlsx>
  python main.py <workbook.xlsx> --full
  python main.py <workbook.xlsx> --weekly
  python main.py <workbook.xlsx> --blockX "Block 5"
  python main.py <workbook.xlsx> --blockX "Block 5" --csv block5.csv
  python main.py <workbook.xlsx> --full --csv rpe_data.csv
"""

import argparse
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from src.parser import parse_workbook
    from src.analyzer import analyze_all
    from src.report import format_console_report, export_csv
    from src.cli_report import full_cli_report
    from src.weekly_summary import build_weekly_message
    from src.block_drill import block_drill_report
else:
    from .src.parser import parse_workbook
    from .src.analyzer import analyze_all
    from .src.report import format_console_report, export_csv
    from .src.cli_report import full_cli_report
    from .src.weekly_summary import build_weekly_message
    from .src.block_drill import block_drill_report


def main():
    parser = argparse.ArgumentParser(
        description="RPE Accuracy Caller — compare rated RPEs to Mike T chart expectations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("workbook", help="Path to the training Excel workbook (.xlsx)")
    parser.add_argument(
        "--full", action="store_true",
        help="Full verbose breakdown with per-set bars, weekly averages, cross-block drift"
    )
    parser.add_argument(
        "--weekly", action="store_true",
        help="Weekly summary: current week vs prior 2 weeks, with drift callouts"
    )
    parser.add_argument(
        "--blockX", metavar="BLOCK_NAME",
        help='Deep drill-down for a single block (e.g. --blockX "Block 5")'
    )
    parser.add_argument(
        "--csv", metavar="OUTPUT_CSV",
        help="Export per-set accuracy data to CSV"
    )
    args = parser.parse_args()

    workbook_path = Path(args.workbook)
    if not workbook_path.exists():
        print(f"Error: file not found: {workbook_path}", file=sys.stderr)
        sys.exit(1)

    print(f"📂 Parsing: {workbook_path.name} ...", file=sys.stderr)
    blocks = parse_workbook(workbook_path)
    total_sets = sum(len(s) for s in blocks.values())
    print(f"✅ {len(blocks)} block(s) | {total_sets} sets loaded\n", file=sys.stderr)

    if total_sets == 0:
        print("No sets found. Check the workbook format.", file=sys.stderr)
        sys.exit(1)

    summaries = analyze_all(blocks)

    if args.blockX:
        print(block_drill_report(summaries, args.blockX))
    elif args.weekly:
        print(build_weekly_message(summaries))
    elif args.full:
        print(full_cli_report(summaries))
    else:
        print(format_console_report(summaries))

    if args.csv:
        csv_data = export_csv(summaries)
        Path(args.csv).write_text(csv_data)
        print(f"\n📊 CSV → {args.csv}", file=sys.stderr)


if __name__ == "__main__":
    main()
