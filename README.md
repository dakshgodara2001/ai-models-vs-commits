# Are AI models killing developers — or creating more of them?

Everyone has an opinion. I wanted data.

So I pulled **every public GitHub commit** from the last 3 years — hundreds of millions per month — and overlaid the release dates of 39 major LLMs to see what actually happens when a new model drops.

![Global GitHub Commit Activity vs. Major LLM Releases](https://raw.githubusercontent.com/dakshgodara2001/ai-models-vs-commits/main/chart.png)

## The short version

Commits didn't go down. They went up. A lot.

- **Jan 2023**: ~200M commits/month (pre-GPT-4 world)
- **Mid 2024**: ~400M commits/month (post-GPT-4o, Claude 3.5, Llama 3)
- **Late 2025**: still climbing, even as models get scarily good at writing code

Every color-coded line is an LLM launch — OpenAI in green, Anthropic in brown, Google in blue, Meta in facebook-blue, and so on. The dashed portion after Oct 2025 is estimated (GitHub Archive stopped reporting commit counts directly, so I scaled from PushEvent volume).

## What's interesting

**The "ChatGPT effect" is real, but slow.** ChatGPT launched Nov 2022. Commits didn't spike the next month — they ramped over the following year. Turns out "AI writes code now" is a gradual cultural shift, not a light switch.

**The big jumps correlate with *coding-specific* model releases.** GPT-4 (Mar 2023), Claude 3.5 Sonnet (Jun 2024), and the open-source Llama launches each precede noticeable upticks. Generic chatbot improvements? Less so.

**2024 was wild.** Twelve major model releases in a single year. The commit line barely had time to breathe between announcements. And it kept going up.

**The curve is flattening in late 2025.** Could be saturation, could be data quality (the dashed-line estimation is inherently noisier), could be the start of something. Worth watching.

## The data

- **Commits**: [GitHub Archive](https://www.gharchive.org/) on BigQuery — every public `PushEvent` since 2023, aggregated monthly
- **LLM releases**: Hand-curated list of 39 launches from OpenAI, Anthropic, Google, Meta, Mistral, xAI, DeepSeek, and Microsoft
- **Outlier handling**: Bot-inflated months (Apr–May 2024) are detected via MAD scores and interpolated
- **Post Oct 2025**: GitHub Archive dropped the `payload.size` field, so commits are estimated using a `PushEvents x 4.14` scaling ratio derived from months where both metrics overlap

## Models tracked

| Org | Models |
|-----|--------|
| OpenAI | GPT-3, ChatGPT, GPT-4, GPT-4 Turbo, GPT-4o, GPT-4o mini, o1-preview, o3-mini, GPT-4.1 |
| Anthropic | Claude 1, 2, 3 Opus, 3.5 Sonnet, 3.5 Haiku, 3.7 Sonnet, 4 Sonnet |
| Google | Bard, PaLM 2, Gemini 1.0, 1.5 Pro, 2.0 Flash, 2.0 Pro, 2.5 Pro |
| Meta | Llama 1, 2, 3, 3.1 405B, 3.2, 4 |
| Mistral | 7B, Mixtral 8x7B, Large 2 |
| Others | GitHub Copilot, Grok-2, DeepSeek V3, DeepSeek R1, Falcon 40B, DBRX |

## Run it yourself

You'll need a GCP project with BigQuery access (~$5/TB scanned, results cache locally).

```bash
pip install -r requirements.txt
gcloud auth application-default login

# Fetch + plot
python main.py --project YOUR_GCP_PROJECT --start 2023-01 --end 2026-01 --out chart.png

# Already have the data? Just re-plot
python main.py --no-fetch --out chart.png
```

## My take

AI isn't replacing developers. It's making more people *feel like* developers. The barrier to shipping something went from "4 years of CS" to "describe what you want." And that shows up in the commit graph.

The question isn't whether AI kills coding. It's whether all these new commits are *good*. That's a different chart.

---

*Built by a PM who got mass data from BigQuery and mass opinions from the internet. Data is from [GitHub Archive](https://www.gharchive.org/). Opinions are my own.*
