from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from mlops_flight_delay.evaluate import classification_metrics
from mlops_flight_delay.split import chronological_bounds, sort_by_event_time

FEATURES = ["DepHour", "IsWeekend"]


def train_model(
    data_path: Path,
    model_path: Path,
    *,
    n_estimators: int = 80,
    max_depth: int = 4,
    random_state: int = 42,
) -> float:
    data = pd.read_csv(data_path)
    missing = set(FEATURES + ["FlightDate", "ArrDelay"]) - set(data.columns)
    if missing:
        raise ValueError(f"Отсутствуют обязательные столбцы: {sorted(missing)}")
    if data[FEATURES + ["ArrDelay"]].isna().any().any():
        raise ValueError("Обучающие данные содержат пропуски")

    data = sort_by_event_time(data)
    x = data[FEATURES]
    y = (data["ArrDelay"] >= 15).astype(int)
    if y.nunique() < 2:
        raise ValueError("Для обучения нужны примеры обоих классов")

    train_end, validation_end = chronological_bounds(data["FlightDate"])
    x_train, y_train = x.iloc[:train_end], y.iloc[:train_end]
    x_validation, y_validation = x.iloc[train_end:validation_end], y.iloc[train_end:validation_end]
    y_test = y.iloc[validation_end:]
    if y_train.nunique() < 2 or y_validation.nunique() < 2 or y_test.nunique() < 2:
        raise ValueError("В каждой хронологической части нужны примеры обоих классов")
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
    )
    model.fit(x_train, y_train)
    validation_metrics = classification_metrics(
        y_validation.to_numpy(), model.predict_proba(x_validation)[:, 1]
    )
    validation_score = validation_metrics["roc_auc"]

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "features": FEATURES,
            "version": "0.2.0",
            "split": {"train_end": train_end, "validation_end": validation_end},
            "validation_roc_auc": float(validation_score),
            "validation_metrics": validation_metrics,
            "parameters": {
                "n_estimators": n_estimators,
                "max_depth": max_depth,
                "random_state": random_state,
            },
        },
        model_path,
    )
    return float(validation_score)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--n-estimators", type=int, default=80)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()
    score = train_model(
        args.data,
        args.model,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        random_state=args.random_state,
    )
    print(f"Validation ROC AUC: {score:.3f}")


if __name__ == "__main__":
    main()
