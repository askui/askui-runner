from ..domain import services as domain_services


class RunnerJobsQueuePolling:
    def __init__(
        self,
        runner_jobs_queue_polling_service: domain_services.RunnerJobsQueuePolling,
    ):
        self.runner_jobs_queue_polling_service = runner_jobs_queue_polling_service

    def poll(self) -> None:
        self.runner_jobs_queue_polling_service.poll()
