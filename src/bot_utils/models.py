from dataclasses import dataclass
from uuid import uuid4, UUID
from datetime import datetime
from typing import Final
import secrets
import string

from telegram import User
import bcrypt

from bot_utils import types


@dataclass
class Question:
    uuid: UUID
    asked_by: User
    asked_date: datetime
    department_id: int
    answered_by: User | None
    answered_date: datetime | None
    message: str


@dataclass
class Admin:
    uuid: UUID
    public_name: str
    telegram_user: User | None
    password_hash: str
    is_super: Final[bool]


class AdminFactory:
    def generate_alphanumeric_password(parts: int, part_length: int) -> str:
        alphabet = string.ascii_letters + string.digits
        output = ""
        for i in range(parts):
            output += "".join([secrets.choice(alphabet) for _ in range(part_length)])
            if i != parts - 1:
                output += "-"

        return output

    def generate_admin_password() -> str:
        return AdminFactory.generate_alphanumeric_password(
            types.PasswordFormat.PARTS, types.PasswordFormat.PART_LENGTH
        )

    def __new_admin(name: str, password: str, is_super: bool) -> Admin:
        return Admin(
            uuid=uuid4(),
            public_name=name,
            telegram_user=None,
            password_hash=bcrypt.hashpw(
                password.encode("ascii"), bcrypt.gensalt(rounds=15)
            ),
            is_super=is_super,
        )

    def new_super_admin(name: str, password: str) -> Admin:
        return AdminFactory.__new_admin(name, password, True)

    def new_admin(
        name: str,
        password: str,
    ) -> Admin:
        return AdminFactory.__new_admin(name, password, False)
