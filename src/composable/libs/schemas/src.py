from pathlib import Path
from typing import Annotated, Any

from packaging.specifiers import SpecifierSet
from pydantic import (
    BaseModel,
    BeforeValidator,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    PlainSerializer,
    WithJsonSchema,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

PydanticSpecifierSet = Annotated[
    SpecifierSet,
    BeforeValidator(lambda v: v if isinstance(v, SpecifierSet) else SpecifierSet(v)),
    PlainSerializer(str, return_type=str),
    WithJsonSchema(
        {
            "type": "string",
            "title": "Version Specifier",
            "examples": [">=1.0.0,<2.0.0", "==1.5.0", "~=1.4.2"],
            "description": "A packaging.specifiers.SpecifierSet string",
        }
    ),
]


class SpecifierSetValidator:
    def __get_pydantic_core_schema__(  # noqa: PLW3201
        self,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        def specifier_set_validator(v: str | SpecifierSet) -> SpecifierSet:
            if isinstance(v, SpecifierSet):
                return v
            return SpecifierSet(v)

        from_src_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(specifier_set_validator),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_src_schema,
            python_schema=core_schema.union_schema(
                [core_schema.is_instance_schema(SpecifierSet), from_src_schema]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

    @classmethod
    def __get_pydantic_json_schema__(  # noqa: PLW3201
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(core_schema.str_schema())


class Src(BaseModel):
    dir: Path
    glob: str
    exclude_patterns: list[str]
    version_spec: Annotated[SpecifierSet, SpecifierSetValidator()]
    version_spec_mapping: dict[str, Annotated[SpecifierSet, SpecifierSetValidator()]]
