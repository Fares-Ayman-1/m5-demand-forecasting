"""Download the competition files with the Kaggle API and write a SHA-256 manifest.

Requires a Kaggle API token (the KAGGLE_API_TOKEN environment variable or ~/.kaggle/kaggle.json)
and the competition rules accepted on kaggle.com. The token is read by the Kaggle client only;
this script never prints it.

    uv run python scripts/download_data.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from m5forecast.config import load_config

EXPECTED = ["calendar.csv", "sell_prices.csv", "sales_train_evaluation.csv", "sample_submission.csv"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    cfg = load_config()
    raw = cfg.paths.raw
    raw.mkdir(parents=True, exist_ok=True)

    # Trust the OS certificate store (needed where antivirus/proxy software re-signs HTTPS traffic).
    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    if not all((raw / f).exists() for f in EXPECTED):
        print(f"downloading {cfg.competition} -> {raw}")
        api.competition_download_files(cfg.competition, path=str(raw), quiet=False)
        for z in raw.glob("*.zip"):
            with zipfile.ZipFile(z) as zf:
                zf.extractall(raw)
            z.unlink()

    missing = [f for f in EXPECTED if not (raw / f).exists()]
    if missing:
        print(f"missing after download: {missing}", file=sys.stderr)
        return 1

    manifest = {
        "competition": cfg.competition,
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "files": {
            f.name: {"bytes": f.stat().st_size, "sha256": sha256(f)} for f in sorted(raw.glob("*.csv"))
        },
    }
    (raw.parent / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"ok: {len(manifest['files'])} files, manifest at {raw.parent / 'MANIFEST.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
