from pathlib import Path

import pytest


@pytest.fixture
def sample_data_path() -> Path:
    return Path(__file__).parents[1] / "data" / "flights_sample.csv"


@pytest.fixture
def model_path(tmp_path: Path) -> Path:
    return tmp_path / "model.joblib"


@pytest.fixture
def contract_path() -> Path:
    return Path(__file__).parents[1] / "data" / "contract.json"
