import threading

from configs.config_manager import get_regions_category
from configs.config_manager import set_active_selection
from services.runtime.game_session_builder import GameSessionBuilder
from ui.debug_ui import DebugWindow
from ui.overlay import CalibrationOverlay
from ui.view_models.overlay import OverlayCategorySnapshot, OverlayViewSnapshot


class GameSessionController:
    def __init__(self, ui_root, on_back_to_main, on_exit_app):
        self.builder = GameSessionBuilder()
        self.ui_root = ui_root
        self.on_back_to_main = on_back_to_main
        self.on_exit_app = on_exit_app

        self.game = None
        self.runtime_thread = None
        self.overlay = None
        self.debug_window = None

    def _build_overlay_view_snapshot(self) -> OverlayViewSnapshot:
        categories = (
            OverlayCategorySnapshot(
                category="bet",
                label_prefix="BET",
                regions=tuple(tuple(region) for region in get_regions_category(self.game.platform, self.game.game_format, "bet")),
            ),
            OverlayCategorySnapshot(
                category="pot",
                label_prefix="POT",
                regions=tuple(tuple(region) for region in get_regions_category(self.game.platform, self.game.game_format, "pot")),
            ),
            OverlayCategorySnapshot(
                category="board",
                label_prefix="BOARD",
                regions=tuple(tuple(region) for region in get_regions_category(self.game.platform, self.game.game_format, "board")),
            ),
            OverlayCategorySnapshot(
                category="hero_action",
                label_prefix="MY TURN",
                regions=tuple(tuple(region) for region in get_regions_category(self.game.platform, self.game.game_format, "hero_action")),
            ),
            OverlayCategorySnapshot(
                category="hero_cards",
                label_prefix="HERO",
                regions=tuple(tuple(region) for region in get_regions_category(self.game.platform, self.game.game_format, "hero_cards")),
            ),
        )
        return OverlayViewSnapshot(
            platform=self.game.platform,
            game_format=self.game.game_format,
            table_left=self.game.table.get_left_edge(),
            table_top=self.game.table.get_top_edge(),
            categories=categories,
        )

    def _build_runtime(self, platform: str, game_format: str):
        self.game = self.builder.build(platform=platform, game_format=game_format, debug_mode=False)
        self.game.pause()
        self.runtime_thread = threading.Thread(target=self.game.start, daemon=True)
        self.runtime_thread.start()

    def _rebuild_runtime(self, platform: str, game_format: str):
        if self.game is not None:
            self.game.pause()
            self.game.stop()
        if self.runtime_thread is not None and self.runtime_thread.is_alive():
            self.runtime_thread.join(timeout=2.0)
        self._build_runtime(platform, game_format)

    def _ensure_runtime(self, platform: str, game_format: str, force_rebuild: bool = False):
        if self.game is None:
            self._build_runtime(platform, game_format)
            return

        if force_rebuild or self.game.platform != platform or self.game.game_format != game_format:
            self._rebuild_runtime(platform, game_format)

    def _ensure_overlay(self):
        if self.overlay is not None:
            self.overlay.reload_view(
                self._build_overlay_view_snapshot(),
                on_update=self.game._on_overlay_update,
            )
            self.game.attach_ui(overlay=self.overlay, debug_window=self.debug_window)
            return
        print("[UI] opening calibration overlay")
        self.overlay = CalibrationOverlay(
            self.ui_root,
            self._build_overlay_view_snapshot(),
            on_update=self.game._on_overlay_update,
        )
        self.overlay.start()
        self.game.attach_ui(overlay=self.overlay, debug_window=self.debug_window)

    def _ensure_debug_window(self):
        if self.debug_window is not None:
            return
        print("[UI] opening debug window")
        self.debug_window = DebugWindow(
            self.ui_root,
            on_pause_changed=self._handle_pause_changed,
            on_tick_rate_changed=self._handle_tick_rate_changed,
            on_game_config_changed=self._handle_game_config_changed,
            on_back_to_main=self._handle_back_to_main,
            on_exit_app=self._handle_exit_app,
            initial_tick_rate=self.game.tick_rate_sec,
            initial_platform=self.game.platform,
            initial_format=self.game.game_format,
        )
        self.debug_window.start()
        self.game.attach_ui(overlay=self.overlay, debug_window=self.debug_window)

    def _stop_debug_window(self):
        if self.debug_window is None:
            return
        print("[UI] closing debug window")
        window = self.debug_window
        self.debug_window = None
        self.game.attach_ui(overlay=self.overlay, debug_window=None)
        window.stop()

    def _stop_overlay(self):
        if self.overlay is None:
            return
        print("[UI] closing calibration overlay")
        overlay = self.overlay
        self.overlay = None
        self.game.attach_ui(overlay=None, debug_window=self.debug_window)
        overlay.stop()

    def _stop_ui(self):
        self._stop_debug_window()
        self._stop_overlay()

    def enter_run_mode(self, platform: str, game_format: str):
        self._ensure_runtime(platform, game_format, force_rebuild=True)
        self._stop_debug_window()
        self._ensure_overlay()
        self.game.resume()

    def enter_debug_mode(self, platform: str, game_format: str):
        self._ensure_runtime(platform, game_format, force_rebuild=True)
        self._ensure_overlay()
        self._ensure_debug_window()
        self.game.resume()

    def return_to_main_menu(self):
        if self.game is None:
            self.on_back_to_main()
            return
        print("[UI] returning to main menu")
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

    def _handle_pause_changed(self, paused: bool):
        if self.game is not None:
            self.game._set_paused(paused)

    def _handle_tick_rate_changed(self, value: float):
        if self.game is not None:
            self.game._set_tick_rate(value)

    def _handle_game_config_changed(self, platform: str, game_format: str):
        print(f"[UI] applying debug game config platform={platform} format={game_format}")
        if self.game is not None and self.game.platform == platform and self.game.game_format == game_format:
            return
        set_active_selection(platform, game_format)
        self.enter_debug_mode(platform=platform, game_format=game_format)

    def _handle_exit_app(self):
        self.shutdown()
        self.on_exit_app()
