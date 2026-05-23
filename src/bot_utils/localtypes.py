from enum import Enum, IntEnum, StrEnum, IntFlag, auto

GO_BACK_CODE = -1


class MainMenuState(Enum):
    MAIN_MENU = auto()
    ERROR_ENCOUNTERED = auto()


class QuestionState(Enum):
    MAIN_MENU = auto()
    DEPARTMENT_MENU = auto()
    QUESTION_VIEW_MENU = auto()
    ASKING_QUESTION = auto()
    VIEWING_QUESTION = auto()
    RETURN_TO_MAIN_MENU = auto()


class AdminState(Enum):
    LOGIN = auto()
    MAIN_MENU = auto()
    ANSWERING_QUESTIONS = auto()
    SETTINGS = auto()
    SU_SETTINGS = auto()
    MAINTAINER_SETTINGS = auto()
    CHANGING_TEXT = auto()
    ENTERING_NAME = auto()
    ENTERING_DEPARTMENT_NAME = auto()
    SELECTING_DEPARTMENT = auto()
    SELECTING_DEPARTMENT_TO_DELETE = auto()
    SELECTING_DEPARTMENT_TO_REDIRECT = auto()
    SELECTING_ADMIN_TO_DELETE = auto()
    CONFIRMING_QUESTION_DELETION = auto()


class AdminFlags(IntFlag):
    IS_SUPER = 1
    IS_MAINTAINER = 2
    NAME_UPDATES = 4
    LOG_ERRORS = 8


class KeyboardFlag(IntFlag):
    IS_REPLY = 1
    WITH_RETURN = 2


class KeyboardsAliases(StrEnum):
    MAIN_MENU = "main_menu"
    QUESTION_MENU = "questions_menu"
    ADMIN_SETTINGS = "admin_settings"
    SU_ADMIN_SETTINGS = "su_admin_settings"
    MAINTAINER_SETTINGS = "maintainer_settings"
    ADMIN_ANSWER_MENU = "admin_answer_menu"
    VIEW_QUESTION = "view_question_menu"
    GO_BACK = "go_back"


class GeneratedKeyboards:
    DEPARTMENTS = auto()
    VIEW_MESSAGE = auto()
    ADMIN_MENU = auto()


class PasswordFormat(IntEnum):
    PARTS = 3
    PART_LENGTH = 6


class DatabaseTables(StrEnum):
    QUESTIONS = "questions"
    ADMINS = "admins"


class FileNames(StrEnum):
    CONFIG = "config.ini"
    PERSISTENCE = "persistence.bin"
    DEFAULTS = "defaults.json"
    DB = "data.db"
    FIRST_SU_PASSWORD = "su.log"
    LOG = "rotating.log"
