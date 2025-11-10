from player_state import PlayerState


# instance of the bot engine
MONTE_CARLO_SIMULATIONS_PER_MOVE = 1000


class Engine:
    def __init__(self):
        self.state = PlayerState()

    def estimate_average_info_score(self) -> int:
        pass

    # generate legal moves
    def move_gen(self) -> list:
        pass

    # find best move
    def best_move(self, move):
        moves = self.move_gen()
        best_move = None
        best_score = -float("inf")
        for move in moves:
            result = self.monte_carlo(MONTE_CARLO_SIMULATIONS_PER_MOVE)
            if result["score"] > best_score:
                best_score = result["score"]
                best_move = move
        return best_move

    def monte_carlo(self, num_simulations: int) -> float:
        score = 0.0
        for _ in range(num_simulations):
            self.generate_possible_game_state(move)
            score += self.entropy()
            self.undo()
        return score / num_simulations

    def generate_possible_game_state(self):
        pass

    # returns to previous state before calling generate_possible_game_state
    def undo(self):
        pass

    def entropy(self):
        pass
