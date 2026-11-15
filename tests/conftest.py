from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from synthetic import write_config, write_raw

from m5forecast.config import Config, load_config


@pytest.fixture(scope="session")
def project(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Config]:
    root = tmp_path_factory.mktemp("m5")
    write_raw(root / "data" / "raw")
    cfg = load_config(write_config(root), root=root)
    return root, cfg


@pytest.fixture(scope="session")
def trained(project: tuple[Path, Config]) -> tuple[Path, Config, dict[str, object]]:
    """Run the full pipeline once (prepare -> backtests -> final model -> serving bundle)."""
    import os

    from m5forecast.data.prepare import prepare
    from m5forecast.train import run

    root, cfg = project
    os.environ.pop("MLFLOW_TRACKING_URI", None)
    prepare(cfg)
    result = run(cfg, stores=None, rounds=cfg.num_boost_round, final=True, root=root)
    return root, cfg, result
