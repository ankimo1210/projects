"""Seed data/health.duckdb with 90 days of plausible fake data (UI dev without credentials)."""
import math
import random
from datetime import date, timedelta
from pathlib import Path

from health.store import Store

random.seed(7)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
store = Store(DATA_DIR / "health.duckdb")
today = date.today()

daily, sleep_rows = [], []
for i in range(90):
    d = today - timedelta(days=89 - i)
    ds = d.isoformat()
    steps = 6000 + 3000 * math.sin(i / 7) + random.randint(-1500, 1500)
    daily += [("steps", ds, max(0, steps)),
              ("calories", ds, 1800 + steps * 0.04),
              ("distance_km", ds, steps * 0.0007),
              ("minutes_very_active", ds, random.randint(0, 60)),
              ("resting_hr", ds, 60 + 3 * math.sin(i / 14) + random.random()),
              ("hrv_rmssd", ds, 35 + 8 * math.sin(i / 10) + random.random() * 3),
              ("sleep_minutes", ds, 380 + random.randint(-60, 60)),
              ("spo2_avg", ds, 96 + random.random()),
              ("weight_kg", ds, 72 - i * 0.01 + random.random() * 0.4),
              ("breathing_rate", ds, 15 + random.random()),
              ("temp_skin_relative", ds, random.random() - 0.5)]
    asleep = 380 + random.randint(-60, 60)
    sleep_rows.append({"log_id": 1000 + i, "date": ds,
                       "start_ts": f"{(d - timedelta(days=1)).isoformat()} 23:30:00",
                       "end_ts": f"{ds} 07:10:00", "minutes_asleep": asleep,
                       "minutes_deep": int(asleep * 0.18), "minutes_light": int(asleep * 0.55),
                       "minutes_rem": int(asleep * 0.22), "minutes_wake": int(asleep * 0.05),
                       "efficiency": random.randint(88, 97), "is_main": True})
store.upsert_daily(daily)
store.upsert_sleep(sleep_rows)
store.upsert_intraday([("hr", f"{today.isoformat()} {h:02d}:{mnt:02d}:00",
                        62 + 25 * math.exp(-((h - 18) ** 2) / 8) + random.random() * 4)
                       for h in range(24) for mnt in range(0, 60, 5)])
print("seeded:", DATA_DIR / "health.duckdb")
