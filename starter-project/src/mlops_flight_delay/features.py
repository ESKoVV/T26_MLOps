from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def _prepare(
    entities: pd.DataFrame,
    history: pd.DataFrame,
    contract: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    entity_key = contract["entity_key"]
    event_time = contract["event_timestamp"]
    feature_time = contract["feature_timestamp"]
    available_time = contract["available_timestamp"]
    feature_columns = list(contract["features"])
    required_entities = {"request_id", entity_key, event_time}
    required_history = {entity_key, feature_time, available_time, *feature_columns}
    missing = (required_entities - set(entities.columns)) | (
        required_history - set(history.columns)
    )
    if missing:
        raise ValueError(f"Отсутствуют обязательные столбцы: {sorted(missing)}")
    if entities["request_id"].duplicated().any():
        raise ValueError("request_id должен быть уникален")

    prepared_entities = entities.copy()
    prepared_history = history.copy()
    prepared_entities[event_time] = pd.to_datetime(
        prepared_entities[event_time], utc=True, errors="raise"
    )
    for column in (feature_time, available_time):
        prepared_history[column] = pd.to_datetime(
            prepared_history[column], utc=True, errors="raise"
        )
    if prepared_history[[entity_key, feature_time, available_time]].duplicated().any():
        raise ValueError("Строка истории признаков должна иметь уникальную временную идентичность")
    return prepared_entities, prepared_history


def naive_latest_join(
    entities: pd.DataFrame,
    history: pd.DataFrame,
    contract: dict[str, Any],
) -> pd.DataFrame:
    """Intentionally unsafe baseline: latest feature per entity ignores event time."""
    entity_key = contract["entity_key"]
    feature_time = contract["feature_timestamp"]
    prepared_entities, prepared_history = _prepare(entities, history, contract)
    latest = prepared_history.sort_values(feature_time).groupby(entity_key).tail(1)
    return prepared_entities.merge(latest, on=entity_key, how="left", validate="many_to_one")


def point_in_time_join(
    entities: pd.DataFrame,
    history: pd.DataFrame,
    contract: dict[str, Any],
) -> pd.DataFrame:
    """Select the latest feature row that was observable at each entity event time."""
    entity_key = contract["entity_key"]
    event_time = contract["event_timestamp"]
    feature_time = contract["feature_timestamp"]
    available_time = contract["available_timestamp"]
    ttl = pd.Timedelta(hours=float(contract["ttl_hours"]))
    feature_columns = list(contract["features"])
    prepared_entities, prepared_history = _prepare(entities, history, contract)

    candidates = prepared_entities.merge(prepared_history, on=entity_key, how="left")
    age = candidates[event_time] - candidates[feature_time]
    eligible = candidates[
        (candidates[feature_time] <= candidates[event_time])
        & (candidates[available_time] <= candidates[event_time])
        & (age >= pd.Timedelta(0))
        & (age <= ttl)
    ].copy()
    eligible["feature_age_hours"] = age.loc[eligible.index].dt.total_seconds() / 3600
    latest = eligible.sort_values(["request_id", feature_time, available_time]).groupby(
        "request_id", as_index=False
    ).tail(1)
    selected = latest[
        ["request_id", feature_time, available_time, "feature_age_hours", *feature_columns]
    ]
    return prepared_entities.merge(selected, on="request_id", how="left", validate="one_to_one")


def build_feature_audit(
    entities: pd.DataFrame,
    naive: pd.DataFrame,
    correct: pd.DataFrame,
    contract: dict[str, Any],
) -> dict[str, Any]:
    event_time = contract["event_timestamp"]
    feature_time = contract["feature_timestamp"]
    available_time = contract["available_timestamp"]
    feature_columns = list(contract["features"])
    naive_leaks = (
        (naive[feature_time] > naive[event_time]) | (naive[available_time] > naive[event_time])
    ).fillna(False)
    correct_leaks = (
        (correct[feature_time] > correct[event_time])
        | (correct[available_time] > correct[event_time])
    ).fillna(False)
    missing = correct[feature_columns].isna().any(axis=1)
    changed = naive[feature_columns].fillna("<missing>").astype(str).ne(
        correct[feature_columns].fillna("<missing>").astype(str)
    ).any(axis=1)
    rows = len(entities)
    return {
        "schema_version": "1.0.0",
        "contract_version": contract["contract_version"],
        "entity_rows": rows,
        "naive_leakage_rows": int(naive_leaks.sum()),
        "point_in_time_leakage_rows": int(correct_leaks.sum()),
        "rows_changed_vs_naive": int(changed.sum()),
        "feature_coverage": round(1.0 - float(missing.mean()), 6) if rows else 0.0,
        "max_feature_age_hours": (
            round(float(correct["feature_age_hours"].max()), 6)
            if correct["feature_age_hours"].notna().any()
            else None
        ),
        "status": "pass" if not correct_leaks.any() else "fail",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entities", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    entities = pd.read_csv(args.entities)
    history = pd.read_csv(args.history)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    naive = naive_latest_join(entities, history, contract)
    correct = point_in_time_join(entities, history, contract)
    audit = build_feature_audit(entities, naive, correct, contract)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    naive.to_csv(args.output_dir / "naive.csv", index=False)
    correct.to_csv(args.output_dir / "point-in-time.csv", index=False)
    (args.output_dir / "audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
