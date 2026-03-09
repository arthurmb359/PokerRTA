import os
import sys
import threading

from controllers.game_session_controller import GameSessionController
from ui import PokerRTAUI


class AppController:
    def __init__(self):
        self._nav_event = threading.Event()
        self._next_action = None
        self.session_controller = GameSessionController(
            on_back_to_main=self._request_back_to_main,
            on_exit_app=self._request_exit_app,
        )

    def _request_back_to_main(self):
        self._next_action = "back_to_main"
        self._nav_event.set()

    def _request_exit_app(self):
        self._next_action = "exit_app"
        self._nav_event.set()

    def run(self):
        while True:
            app = PokerRTAUI()
            started, platform, game_format, debug_mode = app.run()

            if not started:
                print("[Main] closed without starting game.")
                self.session_controller.shutdown()
                return

            self._next_action = None
            self._nav_event.clear()

            if debug_mode:
                self.session_controller.enter_debug_mode(platform=platform, game_format=game_format)
            else:
                self.session_controller.enter_run_mode(platform=platform, game_format=game_format)

            self._nav_event.wait()

            if self._next_action == "back_to_main":
                continue

            if self._next_action == "exit_app":
                # Hard terminate avoids Tkinter cross-thread finalizer noise on shutdown.
                try:
                    sys.stdout.flush()
                    sys.stderr.flush()
                finally:
                    os._exit(0)

            return
