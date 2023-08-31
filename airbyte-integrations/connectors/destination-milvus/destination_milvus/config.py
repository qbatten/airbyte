import json
import re
from typing import Literal, Optional, Union
from airbyte_cdk.utils.spec_schema_transformations import resolve_refs

import dpath.util
from airbyte_cdk.destinations.vector_db_based.config import (
    CohereEmbeddingConfigModel,
    FakeEmbeddingConfigModel,
    OpenAIEmbeddingConfigModel,
    ProcessingConfigModel,
)
from jsonschema import RefResolver
from pydantic import BaseModel, Field


class UsernamePasswordAuth(BaseModel):
    mode: Literal["username_password"] = Field("username_password", const=True)
    username: str = Field(..., title="Username", description="Username for the Milvus instance")
    password: str = Field(..., title="Password", description="Password for the Milvus instance", airbyte_secret=True)


class TokenAuth(BaseModel):
    mode: Literal["token"] = Field("token", const=True)
    token: str = Field(..., title="API Token", description="API Token for the Milvus instance", airbyte_secret=True)


class MilvusIndexingConfigModel(BaseModel):
    host: str = Field(..., title="Public Endpoint")
    db: Optional[str] = Field(title="Database Name", description="The database to connect to", default="")
    collection: str = Field(..., title="Collection Name", description="The collection to load data into")
    auth: Union[UsernamePasswordAuth, TokenAuth] = Field(
        ..., title="Authentication", description="Authentication method", discriminator="mode", type="object"
    )
    vector_field: str = Field(title="Vector Field", description="The field in the entity that contains the vector", default="vector")
    text_field: str = Field(title="Text Field", description="The field in the entity that contains the embedded text", default="text")

    class Config:
        title = "Indexing"
        schema_extra = {
            "group": "Indexing",
            "description": "Indexing configuration",
        }


class ConfigModel(BaseModel):
    processing: ProcessingConfigModel
    embedding: Union[OpenAIEmbeddingConfigModel, CohereEmbeddingConfigModel, FakeEmbeddingConfigModel] = Field(
        ..., title="Embedding", description="Embedding configuration", discriminator="mode", group="embedding", type="object"
    )
    indexing: MilvusIndexingConfigModel

    class Config:
        title = "Milvus Destination Config"
        schema_extra = {
            "groups": [
                {"id": "processing", "title": "Processing"},
                {"id": "embedding", "title": "Embedding"},
                {"id": "indexing", "title": "Indexing"},
            ]
        }

    @staticmethod
    def resolve_refs(schema: dict) -> dict:
        # config schemas can't contain references, so inline them
        json_schema_ref_resolver = RefResolver.from_schema(schema)
        str_schema = json.dumps(schema)
        for ref_block in re.findall(r'{"\$ref": "#\/definitions\/.+?(?="})"}', str_schema):
            ref = json.loads(ref_block)["$ref"]
            str_schema = str_schema.replace(ref_block, json.dumps(json_schema_ref_resolver.resolve(ref)[1]))
        pyschema: dict = json.loads(str_schema)
        del pyschema["definitions"]
        return pyschema

    @staticmethod
    def remove_discriminator(schema: dict) -> None:
        """pydantic adds "discriminator" to the schema for oneOfs, which is not treated right by the platform as we inline all references"""
        dpath.util.delete(schema, "properties/*/discriminator")

    @classmethod
    def schema(cls):
        """we're overriding the schema classmethod to enable some post-processing"""
        schema = super().schema()
        schema = resolve_refs(schema)
        cls.remove_discriminator(schema)
        return schema

