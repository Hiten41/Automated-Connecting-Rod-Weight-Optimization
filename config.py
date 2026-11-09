"""Portable defaults. Environment variables or local_config.json override paths."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS_DIR = ROOT / "runs"
DATA_DIR = ROOT / "data/verified"
MODEL_PATH = ROOT / "models/fea_surrogate.joblib"
