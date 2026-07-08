from engine.type_engine import get_type_multiplier
from engine.damage_engine import calculate_damage, calculate_move_damage
from engine.turn_engine import calculate_turns
from engine.winner_engine import determine_winner
from engine.probability_engine import (
    calculate_win_probability
)


# ============================================
# Battle Engine
# ============================================

def evaluate_matchup(user, opponent):

    user_moves = [move for move in user.get("moves", []) if isinstance(move, dict)]
    opponent_moves = [move for move in opponent.get("moves", []) if isinstance(move, dict)]

    if user_moves and opponent_moves:
        user_results = [(calculate_move_damage(user, opponent, move, random_factor=0.925), move) for move in user_moves]
        opponent_results = [(calculate_move_damage(opponent, user, move, random_factor=0.925), move) for move in opponent_moves]
        user_damage, user_move = max(user_results, key=lambda pair: pair[0]["damage"])
        opponent_damage, opponent_move = max(opponent_results, key=lambda pair: pair[0]["damage"])
        user_multiplier = user_damage["type_multiplier"]
        opponent_multiplier = opponent_damage["type_multiplier"]
    else:
        user_move = opponent_move = None

        user_multiplier = get_type_multiplier(
            user["types"],
            opponent["types"]
        )

        opponent_multiplier = get_type_multiplier(
            opponent["types"],
            user["types"]
        )

        user_damage = calculate_damage(
            user,
            opponent,
            user_multiplier
        )

        opponent_damage = calculate_damage(
            opponent,
            user,
            opponent_multiplier
        )

    turns = calculate_turns(

        user,

        opponent,

        user_damage,

        opponent_damage

    )

    winner = determine_winner(

        user,

        opponent,

        turns

    )

    win_probability = calculate_win_probability(

        user,

        opponent,

        turns

    )

    return {

        "user_multiplier": user_multiplier,

        "opponent_multiplier": opponent_multiplier,

        "user_damage": user_damage,

        "opponent_damage": opponent_damage,

        "user_move": user_move,

        "opponent_move": opponent_move,

        "turns": turns,

        "winner": winner,

        "win_probability": win_probability

    }
