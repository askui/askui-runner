import os
from pathlib import Path
from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import SettingsConfigDict


class WorkspaceCredentials(BaseModel):
    workspace_id: str = Field(
        ...,
        description="ID of the workspace",
        examples=["9cf30c31-ea1e-4ff5-994a-c4a0dc70882f"],
    )
    access_token: str = Field(
        ...,
        description="Access token for authenticating and authorizing with the workspace",
        examples=["yio2P5qX5exUyX4bG1P-T7"],
    )


class AgentFileSyncConfig(BaseModel):
    base_url: HttpUrl = Field(
        HttpUrl("https://workspaces.askui.com/api/v1/files/"),
        description="Base URL of the files API.",
    )
    local_storage_base_dir: Path = Field(
        Path(os.path.join(os.path.expanduser("~"), ".askui")),
        description="Local directory for storing files.",
        examples=["/home/user/.askui", "C:\\Users\\user\\.askui"],
    )


class AgentsConfig(BaseModel):
    credentials: WorkspaceCredentials
    sync: AgentFileSyncConfig = Field(
        default_factory=AgentFileSyncConfig,  # type: ignore
        description="Configuration for syncing files",
    )
    model_config = SettingsConfigDict(env_prefix="askui_runner_agents_", extra="allow")
