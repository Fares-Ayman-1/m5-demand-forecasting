"""Typed configuration loaded from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Paths(BaseModel):
    raw: Path
    interim: Path
    models: Path
    reports: Path

    def resolve(self, root: Path) -> Paths:
        def r(p: Path) -> Path:
            return p if p.is_absolute() else (root / p).resolve()

        return Paths(raw=r(self.raw), interim=r(self.interim), models=r(self.models), reports=r(self.reports))


class FeatureConfig(BaseModel):
    lags: list[int]
    rolling_windows: list[int]


class Config(BaseModel):
    competition: str
    paths: Paths
    tracking_uri: str
    artifact_root: str = "../mlruns"
    experiment: str
    horizon: int = Field(gt=0)
    last_day: int
    backtest_cutoffs: list[int]
    train_start_day: int
    features: FeatureConfig
    lgbm: dict[str, Any]
    num_boost_round: int = Field(gt=0)

    @field_validator("features")
    @classmethod
    def _lags_respect_horizon(cls, v: FeatureConfig, info: Any) -> FeatureConfig:
        horizon = info.data.get("horizon", 28)
        bad = [lag for lag in v.lags if lag < horizon]
        if bad:
            raise ValueError(f"lags {bad} are shorter than the horizon {horizon}: they would leak the target")
        return v

    @field_validator("backtest_cutoffs")
    @classmethod
    def _cutoffs_in_range(cls, v: list[int], info: Any) -> list[int]:
        last, horizon = info.data.get("last_day"), info.data.get("horizon")
        if last is not None and horizon is not None:
            for c in v:
                if c + horizon > last:
                    raise ValueError(
                        f"backtest cutoff {c} + horizon {horizon} is beyond the last known day {last}"
                    )
        return v


def load_config(path: str | Path | None = None, root: Path = PROJECT_ROOT) -> Config:
    p = Path(path) if path else root / "configs" / "default.yaml"
    cfg = Config.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
    cfg.paths = cfg.paths.resolve(root)
    return cfg


def _abs(p: str, root: Path) -> Path:
    path = Path(p)
    return path if path.is_absolute() else (root / path).resolve()


def tracking_uri(cfg: Config, root: Path = PROJECT_ROOT) -> str:
    """SQLite tracking database (MLflow 3 no longer accepts a plain folder as the tracking store)."""
    import os

    env = os.environ.get("MLFLOW_TRACKING_URI")
    if env:
        return env
    db = _abs(cfg.tracking_uri, root)
    db.parent.mkdir(parents=True, exist_ok=True)
    return "sqlite:///" + db.as_posix()


def setup_mlflow(cfg: Config, root: Path = PROJECT_ROOT) -> str:
    """Point MLflow at the shared store and make sure the experiment exists. Returns the experiment id."""
    import mlflow

    mlflow.set_tracking_uri(tracking_uri(cfg, root))
    exp = mlflow.get_experiment_by_name(cfg.experiment)
    if exp is not None:
        mlflow.set_experiment(experiment_id=exp.experiment_id)
        return exp.experiment_id
    artifacts = _abs(cfg.artifact_root, root)
    artifacts.mkdir(parents=True, exist_ok=True)
    exp_id = mlflow.create_experiment(cfg.experiment, artifact_location=artifacts.as_uri())
    mlflow.set_experiment(experiment_id=exp_id)
    return exp_id
