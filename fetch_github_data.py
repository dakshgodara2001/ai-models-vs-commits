"""
fetch_github_data.py
--------------------
Stream GitHub Archive hourly files, extract PushEvents, and aggregate
total commits per YYYY-MM bucket into data/monthly_commits.csv.

GitHub Archive URL pattern:
    https://data.gharchive.org/YYYY-MM-DD-H.json.gz
    where H is 0-23 (no leading zero).

Memory strategy:
- Download each .json.gz file in streaming chunks.
- Decompress and parse line-by-line (one JSON object per line).
- Only keep a running dict of {YYYY-MM: commit_count}; never buffer events.
- Checkpoint progress after every completed day so interrupted runs resume.
"""

import csv
import gzip
import io
import json
import sys
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import requests
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GHARCHIVE_URL = "https://data.gharchive.org/{date}-{hour}.json.gz"
DATA_DIR = Path("data")
OUTPUT_CSV = DATA_DIR / "monthly_commits.csv"
CHECKPOINT_FILE = DATA_DIR / ".fetch_checkpoint"

CHUNK_SIZE = 1 << 20        # 1 MB download chunks
REQUEST_TIMEOUT = 120        # seconds
MAX_RETRIES = 5
RETRY_BACKOFF = [2, 5, 15, 30, 60]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def iter_date_range(start: date, end: date):
    """Yield every date from start to end inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def load_checkpoint() -> set[str]:
    """Return the set of already-processed 'YYYY-MM-DD' strings."""
    if CHECKPOINT_FILE.exists():
        return set(CHECKPOINT_FILE.read_text().splitlines())
    return set()


def save_checkpoint(done_days: set[str]) -> None:
    CHECKPOINT_FILE.write_text("\n".join(sorted(done_days)))


def load_existing_csv() -> dict[str, int]:
    """Load previously saved monthly totals so we can append/update."""
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


# ---------------------------------------------------------------------------
# Download + parse a single hourly file
# ---------------------------------------------------------------------------

def stream_hourly_file(day: date, hour: int) -> int:
    """
    Download one .json.gz file from GitHub Archive, stream-decompress it,
    parse PushEvents, and return the total commit count extracted.

    Returns -1 if the file is missing (404) — normal for future hours.
    Raises on unrecoverable errors.
    """
    url = GHARCHIVE_URL.format(date=day.isoformat(), hour=hour)

    for attempt, backoff in enumerate(RETRY_BACKOFF + [None], start=1):
        try:
            resp = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 404:
                return -1           # file genuinely missing
            resp.raise_for_status()

            # Collect compressed bytes in-memory (chunked) then decompress.
            # Using io.BytesIO keeps peak RAM to the size of one .gz file.
            buf = io.BytesIO()
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                buf.write(chunk)
            buf.seek(0)

            commit_count = 0
            with gzip.open(buf, "rt", encoding="utf-8", errors="replace") as gz:
                for line in gz:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") != "PushEvent":
                        continue
                    payload = event.get("payload", {})
                    size = payload.get("size", 0)
                    if isinstance(size, int) and size > 0:
                        commit_count += size

            return commit_count

        except (requests.RequestException, OSError) as exc:
            if attempt > MAX_RETRIES or backoff is None:
                print(f"\n  [ERROR] {url} failed after {attempt} attempts: {exc}",
                      file=sys.stderr)
                raise
            print(f"\n  [WARN] attempt {attempt} failed ({exc}); retrying in {backoff}s …",
                  file=sys.stderr)
            time.sleep(backoff)

    return 0   # unreachable


# ---------------------------------------------------------------------------
# Main fetch routine
# ---------------------------------------------------------------------------

def fetch(start: date, end: date, *, force: bool = False) -> dict[str, int]:
    """
    Process all hourly files from start..end.
    Returns the complete monthly totals dict (all months, not just new ones).

    Args:
        start:  First date to fetch (inclusive).
        end:    Last date to fetch (inclusive).
        force:  If True, reprocess days already in checkpoint.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    done_days = set() if force else load_checkpoint()
    totals = load_existing_csv()

    all_dates = list(iter_date_range(start, end))
    pending = [d for d in all_dates if d.isoformat() not in done_days]

    if not pending:
        print("All dates already processed. Use --force to reprocess.")
        return totals

    print(f"Fetching {len(pending)} day(s) of GitHub Archive data "
          f"({start} → {end}) …")
    print(f"Output → {OUTPUT_CSV}\n")

    for day in tqdm(pending, unit="day", desc="Days"):
        month_key = day.strftime("%Y-%m")
        day_commits = 0
        missing_hours = 0

        for hour in range(24):
            try:
                n = stream_hourly_file(day, hour)
            except Exception:
                # Already logged; skip this hour rather than abort
                continue
            if n == -1:
                missing_hours += 1
                continue
            day_commits += n

        totals[month_key] = totals.get(month_key, 0) + day_commits
        done_days.add(day.isoformat())

        # Checkpoint after every completed day
        save_checkpoint(done_days)
        save_csv(totals)

    print(f"\nDone. {len(totals)} month(s) aggregated → {OUTPUT_CSV}")
    return totals


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def _parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description="Fetch and aggregate GitHub Archive PushEvent commit counts."
    )
    parser.add_argument("--start", default="2020-01-01",
                        help="Start date YYYY-MM-DD (default: 2020-01-01)")
    parser.add_argument("--end",   default="2025-01-31",
                        help="End date   YYYY-MM-DD (default: 2025-01-31)")
    parser.add_argument("--force", action="store_true",
                        help="Reprocess already-checkpointed days")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    start = date.fromisoformat(args.start)
    end   = date.fromisoformat(args.end)
    fetch(start, end, force=args.force)
