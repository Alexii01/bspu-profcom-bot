from enum import IntFlag
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent.parent
DATA_PREFIX = MODULE_DIR.parent / "data"

ConfigPath = DATA_PREFIX / "token.ini"
TextPath = DATA_PREFIX / "text.json"
KeyboardsPath = DATA_PREFIX / "keyboards.json"
DatabasePath = DATA_PREFIX / "runtime" / "data.db"
PersistencePath = DATA_PREFIX / "runtime" / "persistence.bin"
LogPath = DATA_PREFIX / "logs" / "log.txt"
Tmp = DATA_PREFIX / "runtime" / "tmp.txt"

AdminTable = "admins"
QuestionsTable = "questions"
DepartmentsTable = "departments"


class AdminFlags(IntFlag):
    IS_SUPER = 1
    IS_MAINTAINER = 2
    NAME_UPDATES = 4
    LOG_ERRORS = 8
