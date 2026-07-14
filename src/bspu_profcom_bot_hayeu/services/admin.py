from bspu_profcom_bot_hayeu.db.models import Admin
from bspu_profcom_bot_hayeu.db import database


async def login(user_id: int) -> Admin | None:
    return await Admin.pull(user_id)


async def first_login(user_id: int, passwd: str) -> Admin | None:
    admin = await database.authorise_new_admin(user_id, passwd.encode("ascii"))
    if admin:
        await admin.set_user_id(user_id)

    return admin
