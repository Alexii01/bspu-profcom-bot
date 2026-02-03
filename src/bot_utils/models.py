from dataclasses import dataclass
from uuid import uuid4, UUID
from datetime import datetime
import secrets
import string

import bcrypt

from bot_utils import types


@dataclass
class Question:
    id: UUID
    user_id: int | None
    chat_id: int | None
    department_id: int
    asked_date: str | datetime
    answered_by: int | None
    answered_date: str | datetime | None
    message: str


@dataclass
class Admin:
    id: UUID | str
    public_name: str
    user_id: int | None
    chat_id: int | None
    password_hash: str
    flags: types.AdminFlags


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

    def new_admin(name: str, password: str, flags: types.AdminFlags | None) -> Admin:
        return Admin(
            id=uuid4(),
            public_name=name,
            user_id=None,
            chat_id=None,
            password_hash=bcrypt.hashpw(
                password.encode("ascii"), bcrypt.gensalt(rounds=15)
            ),
            flags=flags if flags else 0,
        )
