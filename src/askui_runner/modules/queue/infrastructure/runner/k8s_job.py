from kubernetes import client, config
from kubernetes.client.rest import ApiException

from ...domain.services import Runner, RunnerJob
from .shared import RunnerConfigFactory

NAMESPACE = "runner"
LABEL_PREFIX = "askui.com"


class K8sJobRunner(Runner):
    def __init__(self, runner_config_factory: RunnerConfigFactory):
        self.load_config()
        self.batch_api = client.BatchV1Api()
        # TODO Make configurable
        self.namespace = NAMESPACE
        self.name = "askui-runner"
        self.label_prefix = LABEL_PREFIX
        self.version = "0.1.0"
        self.ttl_seconds_after_finished = 120
        # TODO Authentication
        self.runner_image = "askuigmbh/askui-runner:test"
        self.controller_name = "askui-ui-controller"
        self.controller_image = (
            "askuigmbh/askui-ui-controller:v0.11.2-chrome-100.0.4896.60-amd64"
        )
        self.runner_config_factory = runner_config_factory
        self.k8s_job: client.V1Job | None = None

    def load_config(self) -> None:
        try:
            print("Loading in-cluster config...")
            config.load_incluster_config()
        except:  # pylint: disable=bare-except
            print("Failed. Falling back to kube config...")
            config.load_kube_config()  # TODO Does that work?

    def _build_k8s_job(self, runner_job: RunnerJob) -> client.V1Job:
        # TODO Is job removed after ttl_seconds_after_finished?
        name = f"{self.name}-{runner_job.id}-{runner_job.tries}"
        labels = {
            "app.kubernetes.io/name": name,
            "app.kubernetes.io/instance": f"{self.name}-{runner_job.id}",
            "app.kubernetes.io/version": self.version,
            "app.kubernetes.io/component": "runner",
            "app.kubernetes.io/part-of": "runner",
            "app.kubernetes.io/managed-by": self.name,
            f"{self.label_prefix}/runner-job-id": runner_job.id,
            f"{self.label_prefix}/workspace-id": runner_job.data.credentials.workspace_id,
            f"{self.label_prefix}/runner-id": runner_job.runner_id,
            # TODO Add run id and schedule id
            # TODO Add tags, host, etc.
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
                ttl_seconds_after_finished=self.ttl_seconds_after_finished,
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        restart_policy="Never",
                        containers=[
                            client.V1Container(
                                name=self.name,
                                image=self.runner_image,
                                command=["/bin/sh", "-c"],
                                args=[ # TODO Is it safe to use single quotation marks inside the json?
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
                                ],
                            ),
                            client.V1Container(
                                name=self.controller_name,
                                image=self.controller_image,
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
                                ]
                            ),
                        ],
                        image_pull_secrets=[  # TODO Remove as soon as both dockerhub repos are public or make configurable
                            client.V1LocalObjectReference(name="docker"),
                        ],
                        volumes=[
                            client.V1Volume(
                                empty_dir=client.V1EmptyDirVolumeSource(),
                                name="exit-signals",
                            )
                        ],
                    ),
                ),
                backoff_limit=0,
                active_deadline_seconds=runner_config.job_timeout,
            ),
        )

    def _handle_api_exception(self, exception: ApiException) -> None:
        if exception.status == 404:
            print(f"The job might not exist anymore: {exception}")
        else:
            print(f"An unexpected error occurred: {exception}")

    def _create_k8s_job(self, job: client.V1Job) -> None:
        try:
            self.batch_api.create_namespaced_job(
                body=job,
                namespace=self.namespace,
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
                namespace=self.namespace,
            )
            if not job.status:
                raise Exception(
                    "The Kubernetes job has no status."
                )  # TODO Wrap into general runner exception
            return job.status
        except ApiException as exception:
            self._handle_api_exception(exception)
            raise exception  # TODO Wrap into general runner exception

    def is_running(self) -> bool:
        """
        Check if the Kubernetes job is currently running.
        """
        try:
            job_status = self._get_k8s_job_status()
            return (
                job_status.active is not None
                and job_status.active > 0
                and (job_status.failed is None or job_status.failed == 0)
            )
        except:
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
        except:
            return False

    def has_failed(self) -> bool:
        """
        Check if the Kubernetes job has failed.
        """
        try:
            job_status = self._get_k8s_job_status()
            return job_status.failed is not None and job_status.failed > 0
        except:
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
                namespace=self.namespace,
            )
        except ApiException as e:
            self._handle_api_exception(e)
