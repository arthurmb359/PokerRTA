import os
import sys

from controllers.game_session_controller import GameSessionController
from ui import PokerRTAUI


def main():
    controller = GameSessionController()
    while True:
        app = PokerRTAUI()
        started, platform, game_format, debug_mode = app.run()

        if not started:
            print("[Main] closed without starting game.")
            return

        action = controller.run_once(
            platform=platform,
            game_format=game_format,
            debug_mode=debug_mode,
        )

        if action == "back_to_main":
            continue

        if action == "exit_app":
            # Hard terminate avoids Tkinter cross-thread finalizer noise on shutdown.
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            finally:
                os._exit(0)

        return


if __name__ == "__main__":
    main()
