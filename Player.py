class Player:

    def __init__(self, x, y, bet_region):
        # Initialize a node with data and next pointer
        self.x = x
        self.y = y
        self.bet_size = 0.0
        self.bet_region = bet_region
        self.position = ""

    def set_player_pos(self, btn, player, total_players=6):
        # Heads-up: dealer/button is always SB, the other player is BB.
        if total_players == 2:
            self.position = "SB" if player == btn else "BB"
            return

        if (player - btn == 0):
            self.position = "BTN"
        elif (player - btn == 5 or player - btn == -1):
            self.position = "CO"
        elif (player - btn == 4 or player - btn == -2):
            self.position = "HJ"
        elif (player - btn == 3 or player - btn == -3):
            self.position = "UTG"
        elif (player - btn == 2 or player - btn == -4):
            self.position = "BB"
        elif (player - btn == 1 or player - btn == -5):
            self.position = "SB"
        else:
            print("BUG")
