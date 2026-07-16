from pathlib import Path
from enum import IntFlag

MODULE_DIR = Path(__file__).resolve().parent
DATA_PREFIX = MODULE_DIR.parent / "data"

ConfigPath = DATA_PREFIX / "token.ini"
TextPath = DATA_PREFIX / "text.json"
KeyboardsPath = DATA_PREFIX / "keyboards.json"
DatabasePath = DATA_PREFIX / "data.db"
PersistencePath = DATA_PREFIX / "persistence.bin"
LogPath = DATA_PREFIX / "logs" / "log.txt"
Tmp = DATA_PREFIX / "tmp"

AdminTable = "admins"
QuestionsTable = "questions"
DepartmentsTable = "departments"


class AdminFlags(IntFlag):
    IS_SUPER = 1
    IS_MAINTAINER = 2
    NAME_UPDATES = 4
    LOG_ERRORS = 8
