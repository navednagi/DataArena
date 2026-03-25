#!/usr/bin/env python3
"""
rpe-accuracy-caller
───────────────────
Compares your rated RPEs against Mike T's chart expectations,
anchored to your actual top-set performance per block.

Modes
─────
  (default)        Concise console report + summary table
  --full           Full verbose breakdown: per-set bars, weekly averages,
                   cross-block drift analysis
  --weekly         Telegram-ready weekly summary message (last block + last 2 weeks)
  --csv <file>     Export per-set data to CSV (combinable with any mode)

Usage
─────
  python main.py <workbook.xlsx>
  python main.py <workbook.xlsx> --full
  python main.py <workbook.xlsx> --weekly
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
else:
    from .src.parser import parse_workbook
    from .src.analyzer import analyze_all
    from .src.report import format_console_report, export_csv
    from .src.cli_report import full_cli_report
    from .src.weekly_summary import build_weekly_message


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
        help="Telegram-ready weekly summary: last block stats + last 2 weeks detail"
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

    if args.weekly:
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
