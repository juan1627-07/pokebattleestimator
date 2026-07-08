import random
import unittest

from engine.team_battle import create_team_battle, play_team_turn, switch_team_member


MOVE = {
    "name": "tackle", "type": "normal", "power": 40,
    "accuracy": 100, "priority": 0, "damage_class": "physical",
}

KO_MOVE = {
    "name": "mega-punch", "type": "normal", "power": 250,
    "accuracy": 100, "priority": 0, "damage_class": "physical",
}


def member(index, speed=80):
    return {
        "name": f"Pokemon {index}", "types": ["normal"],
        "stats": {"hp": 70, "attack": 90, "defense": 80,
                  "special-attack": 70, "special-defense": 80, "speed": speed},
        "ability": None, "item": None, "moves": [dict(MOVE)],
        "image": None, "front_image": None, "back_image": None,
    }


class TeamBattleTests(unittest.TestCase):
    def setUp(self):
        self.users = [member(i, 100) for i in range(1, 7)]
        self.opponents = [member(i, 50) for i in range(7, 13)]

    def test_battle_starts_with_six_members_per_team(self):
        state = create_team_battle(self.users, self.opponents)
        self.assertEqual(len(state["user_team"]), 6)
        self.assertEqual(len(state["opponent_team"]), 6)
        self.assertEqual(state["user"]["name"], "Pokemon 1")

    def test_voluntary_switch_consumes_turn_and_opponent_still_attacks(self):
        state = create_team_battle(self.users, self.opponents)
        original_hp = state["user_team"][0]["current_hp"]
        play_team_turn(state, user_switch=1, opponent_move="tackle", rng=random.Random(4))
        self.assertEqual(state["user_active"], 1)
        self.assertEqual(state["user_team"][0]["current_hp"], original_hp)
        self.assertLess(state["user"]["current_hp"], state["user"]["max_hp"])
        self.assertEqual(state["turn"], 1)
        self.assertEqual(state["log"][0]["actor"], "user")
        self.assertEqual(state["log"][0]["switch"], 1)

    def test_fainted_user_must_choose_a_replacement(self):
        state = create_team_battle(self.users, self.opponents)
        state["user"]["current_hp"] = 1
        play_team_turn(state, user_move="tackle", opponent_move="tackle", rng=random.Random(5))
        self.assertEqual(state["status"], "awaiting_user_switch")
        switch_team_member(state, "user", 2)
        self.assertEqual(state["status"], "active")
        self.assertEqual(state["user_active"], 2)

    def test_opponent_automatically_sends_next_healthy_member(self):
        state = create_team_battle(self.users, self.opponents)
        state["opponent"]["current_hp"] = 1
        play_team_turn(state, user_move="tackle", opponent_move="tackle", rng=random.Random(6))
        self.assertEqual(state["opponent_active"], 1)
        self.assertEqual(state["status"], "active")

    def test_faint_stops_remaining_action_queue_before_forced_replacement(self):
        self.users[0]["moves"] = [dict(KO_MOVE)]
        state = create_team_battle(self.users, self.opponents)
        state["opponent"]["current_hp"] = 1
        play_team_turn(state, user_move="mega-punch", opponent_move="tackle", rng=random.Random(14))
        self.assertEqual(state["opponent_active"], 1)
        self.assertEqual(state["status"], "active")
        self.assertFalse(any(entry.get("actor") == "opponent" and entry.get("move") == "tackle" for entry in state["log"]))

    def test_forced_replacement_does_not_consume_an_extra_turn(self):
        state = create_team_battle(self.users, self.opponents)
        state["user"]["current_hp"] = 1
        play_team_turn(state, user_move="tackle", opponent_move="tackle", rng=random.Random(15))
        forced_turn = state["turn"]
        self.assertEqual(state["status"], "awaiting_user_switch")
        play_team_turn(state, user_switch=2, rng=random.Random(16))
        self.assertEqual(state["turn"], forced_turn)
        self.assertEqual(state["status"], "active")
        self.assertEqual(state["user_active"], 2)

    def test_opponent_can_choose_a_strategic_switch_before_the_attack(self):
        state = create_team_battle(self.users, self.opponents)
        original_hp = state["opponent_team"][0]["current_hp"]
        play_team_turn(
            state,
            user_move="tackle",
            opponent_switch=1,
            rng=random.Random(8),
        )
        self.assertEqual(state["opponent_active"], 1)
        self.assertEqual(state["opponent_team"][0]["current_hp"], original_hp)
        self.assertLess(state["opponent"]["current_hp"], state["opponent"]["max_hp"])

    def test_victory_requires_all_six_opponents_to_faint(self):
        state = create_team_battle(self.users, self.opponents)
        for side in state["opponent_team"]:
            side["current_hp"] = 0
        state["opponent"]["current_hp"] = 1
        play_team_turn(state, user_move="tackle", opponent_move="tackle", rng=random.Random(7))
        self.assertEqual(state["status"], "finished")
        self.assertEqual(state["winner"], "user")


if __name__ == "__main__":
    unittest.main()
