from dataclasses import dataclass

from composable.app_config import AppConfig


@dataclass
class AppState:
    app_config: AppConfig
