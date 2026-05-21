from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    backend_dir: Path
    database_dir: Path
    checkpoint_db_path: Path
    allowed_origins: list[str]
    history_max_turns: int
    fast_model: str
    smart_model: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    backend_dir = Path(__file__).resolve().parents[2]
    root_dir = backend_dir.parent
    database_dir = backend_dir / "database"
    return Settings(
        root_dir=root_dir,
        backend_dir=backend_dir,
        database_dir=database_dir,
        checkpoint_db_path=database_dir / "checkpoints.sqlite",
        allowed_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
        history_max_turns=int(os.getenv("HISTORY_MAX_TURNS", "10")),
        fast_model=os.getenv("FAST_MODEL", "gemini-2.5-flash"),
        smart_model=os.getenv("SMART_MODEL", "gemini-2.5-flash"),
    )
