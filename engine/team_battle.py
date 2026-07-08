"""Six-on-six battle orchestration with persistent party HP and switching."""

import random

from engine.battle_state import _effective_speed, _move, _ordered_actions, _side, _slug, play_turn
from engine.type_engine import get_move_multiplier


def _healthy_indices(state, actor):
    team = state[f"{actor}_team"]
    return [index for index, side in enumerate(team) if side["current_hp"] > 0]


def _reset_stages(side):
    for stat in side.get("stages", {}):
        side["stages"][stat] = 0
    side["protected"] = False
    side["choice_lock"] = None


def _apply_entry_ability(state, actor, log):
    target = "opponent" if actor == "user" else "user"
    side = state[actor]
    if side["current_hp"] > 0 and _slug(side.get("ability")) == "intimidate" and state[target]["current_hp"] > 0:
        stages = state[target]["stages"]
        stages["attack"] = max(-6, stages["attack"] - 1)
        log.append({"actor": actor, "message": f"{side['name']}'s Intimidate lowered {state[target]['name']}'s Attack!"})


def _empty_hazards():
    return {"stealth-rock": 0, "spikes": 0, "toxic-spikes": 0}


def _apply_entry_hazards(state, actor, log):
    side = state[actor]
    if side["current_hp"] <= 0 or _slug(side.get("item")) == "heavy-duty-boots":
        return
    hazards = state.setdefault("hazards", {"user": _empty_hazards(), "opponent": _empty_hazards()})[actor]
    damage = 0
    if hazards.get("stealth-rock"):
        multiplier = get_move_multiplier("rock", side.get("types", []), side.get("ability"))
        damage += max(1, int(side["max_hp"] * multiplier / 8))
    spikes_layers = hazards.get("spikes", 0)
    if spikes_layers and "flying" not in side.get("types", []) and _slug(side.get("ability")) != "levitate":
        damage += max(1, side["max_hp"] * [0, 1, 1, 1][spikes_layers] // [1, 8, 6, 4][spikes_layers])
    if damage:
        side["current_hp"] = max(0, side["current_hp"] - damage)
        log.append({"actor": actor, "damage": damage, "hazard": True, "message": f"{side['name']} took {damage} damage from entry hazards."})
    toxic_layers = hazards.get("toxic-spikes", 0)
    grounded = "flying" not in side.get("types", []) and _slug(side.get("ability")) != "levitate"
    if toxic_layers and grounded and side["current_hp"] > 0 and not side.get("status"):
        if "poison" in side.get("types", []):
            hazards["toxic-spikes"] = 0
            log.append({"actor": actor, "hazard": True, "message": f"{side['name']} absorbed the Toxic Spikes!"})
        elif "steel" not in side.get("types", []):
            side["status"] = "badly-poisoned" if toxic_layers > 1 else "poisoned"
            log.append({"actor": actor, "status": side["status"], "hazard": True, "message": f"{side['name']} was poisoned by Toxic Spikes!"})


def _sync_active(state):
    state["user"] = state["user_team"][state["user_active"]]
    state["opponent"] = state["opponent_team"][state["opponent_active"]]


def create_team_battle(user_profiles, opponent_profiles):
    if not user_profiles or not opponent_profiles:
        raise ValueError("Both teams need at least one Pokemon.")
    state = {
        "mode": "team",
        "turn": 0,
        "status": "active",
        "phase": "PRE_TURN",
        "winner": None,
        "current_actor": "user",
        "user_team": [_side(profile) for profile in user_profiles[:6]],
        "opponent_team": [_side(profile) for profile in opponent_profiles[:6]],
        "user_active": 0,
        "opponent_active": 0,
        "hazards": {"user": _empty_hazards(), "opponent": _empty_hazards()},
        "revealed": {"user": [0], "opponent": [0]},
        "log": [],
        "history": [],
    }
    _sync_active(state)
    _apply_entry_ability(state, "user", state["log"])
    _apply_entry_ability(state, "opponent", state["log"])
    return state


def switch_team_member(state, actor, index, announce=True):
    if actor not in {"user", "opponent"}:
        raise ValueError("Unknown team.")
    team = state[f"{actor}_team"]
    active_key = f"{actor}_active"
    if not isinstance(index, int) or index < 0 or index >= len(team):
        raise ValueError("That team slot does not exist.")
    if index == state[active_key]:
        raise ValueError("That Pokemon is already active.")
    if team[index]["current_hp"] <= 0:
        raise ValueError("A fainted Pokemon cannot battle.")

    outgoing = team[state[active_key]]
    _reset_stages(outgoing)
    state[active_key] = index
    revealed = state.setdefault("revealed", {"user": [state.get("user_active", 0)], "opponent": [state.get("opponent_active", 0)]})
    if index not in revealed.setdefault(actor, []):
        revealed[actor].append(index)
    _sync_active(state)
    state["status"] = "active"
    if announce:
        state["log"].append({"actor": actor, "switch": index, "message": f"{state[actor]['name']}, I choose you!"})
    _apply_entry_hazards(state, actor, state["log"])
    _apply_entry_ability(state, actor, state["log"])
    return state


def _remember_log(state):
    history = state.setdefault("history", [])
    history.extend(state.get("log", []))
    del history[:-80]


def _opposing_actor(actor):
    return "opponent" if actor == "user" else "user"


def _action_actor(user_move=None, opponent_move=None, user_switch=None, opponent_switch=None):
    user_action = user_move is not None or user_switch is not None
    opponent_action = opponent_move is not None or opponent_switch is not None
    if user_action and opponent_action:
        return "both"
    if user_action:
        return "user"
    if opponent_action:
        return "opponent"
    return None


def _resolve_faints(state, auto_switch_opponent=True):
    # If both teams are exhausted, the battle is a draw.
    user_healthy = _healthy_indices(state, "user")
    opponent_healthy = _healthy_indices(state, "opponent")
    if not user_healthy or not opponent_healthy:
        state["status"] = "finished"
        state["winner"] = "user" if user_healthy else "opponent" if opponent_healthy else "tie"
        return

    if state["opponent"]["current_hp"] <= 0:
        if not auto_switch_opponent:
            state["status"] = "awaiting_opponent_switch"
            state["winner"] = None
            return
        next_index = next(index for index in opponent_healthy if index != state["opponent_active"])
        switch_team_member(state, "opponent", next_index)

    if state["user"]["current_hp"] <= 0:
        state["status"] = "awaiting_user_switch"
    else:
        state["status"] = "active"
    state["winner"] = None


def _team_action_order(state, selected):
    actions = []
    for actor, action in selected.items():
        priority = 6 if action["type"] == "switch" else action["move"].get("priority", 0)
        actions.append({
            "actor": actor,
            "type": action["type"],
            "priority": priority,
            "speed": _effective_speed(state[actor]),
        })
    return _ordered_actions(actions)


def _resolve_team_actions(state, selected, rng, auto_switch_opponent):
    state["phase"] = "RESOLUTION"
    state["log"] = []
    state["user"]["protected"] = False
    state["opponent"]["protected"] = False

    ordered = _team_action_order(state, selected)
    move_names = {actor: action["move"]["name"] for actor, action in selected.items() if action["type"] == "move"}
    skip_actors = {actor for actor, action in selected.items() if action["type"] == "switch"}

    for action in ordered:
        if action["type"] != "switch":
            continue
        switch_team_member(state, action["actor"], selected[action["actor"]]["index"])

    state["phase"] = "ANIMATION"
    active_fainted = state["user"]["current_hp"] <= 0 or state["opponent"]["current_hp"] <= 0
    if move_names and state.get("status") == "active" and not active_fainted:
        duel = {
            "turn": state["turn"],
            "status": "active",
            "winner": None,
            "user": state["user"],
            "opponent": state["opponent"],
            "hazards": state.setdefault("hazards", {"user": _empty_hazards(), "opponent": _empty_hazards()}),
            "log": [],
        }
        play_turn(
            duel,
            user_move=move_names.get("user"),
            opponent_move=move_names.get("opponent"),
            rng=rng,
            skip_actors=skip_actors,
        )
        state["turn"] = duel["turn"]
        state["log"].extend(duel["log"])
    elif selected:
        state["turn"] += 1

    state["phase"] = "CHECK_FAINT"
    _sync_active(state)
    _resolve_faints(state, auto_switch_opponent=auto_switch_opponent)
    if state.get("status") == "active":
        state["phase"] = "END_TURN"
        state["current_actor"] = "user"
    else:
        state["phase"] = "CHECK_FAINT"
    _remember_log(state)
    return state


def play_team_turn(state, user_move=None, opponent_move=None, user_switch=None, opponent_switch=None, rng=None, auto_switch_opponent=True, skip_actors=None):
    action_skip_actors = set(skip_actors or [])
    if state.get("status") == "finished":
        raise ValueError("This team battle is already finished.")
    if state.get("status") == "awaiting_user_switch":
        if user_switch is None:
            raise ValueError("Choose a healthy replacement Pokemon.")
        state["phase"] = "PLAYER_ACTION"
        state["log"] = []
        result = switch_team_member(state, "user", user_switch)
        state["current_actor"] = "user"
        state["phase"] = "PRE_TURN"
        _remember_log(state)
        return result
    if state.get("status") == "awaiting_opponent_switch":
        if opponent_switch is None:
            raise ValueError("Waiting for the opponent to choose a healthy replacement Pokemon.")
        state["phase"] = "OPPONENT_ACTION"
        state["log"] = []
        result = switch_team_member(state, "opponent", opponent_switch)
        state["current_actor"] = "opponent"
        state["phase"] = "PRE_TURN"
        _remember_log(state)
        return result
    if action_skip_actors:
        if "user" in action_skip_actors:
            user_move = None
            user_switch = None
        if "opponent" in action_skip_actors:
            opponent_move = None
            opponent_switch = None
    selected = {}
    if user_switch is not None:
        selected["user"] = {"type": "switch", "index": user_switch}
    elif user_move is not None:
        selected["user"] = {"type": "move", "move": _move(state["user"], user_move)}
    if opponent_switch is not None:
        selected["opponent"] = {"type": "switch", "index": opponent_switch}
    elif opponent_move is not None:
        selected["opponent"] = {"type": "move", "move": _move(state["opponent"], opponent_move)}
    actor = _action_actor(user_move, opponent_move, user_switch, opponent_switch)
    if actor is None:
        raise ValueError("Choose one action.")

    rng = rng or random.Random()
    state["phase"] = "PLAYER_ACTION" if "user" in selected else "OPPONENT_ACTION"
    return _resolve_team_actions(state, selected, rng, auto_switch_opponent)
