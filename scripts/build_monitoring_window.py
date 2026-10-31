"""Build LR12 monitoring logs from the BTS fragment and a trained bundle.

reference = feature rows of the training period, current = flights of a later window,
predictions = what the model answered 60 min before departure, labels = ArrDelay that
becomes known after arrival. Times are local airport time written as UTC (BTS gives no
time zone); the delay between prediction and label is what matters for coverage.

usage: build_monitoring_window.py DATA MODEL OUT_DIR --reference-end D --current-start D
       [--current-end D] [--label-delay-hours H]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--reference-end", required=True, help="последний день reference")
    parser.add_argument("--current-start", required=True)
    parser.add_argument("--current-end", default=None)
    parser.add_argument("--label-delay-hours", type=float, default=6.0)
    parser.add_argument(
        "--weekends-only", action="store_true", help="сценарий сдвига: только выходные"
    )
    parser.add_argument(
        "--missing-label-share",
        type=float,
        default=0.0,
        help="доля меток, которые ещё не пришли (сценарий неполного coverage)",
    )
    args = parser.parse_args()

    data = pd.read_csv(args.data, parse_dates=["FlightDate"])
    bundle = joblib.load(args.model)
    features = bundle["features"]
    reference = data[data.FlightDate <= args.reference_end]
    current = data[data.FlightDate >= args.current_start]
    if args.current_end:
        current = current[current.FlightDate <= args.current_end]
    if args.weekends_only:
        current = current[current.IsWeekend == 1]
    current = current.copy()

    departure = current.FlightDate + pd.to_timedelta(current.DepHour.astype("int64"), unit="h")
    current["request_id"] = (
        "bts-"
        + current.FlightDate.dt.strftime("%Y%m%d")
        + "-"
        + current.Carrier
        + current.FlightNumber.astype(str)
        + "-h"
        + current.DepHour.astype(str)
    )
    current["event_time"] = (departure - pd.Timedelta(hours=1)).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    current["prediction_probability"] = bundle["model"].predict_proba(current[features])[:, 1]
    current["model_version"] = str(bundle.get("version", "unknown"))
    label_time = departure + pd.Timedelta(hours=args.label_delay_hours)
    current["label_time"] = label_time.dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    reference[features].to_csv(args.out_dir / "reference.csv", index=False)
    current[features].to_csv(args.out_dir / "current.csv", index=False)
    current[
        ["request_id", "event_time", "prediction_probability", "model_version", *features]
    ].to_csv(args.out_dir / "predictions.csv", index=False)
    labels = current[["request_id", "label_time", "ArrDelay"]]
    if args.missing_label_share:
        labels = labels.drop(labels.sample(frac=args.missing_label_share, random_state=42).index)
    labels.to_csv(args.out_dir / "labels.csv", index=False)
    print(len(reference), len(current), int(current.request_id.duplicated().sum()))


if __name__ == "__main__":
    main()
