"""Level-based move damage calculations for the interactive battle engine."""

import math
import random

from engine.type_engine import get_move_multiplier


def calculated_stat(base, level=50, hp=False, iv=31, ev=0):
    core = math.floor(((2 * base + iv + math.floor(ev / 4)) * level) / 100)
    return core + level + 10 if hp else core + 5


def _name(value):
    if isinstance(value, dict):
        value = value.get("name")
    return str(value or "").lower().replace(" ", "-")


def _stage_multiplier(stage):
    return (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)


def calculate_move_damage(attacker, defender, move, random_factor=None, level=50):
    category = move.get("damage_class", "status")
    power = move.get("power") or 0
    move_type = move.get("type", "normal")
    multiplier = get_move_multiplier(move_type, defender.get("types", []), defender.get("ability"))

    if category not in {"physical", "special"} or power <= 0 or multiplier == 0:
        return {
            "damage": 0, "min_damage": 0, "max_damage": 0,
            "type_multiplier": multiplier, "stab": 1.0,
            "category": category, "critical": False,
        }

    attack_key = "attack" if category == "physical" else "special-attack"
    defense_key = "defense" if category == "physical" else "special-defense"
    attack = calculated_stat(attacker["stats"][attack_key], level)
    defense = calculated_stat(defender["stats"][defense_key], level)
    attack *= _stage_multiplier(attacker.get("stages", {}).get(attack_key, 0))
    defense *= _stage_multiplier(defender.get("stages", {}).get(defense_key, 0))

    if category == "physical" and attacker.get("status") == "burned" and _name(attacker.get("ability")) != "guts":
        attack *= 0.5
    if category == "physical" and _name(attacker.get("ability")) == "huge-power":
        attack *= 2
    if category == "special" and _name(defender.get("item")) == "assault-vest":
        defense *= 1.5

    item = _name(attacker.get("item"))
    if category == "physical" and item == "choice-band":
        attack *= 1.5
    if category == "special" and item == "choice-specs":
        attack *= 1.5

    base = math.floor(math.floor(math.floor((2 * level / 5) + 2) * power * attack / max(defense, 1)) / 50) + 2
    stab = 1.0
    if move_type in attacker.get("types", []):
        stab = 2.0 if _name(attacker.get("ability")) == "adaptability" else 1.5

    modifier = stab * multiplier
    if item == "life-orb":
        modifier *= 1.3
    if item == "expert-belt" and multiplier > 1:
        modifier *= 1.2
    if _name(defender.get("ability")) == "multiscale" and defender.get("current_hp") == defender.get("max_hp"):
        modifier *= 0.5
    if _name(defender.get("ability")) == "wonder-guard" and multiplier <= 1:
        modifier = 0

    minimum = max(1, math.floor(base * modifier * 0.85)) if modifier else 0
    maximum = max(1, math.floor(base * modifier)) if modifier else 0
    factor = random_factor if random_factor is not None else random.uniform(0.85, 1.0)
    damage = max(1, math.floor(base * modifier * factor)) if modifier else 0
    return {
        "damage": damage, "min_damage": minimum, "max_damage": maximum,
        "type_multiplier": multiplier, "stab": stab,
        "category": category, "critical": False,
    }


def calculate_damage(attacker, defender, type_multiplier):
    """Legacy estimator retained for the existing matchup response."""
    offense = attacker["battle_stats"]["offense_stat"]
    target = attacker["battle_stats"]["target_defense"]
    defense = defender["stats"].get(target, 1)
    damage = max(1, (offense * type_multiplier) / max(defense, 1))
    return {"offense": offense, "defense": defense, "type_multiplier": type_multiplier, "damage": round(damage, 2)}
