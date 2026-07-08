# ============================================
# Competitive Engine
# ============================================

ROLE_SCORE = {

    "Fast Physical Sweeper": 95,
    "Fast Special Sweeper": 95,
    "Fast Mixed Sweeper": 94,

    "Physical Sweeper": 90,
    "Special Sweeper": 90,
    "Mixed Sweeper": 88,

    "Bulky Physical": 87,
    "Bulky Special": 87,
    "Bulky Mixed": 86,

    "Physical Wall": 90,
    "Special Wall": 90

}


TIER_SCORE = {

    "Uber":100,
    "OU":95,
    "UU":88,
    "RU":82,
    "NU":75,
    "PU":68,

    "Unknown":80

}


def evaluate_build(

    role,

    tier,

    ability,

    item,

    moves

):

    score = 0

    # -----------------------------
    # Role
    # -----------------------------

    score += ROLE_SCORE.get(

        role,

        80

    )

    # -----------------------------
    # Tier
    # -----------------------------

    score += TIER_SCORE.get(

        tier,

        80

    )

    # -----------------------------
    # Ability
    # -----------------------------

    score += ability.get(

        "score",

        50

    )

    # -----------------------------
    # Item
    # -----------------------------

    score += item.get(

        "score",

        80

    )

    # -----------------------------
    # Moves
    # -----------------------------

    move_score = 0

    if len(moves) == 4:

        move_score = 100

    elif len(moves) == 3:

        move_score = 80

    elif len(moves) == 2:

        move_score = 60

    elif len(moves) == 1:

        move_score = 40

    score += move_score

    # -----------------------------
    # Normalize
    # -----------------------------

    score = round(

        score / 5,

        1

    )

    score = max(

        0,

        min(score,100)

    )

    if score >= 95:

        rating = "★★★★★"

    elif score >= 85:

        rating = "★★★★☆"

    elif score >= 70:

        rating = "★★★☆☆"

    elif score >= 55:

        rating = "★★☆☆☆"

    else:

        rating = "★☆☆☆☆"

    return {

        "score": score,

        "rating": rating

    }