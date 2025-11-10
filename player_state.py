from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Union
from card import Card


NUM_PLAYERS = 6
NUM_CARDS = 54
CARDS_PER_SET = 6
NUM_SETS = 9
ALL_CARDS_MASK = (1 << NUM_CARDS) - 1
ALL_SETS_MASK = (1 << NUM_SETS) - 1
SET_CARD_MASKS = tuple(
    ((1 << CARDS_PER_SET) - 1) << (CARDS_PER_SET * idx) for idx in range(NUM_SETS)
)


@dataclass(frozen=True)
class Turn:
    """One ask/answer moment.

    asker/responder are table slots 0-5, card_id is 0-53, success says if the card
    actually swapped hands, and note is just scratch space.
    """

    asker: int
    responder: int
    card_id: int
    success: bool
    note: Optional[str] = None

    def __post_init__(self) -> None:
        if not (0 <= self.asker <= 5):
            raise ValueError(
                f"Asker index must be between 0 and 5 inclusive, got {self.asker}."
            )
        if not (0 <= self.responder <= 5):
            raise ValueError(
                f"Responder index must be between 0 and 5 inclusive, got {self.responder}."
            )
        if self.asker == self.responder:
            raise ValueError("Asker and responder must be different players.")
        if not (0 <= self.card_id < NUM_CARDS):
            raise ValueError(
                f"Card id must be between 0 and {NUM_CARDS - 1}, got {self.card_id}."
            )

    @property
    def answer(self) -> str:
        """Return the human-readable answer given during the turn."""

        return "yes" if self.success else "no"

    def involves(self, player_index: int) -> bool:
        """Return ``True`` if *player_index* took part in this turn."""

        return player_index in (self.asker, self.responder)


class PlayerState:
    """One player's mental notebook for the whole table.

    We stash "definitely has" and "definitely doesn't" card masks for all six seats,
    plus a rough log of which sets folks have touched. hand/player_index/public_cards
    accept ints, 54-len bool-ish sequences, or iterables of card-ish objects.
    """

    def __init__(
        self,
        hand: list[Card] = None,
        player_index: Optional[int] = None,
        public_cards: Optional[int | Sequence[bool] | Iterable[int | object]] = None,
    ) -> None:
        if player_index is None:
            raise ValueError("player_index must be provided to track table state.")
        if not (0 <= player_index < NUM_PLAYERS):
            raise ValueError(f"player_index must be within [0, {NUM_PLAYERS - 1}].")

        self.player_index = player_index

        private_mask = self._coerce_to_bitmask(hand)
        public_mask = (
            self._coerce_to_bitmask(public_cards) if public_cards is not None else 0
        )
        public_mask &= private_mask

        # per-player certainties live here
        self.known_have: list[int] = [0] * NUM_PLAYERS
        self.known_not: list[int] = [0] * NUM_PLAYERS
        self.set_claims: list[int] = [0] * NUM_PLAYERS
        self.known_sets: list[int] = [0] * NUM_PLAYERS

        # has player[i] asked about set j? boolean[6][9]
        self.asked_sets: list[list[float]] = [[0.0 * 6] for _ in range(9)]

        self.known_have[player_index] = private_mask
        self.private_info = private_mask
        self.public_info = public_mask

        # we already know our own cards (and that nobody else has them)
        self.known_not[player_index] = ALL_CARDS_MASK & ~private_mask
        for other in range(NUM_PLAYERS):
            if other == player_index:
                continue
            self.known_not[other] |= private_mask

        self._update_player_sets(player_index)
        self._sync_self_masks()

    # HELPERS
    @staticmethod
    def _coerce_to_bitmask(
        value: Union[int, Sequence[bool], Iterable[Union[int, object]]],
    ) -> int:
        """Convert *value* to a 54-bit mask representing cards held.

        Supported inputs:

        * ``int`` bitmask – lower 54 bits are used.
        * sequence of booleans/ints length 54 – ``True``/non-zero denotes card present.
        * iterable of card identifiers – each entry may be an ``int`` id or any object
          exposing an ``id`` attribute.
        """

        if isinstance(value, int):
            if value < 0:
                raise ValueError("Bitmask must be non-negative.")
            return value & ALL_CARDS_MASK

        if isinstance(value, Sequence):
            if len(value) == NUM_CARDS and all(
                isinstance(v, (bool, int)) for v in value
            ):
                mask = 0
                for idx, present in enumerate(value):
                    if present:
                        PlayerState._validate_card_id(idx)
                        mask |= 1 << idx
                return mask

        mask = 0
        for card in value:
            card_id = PlayerState._extract_card_id(card)
            PlayerState._validate_card_id(card_id)
            mask |= 1 << card_id
        return mask

    @staticmethod
    def _extract_card_id(card: Union[int, object]) -> int:
        if isinstance(card, int):
            return card
        if hasattr(card, "id"):
            return getattr(card, "id")  # type: ignore[no-any-return]
        raise TypeError("Card entries must be integers or provide an 'id' attribute.")

    @staticmethod
    def _validate_card_id(card_id: int) -> None:
        if not (0 <= card_id < NUM_CARDS):
            raise ValueError(f"Card id must be in [0, {NUM_CARDS - 1}], got {card_id}.")

    @staticmethod
    def _mask_to_list(mask: int) -> list[int]:
        return [idx for idx in range(NUM_CARDS) if (mask >> idx) & 1]

    @staticmethod
    def _validate_player(player: int) -> None:
        if not (0 <= player < NUM_PLAYERS):
            raise ValueError(
                f"Player index must be in [0, {NUM_PLAYERS - 1}], got {player}."
            )

    @staticmethod
    def _validate_set(set_id: int) -> None:
        if not (0 <= set_id < NUM_SETS):
            raise ValueError(f"Set index must be in [0, {NUM_SETS - 1}], got {set_id}.")

    @staticmethod
    def _card_to_set(card_id: int) -> int:
        return card_id // CARDS_PER_SET

    @staticmethod
    def _sets_from_mask(card_mask: int) -> int:
        set_mask = 0
        for set_id in range(NUM_SETS):
            if card_mask & SET_CARD_MASKS[set_id]:
                set_mask |= 1 << set_id
        return set_mask

    @staticmethod
    def _sets_mask_to_list(mask: int) -> list[int]:
        return [idx for idx in range(NUM_SETS) if (mask >> idx) & 1]

    def _sync_self_masks(self) -> None:
        self.private_info = self.known_have[self.player_index]
        self.known_not[self.player_index] = ALL_CARDS_MASK & ~self.private_info
        self.public_info &= self.private_info
        self._update_player_sets(self.player_index)

    def _update_player_sets(self, player: int) -> None:
        self._validate_player(player)
        card_sets = self._sets_from_mask(self.known_have[player])
        self.known_sets[player] = card_sets | self.set_claims[player]

    def _set_known_have(self, player: int, card_id: int) -> None:
        self._validate_player(player)
        self._validate_card_id(card_id)
        mask = 1 << card_id

        for idx in range(NUM_PLAYERS):
            self.known_have[idx] &= ~mask
            if idx != player:
                self.known_not[idx] |= mask

        self.known_have[player] |= mask
        self.known_not[player] &= ~mask
        for idx in range(NUM_PLAYERS):
            self._update_player_sets(idx)
        self._sync_self_masks()

    def _set_known_not(self, player: int, card_id: int) -> None:
        self._validate_player(player)
        self._validate_card_id(card_id)
        mask = 1 << card_id

        self.known_have[player] &= ~mask
        self.known_not[player] |= mask
        self._update_player_sets(player)
        self._sync_self_masks()

    def _claim_set_membership(self, player: int, set_id: int) -> None:
        self._validate_player(player)
        self._validate_set(set_id)
        before = self.set_claims[player]
        self.set_claims[player] |= 1 << set_id
        if self.set_claims[player] != before:
            self._update_player_sets(player)

    # PUBLIC API
    def has_card(self, card_id: int) -> bool:
        self._validate_card_id(card_id)
        return bool(self.private_info & (1 << card_id))

    # given legal turn (one valid ask-answer), update our local knowledge
    def process_turn(self, turn):
        if turn.player_index != self.player_index:
            raise ValueError(
                "process_turn should ask a turn from the perspective of this player."
            )
        if not isinstance(turn, Turn):
            raise TypeError("process_turn expects a Turn instance.")
        mask = 1 << turn.card_id
        set_id = self._card_to_set(turn.card_id)

        self._claim_set_membership(turn.asker, set_id)

        if turn.responder == self.player_index:
            # responder is us; a yes means we just lost the card
            if turn.success:
                self._set_known_have(turn.asker, turn.card_id)
                self.public_info &= ~mask
            else:
                # a no here advertises we don't have it
                self._set_known_not(turn.responder, turn.card_id)
                self.public_info &= ~mask
            return

        if turn.asker == self.player_index:
            if turn.success:
                self._set_known_have(turn.asker, turn.card_id)
                # a successful grab is obvious to the table
                self.public_info |= mask
            else:
                self._set_known_not(turn.responder, turn.card_id)
            return

        # not our turn; just taking notes
        if turn.success:
            self._set_known_have(turn.asker, turn.card_id)
        else:
            self._set_known_not(turn.responder, turn.card_id)

    def snapshot(self) -> dict[str, object]:
        """Spit out the current knowledge in friendly list form."""

        private_cards = self._mask_to_list(self.private_info)
        public_cards = self._mask_to_list(self.public_info)
        concealed_cards = sorted(set(private_cards) - set(public_cards))
        return {
            "private": private_cards,
            "public": public_cards,
            "concealed": concealed_cards,
            "known_have": [self._mask_to_list(mask) for mask in self.known_have],
            "known_not": [self._mask_to_list(mask) for mask in self.known_not],
            "known_sets": [self._sets_mask_to_list(mask) for mask in self.known_sets],
            "set_claims": [self._sets_mask_to_list(mask) for mask in self.set_claims],
        }

    def solve(self, max_passes: int = NUM_CARDS) -> dict[str, object]:
        """Run quick deductions and hand back the refreshed snapshot.

        Loops a few times (bounded by ``max_passes``) applying two cheap rules:
        lone candidate for a card owns it, and a set claim with one viable card means
        they own that last card. Updates happen in-place.
        """

        if max_passes <= 0:
            return self.snapshot()

        for _ in range(max_passes):
            iteration_changed = False

            # Card-level eliminations: if only one candidate remains, assign the card.
            for card_id in range(NUM_CARDS):
                mask = 1 << card_id
                owner = next(
                    (
                        player
                        for player in range(NUM_PLAYERS)
                        if self.known_have[player] & mask
                    ),
                    None,
                )
                if owner is not None:
                    continue

                candidates = [
                    player
                    for player in range(NUM_PLAYERS)
                    if not (self.known_not[player] & mask)
                ]
                if len(candidates) == 1:
                    self._set_known_have(candidates[0], card_id)
                    iteration_changed = True

            # Set-claim eliminations: if the claim leaves only one possible card, assign it.
            for player in range(NUM_PLAYERS):
                claim_mask = self.set_claims[player]
                if claim_mask == 0:
                    continue

                for set_id in range(NUM_SETS):
                    if not (claim_mask & (1 << set_id)):
                        continue

                    start = set_id * CARDS_PER_SET
                    candidate_cards = [
                        card
                        for card in range(start, start + CARDS_PER_SET)
                        if not (self.known_not[player] & (1 << card))
                    ]

                    if len(candidate_cards) == 1:
                        card_id = candidate_cards[0]
                        if not (self.known_have[player] & (1 << card_id)):
                            self._set_known_have(player, card_id)
                            iteration_changed = True

            if not iteration_changed:
                break

        return self.snapshot()
