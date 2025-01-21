import json
import logging
import os
import shutil
import socket
import sys
import tempfile
import time
from typing import Any, Optional

import jinja2

from ...runner import (
    ResultsUpload,
    Runner,
    RunWorkflowsResult,
    WorkflowsDownload,
)
from ..files.utils import create_and_open


def copy_directory_contents(src_dir: str, dest_dir: str) -> None:
    if not os.path.exists(src_dir):
        raise ValueError(f"Source directory {src_dir} does not exist")
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    for item in os.listdir(src_dir):
        src_path = os.path.join(src_dir, item)
        dest_path = os.path.join(dest_dir, item)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dest_path)
        else:
            shutil.copy2(src_path, dest_path)


def is_port_open(host, port):
    """Check if a given port is open on a given host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)  # timeout of 1 second for trying to connect
        try:
            s.connect((host, port))
            return True
        except socket.error:
            return False


def wait_for_controller_to_start(host: str, port: int):
    while True:
        if is_port_open(host, port):
            break
        else:
            logging.info(f"Waiting for controller to start on {host}:{port}...")
            time.sleep(10)


class AskUIJestRunner(Runner):
    _TEMPLATE_EXTENSION = "jinja"

    def __init__(
        self,
        config: dict[str, Any],
        workflows_download_service: WorkflowsDownload,
        results_upload_service: ResultsUpload,
    ) -> None:
        super().__init__(config)
        self.workflows_download_service = workflows_download_service
        self.results_upload_service = results_upload_service
        self.cwd: Optional[str] = None

    @property
    def project_dir(
        self,
    ) -> str:
        entrypoint_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(entrypoint_dir, self.config.project_dir)

    def _create_jinja_env(self, dir_path: str) -> jinja2.Environment:
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(searchpath=dir_path),
        )

    def _render_templates(self, dir_path: str) -> None:
        jinja_env = self._create_jinja_env(dir_path=dir_path)
        templates = jinja_env.list_templates(
            extensions=[AskUIJestRunner._TEMPLATE_EXTENSION]
        )
        for template in templates:
            template_name_without_extension = template[
                : -(len(AskUIJestRunner._TEMPLATE_EXTENSION) + 1)
            ]  # +1 for the dot
            target_file_path = os.path.join(
                dir_path, *template_name_without_extension.split("/")
            )
            with create_and_open(target_file_path, "w") as f:
                f.write(
                    jinja_env.get_template(template).render(self.config.model_dump())
                )

    def setup(self, dir_path: str) -> None:
        self.cwd = os.getcwd()
        os.chdir(self.project_dir)
        os.system("npm install")
        copy_directory_contents(src_dir=self.project_dir, dest_dir=dir_path)
        self._render_templates(dir_path=dir_path)
        with create_and_open(os.path.join(dir_path, "data.json"), "w") as f:
            json.dump(self.config.data, f)
        os.chdir(dir_path)

    def download_workflows(self) -> None:
        self.workflows_download_service.download()

    def run_workflows(self) -> RunWorkflowsResult:
        if self.config.enable.wait_for_controller:
            wait_for_controller_to_start(
                host=self.config.controller.host,
                port=self.config.controller.port,
            )
        exit_code = os.system(self.config.command)
        if exit_code != 0:
            return RunWorkflowsResult.FAILURE
        return RunWorkflowsResult.SUCCESS

    def upload_results(self) -> None:
        self.results_upload_service.upload()

    def teardown(self) -> None:
        if self.cwd is not None:
            os.chdir(self.cwd)


class AskUIVisionAgentExperimentsRunner(Runner):
    def __init__(
        self,
        config: dict[str, Any],
    ) -> None:
        super().__init__(config)
        self.cwd = os.getcwd()

    def run(self) -> RunWorkflowsResult:
        with tempfile.TemporaryDirectory(
            prefix="askui-runner-",
        ) as dir_path:
            os.chdir(dir_path)
            logging.info(f"Cloning vision agent experiments into {dir_path}...")
            os.system(
                "git clone --depth 1 --branch main --single-branch https://github.com/askui/vision-agent-experiments.git"
            )
            os.chdir("vision-agent-experiments")
            logging.info("Setting up environment variables...")
            os.environ["ASKUI_WORKSPACE_ID"] = self.config.credentials.workspace_id
            os.environ["ASKUI_TOKEN"] = self.config.credentials.access_token
            for key, value in self.config.data.items():
                os.environ[key.upper()] = (
                    json.dumps(value) if not isinstance(value, str) else value
                )
            logging.info("Installing dependencies with pdm install...")
            os.system("pdm install")
            logging.info("Running vision agent experiments with pdm run vae...")
            exit_code = os.system("pdm run vae")
            os.chdir(self.cwd)
            if exit_code == 0:
                return RunWorkflowsResult.SUCCESS
            return RunWorkflowsResult.FAILURE
