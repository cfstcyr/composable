from pydantic import BaseModel, ConfigDict


class DockerComposeServiceModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    image: str
    ports: list[str] | None = None
    environment: dict[str, str] | None = None


class DockerComposeModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    services: dict[str, DockerComposeServiceModel]
