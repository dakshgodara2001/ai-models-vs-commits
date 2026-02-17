"""
visualize.py
------------
Generate a publication-quality chart showing:
  - Monthly GitHub commit volume (line)
  - Major LLM release events (vertical markers with labels)

Usage:
    python visualize.py                            # uses data/monthly_commits.csv
    python visualize.py --csv path/to/file.csv
    python visualize.py --start 2020-01 --end 2025-01
    python visualize.py --out chart.png            # save instead of display
"""

import argparse
import csv
import textwrap
from datetime import date, datetime
from pathlib import Path

import matplotlib
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from typing import Optional

from llm_events import ORG_COLORS, get_events_in_range

# ---------------------------------------------------------------------------
# Styling constants
# ---------------------------------------------------------------------------
FIGURE_SIZE      = (20, 9)
LINE_COLOR       = "#1f77b4"
LINE_WIDTH       = 2.2
MARKER_ALPHA     = 0.55
MARKER_LW        = 1.2
LABEL_FONTSIZE   = 7.5
LABEL_MAX_WIDTH  = 14        # chars before wrapping
ANNOTATION_LEVELS = 6        # vertical stagger levels to avoid overlap
LEVEL_STEP_FRAC  = 0.055     # fraction of y-axis height per level
MIN_DAY_GAP      = 20        # days of separation before a new level resets


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def cap_outliers(df: pd.DataFrame, z_thresh: float = 3.0) -> pd.DataFrame:
    """
    Replace outliers with linearly interpolated values.
    Uses Median Absolute Deviation (robust to extreme spikes).
    Prints which months were capped.
    """
    median = df["commits"].median()
    mad = (df["commits"] - median).abs().median()
    # Modified Z-score (Iglewicz & Hoaglin)
    modified_z = 0.6745 * (df["commits"] - median) / (mad + 1)
    outlier_mask = modified_z.abs() > z_thresh

    if outlier_mask.any():
        capped = df.loc[outlier_mask, "month"].tolist()
        print(f"  Capping {len(capped)} outlier month(s): {', '.join(capped)}")
        df = df.copy()
        df.loc[outlier_mask, "commits"] = None
        df["commits"] = df["commits"].interpolate(method="linear").round().astype("int64")

    return df


def load_commits(csv_path: Path,
                 start_month: Optional[str],
                 end_month: Optional[str]) -> pd.DataFrame:
    rows = []
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            rows.append({"month": row["month"], "commits": int(row["commits"])})

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["month"], format="%Y-%m")
    df = df.sort_values("date").reset_index(drop=True)

    if start_month:
        df = df[df["month"] >= start_month]
    if end_month:
        df = df[df["month"] <= end_month]

    df = cap_outliers(df)

    return df


# ---------------------------------------------------------------------------
# Label stagger: assign a vertical level to each event so labels don't pile up
# ---------------------------------------------------------------------------

def assign_levels(events: list[dict], min_day_gap: int = MIN_DAY_GAP) -> list[int]:
    """
    Simple greedy algorithm: keep track of the last date placed at each level.
    Assign the lowest level whose last-placed date is far enough away.
    """
    level_last: dict[int, date] = {}
    levels = []
    for ev in events:
        ev_date = ev["date"]
        assigned = None
        for lvl in range(ANNOTATION_LEVELS):
            last = level_last.get(lvl)
            if last is None or (ev_date - last).days >= min_day_gap:
                assigned = lvl
                break
        if assigned is None:
            assigned = 0   # fallback: overlap at level 0
        level_last[assigned] = ev_date
        levels.append(assigned)
    return levels


# ---------------------------------------------------------------------------
# Main chart function
# ---------------------------------------------------------------------------

def plot(df: pd.DataFrame,
         events: list[dict],
         output_path: Optional[Path] = None) -> None:

    if df.empty:
        raise ValueError("No commit data to plot — check your CSV and date range.")

    # ---- figure setup -------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    fig.patch.set_facecolor("#f8f9fa")
    ax.set_facecolor("#f8f9fa")

    # ---- commit line --------------------------------------------------------
    # Split into confirmed (size field available) and estimated (scaled from PushEvents)
    ESTIMATED_FROM = "2025-10"
    df_actual = df[df["month"] < ESTIMATED_FROM]
    df_est    = df[df["month"] >= ESTIMATED_FROM]

    ax.plot(df_actual["date"], df_actual["commits"],
            color=LINE_COLOR, linewidth=LINE_WIDTH,
            zorder=3, label="Monthly GitHub Commits")

    # Bridge the gap: connect last actual point to first estimated
    if not df_actual.empty and not df_est.empty:
        bridge = pd.concat([df_actual.iloc[[-1]], df_est.iloc[[0]]])
        ax.plot(bridge["date"], bridge["commits"],
                color=LINE_COLOR, linewidth=LINE_WIDTH,
                linestyle="--", zorder=3)

    ax.plot(df_est["date"], df_est["commits"],
            color=LINE_COLOR, linewidth=LINE_WIDTH,
            linestyle="--", zorder=3,
            label="Estimated (PushEvents × 4.14x ratio)")

    ax.fill_between(df["date"], df["commits"],
                    alpha=0.12, color=LINE_COLOR, zorder=2)

    # ---- y-axis formatting --------------------------------------------------
    y_max = df["commits"].max()
    ax.set_ylim(0, y_max * 1.55)          # head-room for labels

    def _human(x, _pos):
        if x >= 1_000_000_000:
            return f"{x/1_000_000_000:.1f}B"
        if x >= 1_000_000:
            return f"{x/1_000_000:.0f}M"
        if x >= 1_000:
            return f"{x/1_000:.0f}K"
        return str(int(x))

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_human))

    # ---- x-axis formatting --------------------------------------------------
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator())

    # ---- event markers ------------------------------------------------------
    levels = assign_levels(events)

    for ev, level in zip(events, levels):
        ev_dt = datetime(ev["date"].year, ev["date"].month, ev["date"].day)
        color = ev["color"]

        # Vertical line from bottom to a staggered height
        line_top_frac = 0.30 + level * LEVEL_STEP_FRAC
        ax.axvline(x=ev_dt, ymin=0, ymax=line_top_frac,
                   color=color, alpha=MARKER_ALPHA,
                   linewidth=MARKER_LW, linestyle="--", zorder=4)

        # Dot at the top of the line
        y_dot = y_max * 1.55 * line_top_frac
        ax.plot(ev_dt, y_dot, "o", color=color,
                markersize=4, alpha=0.85, zorder=5)

        # Label above the dot
        label_text = textwrap.fill(ev["model"], width=LABEL_MAX_WIDTH)
        ax.annotate(
            label_text,
            xy=(ev_dt, y_dot),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center", va="bottom",
            fontsize=LABEL_FONTSIZE,
            color=color,
            fontweight="semibold",
            rotation=70,
            zorder=6,
        )

    # ---- legend for organisations -------------------------------------------
    seen_orgs = {ev["org"] for ev in events}
    org_patches = [
        mpatches.Patch(color=ORG_COLORS.get(org, "#6b7280"), label=org)
        for org in sorted(seen_orgs)
    ]
    commit_line = plt.Line2D([0], [0], color=LINE_COLOR,
                             linewidth=LINE_WIDTH, label="Monthly Commits")
    ax.legend(
        handles=[commit_line] + org_patches,
        loc="upper left",
        fontsize=8.5,
        framealpha=0.85,
        edgecolor="#cccccc",
    )

    # ---- grid + spines ------------------------------------------------------
    ax.grid(axis="y", color="#cccccc", linewidth=0.6, zorder=1)
    ax.grid(axis="x", color="#e5e5e5", linewidth=0.4, zorder=1)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    # ---- titles + labels ----------------------------------------------------
    ax.set_title(
        "Global GitHub Commit Activity vs. Major LLM Releases",
        fontsize=16, fontweight="bold", pad=16,
    )
    ax.set_xlabel("Month", fontsize=11, labelpad=8)
    ax.set_ylabel("Total Public Commits (PushEvents)", fontsize=11, labelpad=8)

    date_range_str = (
        f"{df['date'].min().strftime('%b %Y')} – "
        f"{df['date'].max().strftime('%b %Y')}"
    )
    ax.text(0.99, 0.01, f"Source: GitHub Archive  |  {date_range_str}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7.5, color="#888888")

    plt.tight_layout()

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        print(f"Chart saved → {output_path}")
    else:
        plt.show()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args():
    parser = argparse.ArgumentParser(
        description="Visualize GitHub commit timeline with LLM event overlays."
    )
    parser.add_argument("--csv",   default="data/monthly_commits.csv",
                        help="Path to monthly_commits.csv")
    parser.add_argument("--start", default=None,
                        help="Start month YYYY-MM (default: all data)")
    parser.add_argument("--end",   default=None,
                        help="End   month YYYY-MM (default: all data)")
    parser.add_argument("--out",   default=None,
                        help="Save chart to this path (e.g. chart.png). "
                             "Omit to display interactively.")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    csv_path = Path(args.csv)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Commit data not found at '{csv_path}'.\n"
            "Run fetch_github_data.py first, or pass --csv <path>."
        )

    df = load_commits(csv_path, args.start, args.end)

    # Determine date range for event filtering
    start_date = df["date"].min().date()
    end_date   = df["date"].max().date()
    events = get_events_in_range(start_date, end_date)

    print(f"Loaded {len(df)} months of commit data.")
    print(f"Overlaying {len(events)} LLM release event(s).")

    out = Path(args.out) if args.out else None
    plot(df, events, output_path=out)
