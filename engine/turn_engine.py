# ============================================
# Turn Engine
# ============================================

def calculate_turns(user_profile,
                    opponent_profile,
                    user_damage,
                    opponent_damage):

    """
    Calculates the estimated number of turns
    required for each Pokémon to KO the other.

    Lower is better.
    """

    user_hp = user_profile["stats"]["hp"]

    opponent_hp = opponent_profile["stats"]["hp"]

    user_turns = opponent_hp / max(
        user_damage["damage"],
        1
    )

    opponent_turns = user_hp / max(
        opponent_damage["damage"],
        1
    )

    return {

        "user_turns": round(user_turns,2),

        "opponent_turns": round(opponent_turns,2)

    }