# ============================================
# Winner Engine
# ============================================

def determine_winner(user,
                     opponent,
                     turns):

    user_turns = turns["user_turns"]

    opponent_turns = turns["opponent_turns"]

    if user_turns < opponent_turns:

        return {

            "winner":user["name"],

            "reason":"Lower Turns-To-KO"

        }

    if opponent_turns < user_turns:

        return {

            "winner":opponent["name"],

            "reason":"Lower Turns-To-KO"

        }

    user_speed = user["battle_stats"]["speed"]

    opponent_speed = opponent["battle_stats"]["speed"]

    if user_speed > opponent_speed:

        return {

            "winner":user["name"],

            "reason":"Speed Tie Breaker"

        }

    if opponent_speed > user_speed:

        return {

            "winner":opponent["name"],

            "reason":"Speed Tie Breaker"

        }

    return {

        "winner":"Tie",

        "reason":"Equal Speed"

    }