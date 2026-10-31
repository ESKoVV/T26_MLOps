"""Build LR13 carrier feature history and entity events from the BTS fragment.

History: one row per carrier and day D — share of ATL departures delayed >= 15 min on D
and their count. The batch is computed after the day closes: feature_time = D+1 00:00,
available_time = D+1 06:00. Entities: flights of the event window, event_time =
scheduled departure - 60 min (prediction time).

usage: build_feature_history.py DATA OUT_DIR --event-start D --event-end D
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--event-start", required=True)
    parser.add_argument("--event-end", required=True)
    parser.add_argument("--available-delay-hours", type=float, default=6.0)
    args = parser.parse_args()

    data = pd.read_csv(args.data, parse_dates=["FlightDate"])
    data["delayed"] = (data.ArrDelay >= 15).astype(int)
    daily = (
        data.groupby(["Carrier", "FlightDate"])
        .agg(trailing_delay_rate=("delayed", "mean"), flights_last_24h=("delayed", "size"))
        .reset_index()
    )
    day_end = daily.FlightDate + pd.Timedelta(days=1)
    history = pd.DataFrame(
        {
            "Carrier": daily.Carrier,
            "feature_time": day_end.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "available_time": (
                day_end + pd.Timedelta(hours=args.available_delay_hours)
            ).dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trailing_delay_rate": daily.trailing_delay_rate.round(6),
            "flights_last_24h": daily.flights_last_24h,
        }
    )

    window = data[(data.FlightDate >= args.event_start) & (data.FlightDate <= args.event_end)]
    departure = window.FlightDate + pd.to_timedelta(window.DepHour.astype("int64"), unit="h")
    entities = pd.DataFrame(
        {
            "request_id": "bts-"
            + window.FlightDate.dt.strftime("%Y%m%d")
            + "-"
            + window.Carrier
            + window.FlightNumber.astype(str)
            + "-h"
            + window.DepHour.astype(str),
            "Carrier": window.Carrier,
            "event_time": (departure - pd.Timedelta(hours=1)).dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "DepHour": window.DepHour,
            "IsWeekend": window.IsWeekend,
            "ArrDelay": window.ArrDelay,
        }
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    history.to_csv(args.out_dir / "history.csv", index=False)
    entities.to_csv(args.out_dir / "entities.csv", index=False)
    print(len(history), len(entities), entities.Carrier.nunique())


if __name__ == "__main__":
    main()
