import json
import os
from typing import Any, Literal
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureToggles(BaseModel):
    setup: bool = Field(True, description="Whether to setup project")
    download_workflows: bool = Field(True, description="Whether to download workflows")
    run_workflows: bool = Field(True, description="Whether to run workflows")
    upload_results: bool = Field(True, description="Whether to upload results")
    teardown: bool = Field(True, description="Whether to run teardown project")
    wait_for_controller: bool = Field(
        True, description="Whether to wait for the controller to start"
    )


class WorkspaceCredentials(BaseModel):
    workspace_id: str = Field(..., description="ID of the workspace")
    access_token: str = Field(
        ...,
        description="Access token for authenticating and authorizing with the workspace",
    )


class WorkflowsConfig(BaseModel):
    api_url: str
    prefixes: list[str] | None = Field(default=None)
    dir: str


class ResultsConfig(BaseModel):
    api_url: str
    dir: str


class ScheduleResultsConfig(ResultsConfig):
    pass


class ControllerConfig(BaseModel):
    host: str = Field("127.0.0.1", description="Host of the ui controller")
    port: int = Field(6769, description="Port of the ui controller")


class CoreConfigBase(BaseModel):
    controller: ControllerConfig = Field(default_factory=ControllerConfig)  # type: ignore
    runner_type: Literal[
        "askui_jest_runner", "askui_vision_agent_experiments_runner"
    ] = Field("askui_jest_runner", description="Type of the runner")
    command: str = Field(
        "npx jest --config jest.config.ts",
        description="Command to run the workflows",
    )
    project_dir: str = Field(
        "project_template",
        description="Directory of the AskUi Node.js project template",
    )
    enable: FeatureToggles = Field(
        FeatureToggles(),  # type: ignore
        description="Feature toggles for the runner",
    )


class CoreConfig(CoreConfigBase, BaseSettings):
    credentials: WorkspaceCredentials
    inference_api_url: str
    workflows: WorkflowsConfig
    results: ResultsConfig
    schedule_results: ScheduleResultsConfig | None
    data: dict[str, Any] = Field(default_factory=dict)

    model_config = SettingsConfigDict(env_prefix="askui_runner_core_")


class AgentFileSyncConfig(BaseSettings):
    base_url: str = Field(
        "https://workspaces.askui.com/api/v1/files/",
        description="Base URL of the files API.",
    )
    local_storage_dir: str = Field(
        os.path.join(os.path.expanduser("~"), ".askui", "Agents"),
        description="Local directory for storing files.",
    )


class AgentConfig(BaseSettings):
    credentials: WorkspaceCredentials
    sync: AgentFileSyncConfig = Field(
        default_factory=AgentFileSyncConfig,  # type: ignore
        description="Configuration for syncing files",
    )
    model_config = SettingsConfigDict(env_prefix="askui_agent", extra="allow")

    def dump_example_config_to_json_file(self, output_file_path: str) -> None:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        example_config = self.model_validate_strings(
            {
                "credentials": {
                    "access_token": "your_access_token",
                    "workspace_id": "your_workspace_id",
                }
            }
        )
        with open(output_file_path, "w") as json_file:
            json.dump(example_config.model_dump(), json_file, indent=4)
