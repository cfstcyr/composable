from pathlib import Path
from typing import Any, cast

from omegaconf import OmegaConf


def _load_file_content(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    if path.suffix in {".yaml", ".yml", ".json"}:
        return OmegaConf.load(path)

    with path.open("r", encoding="utf-8") as f:
        content = f.read()

    if path.suffix == ".txt":
        return content.strip()

    raise ValueError(f"Unsupported data file format: {path.suffix}")


def _expand_value(value: Any):
    if not isinstance(value, str):
        return value

    if value.startswith("@@"):
        return value[1:]

    if value.startswith("@"):
        return _load_file_content(Path(value[1:]))

    return value


def expand_values(data: dict[str, Any]) -> dict[str, Any]:
    expanded_data: dict[str, Any] = {}

    for key, value in data.items():
        if isinstance(value, dict):
            expanded_data[key] = expand_values(value)
        elif isinstance(value, list):
            expanded_data[key] = [_expand_value(item) for item in value]
        else:
            expanded_data[key] = _expand_value(value)

    return expanded_data


def load_data(
    data: list[dict[str, Any]],
    data_files: list[Path],
) -> dict[str, Any]:
    cfg = OmegaConf.create({})

    for d in data:
        d_cfg = OmegaConf.create(expand_values(d))
        cfg = OmegaConf.merge(cfg, d_cfg)

    for data_file in data_files:
        if not data_file.exists():
            continue

        file_data = cast(
            dict[str, Any], OmegaConf.to_container(OmegaConf.load(data_file))
        )
        expanded = expand_values(file_data)
        cfg = OmegaConf.merge(cfg, OmegaConf.create(expanded))

    return cast(dict[str, Any], OmegaConf.to_container(cfg, resolve=True))
