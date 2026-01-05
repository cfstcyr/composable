import re
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from pydantic import (
    BaseModel,
    Field,
    RootModel,
)


class BaseSrc(ABC):
    @abstractmethod
    def list_files(self) -> Sequence[Path]: ...

    @abstractmethod
    def get_dir(self) -> Path: ...


class SrcGlob(BaseSrc, BaseModel):
    dir: Path = Field(
        description="Base directory to search for files. If not specified, the current working directory is used.",
    )
    glob: str = Field(
        default="**/*.*",
        examples=["**/*.*", "*.yaml", "configs/**/*.yml"],
        description="Glob pattern to match files within the specified directory.",
    )
    exclude_patterns: list[str] = Field(
        default_factory=lambda: [r"\/_"],
        examples=[r"\/_"],
        description="List of regex patterns to exclude from the results.",
    )

    def list_files(self) -> list[Path]:
        files = list(self.dir.glob(self.glob))

        for pattern in self.exclude_patterns:
            files = [f for f in files if not re.search(pattern, str(f))]

        return files

    def get_dir(self) -> Path:
        return self.dir


class SrcFileRoot(BaseSrc, RootModel[Path]):
    def list_files(self) -> list[Path]:
        return [self.root]

    def get_dir(self) -> Path:
        return self.root.parent


class SrcFile(BaseSrc, BaseModel):
    file: Path

    def list_files(self) -> list[Path]:
        return [self.file]

    def get_dir(self) -> Path:
        return self.file.parent


ScalarSrc = SrcGlob | SrcFile | SrcFileRoot


class SrcList(BaseSrc, RootModel[Sequence[ScalarSrc]]):
    def list_files(self) -> list[Path]:
        return [file for source in self.root for file in source.list_files()]

    def get_dir(self) -> Path:
        return Path.cwd()


Src = ScalarSrc | SrcList
