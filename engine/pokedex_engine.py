"""Local Showdown Pokédex queries for autocomplete and matchup counters."""

import json
import os
import re

from engine.type_engine import get_move_multiplier


DATABASE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "showdown_pokedex.json")
ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "pokemon-assets")
_database = None


def showdown_id(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def load_pokedex():
    global _database
    if _database is None:
        try:
            with open(DATABASE_FILE, "r", encoding="utf-8") as handle:
                _database = json.load(handle)
        except (OSError, json.JSONDecodeError):
            _database = {}
    return _database


def local_official_artwork(num):
    path = os.path.join(ASSET_DIR, "official-artwork", f"{num}.png")
    if os.path.exists(path):
        return f"/static/pokemon-assets/official-artwork/{num}.png"
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{num}.png"


def pokemon_names(query="", limit=20):
    query_id = showdown_id(query)
    if query_id.isdigit():
        names = [
            entry["name"]
            for entry in load_pokedex().values()
            if str(entry.get("num", "")).startswith(query_id)
        ]
    else:
        names = [entry["name"] for key, entry in load_pokedex().items() if not query_id or key.startswith(query_id)]
    return sorted(set(names))[:limit]


def matchup_counters(name, limit=5):
    pokedex = load_pokedex()
    target = pokedex.get(showdown_id(name))
    if not target:
        return []
    target_types = target["types"]
    target_stats = target.get("base_stats", {})
    counters = []
    for pokemon_id, candidate in pokedex.items():
        if pokemon_id == showdown_id(name) or candidate.get("base_species"):
            continue
        candidate_types = candidate.get("types", [])
        attacking = max((get_move_multiplier(t, target_types) for t in candidate_types), default=1)
        if attacking < 2:
            continue
        retaliation = max((get_move_multiplier(t, candidate_types) for t in target_types), default=1)
        stats = candidate.get("base_stats", {})
        offense = max(stats.get("atk", 0), stats.get("spa", 0))
        speed = stats.get("spe", 0)
        target_speed = target_stats.get("spe", 0)
        score = attacking * 100 + offense * 0.35 + (speed - target_speed) * 0.12 - retaliation * 25
        counters.append((score, {
            "name": candidate["name"],
            "types": candidate_types,
            "tier": candidate.get("tier", "Unknown"),
            "multiplier": attacking,
            "reason": f"{attacking:g}× super-effective STAB pressure",
            "image": local_official_artwork(candidate["num"]),
        }))
    return [entry for _, entry in sorted(counters, key=lambda pair: pair[0], reverse=True)[:limit]]
