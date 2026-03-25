#!/usr/bin/env python3
"""
send_weekly.py — generate weekly RPE accuracy report and send to Telegram via OpenClaw.

Usage:
    python send_weekly.py <workbook.xlsx>

Requires: OpenClaw CLI (`openclaw`) with a configured Telegram account.
Sends:
  1. Text summary message (Markdown)
  2. Weekly deviation trend chart (PNG)
  3. Cross-block calibration chart (PNG)
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from src.parser import parse_workbook
    from src.analyzer import analyze_all
    from src.weekly_summary import build_weekly_message
    from src.plots import plot_weekly_deviation, plot_cross_block_deviation
else:
    from .src.parser import parse_workbook
    from .src.analyzer import analyze_all
    from .src.weekly_summary import build_weekly_message
    from .src.plots import plot_weekly_deviation, plot_cross_block_deviation


def send_telegram_message(text: str):
    result = subprocess.run(
        ["openclaw", "send", "--channel", "telegram", "--message", text],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[warn] message send failed: {result.stderr.strip()}", file=sys.stderr)
    else:
        print("[ok] message sent", file=sys.stderr)


def send_telegram_image(image_bytes: bytes, caption: str = ""):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(image_bytes)
        tmp_path = f.name

    cmd = ["openclaw", "send", "--channel", "telegram", "--media", tmp_path]
    if caption:
        cmd += ["--caption", caption]

    result = subprocess.run(cmd, capture_output=True, text=True)
    Path(tmp_path).unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"[warn] image send failed: {result.stderr.strip()}", file=sys.stderr)
    else:
        print("[ok] image sent", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Send weekly RPE accuracy report to Telegram.")
    parser.add_argument("workbook", help="Path to training Excel workbook (.xlsx)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print output without sending to Telegram")
    args = parser.parse_args()

    wb_path = Path(args.workbook)
    if not wb_path.exists():
        print(f"Error: {wb_path} not found", file=sys.stderr)
        sys.exit(1)

    print("Parsing workbook...", file=sys.stderr)
    blocks = parse_workbook(wb_path)
    summaries = analyze_all(blocks)

    last_block_name = summaries[-1].block if summaries else None

    print("Building message...", file=sys.stderr)
    message = build_weekly_message(summaries)

    print("Generating plots...", file=sys.stderr)
    trend_png = plot_weekly_deviation(summaries, last_block_name) if last_block_name else b""
    cross_block_png = plot_cross_block_deviation(summaries)

    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN — message that would be sent:\n")
        print(message)
        print("\n[weekly trend chart would be attached]")
        print("[cross-block chart would be attached]")
        return

    print("Sending...", file=sys.stderr)
    send_telegram_message(message)
    if trend_png:
        send_telegram_image(trend_png, caption=f"{last_block_name} — Weekly Deviation Trend")
    if cross_block_png:
        send_telegram_image(cross_block_png, caption="Cross-Block RPE Calibration")

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
