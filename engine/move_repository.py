"""Move-detail access backed by the generated local move cache."""

import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOVE_CACHE_FILE = os.path.join(BASE_DIR, "cache", "move_cache.json")
_moves = None
DEFAULT_TYPE_MOVES = {
    "normal": ["body-slam", "tackle"],
    "fire": ["flamethrower", "fire-punch"],
    "water": ["surf", "waterfall"],
    "electric": ["thunderbolt", "thunder-punch"],
    "grass": ["energy-ball", "seed-bomb"],
    "ice": ["ice-beam", "ice-punch"],
    "fighting": ["close-combat", "brick-break"],
    "poison": ["sludge-bomb", "poison-jab"],
    "ground": ["earthquake", "earth-power"],
    "flying": ["air-slash", "aerial-ace"],
    "psychic": ["psychic", "psyshock"],
    "bug": ["x-scissor", "bug-buzz"],
    "rock": ["stone-edge", "rock-slide"],
    "ghost": ["shadow-ball", "shadow-claw"],
    "dragon": ["dragon-pulse", "dragon-claw"],
    "dark": ["dark-pulse", "crunch"],
    "steel": ["flash-cannon", "iron-head"],
    "fairy": ["moonblast", "play-rough"],
}


def _slug(value):
    return str(value or "").strip().lower().replace(" ", "-")


def load_moves():
    global _moves
    if _moves is None:
        try:
            with open(MOVE_CACHE_FILE, "r", encoding="utf-8") as handle:
                _moves = json.load(handle)
        except (OSError, json.JSONDecodeError):
            _moves = {}
    return _moves


def get_move(name):
    move = load_moves().get(_slug(name))
    return dict(move) if move else None


def resolve_moves(preferred, learnable=None, pokemon_types=None, attack_category=None, limit=4):
    """Resolve move names to battle-ready details, filling gaps intelligently."""
    result = []
    seen = set()

    def add(name):
        key = _slug(name)
        move = get_move(key)
        if move and key not in seen and len(result) < limit:
            result.append(move)
            seen.add(key)

    for entry in preferred or []:
        add(entry.get("name") if isinstance(entry, dict) else entry)

    candidates = []
    types = set(pokemon_types or [])
    for entry in learnable or []:
        name = entry.get("name") if isinstance(entry, dict) else entry
        move = get_move(name)
        if not move or _slug(name) in seen:
            continue
        score = move.get("power") or 0
        if move.get("type") in types:
            score += 60
        if attack_category and move.get("damage_class") == str(attack_category).lower():
            score += 30
        if move.get("damage_class") == "status":
            score = 10
        candidates.append((score, move["name"]))
    for _, name in sorted(candidates, reverse=True):
        add(name)

    if not result:
        for move_type in pokemon_types or []:
            for name in DEFAULT_TYPE_MOVES.get(_slug(move_type), []):
                add(name)

    if not result:
        for name in ("body-slam", "swift", "tackle"):
            add(name)

    if not result:
        result.append({
            "name": "struggle", "type": "normal", "power": 50,
            "accuracy": 100, "pp": 1, "priority": 0,
            "damage_class": "physical",
        })
    return result
