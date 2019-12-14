from enum import Enum

class GameState(Enum):
    PRE_INIT = 0
    INITIALISE = 1
    STARTED = 2
    FINISHED = 3