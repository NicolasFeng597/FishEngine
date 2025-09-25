# generic fish variables, to be extended by other classes.

# to make card objects immutable
from dataclasses import dataclass

# array of 6 hands; hand[i] denotes the hand of player i
hand = [[] for _ in range(6)]

# ---------------------------------- Card Ids, Labels, and Sets ---------------------------------- #
# Specific naming conventions: "label", "id", and "set".
# Card labels are denoted by the the numerical value of the card, then the suit.
# The value of aces is denoted by "A", and jokers are denoted by "BJ" (black joker)
# and "RJ" (red joker). 
# IDs are ordered from lowest to highest value in a set:
#   ID [0, 1, 2, 3, 4, 5] = [2S, 3S, 4S, 5S, 6S, 7S]
# ID 0-5 inclusive: low spades, set 0
# ID 6-11 inclusive: high spades, set 1
# ID 12-17 inclusive: low clubs, set 2
# ID 18-23 inclusive: high clubs, set 3
# ID 24-29 inclusive: low diamonds, set 4
# ID 30-35 inclusive: high diamonds, set 5
# ID 36-41 inclusive: low hearts, set 6
# ID 42-47 inclusive: high hearts, set 7
# ID 48-53 inclusive: aces and jokers, set 8

CARDS = [Card(i) for i in range(0, 54)]

# final list of card objects; each card is immutable, and transferring cards transfers individual
# card objects. this is because there should only be one card object per physical card.

# representation of a card, each object is immutable and has a unique id
@dataclass(frozen=True)
class Card:
    # converts a card id to a set:
    def idToSet(id: int) -> int:
        pass

    # converts a card id to a label:
    def idToLabel(id: int) -> str:
        pass

    # converts a card label to an id:
    def labelToId(label: str) -> int:
        pass

    # is this card and another in the same set?
    def isSameSet(self, c2: Card) -> bool:
        return self.set == c2.set

    # converts a card id to a 
    def __init__(self, id: int):
        assert(0 <= id <= 53), "Invalid card id"
        self.id = id
        self.set = idToSet(id)

    

    