from dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime
from typing import Self, Tuple, List
import functools
import bcrypt
import string

from bspu_profcom_bot_hayeu.db import database
from bspu_profcom_bot_hayeu.models import SeqGenerator
from bspu_profcom_bot_hayeu import old_states


# TODO: Stop using a dataclass, write all the necessary functions by hand
@dataclass
class Question:
    id: UUID | str
    user_id: int | None
    department_id: str
    asked_date: str | datetime
    answered_by: int | None = None
    answered_date: str | datetime | None = None
    message: str
    is_in_db = False
    is_deleted = False

    @staticmethod
    def __exists_and_valid(func):
        @functools.wraps(func)
        def wrapper(self: Self, *args, **kwargs):
            if self.is_deleted or not self.is_in_db:
                return

            return func(self, args, kwargs)

        return wrapper

    @classmethod
    async def create(cls, *args, **kwargs) -> Self:
        """Creates a question and inserts it into db"""
        instance = cls.__init__(args, kwargs, is_in_db=True)
        await database.insert_question(instance)
        return instance

    @staticmethod
    async def pull(id: str) -> Self:
        """Reads a question from db"""
        return await database.select_question_by_id(id)

    @staticmethod
    async def pull_oldest(dept: str, avoid_ids: List[str] | None = None) -> Self:
        """Pulls oldest question from database"""
        if avoid_ids is None:
            return await database.select_oldest_question_from_department(dept)
        else:
            return await database.select_oldest_question_from_department_but_not_ids(
                dept, avoid_ids
            )

    @staticmethod
    async def pull_from_user(user_id: int) -> List[Self]:
        return await database.select_questions_from_user(user_id)

    @staticmethod
    async def delete_by_id(id: int):
        await database.delete_question_by_id(id)

    async def push(question: Self):
        """Insert question into database"""
        if question.is_deleted or question.is_in_db:
            return
        await database.insert_question(question)
        question.is_in_db = True

    @__exists_and_valid
    async def redirect(self, dept: str):
        await database.update_question_department_with_id(dept, self.id)

    @__exists_and_valid
    async def delete(self):
        await database.delete_question_by_id(self.id)
        self.is_deleted = True


@dataclass
class Admin:
    id: UUID | str
    public_name: str
    user_id: int | None
    password_hash: str
    flags: old_states.AdminFlags
    __is_deleted: bool = False

    @staticmethod
    def __exists_and_valid(func):
        @functools.wraps(func)
        def wrapper(self: Self, *args, **kwargs):
            if self.__is_deleted:
                return

            return func(self, args, kwargs)

        return wrapper

    @classmethod
    async def create(
        cls,
        *,
        public_name: str | None = None,
        name_base: str = "",
        flags: old_states.AdminFlags = None,
    ) -> Tuple[Self, str]:
        """Generates a password and initialises the fields with default values,
        then INSERTs into db.
        """
        passw = SeqGenerator.generate_admin_password()

        instance = Admin(
            id=uuid4(),
            public_name=public_name
            if public_name
            else name_base + SeqGenerator.generate_sequence(string.digits, 6),
            user_id=None,
            flags=flags,
            password_hash=bcrypt.hashpw(passw.encode("ascii"), bcrypt.gensalt()),
        )

        await database.insert_admin(instance)

        return (instance, passw)

    @classmethod
    async def pull(cls, id: str) -> Self | None:
        """Returns an admin associated with a user"""
        return await database.select_admin_with_id(id)

    @classmethod
    async def authorise_new_admin(user_id: int, password: bytes):
        return await database.authorise_new_admin(user_id, password)

    async def set_user_id(self, user_id: int):
        if self.user_id:
            return
        self.user_id = user_id
        database.update_admin_user_id(self.user_id, self.id)

    async def verify(self) -> bool:
        """Check that admin exists"""
        return await database.admin_exists(self.id)

    @__exists_and_valid
    async def rename(self, name: str):
        """Update admin's name in db"""
        await database.update_admin_name(name, self.id)

    @__exists_and_valid
    async def delete(self):
        """Delete admin from db"""
        await database.delete_admin_with_id(self.id)
        self.__is_deleted = True


# TODO: Fill in ORM
@dataclass
class Department:
    pass
