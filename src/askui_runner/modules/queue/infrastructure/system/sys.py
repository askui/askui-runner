import sys

from ...queue import System


class SysSystem(System):
    def exit(self) -> None:
        sys.exit(0)
