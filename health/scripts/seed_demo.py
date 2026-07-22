"""Seed a DuckDB database with plausible fake Google Health data."""

from __future__ import annotations

import argparse
import math
import random
from datetime import date, timedelta
from pathlib import Path

from health.endpoints import CATALOG
from health.store import Store

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "health.duckdb"


def seed(db_path: Path, today: date | None = None) -> None:
    rng = random.Random(7)
    today = today or date.today()
    store = Store(db_path)
    daily, sleep_rows = [], []
    try:
        for i in range(90):
            day = today - timedelta(days=89 - i)
            day_text = day.isoformat()
            steps = 6000 + 3000 * math.sin(i / 7) + rng.randint(-1500, 1500)
            spo2 = 96 + rng.random()
            daily += [
                ("steps", day_text, max(0, steps)),
                ("calories", day_text, 1800 + steps * 0.04),
                ("distance_km", day_text, steps * 0.0007),
                ("minutes_lightly_active", day_text, rng.randint(30, 180)),
                ("minutes_fairly_active", day_text, rng.randint(0, 60)),
                ("minutes_very_active", day_text, rng.randint(0, 60)),
                ("resting_hr", day_text, 60 + 3 * math.sin(i / 14) + rng.random()),
                ("hrv_rmssd", day_text, 35 + 8 * math.sin(i / 10) + rng.random() * 3),
                ("hrv_deep_rmssd", day_text, 40 + 8 * math.sin(i / 10) + rng.random() * 3),
                ("sleep_minutes", day_text, 380 + rng.randint(-60, 60)),
                ("spo2_avg", day_text, spo2),
                ("spo2_lower_bound", day_text, spo2 - 1.5),
                ("spo2_upper_bound", day_text, min(100, spo2 + 1.0)),
                ("weight_kg", day_text, 72 - i * 0.01 + rng.random() * 0.4),
                ("fat_pct", day_text, 19 - i * 0.005 + rng.random() * 0.3),
                ("breathing_rate", day_text, 15 + rng.random()),
                ("temp_skin_relative", day_text, rng.random() - 0.5),
            ]
            asleep = 380 + rng.randint(-60, 60)
            # Bed time varies around 23:30 and crosses midnight every few nights.
            bed_minutes = 23 * 60 + 30 + rng.randint(-40, 80)
            bed_day = day - timedelta(days=1) if bed_minutes < 24 * 60 else day
            bed_clock = bed_minutes % (24 * 60)
            wake_clock = 7 * 60 + rng.randint(-30, 40)
            sleep_rows.append(
                {
                    "provider_id": f"demo-sleep-{i:03d}",
                    "date": day_text,
                    "start_ts": (
                        f"{bed_day.isoformat()} {bed_clock // 60:02d}:{bed_clock % 60:02d}:00"
                    ),
                    "end_ts": f"{day_text} {wake_clock // 60:02d}:{wake_clock % 60:02d}:00",
                    "minutes_asleep": asleep,
                    "minutes_deep": int(asleep * 0.18),
                    "minutes_light": int(asleep * 0.55),
                    "minutes_rem": int(asleep * 0.22),
                    "minutes_wake": int(asleep * 0.05),
                    "efficiency": rng.randint(88, 97),
                    "is_main": True,
                }
            )
        store.upsert_daily(daily)
        store.upsert_sleep(sleep_rows)
        intraday = []
        for day_offset in (0, 1):
            day_text = (today - timedelta(days=day_offset)).isoformat()
            intraday += [
                (
                    "hr",
                    f"{day_text} {hour:02d}:{minute:02d}:00",
                    62 + 25 * math.exp(-((hour - 18) ** 2) / 8) + rng.random() * 4,
                )
                for hour in range(24)
                for minute in range(0, 60, 5)
            ]
            intraday += [
                (
                    "steps",
                    f"{day_text} {hour:02d}:{minute:02d}:00",
                    max(0.0, rng.gauss(35, 30)) if 7 <= hour <= 22 else 0.0,
                )
                for hour in range(24)
                for minute in range(0, 60, 5)
            ]
        store.upsert_intraday(intraday)
        for metric in CATALOG:
            store.set_sync_state(metric.name, today)
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    seed(args.db_path)
    print(f"seeded: {args.db_path}")


if __name__ == "__main__":
    main()
