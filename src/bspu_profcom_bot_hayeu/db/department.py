from typing import Iterable, Self, Dict, Any
import dataclasses
import hashlib


import aiosqlite

from bspu_profcom_bot_hayeu.db.connect import conn_params
from bspu_profcom_bot_hayeu import constants


@dataclasses.dataclass(frozen=True)
class Department:
    id: str
    name: str
    plan_removal: bool
    in_db: bool

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # select department by id
    # select EXISTS questions with department

    # insert department (automatically)
    # update plan_removal
    # delete department

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def to_row(self: Department) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "plan_removal": self.plan_removal}

    @staticmethod
    def _from_row(row: aiosqlite.Row) -> Department:
        return Department(
            id=row["id"], name=row["name"], plan_removal=bool(row["plan_removal"]), in_db=True
        )

    @staticmethod
    def from_row(row: aiosqlite.Row | None) -> Department | None:
        return Department._from_row(row) if row else None

    @staticmethod
    async def from_rows(rows: Iterable[aiosqlite.Row]) -> Iterable[Department]:
        return [Department._from_row(row) for row in rows]

    @staticmethod
    async def new(name: str) -> Department:
        instance = Department(
            id=hashlib.sha1(("".join(name.casefold().split())).encode("utf-8")).hexdigest(),
            name=name,
            plan_removal=False,
            in_db=False,
        )

        async with aiosqlite.connect(*conn_params) as conn:
            await conn.execute(
                (
                    f"INSERT INTO {constants.AdminTable} VALUES (:id, :public_name, :user_id, :password_hash, :flags)"
                ),
                instance,
            )

        return instance

    @staticmethod
    async def pull(id: str) -> Department | None:
        """Reads a question from db"""
        async with aiosqlite.connect(*conn_params) as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {constants.DepartmentsTable} WHERE id=:id LIMIT 1", {"id": id}
            )
            return Department.from_row(await cursor.fetchone())

    async def is_used(self: Self) -> bool:
        async with aiosqlite.connect(*conn_params) as conn:
            cursor = await conn.execute(
                """SELECT EXISTS("""
                """     SELECT 1"""
                f"""    FROM {constants.QuestionsTable}"""
                """     WHERE department_id=:id"""
                """)""",
                {"id": self.id},
            )
            return bool(await cursor.fetchone())

    async def set_plan_removal(self: Self, b: bool) -> Department:
        if self.plan_removal == b:
            return self

        if self.in_db:
            async with aiosqlite.connect(*conn_params) as conn:
                await conn.execute(
                    f""" UPDATE {constants.DepartmentsTable}"""
                    """ SET plan_removal = :b"""
                    """ WHERE id=:id""",
                    {"id": self.id, "b": self.plan_removal},
                )
        dataclasses.replace(self, plan_removal=b)

        return self

    async def delete(self: Self) -> Department:
        if not self.in_db:
            return self

        async with aiosqlite.connect(*conn_params) as conn:
            await conn.execute(
                f"DELETE FROM {constants.DepartmentsTable} WHERE id=:id",
                {"id": self.id},
            )
        dataclasses.replace(self, in_db=False)

        return self
