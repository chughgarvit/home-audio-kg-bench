# Data

## What you work with

You consume **caption records** (the contract in the root README) — never raw audio,
except in Baseline A/B where scripts handle it. Three data sources, in the order you'll
use them:

### 1. Mock data (day 1 — already here)

`mock_captions_sample.json` — one simulated day (07:00–22:00, 5,400 records, 11 activity
types). Regenerate: `python scripts/make_mock_captions.py`. Build and debug everything
on this first.

### 2. Real caption timelines (from the Sounds of Home pipeline)

The main pipeline (separate track) produces `segments_final.csv` — 10s segments of the
**Sounds of Home** dataset labelled with activity/background + confidences. Convert it
to contract records with:

```
python scripts/timeline_to_captions.py path/to/segments_final.csv data/real/
```

One JSON per (recorder, date) day comes out. Ask Garvit for the CSV — expect it within
the first week. Everything you built on mock data must run on these unchanged.

### 3. The raw dataset (reference only — you don't need to download it)

**The Sounds of Home** (Bibbó et al., 2024, Univ. of Surrey): 1,342 hours of
speech-removed residential audio, 7 homes, AudioMoth recorders, with PANNs frame
annotations. Paper: https://arxiv.org/abs/2409.11262

- Full download: https://www.cvssp.org/data/ai4s/sounds_of_home
- Zenodo (4 parts: 119 / 40 / 38 / 13 GB), part 1: https://doi.org/10.5281/zenodo.12737915

We pilot on the 13 GB part. You only need raw audio for Baselines A and B (Tasks 12–13)
— and only the specific hours the benchmark uses, not the whole dataset. Coordinate with
Garvit before downloading anything big.

## Layout (everything under `data/` except the mock sample is gitignored)

```
data/
  mock_captions_sample.json     # committed
  real/                         # converted real timelines (from step 2)
  audio/                        # only the hours needed for baselines A/B
```
