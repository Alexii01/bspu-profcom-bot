import dataclasses
from collections.abc import Iterable
from typing import Any, Self
from uuid import UUID, uuid4

import aiosqlite

from bspu_profcom_bot_hayeu import constants
from bspu_profcom_bot_hayeu.db.connect import database as db
from bspu_profcom_bot_hayeu.db.db_model_base import DbModel


@dataclasses.dataclass(frozen=True)
class AnswerTemplate(DbModel):
    id: UUID
    name: str
    text: str
    in_db: bool

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # select template by id

    # insert template (automatically)
    # edit template name
    # edit template text
    # delete template
    # apply parameters to template

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def to_row(template: "AnswerTemplate") -> dict[str, Any]:
        return {"id": str(template.id), "name": template.name, "text": template.text}

    @staticmethod
    def _from_row(row: aiosqlite.Row) -> "AnswerTemplate":
        return AnswerTemplate(id=UUID(row["id"]), name=row["name"], text=row["text"], in_db=True)

    @staticmethod
    def from_row(row: aiosqlite.Row | None) -> "AnswerTemplate | None":
        return AnswerTemplate._from_row(row) if row else None

    @staticmethod
    def from_rows(rows: Iterable[aiosqlite.Row]) -> Iterable["AnswerTemplate"]:
        return [AnswerTemplate._from_row(row) for row in rows]

    @staticmethod
    async def new(name: str, text: str) -> "AnswerTemplate":
        instance = AnswerTemplate(
            id=uuid4(),
            name=name,
            text=text,
            in_db=False,
        )

        async with aiosqlite.connect(db) as conn:
            await conn.execute(
                f"INSERT INTO {constants.AnswerTemplatesTable} VALUES (:id, :name, :text)",
                instance.to_row(),
            )
            await conn.commit()
        instance = dataclasses.replace(instance, in_db=True)

        return instance

    @staticmethod
    async def pull(id: UUID) -> "AnswerTemplate | None":
        """Reads a department from db"""
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                f"SELECT * FROM {constants.AnswerTemplatesTable} WHERE id=:id LIMIT 1",
                {"id": str(id)},
            )
            return AnswerTemplate.from_row(await cursor.fetchone())

    @staticmethod
    async def pull_all() -> Iterable["AnswerTemplate"]:
        async with aiosqlite.connect(db) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(f"SELECT * FROM {constants.AnswerTemplatesTable}")
            return AnswerTemplate.from_rows(await cursor.fetchall())

    async def rename(self: Self, new_name: str) -> "AnswerTemplate":
        new_self = dataclasses.replace(self, name=new_name)

        if self.in_db:
            async with aiosqlite.connect(db) as conn:
                await conn.execute(
                    f"""UPDATE {constants.AnswerTemplatesTable}
                        SET name = :new_name
                        WHERE id=:id
                        """,
                    {"id": str(self.id), "new_name": new_name},
                )
                await conn.commit()

        return new_self

    async def edit_text(self: Self, new_text: str) -> "AnswerTemplate":
        new_self = dataclasses.replace(self, text=new_text)

        if self.in_db:
            async with aiosqlite.connect(db) as conn:
                await conn.execute(
                    f"""UPDATE {constants.AnswerTemplatesTable}
                                    SET text = :new_text
                                    WHERE id=:id
                                    """,
                    {"id": str(self.id), "new_text": new_text},
                )
                await conn.commit()

        return new_self

    async def delete(self: Self) -> "AnswerTemplate":
        if not self.in_db:
            return self

        async with aiosqlite.connect(db) as conn:
            await conn.execute(
                f"DELETE FROM {constants.AnswerTemplatesTable} WHERE id=:id",
                {"id": str(self.id)},
            )
            await conn.commit()
        new_self = dataclasses.replace(self, in_db=False)

        return new_self

    def __call__(self, *args, **kwargs):
        return self.text.format(*args, **kwargs)
