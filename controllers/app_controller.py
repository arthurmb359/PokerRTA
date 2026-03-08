import os
import sys

from controllers.game_session_controller import GameSessionController
from controllers.session_action import SessionAction
from ui import PokerRTAUI


class AppController:
    def __init__(self):
        self.session_controller = GameSessionController()

    def run(self):
        while True:
            app = PokerRTAUI()
            started, platform, game_format, debug_mode = app.run()

            if not started:
                print("[Main] closed without starting game.")
                return

            action = self.session_controller.run_once(
                platform=platform,
                game_format=game_format,
                debug_mode=debug_mode,
            )

            if action == SessionAction.BACK_TO_MAIN:
                continue

            if action == SessionAction.EXIT_APP:
                # Hard terminate avoids Tkinter cross-thread finalizer noise on shutdown.
                try:
                    sys.stdout.flush()
                    sys.stderr.flush()
                finally:
                    os._exit(0)

            return
