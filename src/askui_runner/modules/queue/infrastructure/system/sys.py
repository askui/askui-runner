import sys

from ...domain.services import System

class SysSystem(System):
    def exit(self) -> None:
        sys.exit(0)
