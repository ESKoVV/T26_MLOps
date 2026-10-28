from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).parents[1]


@pytest.fixture
def sample_data_path() -> Path:
    return ROOT / "data" / "flights_sample.csv"


@pytest.fixture
def contract_path() -> Path:
    return ROOT / "data" / "contract.json"


@pytest.fixture
def model_path(tmp_path: Path) -> Path:
    return tmp_path / "model.joblib"


@pytest.fixture
def valid_frame(sample_data_path: Path) -> pd.DataFrame:
    """A fresh copy of the course sample for each test; mutate freely."""
    return pd.read_csv(sample_data_path)


@pytest.fixture
def csv_factory(tmp_path: Path) -> Callable[..., Path]:
    def write(frame: pd.DataFrame, name: str = "input.csv") -> Path:
        path = tmp_path / name
        frame.to_csv(path, index=False)
        return path

    return write
