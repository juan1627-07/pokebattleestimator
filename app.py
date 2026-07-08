from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from engine.profile_builder import build_battle_profile
from engine.battle_engine import evaluate_matchup
from engine.competitive_engine import evaluate_build
from engine.tier_engine import get_tier_analysis
from engine.battle_state import (
    create_battle, play_turn, RECOVERY_MOVES, SETUP_MOVES, STATUS_MOVES, DEBUFF_MOVES
)
from engine.damage_engine import calculate_move_damage
from engine.move_repository import resolve_moves
from engine.team_battle import create_team_battle, play_team_turn, switch_team_member
from engine.smogon_engine import apply_smogon_build
from engine.pokedex_engine import load_pokedex, pokemon_names, showdown_id, matchup_counters

import copy
import httpx
import json
import os
import uuid
import random
import time


# =====================================================
# Base Directory
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# =====================================================
# Configuration
# =====================================================

APP_VERSION = "0.1.0"
CACHE_VERSION = 140


# =====================================================
# Competitive Engine
# =====================================================

ABILITY_SCORES = {
    "Huge Power": 100,
    "Wonder Guard": 100,
    "Magic Guard": 98,
    "Regenerator": 98,
    "Solar Power": 96,
    "Levitate": 95,
    "Intimidate": 95,
    "Multiscale": 94,
    "Protean": 94,
    "Libero": 94,
    "Technician": 93,
    "Adaptability": 93,
    "Sturdy": 88,
    "Blaze": 65,
    "Torrent": 65,
    "Overgrow": 65
}

ABILITY_SCORE = {

    # Elite Competitive

    "protean":100,
    "libero":100,
    "multiscale":99,
    "speed-boost":99,
    "magic-guard":98,
    "regenerator":98,

    # Weather

    "chlorophyll":95,
    "swift-swim":95,
    "solar-power":95,
    "sand-rush":95,

    # Offensive

    "adaptability":94,
    "technician":93,
    "huge-power":93,
    "beast-boost":93,

    # Defensive

    "intimidate":92,
    "levitate":92,
    "flash-fire":90,
    "sturdy":89,
    "rough-skin":88,

    # Starter abilities

    "blaze":70,
    "torrent":70,
    "overgrow":70,

    # Default

}

NATURES = {

    ("attack", "special-attack"): "Adamant",

    ("speed", "special-attack"): "Jolly",

    ("special-attack", "attack"): "Modest",

    ("speed", "attack"): "Timid",

    ("defense", "special-attack"): "Impish",

    ("special-defense", "attack"): "Calm"

}

ROLE_ITEMS = {

    "Physical Sweeper": "Choice Band",

    "Special Sweeper": "Choice Specs",

    "Fast Sweeper": "Choice Scarf",

    "Physical Tank": "Rocky Helmet",

    "Special Tank": "Assault Vest",

    "Support": "Leftovers",

    "Balanced": "Life Orb"

}


# GENERATION

GENERATION_REGION = {

    "generation-i": "Kanto",
    "generation-ii": "Johto",
    "generation-iii": "Hoenn",
    "generation-iv": "Sinnoh",
    "generation-v": "Unova",
    "generation-vi": "Kalos",
    "generation-vii": "Alola",
    "generation-viii": "Galar",
    "generation-ix": "Paldea"

}

# type colors

TYPE_COLORS = {

    "normal":"#A8A77A",

    "fire":"#EE8130",

    "water":"#6390F0",

    "electric":"#F7D02C",

    "grass":"#7AC74C",

    "ice":"#96D9D6",

    "fighting":"#C22E28",

    "poison":"#A33EA1",

    "ground":"#E2BF65",

    "flying":"#A98FF3",

    "psychic":"#F95587",

    "bug":"#A6B91A",

    "rock":"#B6A136",

    "ghost":"#735797",

    "dragon":"#6F35FC",

    "dark":"#705746",

    "steel":"#B7B7CE",

    "fairy":"#D685AD"

}



app = Flask(__name__)
CORS(app)
client = httpx.Client(

    timeout=20,

    follow_redirects=True,

    headers={

        "User-Agent": "PokemonBattleEstimator/1.0"

    }

)


POKEAPI_BASE = "https://pokeapi.co/api/v2"

CACHE_DIR = os.path.join(
    BASE_DIR,
    "cache"
)

POKEMON_CACHE_FILE = os.path.join(
    CACHE_DIR,
    "pokemon_cache.json"
)

# Memory cache
pokemon_cache = {}
BATTLES = {}
PVP_ROOMS = {}
_initialized = False



COMPETITIVE_DB = {}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COMPETITIVE_DB_FILE = os.path.join(
    BASE_DIR,
    "data",
    "competitive_builds.json"
)

TIER_DB = {}



# =====================================================
# Cache Utilities
# =====================================================

def ensure_cache():
    """Create cache folder/files if they don't exist."""

    os.makedirs(CACHE_DIR, exist_ok=True)

    if not os.path.exists(POKEMON_CACHE_FILE):
        with open(POKEMON_CACHE_FILE, "w") as f:
            json.dump({}, f)


def load_cache():
    """Load pokemon cache into memory."""

    global pokemon_cache

    ensure_cache()

    try:
        with open(POKEMON_CACHE_FILE, "r") as f:
            pokemon_cache = json.load(f)
    except Exception:
        pokemon_cache = {}


def save_cache():
    """Save memory cache to disk."""

    with open(POKEMON_CACHE_FILE, "w") as f:
        json.dump(pokemon_cache, f, indent=4)

# =====================================================
# Competitive Database Loader
# =====================================================

def load_competitive_database():

    global COMPETITIVE_DB

    if not os.path.exists(COMPETITIVE_DB_FILE):

        COMPETITIVE_DB = {}

        return

    try:

        with open(
            COMPETITIVE_DB_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            COMPETITIVE_DB = json.load(f)
            print("========== DATABASE LOADED ==========")
            print(list(COMPETITIVE_DB.keys())[:10])
            print("=====================================")
            print("\n========== COMPETITIVE DB ==========")
            print("Total Entries:", len(COMPETITIVE_DB))

            print("\nBulbasaur:")
            print(COMPETITIVE_DB.get("1"))

            print("\nCharizard:")
            print(COMPETITIVE_DB.get("6"))

            print("\nPikachu:")
            print(COMPETITIVE_DB.get("25"))



            print("====================================\n")

    except json.JSONDecodeError:

        print("[WARNING] competitive_builds.json is invalid.")

        COMPETITIVE_DB = {}


TIER_DB_FILE = os.path.join(
    BASE_DIR,
    "data",
    "tier_database.json"
)

def load_tier_database():

    global TIER_DB

    if not os.path.exists(TIER_DB_FILE):

        TIER_DB = {}

        return

    try:

        with open(
                TIER_DB_FILE,
                "r",
                encoding="utf8"
        ) as f:

            TIER_DB = json.load(f)

    except json.JSONDecodeError:

        print("[WARNING] tier_database.json is invalid.")

        TIER_DB = {}

def get_tier(name):

    return TIER_DB.get(

        clean_name(name),

        "Unknown"

    )


# =====================================================
# Helper
# =====================================================

def clean_name(value):

    value = str(value).strip()

    if value.isdigit():
        return str(int(value))   # "0001" -> "1"

    return value.lower().replace(" ", "-")


ASSET_BASE_URL = "/static/pokemon-assets"
ASSET_BASE_DIR = os.path.join(BASE_DIR, "static", "pokemon-assets")


def _asset_url(*parts):
    path = os.path.join(ASSET_BASE_DIR, *parts)
    if os.path.exists(path):
        return "/".join([ASSET_BASE_URL, *parts])
    return None


def _showdown_sprite_id(name):
    return showdown_id(name)


def _local_image_urls(name, pokedex_number=None):
    sprite_id = _showdown_sprite_id(name)
    urls = {
        "showdown_front": _asset_url("showdown", "front", f"{sprite_id}.gif"),
        "showdown_back": _asset_url("showdown", "back", f"{sprite_id}.gif"),
    }
    if pokedex_number:
        number = str(int(pokedex_number))
        urls.update({
            "official_artwork": _asset_url("official-artwork", f"{number}.png"),
            "official_artwork_shiny": _asset_url("official-artwork-shiny", f"{number}.png"),
            "front_default": _asset_url("sprites", "front", f"{number}.png"),
            "back_default": _asset_url("sprites", "back", f"{number}.png"),
            "front_shiny": _asset_url("sprites", "front-shiny", f"{number}.png"),
            "back_shiny": _asset_url("sprites", "back-shiny", f"{number}.png"),
        })
    return {key: value for key, value in urls.items() if value}


def apply_local_asset_urls(pokemon):
    images = pokemon.setdefault("images", {})
    pokemon_name = pokemon.get("name", "")
    pokemon_id = pokemon.get("metadata", {}).get("id")
    for key, value in _local_image_urls(pokemon_name, pokemon_id).items():
        images[key] = value
    return pokemon


def _fallback_pokemon_from_pokedex(search):
    pokedex = load_pokedex()
    key = showdown_id(search)
    entry = pokedex.get(key)
    if entry is None and str(search).isdigit():
        entry = next((value for value in pokedex.values() if str(value.get("num")) == str(int(search))), None)
        key = showdown_id(entry.get("name")) if entry else key
    if not entry:
        return None

    stats_map = entry.get("base_stats", {})
    stat_names = {
        "hp": "HP",
        "atk": "Attack",
        "def": "Defense",
        "spa": "Sp. Attack",
        "spd": "Sp. Defense",
        "spe": "Speed",
    }
    api_names = {
        "hp": "hp",
        "atk": "attack",
        "def": "defense",
        "spa": "special-attack",
        "spd": "special-defense",
        "spe": "speed",
    }
    stats = [
        {"name": stat_names[source], "api_name": api_names[source], "value": stats_map.get(source, 0)}
        for source in ("hp", "atk", "def", "spa", "spd", "spe")
    ]

    role = determine_role(stats)
    build = get_competitive_build(key) or get_competitive_build(entry.get("name", ""))
    competitive = build.get("competitive", {}) if build else {}
    ability_name = competitive.get("ability") or "Unknown"
    abilities = [{"name": str(ability_name).replace("-", " ").title(), "slot": 1, "type": "Recommended", "recommended": True}]
    natures = recommend_natures(stats, role)
    abilities_ranked = recommend_ability(abilities, role)
    items = recommend_items(role, entry.get("types", []))
    recommended_moves = competitive.get("moves", [])
    tier = competitive.get("tier") or entry.get("tier") or "Unknown"
    item = items[0]
    nature = natures[0]
    ability = abilities_ranked[0]
    images = {
        "official_artwork": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{entry['num']}.png",
        "pokemon_home": None,
        "dream_world": None,
        "showdown_front": f"https://play.pokemonshowdown.com/sprites/ani/{key}.gif",
        "showdown_back": f"https://play.pokemonshowdown.com/sprites/gen5ani-back/{key}.gif",
        "front_default": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{entry['num']}.png",
        "back_default": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/back/{entry['num']}.png",
        "front_shiny": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/shiny/{entry['num']}.png",
        "back_shiny": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/back/shiny/{entry['num']}.png",
        "pokemon_home_shiny": None,
        "official_artwork_shiny": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/shiny/{entry['num']}.png",
    }
    pokemon = {
        "_cache_version": CACHE_VERSION,
        "name": entry.get("name", str(search).title()),
        "metadata": {
            "id": entry.get("num"),
            "pokedex_number": f"{entry.get('num', 0):04d}",
            "generation": "Unknown",
            "region": "Unknown",
            "species": entry.get("base_species") or entry.get("name", "Unknown"),
            "height": None,
            "weight": None,
            "base_experience": None,
            "order": None,
        },
        "images": images,
        "types": [{"name": pokemon_type, "color": TYPE_COLORS.get(pokemon_type, "#777")} for pokemon_type in entry.get("types", [])],
        "abilities": abilities,
        "stats": stats,
        "moves": [{"name": move.replace("-", " ").title(), "url": None, "learn_method": "competitive", "level": None} for move in recommended_moves],
        "battle": {
            "role": role,
            "recommended_nature": nature,
            "recommended_natures": natures,
            "recommended_ability": ability,
            "recommended_abilities": abilities_ranked,
            "recommended_item": item,
            "recommended_items": items,
            "recommended_moves": recommended_moves,
            "competitive_score": None,
            "competitive_rating": None,
            "tier": tier,
            "tier_analysis": get_tier_analysis(tier),
            "matchup_score": None,
            "reason": "Local Showdown Pokédex",
        },
    }
    analysis = evaluate_build(role, tier, ability, item, recommended_moves)
    pokemon["battle"]["competitive_score"] = analysis["score"]
    pokemon["battle"]["competitive_rating"] = analysis["rating"]
    apply_current_competitive_data(pokemon)
    pokemon["battle_profile"] = build_battle_profile(pokemon)
    pokemon_cache[key] = pokemon
    save_cache()
    return pokemon


# =====================================================
# PokéAPI Loader
# =====================================================



def fetch_pokemon(name):
    print("\n===================================")
    print("FETCH POKEMON CALLED")
    print("Input:", name)
    print("===================================\n")

    name = clean_name(name)

    # Serve a current cached record before making any network request.
    cached = pokemon_cache.get(name)
    if cached is None and name.isdigit():
        wanted_id = int(name)
        cached = next((
            value for value in pokemon_cache.values()
            if value.get("metadata", {}).get("id") == wanted_id
        ), None)
    if cached and cached.get("_cache_version") == CACHE_VERSION:
        return apply_current_competitive_data(cached)

    # ------------------------
    # Memory Cache
    # ------------------------

    url = f"{POKEAPI_BASE}/pokemon/{name}"

    try:

        response = client.get(url)

        if response.status_code != 200:
            return _fallback_pokemon_from_pokedex(name)

        data = response.json()

        cache_key = data["name"].lower()

        if cache_key in pokemon_cache:

            cached = pokemon_cache[cache_key]

            print("\n========== CACHE ==========")
            print("Found:", cache_key)
            print("Cached Version:", cached.get("_cache_version"))
            print("Expected:", CACHE_VERSION)
            print("===========================\n")

            if cached.get("_cache_version") == CACHE_VERSION:
                print("RETURNING CACHED DATA\n")
                return cached

        print("CACHE MISS\n")
        # ----------------------------------------
        # Species Information
        # ----------------------------------------

        species_url = data["species"]["url"]

        species_response = client.get(species_url)

        if species_response.status_code == 200:
            species = species_response.json()
        else:
            species = {}

        generation_api = species.get("generation", {}).get("name", "")

        generation = generation_api.replace(
            "generation-",
            "Generation "
        ).upper() if generation_api else "Unknown"

        region = GENERATION_REGION.get(
            generation_api,
            "Unknown"
        )

        species_name = "Unknown"

        for genus in species.get("genera", []):

            if genus["language"]["name"] == "en":
                species_name = genus["genus"]
                break


    except Exception as e:

        import traceback

        print("\n========== ERROR ==========")

        print(e)

        traceback.print_exc()

        print("===========================\n")

        return _fallback_pokemon_from_pokedex(name)

    # ------------------------
    # Stats
    # ------------------------

    stats = []

    stat_mapping = {

        "hp": "HP",

        "attack": "Attack",

        "defense": "Defense",

        "special-attack": "Sp. Attack",

        "special-defense": "Sp. Defense",

        "speed": "Speed"

    }

    for stat in data["stats"]:
        stats.append({

            "name": stat_mapping[stat["stat"]["name"]],

            "api_name": stat["stat"]["name"],

            "value": stat["base_stat"]

        })

    # ------------------------
    # Types
    # ------------------------

    types = []

    for t in data["types"]:
        types.append(t["type"]["name"])

    # ------------------------
    # Abilities
    # ------------------------

    abilities = []

    for ability in data["abilities"]:

        # Determine readable ability type
        if ability["is_hidden"]:
            ability_type = "Hidden"
        elif ability["slot"] == 1:
            ability_type = "Primary"
        else:
            ability_type = "Secondary"

        abilities.append({

            "name": ability["ability"]["name"].replace("-", " ").title(),

            "slot": ability["slot"],

            "type": ability_type,

            # Will be updated by the optimization engine
            "recommended": False

        })

    # Keep abilities ordered by slot
    abilities.sort(key=lambda x: x["slot"])

    # ------------------------
    # Moves
    # ------------------------

    moves = []

    for move in data["moves"]:

        details = move["version_group_details"]

        level = None
        learn_method = None

        if details:
            latest = details[-1]

            level = latest["level_learned_at"]

            learn_method = latest["move_learn_method"]["name"]

        moves.append({

            "name": move["move"]["name"].replace("-", " ").title(),

            "url": move["move"]["url"],

            "learn_method": learn_method,

            "level": level

        })

    # Sort alphabetically
    moves = sorted(moves, key=lambda x: x["name"])

    # ------------------------
    # Artwork
    # ------------------------

    # ------------------------
    # Images
    # ------------------------

    images = {

        # Official artwork (highest quality)
        "official_artwork":
            data["sprites"]["other"]["official-artwork"]["front_default"],

        # Pokémon HOME artwork
        "pokemon_home":
            data["sprites"]["other"]["home"]["front_default"],

        # Dream World artwork (SVG-style)
        "dream_world":
            data["sprites"]["other"]["dream_world"]["front_default"],

        # Official Showdown sprite (animated if available)
        "showdown_front":
            (
                data["sprites"]["other"].get("showdown", {})
                .get("front_default")
            ),

        "showdown_back":
            (
                data["sprites"]["other"].get("showdown", {})
                .get("back_default")
            ),

        # Standard game sprites
        "front_default":
            data["sprites"]["front_default"],

        "back_default":
            data["sprites"]["back_default"],

        # Shiny sprites
        "front_shiny":
            data["sprites"]["front_shiny"],

        "back_shiny":
            data["sprites"]["back_shiny"],

        # Pokémon HOME shiny artwork
        "pokemon_home_shiny":
            data["sprites"]["other"]["home"]["front_shiny"],

        # Official artwork shiny (currently unavailable in PokéAPI,
        # kept for future compatibility)
        "official_artwork_shiny":
            (
                data["sprites"]["other"]["official-artwork"]
                .get("front_shiny")
            )
    }

    role = determine_role(stats)
    natures = recommend_natures(stats,role)
    nature = natures[0]
    abilities_ranked = recommend_ability(abilities,role)
    ability = abilities_ranked[0]
    items = recommend_items(role,types)

    item = items[0]

    print("ROLE:", role)
    print("NATURE:", nature)
    print("ABILITY:", ability)
    print("ITEM:", item)

    pokemon = {

        "_cache_version": CACHE_VERSION,

        "name": data["name"].title(),

        "metadata": {

            "id": data["id"],

            "pokedex_number": f"{data['id']:04d}",

            "generation": generation,

            "region": region,

            "species": species_name,

            "height": data["height"],

            "weight": data["weight"],

            "base_experience": data["base_experience"],

            "order": data["order"],

        },

        "images": images,

        "types": [
            {
                "name": t,
                "color": TYPE_COLORS.get(t, "#777")
            }
            for t in types
        ],

        "abilities": abilities,

        "stats": stats,

        "moves": moves,

        # ==========================================
        # Reserved for Phase 2 onwards
        # ==========================================
        "battle": {

            "role": role,

            "recommended_nature": nature,

            "recommended_natures": natures,

            "recommended_ability": ability,

            "recommended_abilities": abilities_ranked,

            "recommended_item": item,

            "recommended_items": items,

            "recommended_moves": [],

            "competitive_score": None,

            "competitive_rating": None,

            "tier": None,

            "matchup_score": None,

            "reason": None

        }

    }




    # Save cache

    pokemon["_cache_version"] = CACHE_VERSION

    # ----------------------------------------
    # Competitive Build Merge
    # ----------------------------------------

    print("\nREACHED COMPETITIVE LOOKUP\n")

    build = get_competitive_build(data["name"])
    print("\nRETURNED FROM COMPETITIVE LOOKUP\n")
    print("\n================ DEBUG ================")
    print("ROLE FROM ENGINE :", role)
    print("BUILD:")
    print(json.dumps(build, indent=4) if build else None)
    print("Searching        :", name)
    print("Build Found      :", build is not None)
    print("Build Object     :", build)
    print("=======================================\n")
    print("\n========== BUILD DEBUG ==========")

    if build:

        print("Pokemon :", build.get("name"))

        print("Moves   :", build.get("moves"))

        print("Keys    :", list(build.keys()))

        print("Tier    :", build.get("tier"))

    else:

        print("BUILD = None")

    print("================================\n")


    if build:
        print(build)

    print("========================\n")

    if build:
        competitive = build.get("competitive", {})

        pokemon["battle"]["recommended_moves"] = competitive.get("moves", [])

        pokemon["battle"]["tier"] = competitive.get("tier", "Unknown")
        print("\n========== TIER DEBUG ==========")
        print("Pokemon :", pokemon["name"])
        print("Tier    :", pokemon["battle"]["tier"])
        print("===============================\n")

        tier_info = get_tier_analysis(

            pokemon["battle"]["tier"]

        )

        pokemon["battle"]["tier_analysis"] = tier_info

        pokemon["battle"]["reason"] = "Competitive Database"

        # ----------------------------------------
        # Calculate Competitive Score
        # ----------------------------------------

        analysis = evaluate_build(

            pokemon["battle"]["role"],

            pokemon["battle"]["tier"],

            pokemon["battle"]["recommended_ability"],

            pokemon["battle"]["recommended_item"],

            pokemon["battle"]["recommended_moves"]

        )

        pokemon["battle"]["competitive_score"] = analysis["score"]

        pokemon["battle"]["competitive_rating"] = analysis["rating"]

        print("\n========== FINAL BATTLE ==========")
        print(json.dumps(pokemon["battle"], indent=4))
        print("==================================\n")


    apply_current_competitive_data(pokemon)

    pokemon["battle_profile"] = build_battle_profile(
        pokemon
    )

    pokemon_cache[data["name"].lower()] = pokemon

    save_cache()

    return pokemon


def get_competitive_build(search):

    search = clean_name(search)

    print("\n========== LOOKUP ==========")
    print("Searching for:", search)

    print("Database Entries:", len(COMPETITIVE_DB))

    # Search by ID
    if search.isdigit():

        print("Searching by ID...")

        result = COMPETITIVE_DB.get(search)

        print("Result:", result)

        return result

    # Search by Name
    print("Searching by Name...")

    for pokemon_id, pokemon in COMPETITIVE_DB.items():

        print(f"{pokemon_id} -> {pokemon.get('name')}")

        if pokemon.get("name") == search:

            print("FOUND!")

            return pokemon

    print("NOT FOUND")

    return None


def stat_dict(stats):

    """
    Converts the stats list into a dictionary.

    Input:
        [
            {"api_name":"hp","value":78},
            ...
        ]

    Output:
        {
            "hp":78,
            "attack":84,
            ...
        }
    """

    return {

        stat["api_name"]: stat["value"]

        for stat in stats

    }

def determine_role(stats):

    s = stat_dict(stats)

    hp = s["hp"]
    atk = s["attack"]
    defense = s["defense"]
    spa = s["special-attack"]
    spd = s["special-defense"]
    speed = s["speed"]

    total_bulk = hp + defense + spd

    # ==========================================
    # Stage 1
    # Determine Attack Style
    # ==========================================

    difference = atk - spa

    if abs(difference) <= 15:

        attack_style = "Mixed"

    elif difference > 0:

        attack_style = "Physical"

    else:

        attack_style = "Special"

    # ==========================================
    # Stage 2
    # Detect True Walls
    # ==========================================

    if defense >= 130:

        role = "Physical Wall"

    elif spd >= 130:

        role = "Special Wall"

    elif total_bulk >= 330:

        if defense >= spd:

            role = "Physical Wall"

        else:

            role = "Special Wall"

    # ==========================================
    # Stage 3
    # Bulky Pokemon
    # ==========================================

    elif total_bulk >= 250:

        if attack_style == "Physical":

            role = "Bulky Physical"

        elif attack_style == "Special":

            role = "Bulky Special"

        else:

            role = "Bulky Mixed"

    # ==========================================
    # Stage 4
    # Fast Pokemon
    # ==========================================

    elif speed >= 115:

        role = f"Fast {attack_style} Sweeper"

    elif speed >= 95:

        if attack_style == "Mixed":

            role = "Fast Mixed Sweeper"

        else:

            role = f"Fast {attack_style} Sweeper"

    # ==========================================
    # Stage 5
    # Offensive Pokemon
    # ==========================================

    elif attack_style == "Physical":

        role = "Physical Sweeper"

    elif attack_style == "Special":

        role = "Special Sweeper"

    elif attack_style == "Mixed":

        role = "Mixed Sweeper"

    else:

        role = "Balanced"

    print("\n==============================")
    print("HP      :", hp)
    print("ATK     :", atk)
    print("DEF     :", defense)
    print("SPA     :", spa)
    print("SPD     :", spd)
    print("SPE     :", speed)
    print("------------------------------")
    print("Attack Style :", attack_style)
    print("Role         :", role)
    print("==============================\n")

    return role

def debug_role(stats):

    role = determine_role(stats)

    print(f"[ROLE ENGINE] {role}")

    return role


def stat_dict(stats):
    """
    Convert stats list into an easy dictionary.
    """

    return {
        s["api_name"]: s["value"]
        for s in stats
    }


def recommend_natures(stats, role):

    recommendations = []

    # =====================================
    # Fast Sweepers
    # =====================================

    if role == "Fast Physical Sweeper":

        recommendations.extend([

            {
                "name": "Jolly",
                "score": 100,
                "reason": "Maximum Speed."
            },

            {
                "name": "Adamant",
                "score": 92,
                "reason": "More power."
            }

        ])

    elif role == "Fast Special Sweeper":

        recommendations.extend([

            {
                "name": "Timid",
                "score": 100,
                "reason": "Maximum Speed."
            },

            {
                "name": "Modest",
                "score": 94,
                "reason": "Higher Special Attack."
            }

        ])

    # =====================================
    # Physical
    # =====================================

    elif role == "Physical Sweeper":

        recommendations.extend([

            {
                "name": "Adamant",
                "score": 100,
                "reason": "Maximum physical damage."
            },

            {
                "name": "Jolly",
                "score": 92,
                "reason": "Extra Speed."
            }

        ])

    # =====================================
    # Special
    # =====================================

    elif role == "Special Sweeper":

        recommendations.extend([

            {
                "name": "Modest",
                "score": 100,
                "reason": "Maximum Special Attack."
            },

            {
                "name": "Timid",
                "score": 94,
                "reason": "Extra Speed."
            }

        ])

    # =====================================
    # Bulky Physical
    # =====================================

    elif role == "Bulky Physical":

        recommendations.extend([

            {
                "name": "Adamant",
                "score": 98,
                "reason": "Increase Attack."
            },

            {
                "name": "Careful",
                "score": 90,
                "reason": "Improve special bulk."
            }

        ])

    # =====================================
    # Bulky Special
    # =====================================

    elif role == "Bulky Special":

        recommendations.extend([

            {
                "name": "Modest",
                "score": 98,
                "reason": "Increase Special Attack."
            },

            {
                "name": "Calm",
                "score": 90,
                "reason": "Increase Special Defense."
            }

        ])

    # =====================================
    # Walls
    # =====================================

    elif role == "Physical Wall":

        recommendations.extend([

            {
                "name": "Impish",
                "score": 100,
                "reason": "Increase Defense."
            },

            {
                "name": "Relaxed",
                "score": 90,
                "reason": "Alternative defensive nature."
            }

        ])

    elif role == "Special Wall":

        recommendations.extend([

            {
                "name": "Calm",
                "score": 100,
                "reason": "Increase Special Defense."
            },

            {
                "name": "Careful",
                "score": 92,
                "reason": "Alternative special wall."
            }

        ])

    # =====================================
    # Mixed
    # =====================================

    elif "Mixed" in role:

        recommendations.extend([

            {
                "name": "Naive",
                "score": 98,
                "reason": "Fast mixed attacker."
            },

            {
                "name": "Hasty",
                "score": 92,
                "reason": "Alternative mixed offense."
            }

        ])

    else:

        recommendations.append({

            "name": "Serious",

            "score": 50,

            "reason": "Neutral nature."

        })

    return recommendations

def recommend_ability(abilities, role):

    recommendations = []

    for ability in abilities:

        api = ability["name"].lower().replace(" ", "-")

        score = ABILITY_SCORE.get(api,50)

        # =====================================
        # Role bonuses
        # =====================================

        if role.startswith("Fast"):

            if api in (

                "speed-boost",

                "solar-power",

                "chlorophyll",

                "swift-swim"

            ):

                score += 10

        if "Wall" in role:

            if api in (

                "regenerator",

                "sturdy",

                "multiscale"

            ):

                score += 10

        if "Physical" in role:

            if api in (

                "intimidate",

                "huge-power",

                "technician"

            ):

                score += 8

        if "Special" in role:

            if api in (

                "solar-power",

                "adaptability"

            ):

                score += 8

        recommendations.append({

            "name": ability["name"],

            "score": score,

            "type": ability["type"]

        })

    recommendations.sort(

        key=lambda x:x["score"],

        reverse=True

    )

    return recommendations

def recommend_items(role, pokemon_types):

    recommendations = []

    def add(name, score, reason):

        recommendations.append({

            "name": name,

            "score": score,

            "reason": reason

        })

    # =====================================
    # Fast Physical
    # =====================================

    if role == "Fast Physical Sweeper":

        add("Choice Scarf",100,"Maximum Speed")
        add("Life Orb",95,"Higher damage")
        add("Focus Sash",90,"Survive one hit")

    # =====================================
    # Physical
    # =====================================

    elif role == "Physical Sweeper":

        add("Choice Band",100,"Massive Attack")
        add("Life Orb",95,"Flexible offense")
        add("Loaded Dice",88,"Multi-hit strategies")

    # =====================================
    # Fast Special
    # =====================================

    elif role == "Fast Special Sweeper":

        add("Choice Specs",100,"Maximum Special Attack")
        add("Life Orb",95,"Flexible offense")
        add("Heavy-Duty Boots",92,"Hazard protection")

    # =====================================
    # Special
    # =====================================

    elif role == "Special Sweeper":

        add("Choice Specs",100,"Increase Special Attack")
        add("Expert Belt",92,"Coverage attacks")
        add("Life Orb",90,"Flexible offense")

    # =====================================
    # Bulky
    # =====================================

    elif "Bulky" in role:

        add("Leftovers",100,"Passive recovery")
        add("Assault Vest",94,"Increase Special Defense")
        add("Rocky Helmet",88,"Punish contact")

    # =====================================
    # Walls
    # =====================================

    elif "Wall" in role:

        add("Leftovers",100,"Recovery")
        add("Rocky Helmet",96,"Chip damage")
        add("Heavy-Duty Boots",90,"Avoid hazards")

    # =====================================
    # Mixed
    # =====================================

    elif "Mixed" in role:

        add("Life Orb",100,"Mixed offense")
        add("Expert Belt",95,"Coverage")
        add("Focus Sash",90,"Safety")

    else:

        add("Leftovers",80,"Reliable item")

    # =====================================
    # Type Synergy
    # =====================================

    type_names = [

        t["name"]

        if isinstance(t,dict)

        else t

        for t in pokemon_types

    ]

    # =====================================
    # Hazard Vulnerability Bonus
    # =====================================

    boots_bonus = 0

    if "flying" in type_names:
        boots_bonus += 20

    if "fire" in type_names:
        boots_bonus += 10

    if "ice" in type_names:
        boots_bonus += 5

    for item in recommendations:

        if item["name"] == "Heavy-Duty Boots":
            item["score"] += boots_bonus

            item["reason"] = "Excellent against entry hazards."

    recommendations.sort(

        key=lambda x:x["score"],

        reverse=True

    )

    return recommendations
# =====================================================
# Application and battle helpers
# =====================================================

def initialize_app():
    """Load local data whether Flask is run directly or through a WSGI server."""
    global _initialized
    if _initialized:
        return
    load_cache()
    load_competitive_database()
    load_tier_database()
    _initialized = True


def apply_current_competitive_data(pokemon):
    apply_smogon_build(pokemon)
    apply_local_asset_urls(pokemon)
    battle = pokemon.setdefault("battle", {})
    battle["tier_analysis"] = get_tier_analysis(battle.get("tier", "Unknown"))
    pokemon_id = pokemon.get("metadata", {}).get("id")
    if pokemon_id:
        pokemon.setdefault("audio", {})["cry"] = (
            f"https://raw.githubusercontent.com/PokeAPI/cries/main/cries/pokemon/latest/{pokemon_id}.ogg"
        )
    return pokemon


def battle_ready_profile(pokemon):
    apply_current_competitive_data(pokemon)
    profile = build_battle_profile(pokemon)
    profile["moves"] = resolve_moves(
        profile.get("moves", []),
        pokemon.get("moves", []),
        profile.get("types", []),
        profile.get("battle_stats", {}).get("attack_category"),
    )
    return profile


def choose_opponent_move(opponent, user):
    """Choose damage, recovery, setup, or disruption based on battle state."""
    scored = []
    for move in opponent.get("moves", []):
        if isinstance(move.get("current_pp"), int) and move["current_pp"] <= 0:
            continue
        damage = calculate_move_damage(opponent, user, move, random_factor=1.0)["damage"]
        name = move["name"].lower().replace(" ", "-")
        score = damage
        hp_ratio = opponent.get("current_hp", 1) / max(opponent.get("max_hp", 1), 1)
        if name in RECOVERY_MOVES and hp_ratio < 0.55:
            score = 220
        elif name in STATUS_MOVES and not user.get("status"):
            score = 85
        elif name in DEBUFF_MOVES:
            score = 58
        elif name in SETUP_MOVES and max(opponent.get("stages", {}).values(), default=0) < 2:
            score = 72
        elif name == "protect":
            score = 32
        scored.append((score, damage, move["name"]))
    return max(scored, default=(0, 0, "struggle"))[2]


def choose_opponent_switch(state):
    """Switch when badly hurt or when a healthy reserve has a much better matchup."""
    active = state["opponent"]
    user = state["user"]
    healthy = [
        (index, side) for index, side in enumerate(state["opponent_team"])
        if index != state["opponent_active"] and side["current_hp"] > 0
    ]
    if not healthy:
        return None

    def matchup_score(attacker, defender):
        best_outgoing = max((
            calculate_move_damage(attacker, defender, move, random_factor=1.0)["damage"]
            for move in attacker.get("moves", [])
        ), default=0)
        best_incoming = max((
            calculate_move_damage(defender, attacker, move, random_factor=1.0)["damage"]
            for move in defender.get("moves", [])
        ), default=0)
        hp_ratio = attacker["current_hp"] / max(attacker["max_hp"], 1)
        return best_outgoing - best_incoming * 0.65 + hp_ratio * 25

    active_score = matchup_score(active, user)
    best_index, best_side = max(healthy, key=lambda pair: matchup_score(pair[1], user))
    best_score = matchup_score(best_side, user)
    active_hp = active["current_hp"] / max(active["max_hp"], 1)
    if active_hp <= 0.28 or best_score >= active_score + 28:
        return best_index
    return None


def _pvp_code():
    return uuid.uuid4().hex[:6].upper()


def _player_key(room, player_id):
    for key, player in room["players"].items():
        if player["id"] == player_id:
            return key
    return None


def _build_named_team(names):
    clean_names = [clean_name(name) for name in names if clean_name(name)]
    if len(clean_names) != 6:
        raise ValueError("Choose exactly six Pokemon.")
    profiles = []
    for name in clean_names:
        pokemon = fetch_pokemon(name)
        if not pokemon:
            raise ValueError(f"Pokemon '{name}' could not be found.")
        profiles.append(battle_ready_profile(pokemon))
    return profiles


def _masked_team(player):
    slots = player.get("team", []) if player.get("ready") else range(6)
    return [{"hidden": True, "ready": player.get("ready", False)} for _ in slots]


def _perspective_state(state, player_key):
    view = copy.deepcopy(state)
    if player_key != "p1":
        view["user"], view["opponent"] = view["opponent"], view["user"]
        view["user_team"], view["opponent_team"] = view["opponent_team"], view["user_team"]
        view["user_active"], view["opponent_active"] = view["opponent_active"], view["user_active"]
        if view.get("current_actor") == "user":
            view["current_actor"] = "opponent"
        elif view.get("current_actor") == "opponent":
            view["current_actor"] = "user"
        revealed = view.get("revealed", {})
        view["revealed"] = {
            "user": list(revealed.get("opponent", [view["user_active"]])),
            "opponent": list(revealed.get("user", [view["opponent_active"]])),
        }
        if view.get("winner") == "user":
            view["winner"] = "opponent"
        elif view.get("winner") == "opponent":
            view["winner"] = "user"
        if view.get("status") == "awaiting_user_switch":
            view["status"] = "awaiting_opponent_switch"
        elif view.get("status") == "awaiting_opponent_switch":
            view["status"] = "awaiting_user_switch"
        for entry in view.get("log", []):
            if entry.get("actor") == "user":
                entry["actor"] = "opponent"
            elif entry.get("actor") == "opponent":
                entry["actor"] = "user"
    return _mask_opponent_team(view)


def _masked_side(slot):
    return {
        "hidden": True,
        "name": "Hidden",
        "current_hp": 1,
        "max_hp": 1,
        "tier": None,
        "image": None,
        "front_image": None,
    }


def _mask_opponent_team(view):
    revealed = set(view.get("revealed", {}).get("opponent", [view.get("opponent_active", 0)]))
    revealed.add(view.get("opponent_active", 0))
    masked = []
    for index, side in enumerate(view.get("opponent_team", [])):
        if side.get("current_hp", 0) <= 0 or index in revealed:
            masked.append(side)
        else:
            masked.append(_masked_side(side))
    view["opponent_team"] = masked
    return view


def _append_history(state):
    history = state.setdefault("history", [])
    history.extend(state.get("log", []))
    del history[:-80]


def _actor_for_player(player_key):
    return "user" if player_key == "p1" else "opponent"


def _player_for_actor(actor):
    return "p1" if actor == "user" else "p2"


def _pvp_choice_for_payload(payload):
    switch_index = payload.get("switch_index")
    move = payload.get("move")
    if switch_index is not None:
        return {"type": "switch", "index": int(switch_index)}
    if move:
        return {"type": "move", "move": move}
    return None


def _resolve_pvp_choices(room):
    state = room["battle"]
    choices = room.setdefault("choices", {})
    if "user" not in choices or "opponent" not in choices:
        return False
    kwargs = {}
    for actor, choice in choices.items():
        if choice["type"] == "switch":
            kwargs[f"{actor}_switch"] = choice["index"]
        else:
            kwargs[f"{actor}_move"] = choice["move"]
    play_team_turn(state, auto_switch_opponent=False, **kwargs)
    choices.clear()
    room["turn_deadline"] = time.time() + 30
    return True


def _apply_pvp_timeout(room):
    state = room.get("battle")
    deadline = room.get("turn_deadline")
    if room.get("status") != "battle" or not state or state.get("status") == "finished" or not deadline:
        return
    if time.time() < deadline:
        return
    choices = room.setdefault("choices", {})
    if "user" in choices and "opponent" not in choices:
        actor = "opponent"
    elif "opponent" in choices and "user" not in choices:
        actor = "user"
    else:
        actor = state.get("current_actor", "user")
    state["log"] = []
    side = state[actor]
    if side.get("current_hp", 0) <= 0:
        return
    damage = min(5, side["current_hp"])
    side["current_hp"] = max(0, side["current_hp"] - damage)
    state["log"].append({
        "actor": actor,
        "damage": damage,
        "timeout": True,
        "player": _player_for_actor(actor),
        "message": f"{side['name']} lost {damage} HP because no move was chosen in time.",
    })
    _append_history(state)
    room["turn_deadline"] = time.time() + 30
    _resolve_timeout_faints(state)
    if state.get("status") == "active":
        if choices:
            choices[actor] = {"type": "timeout"}
            if "user" in choices and "opponent" in choices:
                choices.clear()
        state["current_actor"] = "user"


def _resolve_timeout_faints(state):
    user_healthy = [index for index, side in enumerate(state.get("user_team", [])) if side.get("current_hp", 0) > 0]
    opponent_healthy = [index for index, side in enumerate(state.get("opponent_team", [])) if side.get("current_hp", 0) > 0]
    if not user_healthy or not opponent_healthy:
        state["status"] = "finished"
        state["winner"] = "user" if user_healthy else "opponent" if opponent_healthy else "tie"
        return
    if state["user"].get("current_hp", 0) <= 0:
        state["status"] = "awaiting_user_switch"
        state["winner"] = None
        return
    if state["opponent"].get("current_hp", 0) <= 0:
        state["status"] = "awaiting_opponent_switch"
        state["winner"] = None
        return
    state["status"] = "active"
    state["winner"] = None


def _room_payload(room, player_key):
    opponent_key = "p2" if player_key == "p1" else "p1"
    deadline = room.get("turn_deadline")
    payload = {
        "room_id": room["id"],
        "player": player_key,
        "status": room["status"],
        "players": {
            player_key: {
                "name": room["players"][player_key]["name"],
                "ready": room["players"][player_key]["ready"],
                "team": [
                    {"name": side["name"], "image": side.get("front_image") or side.get("image")}
                    for side in room["players"][player_key].get("team", [])
                ],
            },
            opponent_key: {
                "name": room["players"][opponent_key]["name"],
                "ready": room["players"][opponent_key]["ready"],
                "team": _masked_team(room["players"][opponent_key]),
            },
        },
        "waiting_for": [],
        "choices": {
            "you": room.get("choices", {}).get("user" if player_key == "p1" else "opponent"),
            "opponent_locked": ("opponent" if player_key == "p1" else "user") in room.get("choices", {}),
        },
        "seconds_remaining": max(0, int(deadline - time.time())) if deadline else None,
    }
    if room.get("battle"):
        payload["battle"] = _perspective_state(room["battle"], player_key)
    return payload


def _finish_pvp_setup(room):
    if room["status"] == "team_select" and all(player["ready"] for player in room["players"].values()):
        state = create_team_battle(room["players"]["p1"]["team"], room["players"]["p2"]["team"])
        state["mode"] = "pvp"
        room["battle"] = state
        room["status"] = "battle"
        room["turn_deadline"] = time.time() + 30
    return room


def random_team_profiles(team_size=6):
    """Build two distinct teams entirely from locally cached Pokemon."""
    candidates = list(pokemon_cache.values())
    random.SystemRandom().shuffle(candidates)
    profiles = []
    seen = set()
    for pokemon in candidates:
        pokemon_id = pokemon.get("metadata", {}).get("id")
        stat_names = {stat.get("api_name") for stat in pokemon.get("stats", [])}
        if not pokemon_id or pokemon_id in seen or len(stat_names) < 6:
            continue
        try:
            profile = battle_ready_profile(pokemon)
        except (AttributeError, KeyError, IndexError, TypeError):
            continue
        if not profile.get("moves"):
            continue
        profiles.append(profile)
        seen.add(pokemon_id)
        if len(profiles) == team_size * 2:
            break
    if len(profiles) < team_size * 2:
        raise RuntimeError("At least 12 cached Pokemon are required for a random team battle.")
    return profiles[:team_size], profiles[team_size:]


initialize_app()


# =====================================================
# Routes
# =====================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/manifest.json")
def web_manifest():
    return send_from_directory(app.static_folder, "manifest.json", mimetype="application/manifest+json")


@app.route("/service-worker.js")
def service_worker():
    response = send_from_directory(app.static_folder, "service-worker.js", mimetype="application/javascript")
    response.headers["Cache-Control"] = "no-cache"
    return response

@app.route("/api/status")
def api_status():

    return jsonify({

        "success": True,

        "application": "Pokemon Battle Estimator",

        "version": "0.1.0"

    })


@app.route("/api/pokemon/<pokemon_name>")
def pokemon_lookup(pokemon_name):

    pokemon = fetch_pokemon(pokemon_name)

    if pokemon is None:

        return jsonify({

            "success": False,

            "message": "Pokemon not found."

        }), 404

    pokemon["battle"]["counters"] = matchup_counters(pokemon["name"])

    return jsonify({

        "success": True,

        "pokemon": pokemon

    })

# TEST ENDPOINT
@app.route("/api/battle/test/<user>/<opponent>")
def battle_test(user, opponent):

    # Fetch both Pokémon
    user_pokemon = fetch_pokemon(user)
    opponent_pokemon = fetch_pokemon(opponent)

    if user_pokemon is None:
        return jsonify({
            "success": False,
            "message": f"User Pokémon '{user}' not found."
        }), 404

    if opponent_pokemon is None:
        return jsonify({
            "success": False,
            "message": f"Opponent Pokémon '{opponent}' not found."
        }), 404

    # Build normalized battle profiles
    user_profile = battle_ready_profile(user_pokemon)
    opponent_profile = battle_ready_profile(opponent_pokemon)

    # Evaluate matchup
    result = evaluate_matchup(
        user_profile,
        opponent_profile
    )

    return jsonify({

        "success": True,

        "user": user_profile,

        "opponent": opponent_profile,

        "battle": result

    })


@app.post("/api/battle/start")
def battle_start():
    payload = request.get_json(silent=True) or {}
    user_name = clean_name(payload.get("user", ""))
    opponent_name = clean_name(payload.get("opponent", ""))
    if not user_name or not opponent_name:
        return jsonify({"success": False, "message": "Choose two Pokemon."}), 400

    user_pokemon = fetch_pokemon(user_name)
    opponent_pokemon = fetch_pokemon(opponent_name)
    if not user_pokemon or not opponent_pokemon:
        return jsonify({"success": False, "message": "One or both Pokemon could not be found."}), 404

    battle_id = uuid.uuid4().hex
    state = create_battle(
        battle_ready_profile(user_pokemon),
        battle_ready_profile(opponent_pokemon),
    )
    BATTLES[battle_id] = state
    return jsonify({"success": True, "battle_id": battle_id, "battle": state})


@app.get("/api/battle/<battle_id>")
def battle_state(battle_id):
    state = BATTLES.get(battle_id)
    if not state:
        return jsonify({"success": False, "message": "Battle not found."}), 404
    return jsonify({"success": True, "battle_id": battle_id, "battle": state})


@app.post("/api/battle/<battle_id>/turn")
def battle_turn(battle_id):
    state = BATTLES.get(battle_id)
    if not state:
        return jsonify({"success": False, "message": "Battle not found."}), 404
    payload = request.get_json(silent=True) or {}
    user_move = payload.get("move")
    if not user_move:
        return jsonify({"success": False, "message": "Choose a move."}), 400
    try:
        opponent_move = choose_opponent_move(state["opponent"], state["user"])
        play_turn(state, user_move, opponent_move)
    except ValueError as error:
        return jsonify({"success": False, "message": str(error)}), 400
    return jsonify({
        "success": True,
        "battle_id": battle_id,
        "opponent_move": opponent_move,
        "battle": state,
    })


@app.get("/api/pokemon-names")
def pokemon_name_search():
    query = request.args.get("q", "").strip()
    if len(query) < 3 and not query.isdigit():
        return jsonify({"success": True, "names": []})
    return jsonify({"success": True, "names": pokemon_names(query, limit=12)})


@app.post("/api/team-battle/start")
def team_battle_start():
    try:
        user_team, opponent_team = random_team_profiles()
    except RuntimeError as error:
        return jsonify({"success": False, "message": str(error)}), 503
    battle_id = uuid.uuid4().hex
    state = create_team_battle(user_team, opponent_team)
    BATTLES[battle_id] = state
    return jsonify({"success": True, "battle_id": battle_id, "battle": state})


@app.post("/api/team-battle/<battle_id>/turn")
def team_battle_turn(battle_id):
    state = BATTLES.get(battle_id)
    if not state or state.get("mode") != "team":
        return jsonify({"success": False, "message": "Team battle not found."}), 404
    payload = request.get_json(silent=True) or {}
    user_move = payload.get("move")
    user_switch = payload.get("switch_index")
    opponent_auto = bool(payload.get("opponent_auto"))
    if user_switch is not None and not isinstance(user_switch, int):
        return jsonify({"success": False, "message": "Invalid team slot."}), 400
    if user_move is None and user_switch is None and not opponent_auto:
        return jsonify({"success": False, "message": "Choose a move or switch Pokemon."}), 400
    try:
        opponent_move = None
        opponent_switch = None
        if opponent_auto:
            if state.get("status") == "awaiting_opponent_switch":
                healthy = [
                    index for index, side in enumerate(state["opponent_team"])
                    if side["current_hp"] > 0 and index != state["opponent_active"]
                ]
                if not healthy:
                    return jsonify({"success": False, "message": "No opponent replacement is available."}), 400
                opponent_switch = healthy[0]
            elif state.get("current_actor") != "opponent":
                return jsonify({"success": False, "message": "It is not the opponent's turn."}), 400
            else:
                opponent_switch = choose_opponent_switch(state)
                if opponent_switch is None:
                    opponent_move = choose_opponent_move(state["opponent"], state["user"])
        elif state.get("status") == "active":
            opponent_switch = choose_opponent_switch(state)
            if opponent_switch is None:
                opponent_move = choose_opponent_move(state["opponent"], state["user"])
        play_team_turn(
            state,
            user_move=user_move,
            opponent_move=opponent_move,
            user_switch=user_switch,
            opponent_switch=opponent_switch,
        )
    except (ValueError, IndexError) as error:
        return jsonify({"success": False, "message": str(error)}), 400
    return jsonify({
        "success": True,
        "battle_id": battle_id,
        "opponent_move": opponent_move,
        "opponent_switch": opponent_switch,
        "battle": state,
    })


@app.post("/api/pvp/create")
def pvp_create():
    payload = request.get_json(silent=True) or {}
    room_id = _pvp_code()
    while room_id in PVP_ROOMS:
        room_id = _pvp_code()
    player_id = uuid.uuid4().hex
    room = {
        "id": room_id,
        "status": "waiting",
        "players": {
            "p1": {"id": player_id, "name": payload.get("name") or "Player 1", "ready": False, "team": []},
            "p2": {"id": None, "name": "Waiting...", "ready": False, "team": []},
        },
        "battle": None,
        "choices": {},
        "turn_deadline": None,
    }
    PVP_ROOMS[room_id] = room
    return jsonify({"success": True, "room": _room_payload(room, "p1"), "player_id": player_id})


@app.post("/api/pvp/<room_id>/join")
def pvp_join(room_id):
    room = PVP_ROOMS.get(room_id.upper())
    if not room:
        return jsonify({"success": False, "message": "Room not found."}), 404
    if room["players"]["p2"]["id"]:
        return jsonify({"success": False, "message": "Room is already full."}), 409
    payload = request.get_json(silent=True) or {}
    player_id = uuid.uuid4().hex
    room["players"]["p2"].update({
        "id": player_id,
        "name": payload.get("name") or "Player 2",
        "ready": False,
        "team": [],
    })
    room["status"] = "team_select"
    return jsonify({"success": True, "room": _room_payload(room, "p2"), "player_id": player_id})


@app.get("/api/pvp/<room_id>")
def pvp_status(room_id):
    room = PVP_ROOMS.get(room_id.upper())
    if not room:
        return jsonify({"success": False, "message": "Room not found."}), 404
    player_key = _player_key(room, request.args.get("player_id"))
    if not player_key:
        return jsonify({"success": False, "message": "Invalid player."}), 403
    _finish_pvp_setup(room)
    _apply_pvp_timeout(room)
    return jsonify({"success": True, "room": _room_payload(room, player_key)})


@app.post("/api/pvp/<room_id>/team")
def pvp_team(room_id):
    room = PVP_ROOMS.get(room_id.upper())
    if not room:
        return jsonify({"success": False, "message": "Room not found."}), 404
    payload = request.get_json(silent=True) or {}
    player_key = _player_key(room, payload.get("player_id"))
    if not player_key:
        return jsonify({"success": False, "message": "Invalid player."}), 403
    if room["status"] not in {"waiting", "team_select"}:
        return jsonify({"success": False, "message": "Team selection is closed."}), 400
    if not room["players"]["p2"]["id"]:
        return jsonify({"success": False, "message": "Wait for your friend to join before locking teams."}), 400
    try:
        team = _build_named_team(payload.get("team") or [])
    except ValueError as error:
        return jsonify({"success": False, "message": str(error)}), 400
    room["players"][player_key]["team"] = team
    room["players"][player_key]["ready"] = True
    room["status"] = "team_select"
    _finish_pvp_setup(room)
    return jsonify({"success": True, "room": _room_payload(room, player_key)})


@app.post("/api/pvp/<room_id>/turn")
def pvp_turn(room_id):
    room = PVP_ROOMS.get(room_id.upper())
    if not room or room.get("status") != "battle" or not room.get("battle"):
        return jsonify({"success": False, "message": "PVP battle not found."}), 404
    payload = request.get_json(silent=True) or {}
    player_key = _player_key(room, payload.get("player_id"))
    if not player_key:
        return jsonify({"success": False, "message": "Invalid player."}), 403
    state = room["battle"]
    _apply_pvp_timeout(room)
    if state.get("status") == "finished":
        return jsonify({"success": True, "room": _room_payload(room, player_key)})

    switch_index = payload.get("switch_index")
    move = payload.get("move")
    try:
        actor = _actor_for_player(player_key)
        if switch_index is not None:
            if state.get("status") == "awaiting_user_switch" and actor != "user":
                return jsonify({"success": False, "message": "Waiting for the other player to switch."}), 400
            if state.get("status") == "awaiting_opponent_switch" and actor != "opponent":
                return jsonify({"success": False, "message": "Waiting for the other player to switch."}), 400
            if state.get("status") in {"awaiting_user_switch", "awaiting_opponent_switch"}:
                room.setdefault("choices", {}).clear()
                if actor == "user":
                    play_team_turn(state, user_switch=int(switch_index), auto_switch_opponent=False)
                else:
                    play_team_turn(state, opponent_switch=int(switch_index), auto_switch_opponent=False)
                room["turn_deadline"] = time.time() + 30
                return jsonify({"success": True, "room": _room_payload(room, player_key)})
        if not move:
            if switch_index is None:
                return jsonify({"success": False, "message": "Choose a move."}), 400
        if state.get("status") in {"awaiting_user_switch", "awaiting_opponent_switch"}:
            return jsonify({"success": False, "message": "A fainted Pokemon must be replaced before moves can be chosen."}), 400
        choices = room.setdefault("choices", {})
        if actor in choices:
            return jsonify({"success": True, "room": _room_payload(room, player_key)})
        choices[actor] = _pvp_choice_for_payload(payload)
        _resolve_pvp_choices(room)
    except (ValueError, IndexError) as error:
        return jsonify({"success": False, "message": str(error)}), 400

    return jsonify({"success": True, "room": _room_payload(room, player_key)})






# =====================================================
# Main
# =====================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8005,
        debug=True
    )
