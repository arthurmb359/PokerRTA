from enum import Enum


class SessionAction(str, Enum):
    BACK_TO_MAIN = "back_to_main"
    EXIT_APP = "exit_app"
