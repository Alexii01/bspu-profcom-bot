from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import Self, Tuple, List

from bot_utils import types


@dataclass
class Question:
    id: UUID | str
    user_id: int | None
    department_id: str
    asked_date: str | datetime
    answered_by: int | None
    answered_date: str | datetime | None
    message: str

    @classmethod
    async def pull(cls, id: str) -> Self:
        pass

    async def pull_latest(self, id: str, ignore_ids: List[str]) -> Self:
        pass

    async def push(self):
        pass

    async def delete(self):
        pass


@dataclass
class Admin:
    id: UUID | str
    public_name: str
    user_id: int | None
    password_hash: str
    flags: types.AdminFlags

    @classmethod
    async def create(cls, flags: types.AdminFlags = None) -> Tuple[Self, str]:
        """Generates a password and initialises the fields with default values,
        then INSERTs into db.
        """
        pass

    @classmethod
    async def login_with_user_id(cls, id: str) -> Self | None:
        """Returns an admin associated with a user"""
        pass

    @classmethod
    async def first_login(cls, id: str, password: str) -> Self | None:
        pass

    async def pull(self):
        """Select admin from db by id"""
        pass

    async def push(self):
        """Expensive update admin from db by id"""
        pass

    async def verify(self) -> bool:
        """Check that admin exists"""
        pass

    async def rename(self):
        """Update admin's name in db"""
        pass

    async def delete(self):
        """Delete admin from db"""
        pass
