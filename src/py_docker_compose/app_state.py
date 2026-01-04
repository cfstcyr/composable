from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppState:
    src_dir: Path
    src_patterns: list[str]
