from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from aiosqlite import Row


class DbModel(ABC):
    @abstractmethod
    def to_row(template) -> dict[str, Any]: ...

    @staticmethod
    @abstractmethod
    def _from_row(row: Row) -> Any: ...

    @staticmethod
    @abstractmethod
    def from_row(row: Row | None) -> Any | None: ...

    @staticmethod
    @abstractmethod
    def from_rows(rows: Iterable[Row]) -> Iterable[Any]: ...

    @staticmethod
    @abstractmethod
    async def new(*args, **kwargs): ...

    @staticmethod
    @abstractmethod
    async def pull(id) -> Any | None: ...

    @abstractmethod
    async def delete(self): ...
