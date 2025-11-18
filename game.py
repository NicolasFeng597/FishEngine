from player_state import PlayerState, Turn
from card import Card
from card import shuffled_cards
from typing import Optional
from random import randint


# cli for simulating games
class Game:
    # all references to players should point to objects in this array
    players = PlayerState[6]

    claimed_sets: list[int] = []
    last_turn: Turn
    _turns: list[Turn] = []
    _cards_owned: list[list[Card]]
    hand_sizes: list[int]

    def __init__(self):
        cards = shuffled_cards()

        for i in range(6):
            self.players[i] = PlayerState(cards[i * 9, i * 9 + 9], i)

    def play_game(self):
        """Starts playing the game, calling player objects to make moves, updating cards_owned,
        etc.

        """
        while self.winner is None:
            turn = self.players[randint(0, 5)].make_turn()
            assert self.is_legal_turn(turn), f"Turn {str(turn)} is illegal."
            self.last_turn = turn
            self._turns.append(turn)
            self.process_turn(turn)

    def process_turn(turn: Turn):
        """Updates master game state given the next move."""

    def is_legal_turn(self, turn: Turn) -> bool:
        """If turn is legal."""
        pass

    @property
    def winner(self) -> Optional[int]:
        """Winner of the game. None if the game is ongoing, 0 if team ___ won, 1 if team ___ won"""
        pass
