"""Convert the Sounds of Home pipeline output (segments_final.csv) to caption records.

Emits one JSON per (recorder, date) day, matching the contract in README.md, into the
given output directory.

Usage: python scripts/timeline_to_captions.py segments_final.csv data/real/
"""
import json
import sys
from pathlib import Path

import pandas as pd

MIN_CONF = 0.30   # floor for null/quiet segments where no class peaked


def to_records(day: pd.DataFrame) -> list[dict]:
    day = day.copy()
    # absolute seconds since midnight FIRST, then sort - sorting on the within-hour
    # t_start alone interleaves hours out of order (stem = YYYYMMDD_HHMMSS)
    day["t_abs"] = day.t_start.astype(float) + day.stem.str[9:11].astype(int) * 3600
    day = day.sort_values("t_abs")
    recs = []
    for _, r in day.iterrows():
        t0 = float(r.t_abs)
        conf = max(float(r.get("act_peak", 0) or 0), float(r.get("bg_peak", 0) or 0), MIN_CONF)
        recs.append({
            "t_start": round(t0, 1),
            "t_end": round(t0 + 10.0, 1),
            "description": str(r.output),
            "activity": r.activity if isinstance(r.activity, str) else None,
            "background": r.background if isinstance(r.background, str) else None,
            "confidence": round(min(conf, 1.0), 3),
            "clip_file": Path(str(r.wav_out)).name,
        })
    return recs


if __name__ == "__main__":
    csv_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(csv_path)
    df["date"] = df.stem.str[:8]
    for (rec, date), day in df.groupby(["recorder", "date"]):
        recs = to_records(day)
        out = out_dir / f"captions_{rec}_{date}.json"
        out.write_text(json.dumps(recs, indent=1))
        print(f"{out}  {len(recs)} records")
