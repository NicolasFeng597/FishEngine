from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Union

NUM_PLAYERS = 6
NUM_CARDS = 54
CARDS_PER_SET = 6
NUM_SETS = 9

def get_team(player_index: int) -> int:
    """Return team (0 or 1) for player index."""
    return 0 if player_index < 3 else 1


@dataclass(frozen=True)
class Turn:
    """One ask/answer moment in the game."""
    asker: int
    responder: int
    card_id: int
    success: bool
    note: Optional[str] = None

    def __post_init__(self) -> None:
        if not (0 <= self.asker < NUM_PLAYERS and 0 <= self.responder < NUM_PLAYERS):
            raise ValueError(f"Player indices must be 0-{NUM_PLAYERS - 1}")
        if self.asker == self.responder:
            raise ValueError("Asker and responder must be different")
        if not (0 <= self.card_id < NUM_CARDS):
            raise ValueError(f"Card id must be 0-{NUM_CARDS - 1}")

    @property
    def answer(self) -> str:
        return "yes" if self.success else "no"

    def involves(self, player_index: int) -> bool:
        return player_index in (self.asker, self.responder)


class PlayerState:
    """Tracks one player's knowledge of the game state."""

    def __init__(
        self,
        hand: Optional[list[Union[int, object]]] = None,
        player_index: Optional[int] = None,
        public_cards: Optional[list[Union[int, object]]] = None,
    ) -> None:
        if player_index is None or not (0 <= player_index < NUM_PLAYERS):
            raise ValueError(f"player_index must be 0-{NUM_PLAYERS - 1}")

        self.player_index = player_index
        hand_ids = self._extract_ids(hand or [])
        
        self.hand = set(hand_ids)
        self.known_have = [set() for _ in range(NUM_PLAYERS)]
        self.known_not = [set() for _ in range(NUM_PLAYERS)]
        self.set_claims = [set() for _ in range(NUM_PLAYERS)]
        self.completed_sets = set()
        
        # Initialize knowledge
        self.known_have[player_index] = self.hand.copy()
        self.known_not[player_index] = set(range(NUM_CARDS)) - self.hand
        for other in range(NUM_PLAYERS):
            if other != player_index:
                self.known_not[other].update(self.hand)
        for card_id in self.hand:
            self.set_claims[player_index].add(card_id // CARDS_PER_SET)

    @staticmethod
    def _extract_ids(cards: list[Union[int, object]]) -> list[int]:
        """Convert cards (int IDs or objects with .id) to list of IDs."""
        result = []
        for card in cards:
            cid = card if isinstance(card, int) else getattr(card, "id", None)
            if cid is None or not (0 <= cid < NUM_CARDS):
                raise ValueError(f"Invalid card: {card}")
            result.append(cid)
        return result

    def _set_known_have(self, player: int, card_id: int) -> None:
        """Mark that a player definitely has a card."""
        for idx in range(NUM_PLAYERS):
            self.known_have[idx].discard(card_id)
            if idx != player:
                self.known_not[idx].add(card_id)
        self.known_have[player].add(card_id)
        self.known_not[player].discard(card_id)
        if player == self.player_index:
            self.hand.add(card_id)

    def _set_known_not(self, player: int, card_id: int) -> None:
        """Mark that a player definitely doesn't have a card."""
        self.known_have[player].discard(card_id)
        self.known_not[player].add(card_id)

    def has_card(self, card_id: int) -> bool:
        """Check if this player has a specific card."""
        return card_id in self.hand

    def get_possible_holders(self, card_id: int) -> list[int]:
        """Return list of players who could have this card."""
        for player in range(NUM_PLAYERS):
            if card_id in self.known_have[player]:
                return [player]
        return [p for p in range(NUM_PLAYERS) if card_id not in self.known_not[p]]

    def process_turn(self, turn: Turn) -> None:
        """Update knowledge based on a turn."""
        set_id = turn.card_id // CARDS_PER_SET
        self.set_claims[turn.asker].add(set_id)
        
        if turn.success:
            self._set_known_have(turn.asker, turn.card_id)
            if turn.responder == self.player_index:
                self.hand.discard(turn.card_id)
        else:
            self._set_known_not(turn.responder, turn.card_id)

    def snapshot(self) -> dict[str, object]:
        """Return current knowledge state."""
        return {
            "player_index": self.player_index,
            "hand": sorted(self.hand),
            "known_have": [sorted(cards) for cards in self.known_have],
            "known_not": [sorted(cards) for cards in self.known_not],
            "set_claims": [sorted(sets) for sets in self.set_claims],
            "completed_sets": sorted(self.completed_sets),
        }

    def solve(self, max_passes: int = NUM_CARDS) -> dict[str, object]:
        """Run logical deductions to infer card locations."""
        for _ in range(max_passes):
            changed = False

            # Rule 1: If only one player could have a card, they have it
            for card_id in range(NUM_CARDS):
                if any(card_id in self.known_have[p] for p in range(NUM_PLAYERS)):
                    continue
                candidates = self.get_possible_holders(card_id)
                if len(candidates) == 1:
                    self._set_known_have(candidates[0], card_id)
                    changed = True

            # Rule 2: Set claim deduction (prioritize players with no known cards)
            for player in range(NUM_PLAYERS):
                for set_id in self.set_claims[player]:
                    start = set_id * CARDS_PER_SET
                    set_cards = range(start, start + CARDS_PER_SET)
                    known = [c for c in set_cards if c in self.known_have[player]]
                    candidates = [c for c in set_cards 
                                if c not in self.known_not[player] 
                                and c not in self.known_have[player]]
                    
                    if len(candidates) == 1 and len(known) == 0:
                        self._set_known_have(player, candidates[0])
                        changed = True
            
            # Second pass: remaining single candidates
            for player in range(NUM_PLAYERS):
                for set_id in self.set_claims[player]:
                    start = set_id * CARDS_PER_SET
                    candidates = [c for c in range(start, start + CARDS_PER_SET)
                                if c not in self.known_not[player] 
                                and c not in self.known_have[player]]
                    if len(candidates) == 1:
                        self._set_known_have(player, candidates[0])
                        changed = True

            if not changed:
                break

        return self.snapshot()
