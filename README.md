# AI Models vs GitHub Commits

A time-series analysis of how major LLM releases correlate with global GitHub commit activity.

![Chart](https://raw.githubusercontent.com/dakshgodara2001/ai-models-vs-commits/main/chart.png)

## What it does

- Pulls monthly GitHub commit totals from the public [GitHub Archive](https://www.gharchive.org/) dataset on BigQuery
- Overlays 39 major LLM release events (GPT-3 through Claude 4, Gemini 2.5, Llama 4, DeepSeek R1, etc.) as annotated vertical markers
- Handles data quality issues: caps outlier months (bot-inflated pushes in Apr–May 2024), and estimates months where GitHub Archive dropped the `size` field (Oct 2025 onward) using a `PushEvents × 4.14` scaling ratio

## Output

A single chart (`chart.png`) with:
- **Solid line** — confirmed commit counts from `payload.size`
- **Dashed line** — estimated commits from PushEvent counts × median ratio
- Color-coded vertical markers per organization (OpenAI, Anthropic, Google, Meta, Mistral, etc.)

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Authenticate with Google Cloud

```bash
# Install gcloud (if needed)
brew install --cask google-cloud-sdk

# Authenticate
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

You'll also need a GCP project with:
- Billing enabled
- BigQuery API enabled (`gcloud services enable bigquery.googleapis.com`)

BigQuery costs: ~$5/TB scanned. A 3-year query scans ~14 TB (~$70). Results are cached locally so you only pay once.

### 3. Run the pipeline

```bash
# Fetch data + generate chart
python main.py --project YOUR_GCP_PROJECT_ID --start 2023-01 --end 2026-01 --out chart.png

# Re-plot without re-fetching (data already in data/monthly_commits.csv)
python main.py --no-fetch --out chart.png
```

## File structure

```
├── main.py                  # Pipeline CLI (fetch → visualize)
├── fetch_bigquery.py        # BigQuery fetch: githubarchive.month.*
├── llm_events.py            # 39 curated LLM release events with org + date
├── visualize.py             # Chart renderer (outlier capping, label stagger)
├── requirements.txt
└── data/                    # Created on first run (gitignored)
    └── monthly_commits.csv  # Aggregated monthly commit totals
```

## Data sources

| Source | Used for |
|--------|----------|
| [GitHub Archive on BigQuery](https://console.cloud.google.com/marketplace/details/github/github-archive) (`githubarchive.month.*`) | Monthly commit totals via `PushEvent.payload.size` |
| Manual curation | LLM release dates |

## LLM events included

OpenAI (GPT-3, ChatGPT, GPT-4, GPT-4o, o1, o3, GPT-4.1), Anthropic (Claude 1–4), Google (Bard, PaLM 2, Gemini 1–2.5), Meta (Llama 1–4), Mistral (7B, Mixtral, Large 2), xAI (Grok-2), DeepSeek (V3, R1), Microsoft (GitHub Copilot), and more.

## CLI reference

```
main.py
  --project      GCP project ID (required for fetch)
  --start        Start month YYYY-MM (default: 2023-01)
  --end          End month YYYY-MM (default: 2026-01)
  --no-fetch     Skip BigQuery fetch, use existing CSV
  --out          Output path for chart (omit to display interactively)
  --plot-start   Restrict chart x-axis start YYYY-MM
  --plot-end     Restrict chart x-axis end YYYY-MM

fetch_bigquery.py
  --project      GCP project ID
  --start        Start month YYYY-MM
  --end          End month YYYY-MM

visualize.py
  --csv          Path to monthly_commits.csv
  --start        Filter chart start YYYY-MM
  --end          Filter chart end YYYY-MM
  --out          Output path (omit to display interactively)
```
