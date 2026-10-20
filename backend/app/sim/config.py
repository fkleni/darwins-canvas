"""All balance numbers of the simulation live here.

Nothing in this file contains logic. We tune the game by editing numbers,
never the rules. Values are first guesses and will be tuned in Phase 5.
"""

# --- World parameters -------------------------------------------------
# kind "ratio":  the value is a multiplier (gravity 2.0 means twice as strong).
#                Differences are measured as a ratio.
# kind "linear": the value is a plain amount (15 C, 21 %).
#                Differences are measured as a plain subtraction.
# baseline:      the starting value of the planet and of every base species.
# max_shift:     how far a creature can move its adaptation in ONE evolution.
#                For "ratio" this is a multiplier, for "linear" an amount.
# scale:         (linear only) how many units count as "one step of stress".
# max_event_change: the most one single event may change this parameter.
#                For "ratio" a multiplier (3.0 means x3 or /3), for "linear" +/- amount.
# min, max:      the lowest and highest value the world can ever have.
PARAMETERS = {
    "gravity": {
        "kind": "ratio", "baseline": 1.0, "max_shift": 1.6,
        "max_event_change": 3.0, "min": 0.1, "max": 50.0,
    },
    "radiation": {
        "kind": "ratio", "baseline": 1.0, "max_shift": 1.6,
        "max_event_change": 3.0, "min": 0.1, "max": 50.0,
    },
    "temperature": {
        "kind": "linear", "baseline": 15.0, "max_shift": 8.0, "scale": 12.0,
        "max_event_change": 25.0, "min": -100.0, "max": 150.0,
    },
    "oxygen": {
        "kind": "linear", "baseline": 21.0, "max_shift": 4.0, "scale": 6.0,
        "max_event_change": 8.0, "min": 0.0, "max": 100.0,
    },
    "water": {
        "kind": "linear", "baseline": 70.0, "max_shift": 15.0, "scale": 25.0,
        "max_event_change": 30.0, "min": 0.0, "max": 100.0,
    },
}

# --- Scoring and extinction -------------------------------------------
SURVIVAL_THRESHOLD = 20      # score below this means extinction
GRACE_EVOLUTIONS = 2         # first evolutions of a lineage cannot go extinct
SCORE_WIDTH = 0.9            # how quickly the score falls as the gap grows

# --- Hard physical limits ---------------------------------------------
# Biggest gravity a creature can survive, by body size (1 = tiny, 5 = huge).
# Bigger bodies carry their own weight worse (square-cube law).
GRAVITY_CEILING_BY_BODY_SIZE = {
    1: 14.0,
    2: 12.0,
    3: 8.0,
    4: 6.0,
    5: 5.0,
}


# --- Cosmetic mutation ------------------------------------------------
MUTATION_PRESSURE_CHANCE = 0.6   # chance that an event's push decides the mutation