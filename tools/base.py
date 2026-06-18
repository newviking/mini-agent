from __future__ import annotations

from abc import ABC, abstractmethod


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, args: dict, session: dict | None = None) -> dict:
        raise NotImplementedError

