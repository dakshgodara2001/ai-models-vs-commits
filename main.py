"""
main.py
-------
Orchestrate the full pipeline:
  1. Fetch monthly GitHub commit counts via BigQuery → data/monthly_commits.csv
  2. Render the chart with LLM event overlays        → chart.png (or interactive)

Examples
--------
# Fetch 2023-01 → 2023-06 and plot:
    python main.py --project YOUR_GCP_PROJECT_ID

# Custom date range:
    python main.py --project YOUR_GCP_PROJECT_ID --start 2022-01 --end 2024-12

# Skip fetching (data already downloaded), just plot:
    python main.py --no-fetch

# Save chart to file:
    python main.py --project YOUR_GCP_PROJECT_ID --out chart.png

Authentication
--------------
Run once before using:
    gcloud auth application-default login
"""

import argparse
import re
import sys
from pathlib import Path


def _validate_month(value: str) -> str:
    """Validate YYYY-MM format and return the value unchanged."""
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise argparse.ArgumentTypeError(
            f"Invalid month format: '{value}'. Expected YYYY-MM (e.g. 2023-01)."
        )
    return value


def _parse_args():
    parser = argparse.ArgumentParser(
        description="LLM impact on GitHub commits — BigQuery pipeline."
    )
    parser.add_argument(
        "--project", default=None,
        help="GCP project ID to bill the BigQuery query against.",
    )
    parser.add_argument(
        "--start", default="2023-01", type=_validate_month,
        help="Start month YYYY-MM (default: 2023-01)",
    )
    parser.add_argument(
        "--end", default="2026-01", type=_validate_month,
        help="End month YYYY-MM (default: 2026-01)",
    )
    parser.add_argument(
        "--no-fetch", action="store_true",
        help="Skip fetch step; use existing data/monthly_commits.csv",
    )
    parser.add_argument(
        "--out", default=None,
        help="Save chart to this path (e.g. chart.png). Omit to show interactively.",
    )
    parser.add_argument(
        "--plot-start", default=None,
        help="Restrict chart to months >= YYYY-MM",
    )
    parser.add_argument(
        "--plot-end", default=None,
        help="Restrict chart to months <= YYYY-MM",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    csv_path = Path("data/monthly_commits.csv")

    # ------------------------------------------------------------------
    # Step 1: Fetch via BigQuery
    # ------------------------------------------------------------------
    if not args.no_fetch:
        if not args.project:
            print(
                "[ERROR] --project is required for BigQuery fetch.\n"
                "        Find yours at: https://console.cloud.google.com/\n"
                "        Or skip fetch with --no-fetch if data already exists.",
                file=sys.stderr,
            )
            sys.exit(1)

        from fetch_bigquery import fetch, load_existing_csv, save_csv

        # Only fetch months not already in the CSV
        existing = load_existing_csv()
        all_months = []
        y, m = int(args.start[:4]), int(args.start[5:7])
        ey, em = int(args.end[:4]), int(args.end[5:7])
        while (y, m) <= (ey, em):
            all_months.append(f"{y:04d}-{m:02d}")
            m += 1
            if m > 12:
                m = 1
                y += 1

        missing = [mo for mo in all_months if mo not in existing]
        if not missing:
            print("[INFO] All months already fetched. Using existing data.")
        else:
            # BigQuery BETWEEN fetches all months in the range, including
            # ones already cached. existing.update() deduplicates by
            # overwriting with fresh values, so this is safe but may
            # scan more data than strictly necessary.
            fetch_start, fetch_end = missing[0], missing[-1]
            print(f"[INFO] {len(existing)} month(s) cached. "
                  f"Fetching {len(missing)} new month(s): {fetch_start} → {fetch_end}")
            new_totals = fetch(args.project, fetch_start, fetch_end)
            existing.update(new_totals)
            save_csv(existing)
    else:
        if not csv_path.exists():
            print(
                f"[ERROR] No data file found at '{csv_path}'.\n"
                "        Run without --no-fetch to query BigQuery first.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"[INFO] Using existing data: {csv_path}")

    # ------------------------------------------------------------------
    # Step 2: Visualize
    # ------------------------------------------------------------------
    from visualize import load_commits, plot
    from llm_events import get_events_in_range

    df = load_commits(csv_path, args.plot_start, args.plot_end)

    if df.empty:
        print("[ERROR] No commit data in the requested plot range.", file=sys.stderr)
        sys.exit(1)

    start_date = df["date"].min().date()
    end_date   = df["date"].max().date()
    events     = get_events_in_range(start_date, end_date)

    print(f"\nPlotting {len(df)} months  |  {len(events)} LLM events")

    out_path = Path(args.out) if args.out else None
    plot(df, events, output_path=out_path)


if __name__ == "__main__":
    main()
