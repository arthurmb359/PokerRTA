import os
import sys

from Game import Game
from ui import PokerSolverUI


def main():
    while True:
        app = PokerSolverUI()
        started, platform, game_format, debug_mode = app.run()

        if not started:
            print("[Main] closed without starting game.")
            return

        game = Game(platform=platform, game_format=game_format, debug_mode=debug_mode)
        action = game.start()

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
