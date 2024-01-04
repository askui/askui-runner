from pydantic import BaseModel, BaseSettings, Field


class FeatureToggles(BaseModel):
    setup: bool = Field(True, description="Whether to setup project")
    download_workflows: bool = Field(True, description="Whether to download workflows")
    run_workflows: bool = Field(True, description="Whether to run workflows")
    upload_results: bool = Field(True, description="Whether to upload results")
    teardown: bool = Field(True, description="Whether to run teardown project")


class WorkspaceCredentials(BaseModel):
    workspace_id: str = Field(..., description="ID of the workspace")
    access_token: str = Field(
        ...,
        description="Access token for authenticating and authorizing with the workspace",
    )


class WorkflowsConfig(BaseModel):
    api_url: str
    prefixes: list[str]
    dir: str


class ResultsConfig(BaseModel):
    api_url: str
    dir: str


class ControllerConfig(BaseModel):
    host: str = Field("127.0.0.1", description="Host of the ui controller")
    port: int = Field(6769, description="Port of the ui controller")


class CoreConfigBase(BaseModel):
    controller: ControllerConfig = Field(ControllerConfig())
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
    
    class Config:
        env_prefix = "askui_runner_core_"
