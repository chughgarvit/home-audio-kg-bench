"""Generate a mock day of caption records (the frozen data contract in README.md).

Simulates 07:00-22:00 of home audio as 10 s records: long quiet stretches, appliance
activities with realistic durations, persistent backgrounds. Deterministic (seeded) so
everyone works on identical data. Real records from the Sounds of Home pipeline follow
the exact same schema.

Usage: python scripts/make_mock_captions.py  ->  data/mock_captions_sample.json
"""
import json
import random
from pathlib import Path

SEED = 1337
SEG = 10.0
DAY_START, DAY_END = 7 * 3600, 22 * 3600
OUT = Path(__file__).resolve().parent.parent / "data" / "mock_captions_sample.json"

# (activity, typical duration in seconds, description template)
ACTIVITIES = [
    ("Running Water in Sink", 60,  "The user runs water in the kitchen sink"),
    ("Microwave",             120, "The microwave hums while heating food"),
    ("Vacuum Cleaner",        300, "The vacuum cleaner roars across the floor"),
    ("Washing Machine",       1800,"The washing machine drums through its cycle"),
    ("Chopping Board",        180, "Rhythmic chopping sounds come from the kitchen"),
    ("Toilet Flushing",       20,  "A toilet flushes"),
    ("Hairdryer",             150, "A hairdryer blows steadily"),
    ("Typing on Keyboard",    600, "Keyboard keys clack in a steady rhythm"),
    ("Timer Beeping",         10,  "A timer beeps insistently"),
    ("Phone Ringing",         20,  "A phone rings"),
    ("Opening or Closing a Door", 10, "A door opens and closes"),
]
BACKGROUNDS = [
    ("Fridge Humming",   "the fridge hums softly"),
    ("Traffic Noise",    "traffic rumbles faintly outside"),
    ("Birds Chirping",   "birds chirp outside the window"),
    ("Air Conditioning", "the air conditioner drones"),
    (None, None),
]


def make_day(rng: random.Random) -> list[dict]:
    records, t = [], float(DAY_START)
    bg, bg_desc = rng.choice(BACKGROUNDS)
    while t < DAY_END:
        if rng.random() < 0.02:                                # switch ambience sometimes
            bg, bg_desc = rng.choice(BACKGROUNDS)
        if rng.random() < 0.25:                                # an activity starts
            act, dur, desc = rng.choice(ACTIVITIES)
            n = max(1, round(rng.gauss(dur, dur * 0.2) / SEG))
            for _ in range(n):
                if t >= DAY_END:
                    break
                text = desc + (f" while {bg_desc}." if bg_desc else ".")
                records.append(record(t, desc=text, activity=act, background=bg,
                                      conf=rng.uniform(0.55, 0.95), rng=rng))
                t += SEG
        else:                                                  # quiet stretch
            n = rng.randint(6, 60)
            for _ in range(n):
                if t >= DAY_END:
                    break
                if bg and rng.random() < 0.7:
                    records.append(record(t, desc=f"Only {bg_desc}.", activity=None,
                                          background=bg, conf=rng.uniform(0.4, 0.8), rng=rng))
                else:
                    records.append(record(t, desc="The house is quiet.", activity=None,
                                          background=None, conf=rng.uniform(0.6, 0.9), rng=rng))
                t += SEG
    return records


def record(t, desc, activity, background, conf, rng):
    return {
        "t_start": round(t, 1),
        "t_end": round(t + SEG, 1),
        "description": desc[0].upper() + desc[1:],
        "activity": activity,
        "background": background,
        "confidence": round(conf, 3),
        "clip_file": f"mock_{int(t):05d}.wav",
    }


if __name__ == "__main__":
    rng = random.Random(SEED)
    recs = make_day(rng)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(recs, indent=1))

    # self-check: schema holds and time is monotone
    assert all(r["t_start"] < r["t_end"] for r in recs)
    assert all(a["t_start"] <= b["t_start"] for a, b in zip(recs, recs[1:]))
    assert all(0.0 <= r["confidence"] <= 1.0 for r in recs)
    acts = {r["activity"] for r in recs if r["activity"]}
    print(f"wrote {len(recs)} records ({recs[0]['t_start']/3600:.0f}:00-"
          f"{recs[-1]['t_end']/3600:.0f}:00) with {len(acts)} activities -> {OUT}")
