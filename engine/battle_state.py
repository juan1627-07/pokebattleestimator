"""Serializable one-on-one battle state and turn resolution."""

import copy
import random

from engine.damage_engine import calculate_move_damage, calculated_stat
from engine.type_engine import get_move_multiplier


STATUS_MOVES = {
    "thunder-wave": "paralyzed",
    "will-o-wisp": "burned",
    "toxic": "badly-poisoned",
    "poison-powder": "poisoned",
    "spore": "asleep",
    "sleep-powder": "asleep",
    "hypnosis": "asleep",
}
RECOVERY_MOVES = {
    "recover", "roost", "soft-boiled", "slack-off", "milk-drink",
    "morning-sun", "synthesis", "moonlight", "shore-up", "heal-order",
}
SETUP_MOVES = {
    "swords-dance": ("attack", 2),
    "nasty-plot": ("special-attack", 2),
    "dragon-dance": ("attack", 1, "speed", 1),
    "calm-mind": ("special-attack", 1, "special-defense", 1),
    "bulk-up": ("attack", 1, "defense", 1),
    "agility": ("speed", 2),
    "quiver-dance": ("special-attack", 1, "special-defense", 1, "speed", 1),
    "shell-smash": ("attack", 2, "special-attack", 2, "speed", 2, "defense", -1, "special-defense", -1),
    "iron-defense": ("defense", 2),
    "amnesia": ("special-defense", 2),
    "work-up": ("attack", 1, "special-attack", 1),
    "coil": ("attack", 1, "defense", 1),
}
DEBUFF_MOVES = {
    "growl": ("attack", -1), "charm": ("attack", -2),
    "leer": ("defense", -1), "tail-whip": ("defense", -1),
    "screech": ("defense", -2), "fake-tears": ("special-defense", -2),
    "metal-sound": ("special-defense", -2), "scary-face": ("speed", -2),
}
HAZARD_MOVES = {"stealth-rock", "spikes", "toxic-spikes"}
CONSUMABLE_ITEMS = {
    "potion": {"label": "Potion", "hp": 20},
    "super-potion": {"label": "Super Potion", "hp": 60},
    "hyper-potion": {"label": "Hyper Potion", "hp": 120},
    "max-potion": {"label": "Max Potion", "full_hp": True},
    "full-restore": {"label": "Full Restore", "full_hp": True, "cure_status": True},
    "ether": {"label": "Ether", "pp": 10},
    "max-ether": {"label": "Max Ether", "full_pp": True},
    "elixir": {"label": "Elixir", "pp": 10, "all_moves": True},
    "max-elixir": {"label": "Max Elixir", "full_pp": True, "all_moves": True},
    "pp-up": {"label": "PP Up", "pp_up": True},
    "antidote": {"label": "Antidote", "statuses": {"poisoned", "badly-poisoned"}},
    "full-heal": {"label": "Full Heal", "cure_status": True},
}
DEFAULT_INVENTORY = {name: 2 for name in CONSUMABLE_ITEMS}
RECHARGE_MOVES = {"hyper-beam", "blast-burn", "hydro-cannon", "frenzy-plant", "giga-impact"}
BATTLEFIELD_THEMES = [
    "field-cyber-arena",
    "field-neo-forest",
    "field-volcanic-fissure",
    "field-fractured-glacier",
    "field-desert-wasteland",
]
BATTLE_LEVEL = 100
STRUGGLE_MOVE = {
    "name": "struggle", "type": "normal", "power": 50,
    "accuracy": 100, "priority": 0, "damage_class": "physical",
}
FIELD_CONDITION_MOVES = {
    "rain-dance": ("stream", {"duration": 5, "water_multiplier": 1.5, "fire_multiplier": 0.5}),
    "sunny-day": ("harsh-sun", {"duration": 5, "fire_multiplier": 1.5, "water_multiplier": 0.5}),
    "sandstorm": ("sandstorm", {"duration": 5, "residual": 1 / 16, "immune_types": ["rock", "ground", "steel"]}),
    "hail": ("snow", {"duration": 5, "residual": 1 / 16, "immune_types": ["ice"]}),
    "snowscape": ("snow", {"duration": 5, "speed_multiplier": 0.5, "affected_types": ["dragon", "flying", "grass", "ground"]}),
}


def _slug(value):
    if isinstance(value, dict):
        value = value.get("name")
    return str(value or "").strip().lower().replace(" ", "-")


def _display(value):
    return _slug(value).replace("-", " ").title()


def _side(profile):
    side = copy.deepcopy(profile)
    side["ability"] = profile.get("ability")
    side["item"] = profile.get("item")
    side["moves"] = [copy.deepcopy(move) for move in profile.get("moves", []) if isinstance(move, dict)]
    side["level"] = BATTLE_LEVEL
    side["max_hp"] = calculated_stat(profile["stats"]["hp"], level=BATTLE_LEVEL, hp=True)
    side["current_hp"] = side["max_hp"]
    side["status"] = None
    side["sleep_turns"] = 0
    side["stages"] = {key: 0 for key in ("attack", "defense", "special-attack", "special-defense", "speed")}
    side["item_consumed"] = False
    side["choice_lock"] = None
    side["protected"] = False
    side["recharging"] = False
    for move in side["moves"]:
        if isinstance(move.get("pp"), int):
            move.setdefault("current_pp", move["pp"])
    return side


def create_battle(user, opponent):
    state = {
        "turn": 0,
        "status": "active",
        "winner": None,
        "user": _side(user),
        "opponent": _side(opponent),
        "field_theme": random.choice(BATTLEFIELD_THEMES),
        "field_conditions": {},
        "hazards": {"user": {"stealth-rock": 0, "spikes": 0, "toxic-spikes": 0}, "opponent": {"stealth-rock": 0, "spikes": 0, "toxic-spikes": 0}},
        "hazard_durations": {"user": {}, "opponent": {}},
        "inventory": {"user": copy.deepcopy(DEFAULT_INVENTORY), "opponent": copy.deepcopy(DEFAULT_INVENTORY)},
        "log": [],
    }
    for actor, target in (("user", "opponent"), ("opponent", "user")):
        if _slug(state[actor].get("ability")) == "intimidate":
            state[target]["stages"]["attack"] = -1
            state["log"].append({"actor": actor, "message": f"{state[actor]['name']}'s Intimidate lowered Attack!"})
    return state


def _move(side, move_name):
    wanted = _slug(move_name)
    if wanted == "struggle" and _all_real_moves_out_of_pp(side):
        return copy.deepcopy(STRUGGLE_MOVE)
    for move in side["moves"]:
        if _slug(move.get("name")) == wanted:
            if isinstance(move.get("current_pp"), int) and move["current_pp"] <= 0:
                raise ValueError(f"{_display(move_name)} has no PP left.")
            return move
    raise ValueError(f"Move '{move_name}' is not available.")


def _all_real_moves_out_of_pp(side):
    moves = side.get("moves", [])
    pp_tracked = [move for move in moves if isinstance(move.get("current_pp"), int)]
    return bool(pp_tracked) and all(move.get("current_pp", 0) <= 0 for move in pp_tracked)


def _stage_multiplier(stage):
    return (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)


def _effective_speed(side, field_conditions=None, actor=None):
    speed = calculated_stat(side["stats"]["speed"], level=side.get("level", BATTLE_LEVEL))
    speed *= _stage_multiplier(side["stages"]["speed"])
    if side["status"] == "paralyzed":
        speed *= 0.5
    if _slug(side.get("item")) == "choice-scarf":
        speed *= 1.5
    for condition in (field_conditions or {}).values():
        payload = condition.get("payload", {})
        affected_types = payload.get("affected_types")
        if payload.get("speed_multiplier") and (
            not affected_types or any(t in side.get("types", []) for t in affected_types)
        ):
            speed *= payload["speed_multiplier"]
    return speed


def _action_sort_key(action):
    actor = action["actor"]
    actor_order = 1 if actor == "user" else 0
    return (action.get("priority", 0), action.get("speed", 0), actor_order)


def _ordered_actions(actions):
    return sorted(actions, key=_action_sort_key, reverse=True)


def _can_move(side, actor, rng, log):
    if side.get("recharging"):
        side["recharging"] = False
        log.append({"actor": actor, "message": f"{side['name']} must recharge."})
        return False
    if side["status"] == "asleep":
        if side["sleep_turns"] > 0:
            side["sleep_turns"] -= 1
            log.append({"actor": actor, "message": f"{side['name']} is asleep."})
            return False
        side["status"] = None
        log.append({"actor": actor, "message": f"{side['name']} woke up!"})
    if side["status"] == "paralyzed" and rng.random() < 0.25:
        log.append({"actor": actor, "message": f"{side['name']} is fully paralyzed!"})
        return False
    return True


def _ensure_hazards(state):
    state.setdefault("hazards", {
        "user": {"stealth-rock": 0, "spikes": 0, "toxic-spikes": 0},
        "opponent": {"stealth-rock": 0, "spikes": 0, "toxic-spikes": 0},
    })
    state.setdefault("hazard_durations", {"user": {}, "opponent": {}})


def _status_action(state, actor_side, target_side, actor, move, rng, log):
    name = _slug(move["name"])
    target = "opponent" if actor == "user" else "user"
    if name in FIELD_CONDITION_MOVES:
        condition_name, payload = FIELD_CONDITION_MOVES[name]
        conditions = state.setdefault("field_conditions", {})
        conditions[condition_name] = {"duration": payload.get("duration", 5), "payload": copy.deepcopy(payload)}
        log.append({"actor": actor, "move": move["name"], "hazard": condition_name, "message": f"{actor_side['name']} changed the battlefield to {_display(condition_name)}!"})
        return
    if name in HAZARD_MOVES:
        _ensure_hazards(state)
        limits = {"stealth-rock": 1, "spikes": 3, "toxic-spikes": 2}
        current = state["hazards"][target].get(name, 0)
        if current >= limits[name]:
            log.append({"actor": actor, "move": move["name"], "message": f"{_display(name)} is already set."})
            return
        state["hazards"][target][name] = current + 1
        state["hazard_durations"].setdefault(target, {})[name] = 5
        log.append({"actor": actor, "move": move["name"], "hazard": name, "message": f"{actor_side['name']} scattered {_display(name)} on the opposing side!"})
        return
    if name == "protect":
        actor_side["protected"] = True
        log.append({"actor": actor, "move": move["name"], "message": f"{actor_side['name']} protected itself."})
        return
    if name in RECOVERY_MOVES:
        healed = min(actor_side["max_hp"] - actor_side["current_hp"], actor_side["max_hp"] // 2)
        actor_side["current_hp"] += healed
        log.append({"actor": actor, "move": move["name"], "healing": healed, "message": f"{actor_side['name']} restored {healed} HP."})
        return
    if name in SETUP_MOVES:
        changes = SETUP_MOVES[name]
        for index in range(0, len(changes), 2):
            stat, amount = changes[index], changes[index + 1]
            actor_side["stages"][stat] = max(-6, min(6, actor_side["stages"][stat] + amount))
        log.append({"actor": actor, "move": move["name"], "message": f"{actor_side['name']}'s stats rose!"})
        return
    if name in DEBUFF_MOVES:
        changes = DEBUFF_MOVES[name]
        for index in range(0, len(changes), 2):
            stat, amount = changes[index], changes[index + 1]
            target_side["stages"][stat] = max(-6, min(6, target_side["stages"][stat] + amount))
        log.append({"actor": actor, "move": move["name"], "message": f"{target_side['name']}'s stats fell!"})
        return
    status = STATUS_MOVES.get(name)
    if status and not target_side["status"]:
        if get_move_multiplier(move.get("type", "normal"), target_side["types"], target_side.get("ability")) == 0:
            log.append({"actor": actor, "move": move["name"], "message": "It had no effect."})
            return
        target_side["status"] = status
        if status == "asleep":
            target_side["sleep_turns"] = rng.randint(1, 3)
        log.append({"actor": actor, "move": move["name"], "status": status, "message": f"{target_side['name']} was {status}!"})
        return
    log.append({"actor": actor, "move": move["name"], "message": f"{actor_side['name']} used {_display(move['name'])}, but nothing happened."})


def _field_damage_multiplier(state, move):
    move_type = _slug(move.get("type"))
    multiplier = 1.0
    for condition in state.get("field_conditions", {}).values():
        payload = condition.get("payload", {})
        multiplier *= payload.get(f"{move_type}_multiplier", 1.0)
    return multiplier


def _attack(state, actor_side, target_side, actor, move, rng, log):
    log.append({"actor": actor, "move": move["name"], "message": f"{actor_side['name']} used {_display(move['name'])}!"})
    if target_side["protected"]:
        log.append({"actor": actor, "message": f"{target_side['name']} protected itself."})
        return
    accuracy = move.get("accuracy")
    if accuracy is not None and rng.uniform(0, 100) > accuracy:
        log.append({"actor": actor, "message": f"{actor_side['name']}'s attack missed!"})
        return

    roll = rng.uniform(0.85, 1.0)
    result = calculate_move_damage(actor_side, target_side, move, random_factor=roll)
    damage = result["damage"]
    field_multiplier = _field_damage_multiplier(state, move)
    if damage and field_multiplier != 1:
        damage = max(1, int(damage * field_multiplier))
        result["damage"] = damage
    if damage >= target_side["current_hp"] and target_side["current_hp"] == target_side["max_hp"]:
        ability = _slug(target_side.get("ability"))
        item = _slug(target_side.get("item"))
        if ability == "sturdy" or (item == "focus-sash" and not target_side["item_consumed"]):
            damage = target_side["current_hp"] - 1
            if item == "focus-sash":
                target_side["item_consumed"] = True
    target_side["current_hp"] = max(0, target_side["current_hp"] - damage)
    message = f"{target_side['name']} took {damage} damage." if damage else f"{target_side['name']} took no damage."
    if result["type_multiplier"] > 1:
        message += " It's super effective!"
    elif 0 < result["type_multiplier"] < 1:
        message += " It's not very effective."
    elif result["type_multiplier"] == 0:
        message += " It had no effect."
    log.append({"actor": actor, **result, "damage": damage, "message": message})

    if damage and _slug(actor_side.get("item")) == "life-orb":
        recoil = max(1, actor_side["max_hp"] // 10)
        actor_side["current_hp"] = max(0, actor_side["current_hp"] - recoil)
        log.append({"actor": actor, "damage": recoil, "message": f"{actor_side['name']} lost {recoil} HP from Life Orb."})
    if _slug(move.get("name")) in RECHARGE_MOVES and actor_side["current_hp"] > 0:
        actor_side["recharging"] = True


def _apply_field_damage(state, side, actor, log):
    if side["current_hp"] <= 0:
        return
    for name, condition in state.get("field_conditions", {}).items():
        payload = condition.get("payload", {})
        residual = payload.get("residual")
        immune_types = payload.get("immune_types", set())
        if residual and not any(t in side.get("types", []) for t in immune_types):
            damage = max(1, int(side["max_hp"] * residual))
            side["current_hp"] = max(0, side["current_hp"] - damage)
            log.append({"actor": actor, "damage": damage, "hazard": name, "message": f"{side['name']} took {damage} damage from {_display(name)}."})


def _tick_field_conditions(state, log):
    expired = []
    for name, condition in state.get("field_conditions", {}).items():
        condition["duration"] = max(0, condition.get("duration", 0) - 1)
        if condition["duration"] <= 0:
            expired.append(name)
    for name in expired:
        state["field_conditions"].pop(name, None)
        log.append({"hazard": name, "message": f"The {_display(name)} faded."})


def _tick_hazards(state, log):
    """Decay entry hazards in the same clear-state phase as weather."""
    _ensure_hazards(state)
    for target, durations in state["hazard_durations"].items():
        expired = []
        for name, duration in list(durations.items()):
            durations[name] = max(0, duration - 1)
            if durations[name] == 0:
                expired.append(name)
        for name in expired:
            state["hazards"][target][name] = 0
            durations.pop(name, None)
            log.append({"hazard": name, "message": f"The {_display(name)} on {target}'s side cleared."})


def apply_consumable(state, item_name, actor="user", move_name=None):
    """Apply a battle item to the actor's active Pokemon and consume one charge."""
    item_key = _slug(item_name)
    item = CONSUMABLE_ITEMS.get(item_key)
    if not item:
        raise ValueError("That item is not available.")
    inventories = state.setdefault("inventory", {"user": copy.deepcopy(DEFAULT_INVENTORY), "opponent": copy.deepcopy(DEFAULT_INVENTORY)})
    # Upgrade states created before per-player inventories were introduced.
    if item_key in inventories:
        inventories = {"user": inventories, "opponent": copy.deepcopy(DEFAULT_INVENTORY)}
        state["inventory"] = inventories
    inventory = inventories.setdefault(actor, copy.deepcopy(DEFAULT_INVENTORY))
    if inventory.get(item_key, 0) <= 0:
        raise ValueError(f"No {item['label']} remaining.")
    side = state[actor]
    healed = 0
    restored_pp = 0
    if item.get("full_hp"):
        healed = side["max_hp"] - side["current_hp"]
        side["current_hp"] = side["max_hp"]
    elif item.get("hp"):
        healed = min(item["hp"], side["max_hp"] - side["current_hp"])
        side["current_hp"] += healed
    cured = bool(side.get("status") and (item.get("cure_status") or side.get("status") in item.get("statuses", set())))
    if cured:
        side["status"] = None
        side["sleep_turns"] = 0
    if item.get("pp") or item.get("full_pp") or item.get("pp_up"):
        moves = side.get("moves", [])
        if not item.get("all_moves"):
            wanted = _slug(move_name) if move_name else None
            moves = [move for move in moves if not wanted or _slug(move.get("name")) == wanted][:1]
            if not moves:
                moves = side.get("moves", [])[:1]
        for move in moves:
            maximum = move.get("pp")
            if isinstance(maximum, int):
                before = move.get("current_pp", maximum)
                if item.get("pp_up"):
                    move["pp"] = max(maximum + 1, int(maximum * 1.2))
                    maximum = move["pp"]
                    move["current_pp"] = min(maximum, before + 1)
                else:
                    move["current_pp"] = maximum if item.get("full_pp") else min(maximum, before + item["pp"])
                restored_pp += move["current_pp"] - before
    if not healed and not restored_pp and not cured:
        raise ValueError("This item would have no effect.")
    inventory[item_key] -= 1
    state["log"] = [{"actor": actor, "healing": healed, "item": item_key, "message": f"{side['name']} used {item['label']}."}]
    return state


def _end_of_turn(state, side, actor, log):
    if side["current_hp"] <= 0:
        return
    _apply_field_damage(state, side, actor, log)
    if side["current_hp"] <= 0:
        return
    if side["status"] in {"burned", "poisoned", "badly-poisoned"}:
        damage = max(1, side["max_hp"] // 8)
        side["current_hp"] = max(0, side["current_hp"] - damage)
        log.append({"actor": actor, "damage": damage, "message": f"{side['name']} took {damage} status damage."})
    item = _slug(side.get("item"))
    if item == "leftovers" and side["current_hp"]:
        healing = min(max(1, side["max_hp"] // 16), side["max_hp"] - side["current_hp"])
        side["current_hp"] += healing
        if healing:
            log.append({"actor": actor, "healing": healing, "message": f"{side['name']} restored {healing} HP with Leftovers."})
    if item == "sitrus-berry" and not side["item_consumed"] and 0 < side["current_hp"] <= side["max_hp"] // 2:
        healing = min(max(1, side["max_hp"] // 4), side["max_hp"] - side["current_hp"])
        side["current_hp"] += healing
        side["item_consumed"] = True
        log.append({"actor": actor, "healing": healing, "message": f"{side['name']} ate its Sitrus Berry and restored {healing} HP."})


def _finish(state):
    user_alive = state["user"]["current_hp"] > 0
    opponent_alive = state["opponent"]["current_hp"] > 0
    if user_alive and opponent_alive:
        return
    state["status"] = "finished"
    state["winner"] = "user" if user_alive else "opponent" if opponent_alive else "tie"


def play_turn(state, user_move=None, opponent_move=None, rng=None, skip_actors=None):
    if state.get("status") != "active":
        raise ValueError("This battle is already finished.")
    rng = rng or random.Random()
    state["turn"] += 1
    state["log"] = []
    state["user"]["protected"] = False
    state["opponent"]["protected"] = False
    skip_actors = set(skip_actors or [])
    selected = {}
    if "user" not in skip_actors:
        selected["user"] = _move(state["user"], user_move)
    if "opponent" not in skip_actors:
        selected["opponent"] = _move(state["opponent"], opponent_move)
    order = [
        action["actor"] for action in _ordered_actions([
            {
                "actor": actor,
                "priority": selected[actor].get("priority", 0),
                "speed": _effective_speed(state[actor], state.get("field_conditions"), actor),
            }
            for actor in selected
        ])
    ]

    for actor in order:
        target = "opponent" if actor == "user" else "user"
        actor_side, target_side = state[actor], state[target]
        if actor_side["current_hp"] <= 0 or not _can_move(actor_side, actor, rng, state["log"]):
            continue
        move = selected[actor]
        if isinstance(move.get("current_pp"), int):
            move["current_pp"] = max(0, move["current_pp"] - 1)
        if move.get("damage_class") == "status" or not move.get("power"):
            _status_action(state, actor_side, target_side, actor, move, rng, state["log"])
        else:
            _attack(state, actor_side, target_side, actor, move, rng, state["log"])
        _finish(state)
        if state["status"] == "finished":
            break

    if state["status"] == "active":
        _end_of_turn(state, state["user"], "user", state["log"])
        _end_of_turn(state, state["opponent"], "opponent", state["log"])
        _tick_field_conditions(state, state["log"])
        _tick_hazards(state, state["log"])
        _finish(state)
    return state
