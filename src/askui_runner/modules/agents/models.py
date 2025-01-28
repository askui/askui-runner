import os
from pathlib import Path
from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import SettingsConfigDict


class WorkspaceCredentials(BaseModel):
    workspace_id: str = Field(..., description="ID of the workspace")
    access_token: str = Field(
        ...,
        description="Access token for authenticating and authorizing with the workspace",
    )


class AgentFileSyncConfig(BaseModel):
    base_url: HttpUrl = Field(
        HttpUrl("https://workspaces.askui.com/api/v1/files/"),
        description="Base URL of the files API.",
    )
    local_storage_base_dir: Path = Field(
        Path(os.path.join(os.path.expanduser("~"), ".askui")),
        description="Local directory for storing files.",
    )


class AgentsConfig(BaseModel):
    credentials: WorkspaceCredentials
    sync: AgentFileSyncConfig = Field(
        default_factory=AgentFileSyncConfig,  # type: ignore
        description="Configuration for syncing files",
    )
    model_config = SettingsConfigDict(env_prefix="askui_runner_agents_", extra="allow")
