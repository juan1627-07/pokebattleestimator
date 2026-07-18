"""Read the generated Smogon/Showdown competitive recommendations."""

import json
import os
import re


DATABASE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "smogon_competitive.json")
_database = None


def showdown_id(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def load_smogon_database():
    global _database
    if _database is None:
        try:
            with open(DATABASE_FILE, "r", encoding="utf-8") as handle:
                _database = json.load(handle)
        except (OSError, json.JSONDecodeError):
            _database = {}
    return _database


def get_smogon_build(name):
    return load_smogon_database().get(showdown_id(name))


def apply_smogon_build(pokemon):
    build = get_smogon_build(pokemon.get("name"))
    if not build:
        return pokemon
    battle = pokemon.setdefault("battle", {})
    if build.get("tier") and build["tier"] != "Unknown":
        battle["tier"] = build["tier"]
        battle["tier_analysis"] = None
    if build.get("moves"):
        battle["recommended_moves"] = build["moves"]
        battle["moves_source"] = "Smogon usage"
        battle["smogon_format"] = build.get("format")
        battle["smogon_month"] = build.get("source_month")
    elif "-mega" in str(pokemon.get("name", "")).lower():
        # Mega forms can be present in Showdown data without independent usage
        # samples.  Keep their moves usable by inheriting their base form set.
        base_name = re.split(r"-mega", str(pokemon["name"]), flags=re.IGNORECASE)[0]
        base_build = get_smogon_build(base_name) or {}
        if base_build.get("moves"):
            battle["recommended_moves"] = base_build["moves"]
            battle["moves_source"] = "Base-form competitive moves"
            battle["smogon_format"] = base_build.get("format")
            battle["smogon_month"] = base_build.get("source_month")
    return pokemon
