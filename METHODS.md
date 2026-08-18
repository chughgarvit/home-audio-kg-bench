# Methods — how each piece is built (pseudocode level)

Read the method for a task **before** starting it. If you deviate, write one line in your
nightly update saying how and why.

## M1 — State intervals from records (Task 5)

Run-length grouping with a gap tolerance:

```
GAP_TOL = 2          # segments; ≥20s of silence closes an interval
for each appliance-implying activity a:
    walk records in time order
    open an interval when a record with activity==a appears
    extend it while records with a keep appearing (gaps < GAP_TOL allowed)
    close it (t_end = last evidence t_end) when GAP_TOL consecutive records lack a
    interval.confidence = mean(evidence confidences)
    if the day ends while open: t_end stays None   # "still open" is information
```

## M2 — Graph construction (Task 4)

```
for each record r:
    add SoundEvent node (id ev:{t_start})
    if r.activity:   add/find ActivityType node, edge instance_of
    if r.background: same, tagged kind="background"
run M1 → add State nodes + state_of + evidenced_by edges
```
Rule-based only — the `activity` field is already categorical; no LLM in the graph layer.

## M3 — Question answering (Task 7)

LA-RAG-style pipeline, but over the graph and with open intents:

```
1. classify question type (keyword rules; LLM fallback for odd phrasings):
     "did I turn/switch off", "still on/running" → state
     "has X finished"                            → state (closed-interval check)
     "what made that sound (at T)"               → attribution
     "was someone / did X happen"                → detection
     "what was I doing / what happened"          → reconstruction
     "how many times"                            → counting
2. extract entity (match against known Appliance/ActivityType labels)
   and time window (explicit T, "while I was away" = given window, else whole day)
3. call the query API (graph/api.py) — the only allowed access path
4. compose the answer from the returned evidence (template first, LLM to smooth
   phrasing only — the LLM may not add facts the evidence doesn't contain)
```

## M4 — Absence + uncertainty rules (Task 8)

```
state question, interval closed  → "yes, stopped at t_end"        conf = interval conf
state question, interval open    → "last heard at t, no stop since; may still be on"
                                   conf = interval conf × 0.7
no matching evidence in window   → "I don't have evidence for that"  (never guess)
attribution at time T            → nearest SoundEvent within ±60s; if several, list
                                   top-2 by confidence ("probably X, could be Y")
```
Answer wording must always carry the uncertainty ("probably", "I heard no…", times).

## M5 — Benchmark generation (Task 10)

Template + slot-filling from the ground-truth timeline (records are the oracle):

```
for each day of records, per question type:
  detection:      "Did the {activity} run today?"        gold = yes/no from timeline
  counting:       "How many times did {activity} occur?" gold = interval count (M1)
  temporal:       "When did {activity} last run?"        gold = [t_start, t_end]
  state:          "Is the {appliance} still running at {T}?"  pick T inside/after intervals
  attribution:    "What made the sound at {T}?"          T inside a labelled event
  reconstruction: "What happened between {T1}-{T2}?"     gold = list of activities
  unanswerable:   same templates with entities that never occur that day
                  gold = "no evidence"
```
Balance: roughly equal per type, ~15% unanswerable. Store: question, type, day, time
window, gold answer, acceptable alternatives. Target 300–500 pairs over ≥3 days.

## M6 — Metrics (Task 11)

- detection / state / unanswerable → accuracy (answer contains the gold verdict)
- counting → exact match, and ±1 reported separately
- temporal → IoU ≥ 0.5 counts as correct (CASTELLA / LA-RAG convention)
- reconstruction → LLM-judge 0–5 (LA-RAG's protocol): 5 = all key events, correct order;
  3–4 = minor omissions; ≤2 = wrong/invented. Judge prompt lives in
  `benchmark/judge_prompt.txt` — fixed once, never tuned per system.
- always: mean latency per question, and "% answered when gold = no evidence"
  (hallucination rate — the most important single number for our claim)

## M7 — Baseline wiring (Tasks 12–14)

All baselines answer the *same* `qa_pairs.json` through the *same* `evaluate.py`.

```
A  Qwen2.5-Omni: audio of the question's time window (concat ≤ few min) + question
   → its text answer → metrics. No graph, no captions.
B  LA-RAG-repro: PANNs (CPU) over the window → event table (label, t, conf)
   → classify question into LA-RAG's 4 intents only (detection/counting/summary/anomaly)
   → LLM answers from the table. State/attribution/incompleteness questions get
   whichever of the 4 intents fits best — that handicap IS the finding.
C  GAMA zero-shot: GAMA captions per 10s → your own graph + QA pipeline unchanged.
   Isolates the value of (i) fine-tuning, (ii) the graph, separately from the captioner.
```
