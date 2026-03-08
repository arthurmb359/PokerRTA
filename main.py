from Game import Game
from ui import PokerSolverUI


def main():
    app = PokerSolverUI()
    started, platform, game_format = app.run()

    if not started:
        print("[Main] encerrado sem iniciar jogo.")
        return

    game = Game(platform=platform, game_format=game_format)
    game.start()


if __name__ == "__main__":
    main()
