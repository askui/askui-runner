import time
from datetime import datetime, timezone

from ...queue import Clock


class TimeClock(Clock):
    def now(self) -> int:
        return int(datetime.now(tz=timezone.utc).timestamp())

    def sleep(self, seconds: int) -> None:
        time.sleep(seconds)
