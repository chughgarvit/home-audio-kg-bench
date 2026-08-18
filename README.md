# home-audio-kg-bench

Knowledge graph + question answering + benchmark for **audio-first home activity
understanding** — the intern track of the ambient-audio project (IIT Jodhpur).

**The system in one line:**

```
10s audio captions (with confidence)  →  temporal knowledge graph  →  QA with grounded,
uncertainty-aware answers  →  benchmarked against published baselines
```

Everything here runs on a **laptop (CPU)**. No GPU, no model training — the trained audio
model is a separate track (Sarita); you consume its outputs through the data contract below.

---

## Your goal (read this first)

Build the **reasoning-and-evaluation half** of the system and prove it works. Concretely,
in 15 days you produce **four deliverables**:

1. **A working pipeline**: timestamped audio captions in → temporal knowledge graph →
   answers to the 10 target questions, each answer grounded in evidence and honest about
   uncertainty. Runnable by anyone in ≤10 commands. *(Tasks 1–9)*
2. **The benchmark**: a file of 300–500 question–answer pairs over home-audio timelines —
   the first benchmark for this task. *(Task 10)*
3. **The comparison**: 3 published baseline systems run on that same benchmark through one
   shared harness, so the numbers are directly comparable. *(Tasks 11–14)*
4. **The results table + demo**: one table (our system vs. baselines, per question type),
   a 5-minute screen recording, and a short report. *(Task 15)*

**Definition of done:** a stranger can clone this repo, run the pipeline on the sample
data, ask "Has the washing machine finished?", get a correct evidence-backed answer — and
reproduce the results table with one command.

**Why it matters:** deliverables 2–4 become the *evaluation section of the paper* we are
writing. You are not doing support work; you are building the part that makes the claims
credible.

**Working rules:** commit daily to this repo · 5-line update to Garvit every night ·
ask questions early, don't stay stuck >2 hours.

---

## The data contract (frozen — everything reads this)

One JSON record per 10 seconds of audio:

```json
{
  "t_start": 43200.0,
  "t_end":   43210.0,
  "description": "The user runs water in the sink while the fridge hums in the background.",
  "activity":   "Running Water in Sink",
  "background": "Fridge Humming",
  "confidence": 0.72,
  "clip_file":  "14_20231122_130000_0042.wav"
}
```

`activity`/`background` may be `null`. `confidence` is 0–1. A sample day lives in
`data/mock_captions_sample.json` (regenerate with `python scripts/make_mock_captions.py`).
Real records from the Sounds of Home pipeline will replace mock ones later — same schema,
zero code changes on your side. That's the whole point of the contract.

## The 10 target questions (this is the spec — the whole system exists to answer these)

1. What was I doing before the call?
2. Did I turn that off?
3. Has the washing machine finished?
4. What made that sound?
5. Was someone at the door?
6. Where did I last use my keys?
7. Have I already added water?
8. Is someone still in the kitchen?
9. Did I complete the task?
10. What happened while I was away?

(Also in `benchmark/questions.json` with type tags.)

---

## Repo map

| File | What it is |
|---|---|
| `README.md` | goal, contract, tasks (this file) |
| `METHODS.md` | **how** each task is done — pseudocode per task, read before starting one |
| `graph/SCHEMA.md` | the graph definition (nodes/edges/rules) with a worked example |
| `data/README.md` | where the datasets are and how real data arrives |
| `scripts/make_mock_captions.py` | generates the mock day |
| `scripts/timeline_to_captions.py` | converts the real pipeline CSV → caption records |
| `benchmark/questions.json` | the 10 questions + benchmark question types |

## Tasks — numbered, with details

Concrete methods for each task are in **`METHODS.md`** (M1–M7) — the task list says
*what*, METHODS says *how*.

### Part A — Knowledge graph (`graph/`)

**1. Environment + data.**
Clone, `python -m venv .venv`, install `networkx pandas gradio pyvis tqdm openai`.
Run `python scripts/make_mock_captions.py` and open the output — understand every field
before writing any code.

**2. Loader + validator (`graph/captions.py`).**
`load_captions(path)`: reads the JSON, validates every record (field types, `t_start <
t_end`, records in order, confidence in [0,1]), fails loudly with the record index on
any violation. Prints a one-line summary (n records, time span, n activities).

**3. Graph schema — read `graph/SCHEMA.md` (provided).**
The schema is already defined: 4 node types, 3 edge types, append-only, provenance
mandatory. Walk through its worked example by hand against ~10 mock records until the
mapping record→graph is obvious to you. If something in the data doesn't fit the schema,
propose a change — **schema changes need Garvit's sign-off**, code changes don't.

**4. Graph builder (`graph/build.py`).**
`build_graph(records) -> nx.MultiDiGraph`. One `SoundEvent` node per record, linked to
its `Activity`/`Appliance` node. Rule-based — no LLM needed here, the `activity` and
`background` fields are already categorical.

**5. State intervals + provenance.**
An appliance's sound starting opens a `has_state(running, t_on, ...)` edge; the sound
stopping closes it (`t_off`). **Append-only**: a new state never deletes an old one —
history is the product. Every node/edge stores the `clip_file` values it came from.
Add `save_graph()/load_graph()` (JSON); assert a snapshot round-trips identically.

**6. Query API (`graph/api.py`) — frozen after review.**
Exactly four functions:
`upsert(record)` · `query(entity, t_range)` · `history(entity)` · `provenance(node_id)`.
Ten `assert`-based checks in `graph/test_api.py` exercising all four. Downstream code
(QA, benchmark) may only touch the graph through this API.

### Part B — Question answering (`qa/`)

**7. QA pipeline (`qa/answer.py`).**
`answer(question, graph, now) -> {"answer": str, "confidence": float, "evidence": [...]}`.
Steps: parse the question to (entity, time window, question type) — rules first, one
LLM call as fallback — then call the query API, then compose one answer sentence that
**states the evidence and the confidence in words**:
*"The tap started at 14:02 and I heard no stop sound — it's probably still running."*

**8. Absence reasoning + honest ignorance.**
Two behaviours that make or break the demo: (a) answers derived from *missing* sounds
(no off-sound since the on-sound ⇒ probably still on); (b) when the graph has no
evidence, the answer is **"I don't have evidence for that"** — the system never guesses.

**9. Demo UI.**
`qa/app.py` (Gradio): load a day of records → event timeline + pyvis graph view
(colour = confidence) → chat box answering the 10 questions. Demo-grade, not
production-grade — but presentable, this is what the professors see.

### Part C — Benchmark + baselines (`benchmark/`, `baselines/`) — your main contribution

**10. Benchmark construction (`benchmark/build_qa.py`).**
Generate question–answer pairs over caption timelines, in the style of
[CASTELLA](https://github.com/line/CASTELLA) / LA-RAG's benchmark construction:
for each day of records, emit questions of each type — *detection* ("did X happen?"),
*counting*, *temporal* ("when"), *state* ("is X still on?"), *attribution* ("what made
that sound at T?"), *reconstruction* ("what happened between T1–T2?"), and
**unanswerable** ones (the correct answer is "no evidence"). Ground-truth answers come
from the records themselves. Target: **300–500 QA pairs** across ≥3 days of data,
saved as `benchmark/qa_pairs.json` with type tags.

**11. Evaluation harness (`benchmark/evaluate.py`).**
One entry point: `python benchmark/evaluate.py --system <name>` → accuracy per question
type + overall + mean latency, printed and saved as CSV. Exact/containment match for
closed answers; an LLM-judge (0–5, LA-RAG style) for free-text ones. Every baseline
below plugs into this same harness — that is what makes the numbers comparable.

**12. Baseline A — ungrounded audio LLM.**
[Qwen2.5-Omni-7B](https://huggingface.co/Qwen/Qwen2.5-Omni-7B) (open weights): feed the
raw audio chunk(s) + question directly, no graph. This is the "just ask a big model"
baseline; LA-RAG's Table 2 predicts it detects well but localizes/aggregates poorly —
verify that on our benchmark. (Runs slowly on CPU; a small GPU or Colab is fine here.)

**13. Baseline B — flat event table + LLM (LA-RAG reproduction).**
[PANNs](https://github.com/qiuqiangkong/audioset_tagging_cnn) event table (timestamped
labels, no graph) → LLM answers questions from the table with LA-RAG's four fixed
intents (detection / counting / summary / anomaly). LA-RAG has **no public code** — you
are rebuilding its recipe from the paper (arXiv 2602.14612). This is the key ablation:
*graph + open intents* vs *table + fixed intents*.

**14. Baseline C — zero-shot captioner (+ stretch baselines).**
[GAMA](https://github.com/Sreyan88/GAMA) zero-shot captions → your same QA layer
(shows what fine-tuning adds). Stretch, in priority order:
[PRISM](https://github.com/cmusmashlab/prism) audio-only on the procedural question
subset (the fixed-procedure paradigm we argue against);
[Audio Flamingo 3](https://github.com/NVIDIA/audio-flamingo) as a second LALM;
[LTU](https://github.com/YuanGongND/ltu) as a third. Question formats worth borrowing:
[DAQA](https://github.com/facebookresearch/daqa) (temporal audio QA).

**15. Results + handover.**
`RESULTS.md`: one table — rows = systems (ours, A, B, C, stretch), columns = question
types + overall + latency — plus 5 lines of findings per baseline. A 5-minute screen
recording of the demo. A handover note listing every known bug and shortcut.

---

## Papers being compared against (read intro + method of each, skim the rest)

| System / benchmark | Paper | Code / data |
|---|---|---|
| LA-RAG (event store + fixed intents) | [arXiv 2602.14612](https://arxiv.org/abs/2602.14612) | none — reproduce (Task 13) |
| EchoScriptor / EchoLLM (captions + narratives) | [CHI '26](https://dl.acm.org/doi/10.1145/3772318.3791528) | none — AST+LLM recipe in paper |
| PRISM Tracker / Q&A (fixed procedure graph) | IMWUT '23 / '24 | [github.com/cmusmashlab/prism](https://github.com/cmusmashlab/prism) |
| Qwen2.5-Omni (ungrounded LALM) | Qwen tech report | [HF weights](https://huggingface.co/Qwen/Qwen2.5-Omni-7B) |
| GAMA (audio-language backbone) | EMNLP '24 | [github.com/Sreyan88/GAMA](https://github.com/Sreyan88/GAMA) |
| Audio Flamingo 3 | NVIDIA '25 | [github.com/NVIDIA/audio-flamingo](https://github.com/NVIDIA/audio-flamingo) |
| LTU (audio QA) | ICLR '24 | [github.com/YuanGongND/ltu](https://github.com/YuanGongND/ltu) |
| CASTELLA (long-audio moments — benchmark format) | ICASSP '26 | [github.com/line/CASTELLA](https://github.com/line/CASTELLA) |
| DAQA (temporal audio QA format) | IEEE TASLP '20 | [github.com/facebookresearch/daqa](https://github.com/facebookresearch/daqa) |
| Sounds of Home (our data) | [arXiv 2409.11262](https://arxiv.org/abs/2409.11262) | CVSSP / Zenodo |
| PANNs (event tagger for Baseline B) | IEEE TASLP '20 | [github.com/qiuqiangkong/audioset_tagging_cnn](https://github.com/qiuqiangkong/audioset_tagging_cnn) |

## Priorities if time runs short

Cut in this order (last = cut first): stretch baselines (14b) → UI polish (9) →
Baseline A on full benchmark (subsample it instead). **Never cut:** the query API (6),
the benchmark file (10), the harness (11), Baseline B (13) — those four are the paper's
evaluation section.
