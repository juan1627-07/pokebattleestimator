# ============================================
# Move Engine
# ============================================

MOVE_SCORE = {

    "stab": 35,

    "power": 25,

    "accuracy": 15,

    "priority": 10,

    "physical_special": 20,

    # Competitive bonuses

    "recovery": 25,

    "setup": 30,

    "hazard": 20,

    "hazard_removal": 20,

    "pivot": 18,

    # Penalties

    "recharge_penalty": -50,

    "two_turn_penalty": -35,

    "recoil_penalty": -10

}

UTILITY_ATTACKS = {

    "seismic-toss",

    "night-shade",

    "foul-play"

}

# ============================================
# Competitive Move Categories
# ============================================

RECOVERY_MOVES = {

    "soft-boiled",
    "recover",
    "roost",
    "wish",
    "protect",
    "toxic",
    "stealth-rock",
    "spikes",
    "thunder-wave",
    "heal-bell"
}


SETUP_MOVES = {

    "swords-dance",
    "dragon-dance",
    "nasty-plot",
    "calm-mind",
    "bulk-up",
    "quiver-dance"

}

HAZARD_MOVES = {

    "stealth-rock",
    "spikes",
    "toxic-spikes",
    "sticky-web"

}

HAZARD_REMOVAL = {

    "rapid-spin",
    "defog"

}

PIVOT_MOVES = {

    "u-turn",
    "volt-switch",
    "flip-turn"

}

RECHARGE_MOVES = {

    "hyper-beam",
    "blast-burn",
    "hydro-cannon",
    "frenzy-plant",
    "giga-impact"

}

TWO_TURN_MOVES = {

    "fly",
    "dig",
    "bounce",
    "dive"

}

def score_move(
    move,
    pokemon_types,
    attack_category
):

    score = 0

    move_type = move["type"]

    if move_type in pokemon_types:
        score += MOVE_SCORE["stab"]

    power = move.get("power") or 0

    score += min(power,150)/150 * MOVE_SCORE["power"]

    accuracy = move.get("accuracy") or 100

    score += (accuracy/100) * MOVE_SCORE["accuracy"]

    priority = move.get("priority") or 0

    score += priority * MOVE_SCORE["priority"]

    if move["damage_class"] == attack_category.lower():

        score += MOVE_SCORE["physical_special"]

    move_name = move["name"].lower()

    # Recovery

    if move_name in RECOVERY_MOVES:
        score += MOVE_SCORE["recovery"]

    # Setup

    if move_name in SETUP_MOVES:
        score += MOVE_SCORE["setup"]

    # Entry Hazards

    if move_name in HAZARD_MOVES:
        score += MOVE_SCORE["hazard"]

    # Hazard Removal

    if move_name in HAZARD_REMOVAL:
        score += MOVE_SCORE["hazard_removal"]

    # Pivot Moves

    if move_name in PIVOT_MOVES:
        score += MOVE_SCORE["pivot"]

    # Recharge Penalty

    if move_name in RECHARGE_MOVES:
        score += MOVE_SCORE["recharge_penalty"]

    # Two-Turn Penalty

    if move_name in TWO_TURN_MOVES:
        score += MOVE_SCORE["two_turn_penalty"]

    return round(score,2)


def build_moveset(

    scored_moves,

    role,

    pokemon_types,

    limit=4

):

    role = role.lower()

    moveset = []

    move_lookup = {

        m["name"].lower(): m

        for m in scored_moves

    }

    # ---------------------------------------
    # Helper
    # ---------------------------------------

    def add(move_name):

        if len(moveset) >= limit:
            return

        move = move_lookup.get(move_name)

        if move and move["name"] not in moveset:

            moveset.append(

                move["name"]

            )

    # =======================================
    # WALLS
    # =======================================

    if "wall" in role:

        # Recovery first

        for move in RECOVERY_MOVES:
            add(move)

        # Hazards

        for move in HAZARD_MOVES:
            add(move)

        # Utility

        utility = [

            "toxic",

            "thunder-wave",

            "protect",

            "heal-bell"

        ]

        for move in utility:
            add(move)

    # =======================================
    # BULKY
    # =======================================

    elif "bulky" in role:

        for move in SETUP_MOVES:
            add(move)

        for move in RECOVERY_MOVES:
            add(move)

    # =======================================
    # FAST SWEEPERS
    # =======================================

    elif "fast" in role:

        for move in SETUP_MOVES:
            add(move)

    # =======================================
    # MIXED
    # =======================================

    elif "mixed" in role:

        for move in SETUP_MOVES:
            add(move)

    # =======================================
    # Ensure STAB exists
    # =======================================

    has_stab = False

    for move in moveset:

        info = move_lookup.get(

            move.lower()

        )

        if info:

            if info["type"] in pokemon_types:

                has_stab = True

                break

    if not has_stab:

        for move in scored_moves:

            if move["type"] in pokemon_types:

                add(move["name"])

                break

    # =======================================
    # Fill remaining by score
    # =======================================

    for move in scored_moves:

        if len(moveset) >= limit:

            break

        if move["name"] not in moveset:

            moveset.append(

                move["name"]

            )

    return moveset