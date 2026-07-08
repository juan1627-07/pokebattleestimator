import random
import unittest

from engine.battle_state import create_battle, play_turn
from engine.damage_engine import calculate_move_damage
from engine.type_engine import get_move_multiplier


def profile(name, types, speed, moves, item=None, ability=None):
    return {
        "name": name,
        "types": types,
        "stats": {
            "hp": 80,
            "attack": 100,
            "defense": 90,
            "special-attack": 100,
            "special-defense": 90,
            "speed": speed,
        },
        "ability": ability,
        "item": item,
        "moves": moves,
    }


TACKLE = {
    "name": "tackle", "type": "normal", "power": 40,
    "accuracy": 100, "priority": 0, "damage_class": "physical",
}


class TypeTests(unittest.TestCase):
    def test_dual_type_multiplier_is_for_one_move(self):
        self.assertEqual(get_move_multiplier("fire", ["grass", "steel"]), 4.0)

    def test_immunity(self):
        self.assertEqual(get_move_multiplier("ground", ["flying"]), 0.0)


class DamageTests(unittest.TestCase):
    def test_damage_uses_move_category_power_and_stab(self):
        attacker = profile("Blazer", ["fire"], 100, [])
        defender = profile("Leaf", ["grass"], 50, [])
        move = {
            "name": "flamethrower", "type": "fire", "power": 90,
            "accuracy": 100, "priority": 0, "damage_class": "special",
        }
        result = calculate_move_damage(attacker, defender, move, random_factor=1.0)
        self.assertEqual(result["type_multiplier"], 2.0)
        self.assertEqual(result["stab"], 1.5)
        self.assertGreater(result["damage"], 0)


class BattleStateTests(unittest.TestCase):
    def test_faster_pokemon_moves_first_and_hp_changes(self):
        fast = profile("Fast", ["normal"], 120, [TACKLE])
        slow = profile("Slow", ["normal"], 60, [TACKLE])
        state = create_battle(fast, slow)
        result = play_turn(state, "tackle", "tackle", rng=random.Random(1))
        self.assertEqual(result["log"][0]["actor"], "user")
        self.assertLess(result["opponent"]["current_hp"], result["opponent"]["max_hp"])

    def test_equal_priority_and_speed_uses_stable_tie_break(self):
        user = profile("User", ["normal"], 100, [TACKLE])
        opponent = profile("Opponent", ["normal"], 100, [TACKLE])
        state = create_battle(user, opponent)
        result = play_turn(state, "tackle", "tackle", rng=random.Random(9))
        self.assertEqual(result["log"][0]["actor"], "user")

    def test_recharge_move_skips_next_action(self):
        hyper_beam = {
            "name": "hyper-beam", "type": "normal", "power": 150,
            "accuracy": 100, "priority": 0, "damage_class": "special",
            "pp": 5,
        }
        user = profile("User", ["normal"], 120, [hyper_beam, TACKLE])
        opponent = profile("Opponent", ["normal"], 60, [TACKLE])
        state = create_battle(user, opponent)
        play_turn(state, "hyper-beam", "tackle", rng=random.Random(10))
        result = play_turn(state, "tackle", "tackle", rng=random.Random(11))
        self.assertTrue(any("must recharge" in entry["message"] for entry in result["log"]))

    def test_move_pp_decrements_and_zero_pp_is_rejected(self):
        one_pp_tackle = dict(TACKLE, pp=1)
        user = profile("User", ["normal"], 120, [one_pp_tackle])
        opponent = profile("Opponent", ["normal"], 60, [TACKLE])
        state = create_battle(user, opponent)
        play_turn(state, "tackle", "tackle", rng=random.Random(12))
        self.assertEqual(state["user"]["moves"][0]["current_pp"], 0)
        with self.assertRaises(ValueError):
            play_turn(state, "tackle", "tackle", rng=random.Random(13))

    def test_sitrus_berry_is_consumed_below_half_hp(self):
        fast = profile("Fast", ["normal"], 120, [TACKLE], item="Sitrus Berry")
        slow = profile("Slow", ["normal"], 60, [TACKLE])
        state = create_battle(fast, slow)
        state["user"]["current_hp"] = max(1, state["user"]["max_hp"] // 2 - 1)
        result = play_turn(state, "tackle", "tackle", rng=random.Random(2))
        self.assertTrue(result["user"]["item_consumed"])

    def test_status_move_sets_major_status(self):
        thunder_wave = {
            "name": "thunder-wave", "type": "electric", "power": None,
            "accuracy": 100, "priority": 0, "damage_class": "status",
        }
        user = profile("User", ["electric"], 120, [thunder_wave])
        opponent = profile("Opponent", ["normal"], 60, [TACKLE])
        state = create_battle(user, opponent)
        result = play_turn(state, "thunder-wave", "tackle", rng=random.Random(3))
        self.assertEqual(result["opponent"]["status"], "paralyzed")

    def test_unsupported_status_move_has_player_facing_log(self):
        splash = {
            "name": "splash", "type": "normal", "power": None,
            "accuracy": 100, "priority": 0, "damage_class": "status",
        }
        user = profile("User", ["normal"], 120, [splash])
        opponent = profile("Opponent", ["normal"], 60, [TACKLE])
        state = create_battle(user, opponent)
        result = play_turn(state, "splash", "tackle", rng=random.Random(17))
        messages = [entry["message"] for entry in result["log"]]
        self.assertTrue(any("but nothing happened" in message for message in messages))
        self.assertFalse(any("no supported effect" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
