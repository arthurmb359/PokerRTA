from controllers.game_session import GameSession
from ui.debug_ui import DebugWindow
from ui.overlay import CalibrationOverlay


class GameSessionController:
    def run_once(self, platform: str, game_format: str, debug_mode: bool) -> str:
        game = GameSession(platform=platform, game_format=game_format, debug_mode=debug_mode)

        overlay = CalibrationOverlay(
            game.platform,
            game.game_format,
            game.table.get_left_edge(),
            game.table.get_top_edge(),
            on_update=game._on_overlay_update,
        )
        overlay.start()

        debug_window = None
        if debug_mode:
            debug_window = DebugWindow(
                on_pause_changed=game._set_paused,
                on_tick_rate_changed=game._set_tick_rate,
                on_back_to_main=game._request_back_to_main,
                on_exit_app=game._request_exit_app,
                initial_tick_rate=game.tick_rate_sec,
            )
            debug_window.start()

        game.attach_ui(overlay=overlay, debug_window=debug_window)
        return game.start()
