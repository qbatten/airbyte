# generated by datamodel-codegen:
#   filename:  ConnectorReleases.yaml

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import AnyUrl, BaseModel, Extra, Field, constr


class StreamBreakingChangeScope(BaseModel):
    class Config:
        extra = Extra.forbid

    scopeType: Any = Field("stream", const=True)
    impactedScopes: List[str] = Field(..., description="List of streams that are impacted by the breaking change.", min_items=1)


class BreakingChangeScope(BaseModel):
    __root__: StreamBreakingChangeScope = Field(..., description="A scope that can be used to limit the impact of a breaking change.")


class VersionBreakingChange(BaseModel):
    class Config:
        extra = Extra.forbid

    upgradeDeadline: date = Field(..., description="The deadline by which to upgrade before the breaking change takes effect.")
    message: str = Field(..., description="Descriptive message detailing the breaking change.")
    forceRelease: Optional[bool] = Field(None, description="The flag used to indicate whether a breaking change in the connector version should take effect less tha one week, bypassing the standard deadline requirement.")
    migrationDocumentationUrl: Optional[AnyUrl] = Field(
        None,
        description="URL to documentation on how to migrate to the current version. Defaults to ${documentationUrl}-migrations#${version}",
    )
    scopedImpact: Optional[List[BreakingChangeScope]] = Field(
        None,
        description="List of scopes that are impacted by the breaking change. If not specified, the breaking change cannot be scoped to reduce impact via the supported scope types.",
        min_items=1,
    )


class ConnectorBreakingChanges(BaseModel):
    class Config:
        extra = Extra.forbid

    __root__: Dict[constr(regex=r"^\d+\.\d+\.\d+$"), VersionBreakingChange] = Field(
        ..., description="Each entry denotes a breaking change in a specific version of a connector that requires user action to upgrade."
    )


class ConnectorReleases(BaseModel):
    class Config:
        extra = Extra.forbid

    breakingChanges: ConnectorBreakingChanges
    migrationDocumentationUrl: Optional[AnyUrl] = Field(
        None,
        description="URL to documentation on how to migrate from the previous version to the current version. Defaults to ${documentationUrl}-migrations",
    )
