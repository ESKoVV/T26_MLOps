from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from mlops_flight_delay.split import SPLIT_POLICY, chronological_bounds, sort_by_event_time


def _check(name: str, passed: bool, details: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "details": details}


def chronological_split_summary(
    data: pd.DataFrame, *, target_threshold: int = 15
) -> dict[str, Any]:
    """Describe the train/validation/test periods exactly as training will cut them."""
    frame = sort_by_event_time(data)
    train_end, validation_end = chronological_bounds(frame["FlightDate"])
    parts = {
        "train": frame.iloc[:train_end],
        "validation": frame.iloc[train_end:validation_end],
        "test": frame.iloc[validation_end:],
    }
    summary: dict[str, Any] = {"policy": SPLIT_POLICY, "target": f"ArrDelay >= {target_threshold}"}
    for name, part in parts.items():
        if part.empty:
            summary[name] = {"rows": 0}
            continue
        summary[name] = {
            "rows": len(part),
            "start": part["FlightDate"].min().strftime("%Y-%m-%d"),
            "end": part["FlightDate"].max().strftime("%Y-%m-%d"),
            "positive_rate": round(float((part["ArrDelay"] >= target_threshold).mean()), 4),
        }
    non_empty = all(len(part) for part in parts.values())
    summary["ordered"] = bool(
        non_empty
        and parts["train"]["FlightDate"].max() < parts["validation"]["FlightDate"].min()
        and parts["validation"]["FlightDate"].max() < parts["test"]["FlightDate"].min()
    )
    return summary


def read_dvc_md5(dvc_file: Path) -> str | None:
    """Return the md5 of the first output in a .dvc pointer (DVC 3 writes '- md5: ...')."""
    for line in dvc_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip().removeprefix("- ")
        if stripped.startswith("md5:"):
            return stripped.split(":", 1)[1].strip()
    return None


def dvc_pointer_check(data_path: Path, dvc_file: Path) -> dict[str, Any]:
    """Compare the working file with the md5 recorded in its .dvc pointer."""
    recorded = read_dvc_md5(dvc_file)
    actual = hashlib.md5(data_path.read_bytes()).hexdigest()
    return _check(
        "dvc.md5_matches",
        recorded is not None and recorded == actual,
        f"recorded={recorded} actual={actual}",
    )


def validate_dataset(
    data_path: Path, contract_path: Path, dvc_file: Path | None = None
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    data = pd.read_csv(data_path)
    checks: list[dict[str, Any]] = []

    expected = set(contract["columns"])
    actual = set(data.columns)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    checks.append(_check("required_columns", not missing, f"missing={missing}"))
    checks.append(
        _check(
            "extra_columns",
            contract.get("allow_extra_columns", False) or not extra,
            f"extra={extra}",
        )
    )
    minimum_rows = int(contract.get("minimum_rows", 1))
    checks.append(_check("minimum_rows", len(data) >= minimum_rows, f"rows={len(data)}"))

    duplicates = int(data.duplicated().sum())
    duplicate_policy = contract.get("duplicate_rows", "allow")
    checks.append(
        _check(
            "duplicate_rows",
            duplicate_policy != "forbid" or duplicates == 0,
            f"duplicates={duplicates}",
        )
    )

    for column, rules in contract["columns"].items():
        if column not in data.columns:
            continue
        series = data[column]
        null_count = int(series.isna().sum())
        checks.append(
            _check(
                f"{column}.nullable",
                bool(rules.get("nullable", True)) or null_count == 0,
                f"nulls={null_count}",
            )
        )

        if rules.get("type") in {"integer", "number"}:
            numeric = pd.to_numeric(series, errors="coerce")
            invalid = int((numeric.isna() & series.notna()).sum())
            checks.append(_check(f"{column}.type", invalid == 0, f"invalid={invalid}"))
            valid_numeric = numeric.dropna()
            if rules.get("type") == "integer":
                non_integer = int((valid_numeric % 1 != 0).sum())
                checks.append(
                    _check(f"{column}.integer", non_integer == 0, f"non_integer={non_integer}")
                )
            if "minimum" in rules:
                below = int((valid_numeric < rules["minimum"]).sum())
                checks.append(_check(f"{column}.minimum", below == 0, f"below={below}"))
            if "maximum" in rules:
                above = int((valid_numeric > rules["maximum"]).sum())
                checks.append(_check(f"{column}.maximum", above == 0, f"above={above}"))

        if rules.get("type") == "date":
            parsed = pd.to_datetime(series, format=rules.get("format"), errors="coerce")
            invalid = int((parsed.isna() & series.notna()).sum())
            checks.append(_check(f"{column}.date", invalid == 0, f"invalid={invalid}"))

        if rules.get("type") == "string" and "pattern" in rules:
            mismatched = int((~series.dropna().astype(str).str.fullmatch(rules["pattern"])).sum())
            checks.append(_check(f"{column}.pattern", mismatched == 0, f"mismatched={mismatched}"))

        if "allowed_values" in rules:
            allowed = set(rules["allowed_values"])
            invalid_values = sorted({value for value in series.dropna() if value not in allowed})
            checks.append(
                _check(
                    f"{column}.allowed_values",
                    not invalid_values,
                    f"invalid_values={invalid_values}",
                )
            )

    if "FlightDate" in data.columns:
        dates = pd.to_datetime(data["FlightDate"], errors="coerce")
        checks.append(
            _check(
                "FlightDate.chronological_order",
                bool(dates.is_monotonic_increasing),
                "rows must be sorted by event time",
            )
        )

    if dvc_file is not None:
        checks.append(dvc_pointer_check(data_path, dvc_file))

    split = None
    if all(item["passed"] for item in checks):
        split = chronological_split_summary(data)
        checks.append(
            _check(
                "split.chronological_boundaries",
                split["ordered"],
                "max(train) < min(validation) <= max(validation) < min(test)",
            )
        )

    return {
        "contract_version": contract["contract_version"],
        "dataset": contract["dataset"],
        "data_file": data_path.as_posix(),
        "sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "rows": len(data),
        "columns": list(data.columns),
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
        "split": split,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Проверка CSV по контракту данных")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--dvc-file", type=Path, help="сверить файл с md5 из .dvc-указателя")
    args = parser.parse_args()

    result = validate_dataset(args.data, args.contract, args.dvc_file)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
