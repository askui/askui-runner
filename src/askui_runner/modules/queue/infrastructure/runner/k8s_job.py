from ...domain.services import Runner, RunnerJob


# TODO
class K8sJobRunner(Runner):
    def start(self, runner_job: RunnerJob) -> None:
        raise NotImplementedError()

    def is_running(self) -> bool:
        raise NotImplementedError()

    def has_passed(self) -> bool:
        raise NotImplementedError()

    def has_failed(self) -> bool:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()
