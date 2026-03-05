from dataclasses import dataclass
from uuid import uuid4, UUID
from datetime import datetime
import secrets
import string

import bcrypt

from src.bot_utils import __types


@dataclass
class Question:
    id: UUID
    user_id: int | None
    department_id: str
    asked_date: str | datetime
    answered_by: int | None
    answered_date: str | datetime | None
    message: str


@dataclass
class Admin:
    id: UUID | str
    public_name: str
    user_id: int | None
    password_hash: str
    flags: __types.AdminFlags


class AdminFactory:
    @staticmethod
    def generate_sequence(alphabet: str, length: int) -> str:
        return "".join([secrets.choice(alphabet) for _ in range(length)])

    # TODO: Merge with generate_admin_password
    @staticmethod
    def generate_alphanumeric_password(parts: int, part_length: int) -> str:
        alphabet = string.ascii_letters + string.digits
        output = ""
        for i in range(parts):
            output += AdminFactory.generate_sequence(alphabet, part_length)
            if i != parts - 1:
                output += "-"

        return output

    @staticmethod
    def generate_admin_password() -> str:
        return AdminFactory.generate_alphanumeric_password(
            __types.PasswordFormat.PARTS, __types.PasswordFormat.PART_LENGTH
        )

    @staticmethod
    async def new_admin(
        name: str, password: str, flags: __types.AdminFlags | None = None
    ) -> Admin:
        return Admin(
            id=uuid4(),
            public_name=name,
            user_id=None,
            password_hash=bcrypt.hashpw(
                password.encode("ascii"), bcrypt.gensalt(rounds=15)
            ),
            flags=flags if flags else 0,
        )

    @staticmethod
    async def new_blank_admin(
        name_template: str, password: str, flags: __types.AdminFlags | None = None
    ):
        return await AdminFactory.new_admin(
            name_template + AdminFactory.generate_sequence(string.digits, 6),
            password,
            flags,
        )


class SeqGenerator:
    @staticmethod
    def generate_sequence(alphabet: str, length: int) -> str:
        return "".join([secrets.choice(alphabet) for _ in range(length)])

    @staticmethod
    def generate_alphanumeric_password(parts: int, part_length: int) -> str:
        alphabet = string.ascii_letters + string.digits
        output = ""
        for i in range(parts):
            output += SeqGenerator.generate_sequence(alphabet, part_length)
            if i != parts - 1:
                output += "-"

        return output

    @staticmethod
    def generate_admin_password() -> str:
        return AdminFactory.generate_alphanumeric_password(
            __types.PasswordFormat.PARTS, __types.PasswordFormat.PART_LENGTH
        )
