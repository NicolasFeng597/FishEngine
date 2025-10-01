import os
import sys
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from player_state import (
    ALL_CARDS_MASK,
    CARDS_PER_SET,
    NUM_PLAYERS,
    NUM_SETS,
    PlayerState,
    Turn,
)


class PlayerStateTests(unittest.TestCase):
    def test_initialisation_with_card_ids(self):
        state = PlayerState(hand=[0, 5, 53], player_index=0)
        self.assertTrue(state.has_card(0))
        self.assertTrue(state.has_card(5))
        self.assertTrue(state.has_card(53))
        owned_mask = (1 << 0) | (1 << 5) | (1 << 53)
        self.assertEqual(state.known_have[0], owned_mask)
        self.assertEqual(state.known_not[0], ALL_CARDS_MASK & ~owned_mask)
        for other in range(1, NUM_PLAYERS):
            self.assertTrue(state.known_not[other] & owned_mask)
            self.assertEqual(state.known_have[other] & owned_mask, 0)
            self.assertEqual(state.known_sets[other], 0)
    # public info starts empty
        self.assertEqual(state.public_info, 0)
        own_sets = state.known_sets[0]
        expected_sets = {0 // CARDS_PER_SET, 5 // CARDS_PER_SET, 53 // CARDS_PER_SET}
        self.assertEqual({idx for idx in range(NUM_SETS) if (own_sets >> idx) & 1}, expected_sets)

    def test_process_turn_asker_success(self):
        state = PlayerState(hand=[1], player_index=2)
        turn = Turn(asker=2, responder=4, card_id=10, success=True)
        state.process_turn(turn)
        self.assertTrue(state.has_card(10))
        self.assertTrue(state.public_info & (1 << 10))
        self.assertTrue(state.known_have[2] & (1 << 10))
        for other in range(NUM_PLAYERS):
            if other != 2:
                self.assertTrue(state.known_not[other] & (1 << 10))
        set_id = turn.card_id // 6
        self.assertTrue(state.known_sets[2] & (1 << set_id))
        self.assertTrue(state.set_claims[2] & (1 << set_id))

    def test_process_turn_responder_success(self):
        state = PlayerState(hand=[3, 4], player_index=1)
        turn = Turn(asker=5, responder=1, card_id=4, success=True)
        state.process_turn(turn)
        self.assertFalse(state.has_card(4))
        self.assertFalse(state.public_info & (1 << 4))
        self.assertTrue(state.known_have[5] & (1 << 4))
        self.assertTrue(state.known_not[1] & (1 << 4))
        set_id = turn.card_id // 6
        self.assertTrue(state.set_claims[5] & (1 << set_id))
        self.assertTrue(state.known_sets[5] & (1 << set_id))

    def test_process_turn_responder_failure(self):
        state = PlayerState(hand=[7], player_index=3)
        turn = Turn(asker=0, responder=3, card_id=12, success=False)
        state.process_turn(turn)
        self.assertFalse(state.has_card(12))
        self.assertFalse(state.public_info & (1 << 12))
        self.assertTrue(state.known_not[3] & (1 << 12))
        self.assertEqual(state.known_have[3] & (1 << 12), 0)
        self.assertTrue(state.set_claims[0] & (1 << (12 // 6)))
        self.assertTrue(state.known_sets[0] & (1 << (12 // 6)))

    def test_process_turn_observed_players(self):
        state = PlayerState(hand=[18, 19], player_index=0)
        turn_success = Turn(asker=2, responder=4, card_id=22, success=True)
        state.process_turn(turn_success)
        self.assertTrue(state.known_have[2] & (1 << 22))
        for other in range(NUM_PLAYERS):
            if other != 2:
                self.assertTrue(state.known_not[other] & (1 << 22))
        self.assertTrue(state.set_claims[2] & (1 << (22 // 6)))

        turn_fail = Turn(asker=1, responder=3, card_id=7, success=False)
        state.process_turn(turn_fail)
        self.assertTrue(state.known_not[3] & (1 << 7))
        self.assertEqual(state.known_have[3] & (1 << 7), 0)
        self.assertTrue(state.set_claims[1] & (1 << (7 // 6)))

    def test_solve_output(self):
        state = PlayerState(hand=[2, 8], player_index=4, public_cards=[2])
        summary = state.solve()
        self.assertEqual(sorted(summary["private"]), [2, 8])
        self.assertEqual(sorted(summary["public"]), [2])
        self.assertEqual(sorted(summary["concealed"]), [8])
        self.assertEqual(sorted(summary["known_have"][4]), [2, 8])
        for other in range(NUM_PLAYERS):
            if other != 4:
                self.assertIn(2, summary["known_not"][other])
        expected_sets = sorted({card // CARDS_PER_SET for card in (2, 8)})
        self.assertEqual(sorted(summary["known_sets"][4]), expected_sets)
        self.assertEqual(summary["set_claims"][4], [])

    def test_solve_deduces_card_from_elimination(self):
        state = PlayerState(hand=[0], player_index=0)
        target_card = 15
        deduced_player = 3

        for responder in range(NUM_PLAYERS):
            if responder == deduced_player:
                continue
            asker = (responder + 1) % NUM_PLAYERS
            if asker == responder:
                asker = (asker + 1) % NUM_PLAYERS
            turn = Turn(asker=asker, responder=responder, card_id=target_card, success=False)
            state.process_turn(turn)

        self.assertFalse(state.known_have[deduced_player] & (1 << target_card))
        state.solve()
        self.assertTrue(state.known_have[deduced_player] & (1 << target_card))
        for other in range(NUM_PLAYERS):
            if other != deduced_player:
                self.assertTrue(state.known_not[other] & (1 << target_card))

    def test_solve_uses_set_claims(self):
        state = PlayerState(hand=[0], player_index=0)
        candidate = 4
        set_id = 2
        cards = list(range(set_id * CARDS_PER_SET, set_id * CARDS_PER_SET + CARDS_PER_SET))

    # have the candidate ping the set to mark a claim
        state.process_turn(Turn(asker=candidate, responder=0, card_id=cards[0], success=False))

        owners = [1, 1, 2, 3, 5]
        for card, owner in zip(cards[:-1], owners):
            responder = (owner + 1) % NUM_PLAYERS
            if responder == owner:
                responder = (responder + 1) % NUM_PLAYERS
            state.process_turn(Turn(asker=owner, responder=responder, card_id=card, success=True))

        final_card = cards[-1]
        self.assertFalse(state.known_have[candidate] & (1 << final_card))
        possible_holders = [
            player for player in range(NUM_PLAYERS) if not (state.known_not[player] & (1 << final_card))
        ]
        self.assertGreaterEqual(len(possible_holders), 2)

        state.solve()
        self.assertTrue(state.known_have[candidate] & (1 << final_card))
        for other in range(NUM_PLAYERS):
            if other != candidate:
                self.assertTrue(state.known_not[other] & (1 << final_card))


class TurnTests(unittest.TestCase):
    def test_turn_validation(self):
        with self.assertRaises(ValueError):
            Turn(asker=0, responder=0, card_id=1, success=True)
        with self.assertRaises(ValueError):
            Turn(asker=-1, responder=2, card_id=1, success=False)
        with self.assertRaises(ValueError):
            Turn(asker=1, responder=2, card_id=54, success=False)

    def test_turn_answer(self):
        turn_yes = Turn(asker=1, responder=2, card_id=5, success=True)
        turn_no = Turn(asker=1, responder=2, card_id=5, success=False)
        self.assertEqual(turn_yes.answer, "yes")
        self.assertEqual(turn_no.answer, "no")


if __name__ == "__main__":
    unittest.main()
