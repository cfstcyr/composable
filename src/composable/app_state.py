from dataclasses import dataclass

from composable.app_config import AppConfig
from composable.libs.schemas.src import Src


@dataclass
class AppState:
    src: Src
    app_config: AppConfig
