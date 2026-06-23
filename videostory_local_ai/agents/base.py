from dataclasses import dataclass
from typing import Any, Callable, Optional

ProgressCallback = Optional[Callable[[str, int], None]]


@dataclass
class AgentResult:
    ok: bool
    data: Any = None
    error: str = ''


class BaseAgent:
    """Classe mère minimaliste pour standardiser les agents locaux."""

    name = 'BaseAgent'

    def __init__(self, progress_callback: ProgressCallback = None) -> None:
        self.progress_callback = progress_callback

    def progress(self, message: str, value: int) -> None:
        if self.progress_callback:
            self.progress_callback(message, value)
