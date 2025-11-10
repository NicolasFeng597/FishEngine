# FishEngine
Solver/engine/CLI for simulating the card game Fish (aka Literature)

Using Python 3.13.5

The class heirarchy of this repository is as follows:
Game -- an instance of a game being played
    players: list[Player] -- array of unique players
    last_turn: Turn -- the last turn in the game
    next_turn_player: int -- the id of the player who's turn it is
    
Player -- a player of Fish
    id: int -- unique identifier
    hand: list[Card] -- current hand
    
    make_turn(game: Game, player: int, card: Card) -- asks player for card, updating Game and hand
    process_turn(turn: Turn) -- updates player's info given a turn

Card -- a specific card in the deck
    id: int -- unique identifier