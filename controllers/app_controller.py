import os
import sys

from controllers.game_session_controller import GameSessionController
from services.recognition.ocr_service import OCRService
from ui import PokerToolUI


class AppController:
    def __init__(self):
        self._shutting_down = False
        self.ui = PokerToolUI(
            on_start_run=self._on_start_run,
            on_start_debug=self._on_start_debug,
            on_exit=self._on_menu_exit,
        )
        self.session_controller = GameSessionController(
            ui_root=self.ui.root,
            on_back_to_main=self._request_back_to_main,
            on_exit_app=self._request_exit_app,
        )
        self.ui.call_soon(OCRService.warmup_async, "en")

    def _on_start_run(self, platform: str, game_format: str):
        self.ui.hide()
        self.session_controller.enter_run_mode(platform=platform, game_format=game_format)

    def _on_start_debug(self, platform: str, game_format: str):
        self.ui.hide()
        self.session_controller.enter_debug_mode(platform=platform, game_format=game_format)

    def _on_menu_exit(self):
        print("[Main] closed without starting game.")
        self._request_exit_app()

    def _request_back_to_main(self):
        print("[UI] scheduling main menu show")
        self.ui.call_soon(self._show_main_menu)

    def _show_main_menu(self):
        if self._shutting_down:
            return
        print("[UI] showing main menu")
        self.ui.show()

    def _request_exit_app(self):
        self.ui.call_soon(self._shutdown_and_exit)

    def _shutdown_and_exit(self):
        if self._shutting_down:
            return

        self._shutting_down = True
        self.session_controller.shutdown()
        self.ui.close()

        # Hard terminate avoids Tkinter cross-thread finalizer noise on shutdown.
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            os._exit(0)

    def run(self):
        self.ui.run()
