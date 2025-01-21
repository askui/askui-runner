import logging
from importlib.metadata import version

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from ...queue import Runner, RunnerJob
from ...models import K8sJobRunnerConfig
from .shared import RunnerConfigFactory


class K8sJobRunner(Runner):
    def __init__(
        self, config: K8sJobRunnerConfig, runner_config_factory: RunnerConfigFactory
    ):
        self.config = config
        self.load_k8s_config()
        self.batch_api = client.BatchV1Api()
        self.runner_config_factory = runner_config_factory
        self.k8s_job: client.V1Job | None = None

    def load_k8s_config(self) -> None:
        try:
            logging.info("Loading in-cluster config...")
            config.load_incluster_config()
        except:  # noqa: E722
            logging.info("Failed. Falling back to kube config...")
            config.load_kube_config()

    def _build_k8s_job(self, runner_job: RunnerJob) -> client.V1Job:
        name = f"askui-runner-{runner_job.id}-{runner_job.tries}"
        label_prefix = "askui.com"
        labels = {
            "app.kubernetes.io/name": name,
            "app.kubernetes.io/instance": name,
            "app.kubernetes.io/version": version("askui-runner"),
            "app.kubernetes.io/component": "runner",
            "app.kubernetes.io/part-of": "runner",
            # "app.kubernetes.io/managed-by": ,
            f"{label_prefix}/runner-job-id": runner_job.id,
            f"{label_prefix}/workspace-id": runner_job.data.credentials.workspace_id,
            f"{label_prefix}/runner-id": runner_job.runner_id,
        }
        runner_config = self.runner_config_factory(runner_job_data=runner_job.data)
        return client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=name,
                labels=labels,
            ),
            spec=client.V1JobSpec(
                ttl_seconds_after_finished=120,
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        restart_policy="Never",
                        containers=[
                            client.V1Container(
                                name="askui-runner",
                                image=self.config.runner_container.image,
                                image_pull_policy="Always",
                                command=["/bin/sh", "-c"],
                                args=[  # WARNING: may be unsafe if json values include single quotes
                                    f"""
                                    python -m askui_runner -c '{runner_config.json()}';
                                    exit_code=$?;
                                    echo -n "$exit_code" > /opt/exit-signals/EXIT;
                                    exit $exit_code;
                                    """,
                                ],
                                volume_mounts=[
                                    client.V1VolumeMount(
                                        mount_path="/opt/exit-signals",
                                        name="exit-signals",
                                    ),
                                    client.V1VolumeMount(
                                        name="cache-volume",
                                        mount_path="/dev/shm",
                                    ),
                                ],
                                resources=client.V1ResourceRequirements(
                                    **self.config.runner_container.resources.model_dump()
                                ),
                            ),
                            client.V1Container(
                                name="askui-controller",
                                image=self.config.controller_container.image,
                                command=["/bin/sh", "-c"],
                                args=[
                                    # Doesn't handle pod restart --> exits immediately because of existing EXIT file
                                    """
                                    ./entrypoint.sh &
                                    while [ ! -f /opt/exit-signals/EXIT ]; do
                                        sleep 5;
                                    done;
                                    exit $(cat /opt/exit-signals/EXIT);
                                    """,
                                ],
                                volume_mounts=[
                                    client.V1VolumeMount(
                                        mount_path="/opt/exit-signals",
                                        name="exit-signals",
                                        read_only=True,
                                    ),
                                    client.V1VolumeMount(
                                        name="cache-volume",
                                        mount_path="/dev/shm",
                                    ),
                                ],
                                resources=client.V1ResourceRequirements(
                                    **self.config.controller_container.resources.model_dump()
                                ),
                            ),
                        ],
                        image_pull_secrets=[
                            client.V1LocalObjectReference(name="docker"),
                        ],
                        volumes=[
                            client.V1Volume(
                                empty_dir=client.V1EmptyDirVolumeSource(),
                                name="exit-signals",
                            ),
                            client.V1Volume(
                                name="cache-volume",
                                empty_dir=client.V1EmptyDirVolumeSource(
                                    medium="Memory",
                                    size_limit=self.config.shared_memory,
                                ),
                            ),
                        ],
                        tolerations=[
                            client.V1Toleration(
                                **toleration.model_dump(),
                            )
                            for toleration in self.config.tolerations
                        ]
                        if self.config.tolerations
                        else None,
                        node_selector=self.config.node_selector,
                    ),
                ),
                backoff_limit=0,
                active_deadline_seconds=runner_config.job_timeout,
            ),
        )

    def _handle_api_exception(self, exception: ApiException) -> None:
        if exception.status == 404:
            logging.error(f"The K8s job might not exist anymore: {exception}")
        else:
            logging.error(f"An unexpected error occurred: {exception}")

    def _create_k8s_job(self, job: client.V1Job) -> None:
        try:
            self.batch_api.create_namespaced_job(
                body=job,
                namespace=self.config.namespace,
            )
        except ApiException as exception:
            self._handle_api_exception(exception)

    def start(self, runner_job: RunnerJob) -> None:
        self.k8s_job = self._build_k8s_job(runner_job=runner_job)
        self._create_k8s_job(job=self.k8s_job)

    def _get_k8s_job_status(self) -> client.V1JobStatus:
        """
        Helper method to get the current status of the Kubernetes job.
        """
        try:
            if not self.k8s_job:
                raise Exception("No Kubernetes job has been created or started yet.")
            job: client.V1Job = self.batch_api.read_namespaced_job(
                name=self.k8s_job.metadata.name,  # type: ignore
                namespace=self.config.namespace,
            )
            if not job.status:
                raise Exception("The Kubernetes job has no status.")
            return job.status
        except ApiException as exception:
            self._handle_api_exception(exception)
            raise exception

    def is_running(self) -> bool:
        """
        Check if the Kubernetes job is currently running.
        """
        try:
            self._get_k8s_job_status()
            return not self.has_passed() and not self.has_failed()
        except:  # noqa: E722
            return False

    def has_passed(self) -> bool:
        """
        Check if the Kubernetes job has completed successfully.
        """
        try:
            job_status = self._get_k8s_job_status()
            return (
                job_status.succeeded is not None
                and job_status.succeeded > 0
                and (job_status.active is None or job_status.active == 0)
                and (job_status.failed is None or job_status.failed == 0)
            )
        except:  # noqa: E722
            return False

    def has_failed(self) -> bool:
        """
        Check if the Kubernetes job has failed.
        """
        try:
            job_status = self._get_k8s_job_status()
            return job_status.failed is not None and job_status.failed > 0
        except:  # noqa: E722
            return True

    def stop(self) -> None:
        """
        Stop and delete the Kubernetes job.
        """
        if not self.k8s_job:
            raise Exception("No Kubernetes job has been created or started yet.")
        try:
            self.batch_api.delete_namespaced_job(
                name=self.k8s_job.metadata.name,  # type: ignore
                namespace=self.config.namespace,
            )
        except ApiException as e:
            self._handle_api_exception(e)
