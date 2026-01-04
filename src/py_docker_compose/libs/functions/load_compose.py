from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from omegaconf import OmegaConf

from py_docker_compose.libs.models.docker_compose import DockerComposeModel


def load_compose(
    src_dir: Path,
    src_patterns: list[str],
    *,
    data: dict[str, Any] = {},
) -> DockerComposeModel:
    env = Environment(
        loader=FileSystemLoader(src_dir), undefined=StrictUndefined, autoescape=True
    )
    conf = OmegaConf.create()

    for pattern in src_patterns:
        for file in sorted(src_dir.rglob(pattern)):
            template = env.get_template(str(file.relative_to(src_dir)))
            rendered_content = template.render(**data)
            conf = OmegaConf.merge(conf, OmegaConf.create(rendered_content))

    return DockerComposeModel.model_validate(OmegaConf.to_container(conf, resolve=True))
