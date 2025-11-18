import os
import sys
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from player_state import (
    CARDS_PER_SET,
    NUM_PLAYERS,
    NUM_SETS,
    NUM_CARDS,
    PlayerState,
    Turn,
)


class PlayerStateTests(unittest.TestCase):
    def test_initialisation_with_card_ids(self):
        state = PlayerState(hand=[0, 5, 53], player_index=0)
        self.assertTrue(state.has_card(0))
        self.assertTrue(state.has_card(5))
        self.assertTrue(state.has_card(53))
        
        # Check known_have for our player
        self.assertEqual(state.known_have[0], {0, 5, 53})
        
        # Check known_not for our player (should not have all other cards)
        expected_not_have = set(range(NUM_CARDS)) - {0, 5, 53}
        self.assertEqual(state.known_not[0], expected_not_have)
        
        # Other players should not have our cards
        for other in range(1, NUM_PLAYERS):
            self.assertTrue(0 in state.known_not[other])
            self.assertTrue(5 in state.known_not[other])
            self.assertTrue(53 in state.known_not[other])
            self.assertEqual(len(state.known_have[other]), 0)
            self.assertEqual(len(state.set_claims[other]), 0)
        
        # Public info starts empty
        self.assertEqual(state.public_hand, set())
        
        # Check our set claims based on our hand
        own_sets = state.set_claims[0]
        expected_sets = {0 // CARDS_PER_SET, 5 // CARDS_PER_SET, 53 // CARDS_PER_SET}
        self.assertEqual(own_sets, expected_sets)

    def test_process_turn_asker_success(self):
        state = PlayerState(hand=[1], player_index=2)
        turn = Turn(asker=2, responder=4, card_id=10, success=True)
        state.process_turn(turn)
        
        # We (player 2) should now have card 10
        self.assertTrue(state.has_card(10))
        self.assertTrue(10 in state.public_hand)
        self.assertTrue(10 in state.known_have[2])
        
        # Other players should not have it
        for other in range(NUM_PLAYERS):
            if other != 2:
                self.assertTrue(10 in state.known_not[other])
        
        # We should have claimed the set
        set_id = turn.card_id // CARDS_PER_SET
        self.assertTrue(set_id in state.set_claims[2])

    def test_process_turn_responder_success(self):
        state = PlayerState(hand=[3, 4], player_index=1)
        turn = Turn(asker=5, responder=1, card_id=4, success=True)
        state.process_turn(turn)
        
        # We (player 1) should no longer have card 4
        self.assertFalse(state.has_card(4))
        self.assertFalse(4 in state.public_hand)
        
        # Player 5 should have it now
        self.assertTrue(4 in state.known_have[5])
        self.assertTrue(4 in state.known_not[1])
        
        # Player 5 should have claimed the set
        set_id = turn.card_id // CARDS_PER_SET
        self.assertTrue(set_id in state.set_claims[5])

    def test_process_turn_responder_failure(self):
        state = PlayerState(hand=[7], player_index=3)
        turn = Turn(asker=0, responder=3, card_id=12, success=False)
        state.process_turn(turn)
        
        # We (player 3) should not have card 12
        self.assertFalse(state.has_card(12))
        self.assertFalse(12 in state.public_hand)
        self.assertTrue(12 in state.known_not[3])
        self.assertFalse(12 in state.known_have[3])
        
        # Player 0 should have claimed the set
        self.assertTrue((12 // CARDS_PER_SET) in state.set_claims[0])

    def test_process_turn_observed_players(self):
        state = PlayerState(hand=[18, 19], player_index=0)
        
        # Observe a successful turn
        turn_success = Turn(asker=2, responder=4, card_id=22, success=True)
        state.process_turn(turn_success)
        self.assertTrue(22 in state.known_have[2])
        
        # Other players should not have it
        for other in range(NUM_PLAYERS):
            if other != 2:
                self.assertTrue(22 in state.known_not[other])
        self.assertTrue((22 // CARDS_PER_SET) in state.set_claims[2])

        # Observe a failed turn
        turn_fail = Turn(asker=1, responder=3, card_id=7, success=False)
        state.process_turn(turn_fail)
        self.assertTrue(7 in state.known_not[3])
        self.assertFalse(7 in state.known_have[3])
        self.assertTrue((7 // CARDS_PER_SET) in state.set_claims[1])

    def test_solve_output(self):
        state = PlayerState(hand=[2, 8], player_index=4, public_cards=[2])
        summary = state.solve()
        
        self.assertEqual(sorted(summary["hand"]), [2, 8])
        self.assertEqual(sorted(summary["public_hand"]), [2])
        self.assertEqual(sorted(summary["private_hand"]), [8])
        self.assertEqual(sorted(summary["known_have"][4]), [2, 8])
        
        # Other players should know we don't have card 2
        for other in range(NUM_PLAYERS):
            if other != 4:
                self.assertIn(2, summary["known_not"][other])
        
        expected_sets = sorted({card // CARDS_PER_SET for card in (2, 8)})
        self.assertEqual(sorted(summary["set_claims"][4]), expected_sets)

    def test_solve_deduces_card_from_elimination(self):
        state = PlayerState(hand=[0], player_index=0)
        target_card = 15
        deduced_player = 3

        # Have all players except deduced_player say they don't have the card
        for responder in range(NUM_PLAYERS):
            if responder == deduced_player:
                continue
            asker = (responder + 1) % NUM_PLAYERS
            if asker == responder:
                asker = (asker + 1) % NUM_PLAYERS
            turn = Turn(asker=asker, responder=responder, card_id=target_card, success=False)
            state.process_turn(turn)

        # Before solve, we shouldn't know who has it
        self.assertFalse(target_card in state.known_have[deduced_player])
        
        # After solve, should deduce the remaining player has it
        state.solve()
        self.assertTrue(target_card in state.known_have[deduced_player])
        
        # All other players should not have it
        for other in range(NUM_PLAYERS):
            if other != deduced_player:
                self.assertTrue(target_card in state.known_not[other])

    def test_solve_uses_set_claims(self):
        state = PlayerState(hand=[0], player_index=0)
        candidate = 4
        set_id = 2
        cards = list(range(set_id * CARDS_PER_SET, set_id * CARDS_PER_SET + CARDS_PER_SET))

        # Have the candidate ping the set to mark a claim
        state.process_turn(Turn(asker=candidate, responder=0, card_id=cards[0], success=False))

        # Assign all cards in the set except the last one to other players
        owners = [1, 1, 2, 3, 5]
        for card, owner in zip(cards[:-1], owners):
            responder = (owner + 1) % NUM_PLAYERS
            if responder == owner:
                responder = (responder + 1) % NUM_PLAYERS
            state.process_turn(Turn(asker=owner, responder=responder, card_id=card, success=True))

        final_card = cards[-1]
        
        # Before solve, we shouldn't know candidate has the final card
        self.assertFalse(final_card in state.known_have[candidate])
        
        # Multiple players should be possible holders
        possible_holders = [
            player for player in range(NUM_PLAYERS) 
            if final_card not in state.known_not[player]
        ]
        self.assertGreaterEqual(len(possible_holders), 2)

        # After solve, should deduce candidate has it (they claimed the set)
        state.solve()
        self.assertTrue(final_card in state.known_have[candidate])
        
        # All other players should not have it
        for other in range(NUM_PLAYERS):
            if other != candidate:
                self.assertTrue(final_card in state.known_not[other])


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
