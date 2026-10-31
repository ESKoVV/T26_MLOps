"""LR14: choose the classification threshold on validation and score the test period.

The threshold maximizes F1 on the validation part only; test is scored once with it.
usage: build_governance_eval.py DATA MODEL OUT_CSV OUT_THRESHOLD_JSON
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from mlops_flight_delay.split import chronological_bounds, sort_by_event_time
from mlops_flight_delay.train import delay_target


def main() -> None:
    data_path, model_path, out_csv, out_json = map(Path, sys.argv[1:5])
    bundle = joblib.load(model_path)
    data = sort_by_event_time(pd.read_csv(data_path))
    train_end, validation_end = chronological_bounds(data["FlightDate"])
    validation, test = data.iloc[train_end:validation_end], data.iloc[validation_end:]
    features = bundle["features"]

    scores = bundle["model"].predict_proba(validation[features])[:, 1]
    target = delay_target(validation["ArrDelay"])
    grid = np.round(np.arange(0.05, 0.51, 0.01), 2)
    f1 = [f1_score(target, scores >= threshold, zero_division=0) for threshold in grid]
    best = int(np.argmax(f1))

    test_scores = bundle["model"].predict_proba(test[features])[:, 1]
    request_id = (
        "bts-"
        + test.FlightDate.dt.strftime("%Y%m%d")
        + "-"
        + test.Carrier
        + test.FlightNumber.astype(str)
        + "-h"
        + test.DepHour.astype(str)
    )
    pd.DataFrame(
        {
            "request_id": request_id,
            "y_true": delay_target(test["ArrDelay"]).to_numpy(),
            "prediction_probability": test_scores.round(6),
            "IsWeekend": test["IsWeekend"].to_numpy(),
        }
    ).to_csv(out_csv, index=False)
    out_json.write_text(
        json.dumps(
            {
                "selected_on": "validation",
                "validation_period": [
                    str(validation.FlightDate.min().date()),
                    str(validation.FlightDate.max().date()),
                ],
                "criterion": "max F1",
                "threshold": float(grid[best]),
                "validation_f1": round(float(f1[best]), 6),
                "validation_f1_at_0_5": round(float(f1[list(grid).index(0.5)]), 6),
                "test_rows": len(test),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(grid[best], round(float(f1[best]), 4))


if __name__ == "__main__":
    main()
