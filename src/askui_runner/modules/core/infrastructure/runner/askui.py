import os
import shutil
import sys
from typing import Any, Optional

import jinja2

from ...domain.services import (
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


class AskUiJestRunnerService(Runner):
    def __init__(
        self,
        config: dict[str, Any],
        workflows_download_service: WorkflowsDownload,
        results_upload_service: ResultsUpload,
    ) -> None:
        super().__init__(config, workflows_download_service, results_upload_service)
        self.cwd: Optional[str] = None

    @property
    def project_dir(
        self,
    ) -> (
        str
    ):
        entrypoint_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(entrypoint_dir, self.config.project_dir) # TODO Rename project_dir to project_template_dir

    def create_jinja_env(self, dir_path: str) -> jinja2.Environment:
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(searchpath=dir_path),
        )

    def render_templates(self, dir_path: str) -> None:
        jinja_env = self.create_jinja_env(dir_path=dir_path)
        for root, _, files in os.walk(dir_path):
            for file in files:
                if not file.endswith(".jinja"):
                    continue
                template_file_path = os.path.relpath(os.path.join(root, file), dir_path)
                target_file_path = os.path.join(
                    root, file[:-6]
                )  # TODO Use jinja literal for -6
                with create_and_open(target_file_path, "w") as f:
                    f.write(
                        jinja_env.get_template(template_file_path).render(
                            self.config.dict()
                        )
                    )

    def setup(self, dir_path: str) -> None:
        self.cwd = os.getcwd()
        os.chdir(self.project_dir)
        os.system("npm install")
        copy_directory_contents(src_dir=self.project_dir, dest_dir=dir_path)
        self.render_templates(dir_path=dir_path)
        os.chdir(dir_path)

    def run_workflows(self) -> RunWorkflowsResult:
        # TODO Determine how this was ended based on exit code, configure jest accordingly, things in file system etc. and with what exit code runner should end --> Use that exit code to set the status
        # TODO Differentiate of failure of runner and failure of workflows and workflows not available and worklows erroneous (including not parseable)
        exit_code = os.system("npx jest --config jest.config.ts")
        if exit_code != 0:
            return RunWorkflowsResult.FAILURE
        return RunWorkflowsResult.SUCCESS

    def teardown(self) -> None:
        if self.cwd is not None:
            os.chdir(self.cwd)
