import unittest
from src.askui_runner.modules.core.models import WorkspaceCredentials
from src.askui_runner.modules.queue.domain.services import RunnerJobStatus
from src.askui_runner.modules.queue.infrastructure.runner.k8s_job import (
    K8sJobRunner,
    RunnerJob,
)
from src.askui_runner.modules.queue.models import (
    Config,
    K8sJobRunnerConfig,
    K8sToleration,
    RunnerJobData,
)


class TestK8sJobRunner(unittest.TestCase):
    def setUp(self):
        self.config = K8sJobRunnerConfig(
            namespace="test_namespace",
            node_selector={"test": "test"},
            tolerations=[
                K8sToleration(
                    effect="NoSchedule",
                    key="test",
                    operator="Equal",
                    value="test",
                )
            ],
        )

        def build_runner_config(runner_job_data: RunnerJobData) -> Config:
            config = Config(
                entrypoint="JOB",
                credentials=runner_job_data.credentials,
                job=runner_job_data,
            )
            config.runner.id = "test_id"
            return config

        self.runner_config_factory = build_runner_config
        self.runner = K8sJobRunner(self.config, self.runner_config_factory)

    def test_build_k8s_job(self):
        mock_runner_job = RunnerJob(
            id="test_id",
            ack="test_ack",
            status=RunnerJobStatus.RUNNING,
            visible=1,
            runner_id="test_runner_id",
            tries=1,
            data=RunnerJobData(
                credentials=WorkspaceCredentials(
                    access_token="test_access_token",
                    workspace_id="test_workspace_id",
                ),
                workflows=[],
                results_api_url="https://results.com",
                workflows_api_url="https://workflows.com",
                inference_api_url="https://inference.com",
            ),
        )
        k8s_job = self.runner._build_k8s_job(mock_runner_job)
        k8s_job_dict = k8s_job.to_dict()
        self.maxDiff = None
        self.assertEqual(
            k8s_job_dict["metadata"]["name"],
            "askui-runner-test_id-1",
        )
        self.assertEqual(
            k8s_job_dict["metadata"]["labels"],
            {
                "app.kubernetes.io/component": "runner",
                "app.kubernetes.io/instance": "askui-runner-test_id-1",
                "app.kubernetes.io/name": "askui-runner-test_id-1",
                "app.kubernetes.io/part-of": "runner",
                "app.kubernetes.io/version": "0.1.0",
                "askui.com/runner-id": "test_runner_id",
                "askui.com/runner-job-id": "test_id",
                "askui.com/workspace-id": "test_workspace_id",
            },
        )
        self.assertEqual(
            k8s_job_dict["spec"]["ttl_seconds_after_finished"],
            120,
        )
        self.assertEqual(
            k8s_job_dict["spec"]["template"]["spec"]["restart_policy"],
            "Never",
        )
        self.assertEqual(
            k8s_job_dict["spec"]["template"]["spec"]["node_selector"],
            {"test": "test"},
        )
        self.assertEqual(
            k8s_job_dict["spec"]["template"]["spec"]["tolerations"],
            [
                {
                    "effect": "NoSchedule",
                    "key": "test",
                    "operator": "Equal",
                    "value": "test",
                    "toleration_seconds": None,
                }
            ],
        )
        self.assertEqual(
            k8s_job_dict["spec"]["template"]["spec"]["containers"],
            [
                {
                    "args": [
                        "\n"
                        "                                    "
                        "python -m "
                        "askui_runner -c "
                        '\'{"entrypoint": '
                        '"JOB", "runner": '
                        '{"id": '
                        '"test_id", '
                        '"exec": "pdm run '
                        'python -m runner", '
                        '"tags": [], "type": '
                        '"SUBPROCESS", '
                        '"host": "SELF", '
                        '"project_dir": '
                        '"project_template", '
                        '"workflows_dir": '
                        '"workflows", '
                        '"results_dir": '
                        '"results-allure", '
                        '"enable": {"setup": '
                        "true, "
                        '"download_workflows": '
                        "true, "
                        '"run_workflows": '
                        "true, "
                        '"upload_results": '
                        'true, "teardown": '
                        "true}}, "
                        '"credentials": '
                        '{"workspace_id": '
                        '"test_workspace_id", '
                        '"access_token": '
                        '"test_access_token"}, '
                        '"queue": {"api_url": '
                        '"https://app-gateway-api.askui.com/prod/api/v1/workspaces/test_workspace_id/runner-jobs", '
                        '"keep_alive": true, '
                        '"polling_interval": '
                        "30, "
                        '"k8s_job_runner": '
                        '{"namespace": "dev", '
                        '"shared_memory": '
                        '"1Gi", '
                        '"tolerations": [], '
                        '"node_selector": '
                        "null, "
                        '"runner_container": '
                        '{"image": '
                        '"askuigmbh/askui-runner:latest", '
                        '"resources": '
                        '{"requests": {"cpu": '
                        '"500m", "memory": '
                        '"1Gi"}, "limits": '
                        '{"cpu": "500m", '
                        '"memory": "1Gi"}}}, '
                        '"controller_container": '
                        '{"image": '
                        '"askuigmbh/askui-ui-controller:v0.11.2-chrome-100.0.4896.60-amd64", '
                        '"resources": '
                        '{"requests": {"cpu": '
                        '"500m", "memory": '
                        '"1Gi"}, "limits": '
                        '{"cpu": "500m", '
                        '"memory": '
                        '"1Gi"}}}}}, '
                        '"job_timeout": 3600, '
                        '"job": '
                        '{"credentials": '
                        '{"workspace_id": '
                        '"test_workspace_id", '
                        '"access_token": '
                        '"test_access_token"}, '
                        '"workflows": [], '
                        '"results_api_url": '
                        '"https://results.com", '
                        '"workflows_api_url": '
                        '"https://workflows.com", '
                        '"inference_api_url": '
                        '"https://inference.com"}, '
                        '"log_level": '
                        '"INFO"}\';\n'
                        "                                    "
                        "exit_code=$?;\n"
                        "                                    "
                        'echo -n "$exit_code" '
                        "> "
                        "/opt/exit-signals/EXIT;\n"
                        "                                    "
                        "exit $exit_code;\n"
                        "                                    "
                    ],
                    "command": ["/bin/sh", "-c"],
                    "env": None,
                    "env_from": None,
                    "image": "askuigmbh/askui-runner:latest",
                    "image_pull_policy": "Always",
                    "lifecycle": None,
                    "liveness_probe": None,
                    "name": "askui-runner",
                    "ports": None,
                    "readiness_probe": None,
                    "resources": {
                        "limits": {"cpu": "500m", "memory": "1Gi"},
                        "requests": {"cpu": "500m", "memory": "1Gi"},
                    },
                    "security_context": None,
                    "startup_probe": None,
                    "stdin": None,
                    "stdin_once": None,
                    "termination_message_path": None,
                    "termination_message_policy": None,
                    "tty": None,
                    "volume_devices": None,
                    "volume_mounts": [
                        {
                            "mount_path": "/opt/exit-signals",
                            "mount_propagation": None,
                            "name": "exit-signals",
                            "read_only": None,
                            "sub_path": None,
                            "sub_path_expr": None,
                        },
                        {
                            "mount_path": "/dev/shm",
                            "mount_propagation": None,
                            "name": "cache-volume",
                            "read_only": None,
                            "sub_path": None,
                            "sub_path_expr": None,
                        },
                    ],
                    "working_dir": None,
                },
                {
                    "args": [
                        "\n"
                        "                                    "
                        "./entrypoint.sh &\n"
                        "                                    "
                        "while [ ! -f "
                        "/opt/exit-signals/EXIT "
                        "]; do\n"
                        "                                        "
                        "sleep 5;\n"
                        "                                    "
                        "done;\n"
                        "                                    "
                        "exit $(cat "
                        "/opt/exit-signals/EXIT);\n"
                        "                                    "
                    ],
                    "command": ["/bin/sh", "-c"],
                    "env": None,
                    "env_from": None,
                    "image": "askuigmbh/askui-ui-controller:v0.11.2-chrome-100.0.4896.60-amd64",
                    "image_pull_policy": None,
                    "lifecycle": None,
                    "liveness_probe": None,
                    "name": "askui-controller",
                    "ports": None,
                    "readiness_probe": None,
                    "resources": {
                        "limits": {"cpu": "500m", "memory": "1Gi"},
                        "requests": {"cpu": "500m", "memory": "1Gi"},
                    },
                    "security_context": None,
                    "startup_probe": None,
                    "stdin": None,
                    "stdin_once": None,
                    "termination_message_path": None,
                    "termination_message_policy": None,
                    "tty": None,
                    "volume_devices": None,
                    "volume_mounts": [
                        {
                            "mount_path": "/opt/exit-signals",
                            "mount_propagation": None,
                            "name": "exit-signals",
                            "read_only": True,
                            "sub_path": None,
                            "sub_path_expr": None,
                        },
                        {
                            "mount_path": "/dev/shm",
                            "mount_propagation": None,
                            "name": "cache-volume",
                            "read_only": None,
                            "sub_path": None,
                            "sub_path_expr": None,
                        },
                    ],
                    "working_dir": None,
                },
            ],
        )
        self.assertEqual(
            k8s_job_dict["spec"]["template"]["spec"]["image_pull_secrets"],
            [{"name": "docker"}],
        )
        self.assertEqual(
            k8s_job_dict["spec"]["template"]["spec"]["volumes"],
            [
                {
                    "aws_elastic_block_store": None,
                    "azure_disk": None,
                    "azure_file": None,
                    "cephfs": None,
                    "cinder": None,
                    "config_map": None,
                    "csi": None,
                    "downward_api": None,
                    "empty_dir": {"medium": None, "size_limit": None},
                    "ephemeral": None,
                    "fc": None,
                    "flex_volume": None,
                    "flocker": None,
                    "gce_persistent_disk": None,
                    "git_repo": None,
                    "glusterfs": None,
                    "host_path": None,
                    "iscsi": None,
                    "name": "exit-signals",
                    "nfs": None,
                    "persistent_volume_claim": None,
                    "photon_persistent_disk": None,
                    "portworx_volume": None,
                    "projected": None,
                    "quobyte": None,
                    "rbd": None,
                    "scale_io": None,
                    "secret": None,
                    "storageos": None,
                    "vsphere_volume": None,
                },
                {
                    "aws_elastic_block_store": None,
                    "azure_disk": None,
                    "azure_file": None,
                    "cephfs": None,
                    "cinder": None,
                    "config_map": None,
                    "csi": None,
                    "downward_api": None,
                    "empty_dir": {"medium": "Memory", "size_limit": "1Gi"},
                    "ephemeral": None,
                    "fc": None,
                    "flex_volume": None,
                    "flocker": None,
                    "gce_persistent_disk": None,
                    "git_repo": None,
                    "glusterfs": None,
                    "host_path": None,
                    "iscsi": None,
                    "name": "cache-volume",
                    "nfs": None,
                    "persistent_volume_claim": None,
                    "photon_persistent_disk": None,
                    "portworx_volume": None,
                    "projected": None,
                    "quobyte": None,
                    "rbd": None,
                    "scale_io": None,
                    "secret": None,
                    "storageos": None,
                    "vsphere_volume": None,
                },
            ],
        )
        self.assertEqual(
            k8s_job_dict["spec"]["active_deadline_seconds"],
            3600,
        )
        self.assertEqual(
            k8s_job_dict["spec"]["backoff_limit"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
