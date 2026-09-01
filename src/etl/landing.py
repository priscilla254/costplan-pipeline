"""Local landing zone. Swap for Azure Blob later without changing parsers."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned or "unknown"


def land_file(source_path: str | Path, identifier: str, landing_dir: str | Path) -> Path:
    source = Path(source_path)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest_dir = Path(landing_dir) / _safe_segment(identifier)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{stamp}_{source.name}"
    dest.write_bytes(source.read_bytes())
    return dest
