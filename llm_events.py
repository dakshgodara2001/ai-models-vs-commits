"""
Curated dataset of major LLM public release dates.

Each entry: (model_name, organization, release_date as YYYY-MM-DD)
Release date = first public availability (API, paper, or product launch).
"""

from datetime import date

# ---------------------------------------------------------------------------
# Color palette per organization (matplotlib-compatible)
# ---------------------------------------------------------------------------
ORG_COLORS = {
    "OpenAI":    "#10a37f",   # green
    "Anthropic": "#c97d4e",   # orange-brown
    "Google":    "#4285f4",   # blue
    "Meta":      "#1877f2",   # facebook blue
    "Mistral":   "#7c3aed",   # purple
    "Microsoft": "#00a4ef",   # azure
    "Cohere":    "#d946ef",   # pink
    "xAI":       "#000000",   # black
    "DeepSeek":  "#e11d48",   # red
    "Other":     "#6b7280",   # gray
}

# ---------------------------------------------------------------------------
# Release dataset
# Format: (model_name, organization, release_date)
# ---------------------------------------------------------------------------
LLM_RELEASES = [
    # 2020
    ("GPT-3",                "OpenAI",    date(2020,  6, 11)),
    # 2021
    ("GitHub Copilot",       "Microsoft", date(2021,  6, 29)),
    ("CodeX",                "OpenAI",    date(2021,  8, 10)),
    # 2022
    ("ChatGPT",              "OpenAI",    date(2022, 11, 30)),
    # 2023 Q1
    ("Llama 1",              "Meta",      date(2023,  2, 24)),
    ("GPT-4",                "OpenAI",    date(2023,  3, 14)),
    ("Claude 1",             "Anthropic", date(2023,  3, 14)),
    ("Bard",                 "Google",    date(2023,  3, 21)),
    # 2023 Q2
    ("Falcon 40B",           "Other",     date(2023,  5, 23)),
    ("PaLM 2",               "Google",    date(2023,  5, 10)),
    # 2023 Q3
    ("Claude 2",             "Anthropic", date(2023,  7, 11)),
    ("Llama 2",              "Meta",      date(2023,  7, 18)),
    ("Mistral 7B",           "Mistral",   date(2023,  9, 27)),
    # 2023 Q4
    ("GPT-4 Turbo",          "OpenAI",    date(2023, 11,  6)),
    ("Gemini 1.0",           "Google",    date(2023, 12,  6)),
    ("Mixtral 8x7B",         "Mistral",   date(2023, 12, 11)),
    # 2024 Q1
    ("Gemini 1.5 Pro",       "Google",    date(2024,  2, 15)),
    ("Claude 3 Opus",        "Anthropic", date(2024,  3,  4)),
    ("DBRX",                 "Other",     date(2024,  3, 27)),
    # 2024 Q2
    ("Llama 3 8/70B",        "Meta",      date(2024,  4, 18)),
    ("GPT-4o",               "OpenAI",    date(2024,  5, 13)),
    ("Claude 3.5 Sonnet",    "Anthropic", date(2024,  6, 20)),
    # 2024 Q3
    ("Llama 3.1 405B",       "Meta",      date(2024,  7, 23)),
    ("Mistral Large 2",      "Mistral",   date(2024,  7, 24)),
    ("GPT-4o mini",          "OpenAI",    date(2024,  7, 18)),
    ("Grok-2",               "xAI",       date(2024,  8, 13)),
    ("o1-preview",           "OpenAI",    date(2024,  9, 12)),
    # 2024 Q4
    ("Claude 3.5 Haiku",     "Anthropic", date(2024, 10, 22)),
    ("Llama 3.2",            "Meta",      date(2024,  9, 25)),
    ("Gemini 2.0 Flash",     "Google",    date(2024, 12, 11)),
    ("DeepSeek V3",          "DeepSeek",  date(2024, 12, 26)),
    # 2025
    ("DeepSeek R1",          "DeepSeek",  date(2025,  1, 20)),
    ("o3-mini",              "OpenAI",    date(2025,  1, 31)),
    ("Claude 3.7 Sonnet",    "Anthropic", date(2025,  2, 24)),
    ("Gemini 2.0 Pro",       "Google",    date(2025,  2,  5)),
    ("Llama 4",              "Meta",      date(2025,  4,  5)),
    ("GPT-4.1",              "OpenAI",    date(2025,  4, 14)),
    ("Claude 4 Sonnet",      "Anthropic", date(2025,  5, 22)),
    ("Gemini 2.5 Pro",       "Google",    date(2025,  3, 25)),
]


def get_events_as_dicts():
    """Return releases as a list of dicts."""
    return [
        {
            "model":   name,
            "org":     org,
            "date":    release_date,
            "color":   ORG_COLORS.get(org, ORG_COLORS["Other"]),
        }
        for name, org, release_date in LLM_RELEASES
    ]


def get_events_in_range(start: date, end: date):
    """Return only events whose date falls within [start, end]."""
    all_events = get_events_as_dicts()
    return [e for e in all_events if start <= e["date"] <= end]
