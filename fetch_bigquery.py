"""
fetch_bigquery.py
-----------------
Pull monthly GitHub commit totals from the public GitHub Archive dataset
on Google BigQuery — completes in seconds instead of hours.

Public dataset:  bigquery-public-data.github_archive (or githubarchive.month.*)
Billing:         ~$0.30–$0.60 per 6-month query at $5/TB (well within free tier quota)

Authentication (pick one):
  1. gcloud CLI (recommended for local use):
       gcloud auth application-default login
  2. Service-account key:
       export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

Usage:
    python fetch_bigquery.py --project YOUR_GCP_PROJECT_ID
    python fetch_bigquery.py --project YOUR_GCP_PROJECT_ID --start 2022-01 --end 2024-12
"""

import argparse
import csv
from pathlib import Path

from google.cloud import bigquery

DATA_DIR   = Path("data")
OUTPUT_CSV = DATA_DIR / "monthly_commits.csv"

# ---------------------------------------------------------------------------
# BigQuery SQL
# ---------------------------------------------------------------------------
# githubarchive.month.* has one table per month named YYYYMM.
# payload is a raw JSON string; $.size is the authoritative commit count.
# We cast to INT64 and guard against NULL / non-numeric values with SAFE_CAST.
QUERY_TEMPLATE = """
SELECT
    FORMAT_TIMESTAMP('%Y-%m', created_at) AS month,
    SUM(SAFE_CAST(JSON_EXTRACT_SCALAR(payload, '$.size') AS INT64)) AS commits
FROM
    `githubarchive.month.*`
WHERE
    _TABLE_SUFFIX BETWEEN @start_suffix AND @end_suffix
    AND type = 'PushEvent'
GROUP BY
    month
ORDER BY
    month
"""


def _suffix(yyyy_mm: str) -> str:
    """Convert 'YYYY-MM' → 'YYYYMM' for BigQuery table suffix."""
    return yyyy_mm.replace("-", "")


def fetch(project: str, start_month: str, end_month: str) -> dict[str, int]:
    """
    Run the BigQuery query and return {YYYY-MM: commit_count}.

    Args:
        project:     GCP project ID used for billing.
        start_month: Inclusive start, e.g. '2023-01'.
        end_month:   Inclusive end,   e.g. '2023-06'.
    """
    client = bigquery.Client(project=project)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_suffix", "STRING", _suffix(start_month)),
            bigquery.ScalarQueryParameter("end_suffix",   "STRING", _suffix(end_month)),
        ]
    )

    print(f"Running BigQuery query  ({start_month} → {end_month}) …")
    print(f"  Billing project : {project}")
    print(f"  Dataset         : githubarchive.month.*\n")

    job = client.query(QUERY_TEMPLATE, job_config=job_config)

    # Wait for results and report bytes processed
    results = job.result()
    gb_processed = (job.total_bytes_processed or 0) / 1e9
    print(f"  Query complete  : {gb_processed:.1f} GB scanned "
          f"(~${gb_processed * 0.005:.2f} cost)")

    totals: dict[str, int] = {}
    for row in results:
        if row.commits is not None:
            totals[row.month] = int(row.commits)

    return totals


def load_existing_csv() -> dict[str, int]:
    """Load previously saved monthly totals."""
    totals: dict[str, int] = {}
    if OUTPUT_CSV.exists():
        with OUTPUT_CSV.open() as f:
            for row in csv.DictReader(f):
                totals[row["month"]] = int(row["commits"])
    return totals


def save_csv(totals: dict[str, int]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "commits"])
        for month in sorted(totals):
            writer.writerow([month, totals[month]])
    print(f"\n  Saved {len(totals)} month(s) → {OUTPUT_CSV}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch GitHub commit counts via BigQuery."
    )
    parser.add_argument(
        "--project", required=True,
        help="GCP project ID to bill the query against.",
    )
    parser.add_argument(
        "--start", default="2023-01",
        help="Start month YYYY-MM (default: 2023-01)",
    )
    parser.add_argument(
        "--end", default="2023-06",
        help="End month YYYY-MM (default: 2023-06)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    totals = fetch(args.project, args.start, args.end)
    save_csv(totals)
    print("\nDone. Run visualize.py to generate the chart.")
