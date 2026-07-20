from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import expit


def queue_imbalance(bid_size: float | np.ndarray, ask_size: float | np.ndarray):
    bid = np.asarray(bid_size, dtype=float)
    ask = np.asarray(ask_size, dtype=float)
    denominator = bid + ask
    if np.any(denominator <= 0):
        raise ValueError("bid_size + ask_size must be positive")
    result = (bid - ask) / denominator
    return float(result) if result.ndim == 0 else result


@dataclass(frozen=True)
class Level1Event:
    timestamp: float
    day: int
    bid_price: float
    ask_price: float
    bid_size: float
    ask_size: float
    is_mid_price_change: bool

    @property
    def mid_price(self) -> float:
        return (self.bid_price + self.ask_price) / 2.0

    @property
    def imbalance(self) -> float:
        return queue_imbalance(self.bid_size, self.ask_size)


@dataclass(frozen=True)
class QueueObservations:
    imbalance: np.ndarray
    response: np.ndarray
    sampled_time: np.ndarray
    interval_start: np.ndarray
    interval_end: np.ndarray
    source_event_time: np.ndarray
    day: np.ndarray
    interval_index: np.ndarray
    latent_probability_up: np.ndarray

    def assert_aligned(self) -> None:
        if not np.all(self.sampled_time > self.interval_start):
            raise AssertionError("a sample is not strictly after its interval start")
        if not np.all(self.sampled_time < self.interval_end):
            raise AssertionError("a sample is not strictly before its target move")
        if not np.all(self.source_event_time <= self.sampled_time):
            raise AssertionError("a feature event occurs after the observation time")
        if not np.all(self.source_event_time < self.interval_end):
            raise AssertionError("post-move information entered a feature")


class QueueImbalanceFixture:
    """Deterministic Level-1 stream with an inspectable one-tick target.

    The target direction for every interval is sampled from a logistic probability
    driven by the pre-move imbalance. At the target move timestamp an intentionally
    reversed queue state is inserted, so an endpoint/leakage bug is detectable.
    """

    def __init__(
        self,
        *,
        days: int = 12,
        intervals_per_day: int = 140,
        seed: int = 7,
        interval_seconds: float = 10.0,
    ) -> None:
        if days <= 0 or intervals_per_day <= 1:
            raise ValueError("days and intervals_per_day must be positive")
        self.days = days
        self.intervals_per_day = intervals_per_day
        self.seed = seed
        self.interval_seconds = interval_seconds
        self.events: list[Level1Event] = []
        self.move_times: list[np.ndarray] = []
        self.directions: list[np.ndarray] = []
        self.latent_imbalances: list[np.ndarray] = []
        self.latent_probabilities: list[np.ndarray] = []
        self._build()

    @staticmethod
    def _sizes(imbalance: float, scale: float = 100.0) -> tuple[float, float]:
        clipped = float(np.clip(imbalance, -0.95, 0.95))
        return scale * (1.0 + clipped), scale * (1.0 - clipped)

    def _append_state(
        self,
        *,
        timestamp: float,
        day: int,
        mid: float,
        imbalance: float,
        is_move: bool,
    ) -> None:
        bid_size, ask_size = self._sizes(imbalance)
        self.events.append(
            Level1Event(
                timestamp=timestamp,
                day=day,
                bid_price=mid - 0.005,
                ask_price=mid + 0.005,
                bid_size=bid_size,
                ask_size=ask_size,
                is_mid_price_change=is_move,
            )
        )

    def _build(self) -> None:
        rng = np.random.default_rng(self.seed)
        global_interval = 0
        for day in range(self.days):
            day_start = day * 10_000.0
            mid = 100.0 + day * 0.02
            phase = np.arange(self.intervals_per_day) + day * 17
            latent = 0.82 * np.sin(phase * 0.37) + 0.08 * np.cos(phase * 0.11)
            latent = np.clip(latent, -0.9, 0.9)
            probability = expit(3.2 * latent)
            direction = np.where(rng.random(self.intervals_per_day) < probability, 1, -1)
            move_times = day_start + self.interval_seconds * (np.arange(self.intervals_per_day) + 1)

            self._append_state(
                timestamp=day_start,
                day=day,
                mid=mid,
                imbalance=float(latent[0]),
                is_move=False,
            )
            for index in range(self.intervals_per_day):
                start = day_start + self.interval_seconds * index
                signal = float(latent[index])
                for fraction, perturbation in ((0.3, -0.035), (0.7, 0.035)):
                    self._append_state(
                        timestamp=start + self.interval_seconds * fraction,
                        day=day,
                        mid=mid,
                        imbalance=float(np.clip(signal + perturbation, -0.92, 0.92)),
                        is_move=False,
                    )
                mid += float(direction[index]) * 0.01
                end = float(move_times[index])
                self._append_state(
                    timestamp=end,
                    day=day,
                    mid=mid,
                    imbalance=-signal,
                    is_move=True,
                )
                if index + 1 < self.intervals_per_day:
                    self._append_state(
                        timestamp=end,
                        day=day,
                        mid=mid,
                        imbalance=float(latent[index + 1]),
                        is_move=False,
                    )
                global_interval += 1

            self.move_times.append(move_times)
            self.directions.append(direction.astype(np.int8))
            self.latent_imbalances.append(latent)
            self.latent_probabilities.append(probability)

        # Construction is chronological already; stable sorting preserves the post-move
        # state followed by the next interval's state at a shared boundary.
        self.events.sort(key=lambda event: event.timestamp)

    def sample_paper_observations(
        self,
        *,
        observations_per_day: int = 100,
        seed: int | None = None,
    ) -> QueueObservations:
        if observations_per_day > self.intervals_per_day:
            raise ValueError("observations_per_day exceeds available mid-price changes")
        rng = np.random.default_rng(self.seed + 1 if seed is None else seed)
        event_times = np.fromiter((event.timestamp for event in self.events), dtype=float)

        values: dict[str, list[float | int]] = {
            "imbalance": [],
            "response": [],
            "sampled_time": [],
            "interval_start": [],
            "interval_end": [],
            "source_event_time": [],
            "day": [],
            "interval_index": [],
            "latent_probability_up": [],
        }
        for day in range(self.days):
            selected = rng.choice(self.intervals_per_day, size=observations_per_day, replace=False)
            for interval in selected:
                end = float(self.move_times[day][interval])
                start = end - self.interval_seconds
                sampled = float(rng.uniform(start, end))
                if sampled <= start:
                    sampled = float(np.nextafter(start, end))
                if sampled >= end:
                    sampled = float(np.nextafter(end, start))
                event_index = int(np.searchsorted(event_times, sampled, side="right") - 1)
                event = self.events[event_index]
                if event.day != day:
                    raise AssertionError("event lookup crossed a day boundary")
                values["imbalance"].append(event.imbalance)
                values["response"].append(int(self.directions[day][interval] > 0))
                values["sampled_time"].append(sampled)
                values["interval_start"].append(start)
                values["interval_end"].append(end)
                values["source_event_time"].append(event.timestamp)
                values["day"].append(day)
                values["interval_index"].append(interval)
                values["latent_probability_up"].append(
                    float(self.latent_probabilities[day][interval])
                )

        observations = QueueObservations(
            imbalance=np.asarray(values["imbalance"], dtype=float),
            response=np.asarray(values["response"], dtype=np.int8),
            sampled_time=np.asarray(values["sampled_time"], dtype=float),
            interval_start=np.asarray(values["interval_start"], dtype=float),
            interval_end=np.asarray(values["interval_end"], dtype=float),
            source_event_time=np.asarray(values["source_event_time"], dtype=float),
            day=np.asarray(values["day"], dtype=np.int16),
            interval_index=np.asarray(values["interval_index"], dtype=np.int32),
            latent_probability_up=np.asarray(values["latent_probability_up"], dtype=float),
        )
        observations.assert_aligned()
        return observations
