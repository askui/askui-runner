from ..domain import services as domain_services


class Runner:
    def __init__(self, runner: domain_services.Runner):
        self.runner = runner

    def run(self) -> domain_services.RunWorkflowsResult:
        return self.runner.run()
