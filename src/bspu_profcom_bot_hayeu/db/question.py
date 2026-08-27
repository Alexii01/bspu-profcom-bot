import dataclasses
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Self
from uuid import UUID, uuid4

import aiosqlite

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.db.connect import database as db
from bspu_profcom_bot_hayeu.db.db_model_base import DbModel


def _optional(value, fn):
    return fn(value) if value is not None else None


@dataclasses.dataclass(frozen=True)
class Question(DbModel):
    id: UUID
    user_id: int
    department_id: UUID
    asked_date: datetime
    message: str
    answered_by: int | None
    answered_date: datetime | None
    in_db: bool = False

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # select questions by user
    # select question by id

    # select oldest question
    # select oldest question but not ids
    # select oldest question from department
    # select oldest questoin from department but not ids

    # insert question (automatic)
    # update question department by id
    # delete question by id

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def _from_row(row: aiosqlite.Row) -> Question:
        return Question(
            id=UUID(row["id"]),
            user_id=row["user_id"],
            department_id=UUID(row["department_id"]),
            asked_date=datetime.fromisoformat(row["asked_date"]),
            message=row["message"],
            answered_by=row["answered_by"],
            answered_date=_optional(row["answered_date"], datetime.fromisoformat)
            if row["answered_date"]
            else None,
            in_db=True,
        )

    @staticmethod
    def from_row(row: aiosqlite.Row | None) -> Question | None:
        return Question._from_row(row) if row else None

    @staticmethod
    def from_rows(rows: Iterable[aiosqlite.Row]) -> list[Question]:
        return [Question._from_row(row) for row in rows]

    def to_row(self: Self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "department_id": str(self.department_id),
            "asked_date": self.asked_date.isoformat(),
            "message": self.message,
            "answered_by": self.answered_by,
            "answered_date": _optional(self.answered_date, datetime.isoformat),
        }

    @staticmethod
    async def new(
        user_id: int,
        department_id: UUID,
        asked_date: datetime,
        message: str,
        answered_by: int | None,
        answered_date: datetime | None,
    ) -> Question:
        """Creates a question and inserts it into db"""
        instance = Question(
            id=uuid4(),
            user_id=user_id,
            department_id=department_id,
            asked_date=asked_date,
            message=message,
            answered_by=answered_by,
            answered_date=answered_date,
        )
        await instance.insert()
        return instance

    @staticmethod
    async def pull(id: UUID) -> Question | None:
        """Reads a question from db"""
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                f"SELECT * FROM {constants.QuestionsTable} WHERE id=:id LIMIT 1",
                {"id": str(id)},
            )
            return Question.from_row(await cursor.fetchone())

    @staticmethod
    async def pull_from_user(user_id: int) -> list[Question]:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                f"SELECT * FROM {constants.QuestionsTable} WHERE user_id=:user_id",
                {"user_id": user_id},
            )
            return Question.from_rows(await cursor.fetchall())

    @staticmethod
    async def _pull_oldest() -> Question | None:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                f"""
                    SELECT *
                    FROM {constants.QuestionsTable}
                    ORDER BY asked_date
                    ASC LIMIT 1
                """,
            )
            return Question.from_row(await cursor.fetchone())

    @staticmethod
    async def _pull_oldest_from_dept(dept: UUID) -> Question | None:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                f"""
                    SELECT *
                    FROM {constants.QuestionsTable}
                    WHERE department=:dept
                    ORDER BY asked_date
                    ASC LIMIT 1
                """,
                {"dept": str(dept)},
            )
            return Question.from_row(await cursor.fetchone())

    @staticmethod
    async def _pull_oldest_except(ids: list[UUID]) -> Question | None:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                        SELECT *
                        FROM {}
                        WHERE NOT IN ({})
                        ORDER BY asked_date
                        ASC LIMIT 1
                """.format(constants.QuestionsTable, ", ".join("?" for _ in ids)),
                [str(id) for id in ids],
            )
            return Question.from_row(await cursor.fetchone())

    @staticmethod
    async def _pull_oldest_from_dept_except(dept: UUID, ids: list[UUID]) -> Question | None:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                        SELECT *
                        FROM {}
                        WHERE department=?  AND id NOT IN ({})
                        ORDER BY asked_date
                        ASC LIMIT 1
                """.format(constants.QuestionsTable, ", ".join("?" for _ in ids)),
                [str(dept)] + [str(id) for id in ids],
            )
            return Question.from_row(await cursor.fetchone())

    @staticmethod
    async def pull_oldest(
        dept: UUID | None = None, avoid_ids: list[UUID] | None = None
    ) -> Question | None:
        """Pulls oldest question"""
        if dept and avoid_ids:
            return await Question._pull_oldest_from_dept_except(dept, avoid_ids)
        elif not dept and avoid_ids:
            return await Question._pull_oldest_except(avoid_ids)
        elif dept and not avoid_ids:
            return await Question._pull_oldest_from_dept(dept)
        else:
            return await Question._pull_oldest()

    @staticmethod
    async def delete_by_id(id: UUID):
        async with aiosqlite.connect(db) as conn:
            await conn.execute(
                (f"DELETE FROM {constants.QuestionsTable} WHERE id=:id"), {"id": str(id)}
            )
            await conn.commit()

    async def insert(question: Self) -> Question:
        """Insert question into database"""
        if not question.in_db:
            async with aiosqlite.connect(db) as conn:
                await conn.execute(
                    f"""
                        INSERT INTO {constants.QuestionsTable} VALUES
                        (:id, :user_id, :department_id, :asked_date,
                        :answered_by, :answered_date, :message)
                    """,
                    Question.to_row(question),
                )
                await conn.commit()
            new_self = dataclasses.replace(question, in_db=True)
        return new_self

    async def redirect(self: Self, dept: UUID) -> Question:
        if self.in_db:
            async with aiosqlite.connect(db) as conn:
                await conn.execute(
                    f"UPDATE {constants.QuestionsTable} SET department=:dept WHERE id=:id",
                    {
                        "dept": str(dept),
                        "id": str(self.id),
                    },
                )
                await conn.commit()
        new_self = dataclasses.replace(self, department_id=dept)
        return new_self

    async def delete(self: Self) -> Question:
        if self.in_db:
            await Question.delete_by_id(self.id)
            new_self = dataclasses.replace(self, in_db=False)
        return new_self
