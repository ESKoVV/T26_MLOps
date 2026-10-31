"""Chronological train/validation/test split shared by validation and training."""

from __future__ import annotations

import pandas as pd

SPLIT_FRACTIONS = (0.6, 0.8)
SPLIT_POLICY = "chronological-60-20-20-by-date"


def sort_by_event_time(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy sorted by FlightDate; equal dates keep their file order."""
    result = frame.copy()
    result["FlightDate"] = pd.to_datetime(result["FlightDate"], errors="raise")
    return result.sort_values("FlightDate", kind="stable").reset_index(drop=True)


def chronological_bounds(dates: pd.Series) -> tuple[int, int]:
    """Row indices that end train and validation in a frame sorted by date.

    Cuts start near 60 % and 80 % of rows and move back to the first row of that
    calendar day, so one day never lands in two parts. With one row per day this
    equals int(n * 0.6) and int(n * 0.8).
    """
    values = pd.to_datetime(dates).reset_index(drop=True)
    bounds = []
    for fraction in SPLIT_FRACTIONS:
        position = int(len(values) * fraction)
        if position >= len(values):
            bounds.append(len(values))
            continue
        bounds.append(int(values.searchsorted(values.iloc[position], side="left")))
    return bounds[0], bounds[1]
