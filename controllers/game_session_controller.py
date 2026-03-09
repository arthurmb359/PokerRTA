import threading

from controllers.game_session_builder import GameSessionBuilder
from ui.debug_ui import DebugWindow
from ui.overlay import CalibrationOverlay


class GameSessionController:
    def __init__(self, on_back_to_main, on_exit_app):
        self.builder = GameSessionBuilder()
        self.on_back_to_main = on_back_to_main
        self.on_exit_app = on_exit_app

        self.game = None
        self.runtime_thread = None
        self.overlay = None
        self.debug_window = None

    def _build_runtime(self, platform: str, game_format: str):
        self.game = self.builder.build(platform=platform, game_format=game_format, debug_mode=False)
        self.game.pause()
        self.runtime_thread = threading.Thread(target=self.game.start, daemon=True)
        self.runtime_thread.start()

    def _ensure_runtime(self, platform: str, game_format: str):
        if self.game is None:
            self._build_runtime(platform, game_format)
            return

        if self.game.platform != platform or self.game.game_format != game_format:
            self._stop_ui()
            self.game.stop()
            if self.runtime_thread is not None and self.runtime_thread.is_alive():
                self.runtime_thread.join(timeout=2.0)
            self._build_runtime(platform, game_format)

    def _ensure_overlay(self):
        if self.overlay is not None:
            return
        self.overlay = CalibrationOverlay(
            self.game.platform,
            self.game.game_format,
            self.game.table.get_left_edge(),
            self.game.table.get_top_edge(),
            on_update=self.game._on_overlay_update,
        )
        self.overlay.start()
        self.game.attach_ui(overlay=self.overlay, debug_window=self.debug_window)

    def _ensure_debug_window(self):
        if self.debug_window is not None:
            return
        self.debug_window = DebugWindow(
            on_pause_changed=self.game._set_paused,
            on_tick_rate_changed=self.game._set_tick_rate,
            on_back_to_main=self._handle_back_to_main,
            on_exit_app=self._handle_exit_app,
            initial_tick_rate=self.game.tick_rate_sec,
        )
        self.debug_window.start()
        self.game.attach_ui(overlay=self.overlay, debug_window=self.debug_window)

    def _stop_debug_window(self):
        if self.debug_window is None:
            return
        window = self.debug_window
        self.debug_window = None
        self.game.attach_ui(overlay=self.overlay, debug_window=None)
        window.stop()

    def _stop_overlay(self):
        if self.overlay is None:
            return
        overlay = self.overlay
        self.overlay = None
        self.game.attach_ui(overlay=None, debug_window=self.debug_window)
        overlay.stop()

    def _stop_ui(self):
        self._stop_debug_window()
        self._stop_overlay()

    def enter_run_mode(self, platform: str, game_format: str):
        self._ensure_runtime(platform, game_format)
        self._stop_debug_window()
        self._ensure_overlay()
        self.game.resume()

    def enter_debug_mode(self, platform: str, game_format: str):
        self._ensure_runtime(platform, game_format)
        self._ensure_overlay()
        self._ensure_debug_window()
        self.game.resume()

    def return_to_main_menu(self):
        if self.game is None:
            self.on_back_to_main()
            return
        self.game.pause()
        self._stop_ui()
        self.on_back_to_main()

    def shutdown(self):
        self._stop_ui()
        if self.game is not None:
            self.game.stop()
        if self.runtime_thread is not None and self.runtime_thread.is_alive():
            self.runtime_thread.join(timeout=2.0)
        self.game = None
        self.runtime_thread = None

    def _handle_back_to_main(self):
        self.return_to_main_menu()

    def _handle_exit_app(self):
        self.shutdown()
        self.on_exit_app()
