from player_state import PlayerState
from card import Card
from card import shuffled_cards

# cli for simulating games
class Game:
    # all references to players should point to objects in this array
    players = PlayerState[6]

    def __init__(self):
        cards = shuffled_cards()

        for i in range(6):
            self.players[i] = PlayerState(cards[i * 9, i * 9 + 9], i)

            self._turns = []
