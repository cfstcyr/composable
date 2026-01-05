from dataclasses import dataclass

from py_docker_compose.libs.schemas.src import Src


@dataclass
class AppState:
    src: Src
