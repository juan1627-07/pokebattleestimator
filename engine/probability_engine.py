# ============================================
# Probability Engine
# ============================================

def calculate_win_probability(user,
                              opponent,
                              turns):

    """
    Converts Turns-To-KO into
    a smooth probability.

    Returns 0-100%.
    """

    user_turns = turns["user_turns"]

    opponent_turns = turns["opponent_turns"]

    total = user_turns + opponent_turns

    if total <= 0:

        return 50

    probability = (

        opponent_turns /

        total

    ) * 100

    probability = max(

        0,

        min(

            probability,

            100

        )

    )

    return round(probability)