import json
import os
import httpx
import time
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


#from engine.move_engine import score_move
from engine.move_engine import (
    score_move,
    build_moveset,
    RECOVERY_MOVES,
    SETUP_MOVES,
    HAZARD_MOVES,
    HAZARD_REMOVAL,
    PIVOT_MOVES,
    UTILITY_ATTACKS
)

POKEAPI = "https://pokeapi.co/api/v2"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_DIR = os.path.dirname(BASE_DIR)

OUTPUT_FILE = os.path.join(
    PROJECT_DIR,
    "data",
    "competitive_builds.json"
)

MOVE_CACHE_FILE = os.path.join(
    PROJECT_DIR,
    "cache",
    "move_cache.json"
)

TIER_FILE = os.path.join(

    PROJECT_DIR,

    "data",

    "tier_database.json"

)

TIER_DB = {}


client = httpx.Client(timeout=30)

competitive_db = {}
move_cache = {}

def fetch_pokemon(pokemon_id):

    url = f"{POKEAPI}/pokemon/{pokemon_id}"

    response = client.get(url)

    if response.status_code != 200:
        return None

    return response.json()

def fetch_move(move_name):

    move_name = move_name.lower()

    # -------------------------
    # Cache
    # -------------------------

    if move_name in move_cache:

        return move_cache[move_name]

    url = f"{POKEAPI}/move/{move_name}"

    response = client.get(url)

    if response.status_code != 200:

        return None

    data = response.json()

    move = {

        "name": data["name"],

        "type": data["type"]["name"],

        "power": data["power"],

        "accuracy": data["accuracy"],

        "pp": data["pp"],

        "priority": data["priority"],

        "damage_class":
            data["damage_class"]["name"]

    }

    move_cache[move_name] = move

    save_move_cache()

    return move

def get_stats(data):

    stats = {}

    for s in data["stats"]:

        stats[s["stat"]["name"]] = s["base_stat"]

    return stats

def get_abilities(data):

    abilities = []

    for a in data["abilities"]:

        abilities.append(

            a["ability"]["name"]

        )

    return abilities

def get_types(data):

    return [

        t["type"]["name"]

        for t in data["types"]

    ]

def get_moves(data):

    return [

        move["move"]["name"]

        for move in data["moves"]

    ]

def determine_role(stats):

    atk = stats["attack"]

    spa = stats["special-attack"]

    hp = stats["hp"]

    defense = stats["defense"]

    spd = stats["special-defense"]

    speed = stats["speed"]

    bulk = hp + defense + spd

    if speed >= 120:

        return "Fast Sweeper"

    if atk >= 120:

        return "Physical Sweeper"

    if spa >= 120:

        return "Special Sweeper"

    if bulk >= 300:

        return "Tank"

    return "Balanced"

def determine_attack_category(stats):

    if stats["attack"] >= stats["special-attack"]:

        return "physical"

    return "special"

def recommend_nature(role):

    table = {

        "Physical Sweeper":"Jolly",

        "Special Sweeper":"Timid",

        "Fast Sweeper":"Timid",

        "Tank":"Impish",

        "Balanced":"Adamant"

    }

    return table.get(role,"Serious")

ABILITY_PRIORITY = [

    "protean",

    "libero",

    "regenerator",

    "magic-guard",

    "multiscale",

    "levitate",

    "intimidate",

    "speed-boost",

    "beast-boost",

    "adaptability",

    "technician",

    "huge-power",

    "rough-skin",

    "flash-fire",

    "sturdy"
]

def recommend_ability(abilities):

    for priority in ABILITY_PRIORITY:

        if priority in abilities:

            return priority.replace("-", " ").title()

    return abilities[0].replace("-", " ").title()

def recommend_item(role):

    items = {

        "Physical Sweeper":"Choice Band",

        "Special Sweeper":"Choice Specs",

        "Fast Sweeper":"Life Orb",

        "Tank":"Leftovers",

        "Balanced":"Leftovers"

    }

    return items[role]

def select_best_moves(

    move_names,

    pokemon_types,

    attack_category,

    role

):

    scored_moves = []

    for move_name in move_names:

        move = fetch_move(move_name)

        if move is None:
            continue

        move_name = move["name"].lower()

        # ==========================================
        # Status Move Filtering
        # ==========================================

        if move["damage_class"] == "status":

            important = (

                move_name in RECOVERY_MOVES

                or move_name in SETUP_MOVES

                or move_name in HAZARD_MOVES

                or move_name in HAZARD_REMOVAL

                or move_name in PIVOT_MOVES

            )

            if not important:
                continue

        # ==========================================
        # Skip weak attacking moves
        # ==========================================

        elif move["power"] is not None:

            if (

                    move["power"] < 50

                    and move_name not in UTILITY_ATTACKS

            ):
                continue

        score = score_move(

            move,

            pokemon_types,

            attack_category

        )

        scored_moves.append({

            "name": move["name"],

            "score": score,

            "type": move["type"]

        })

    scored_moves.sort(

        key=lambda x: x["score"],

        reverse=True

    )

    best = build_moveset(

        scored_moves,

        role,

        pokemon_types

    )

    print("\n========== MOVESET ==========")
    print("Role :", role)
    print(best)
    print("=============================\n")

    return best

def load_move_cache():

    global move_cache

    if os.path.exists(MOVE_CACHE_FILE):

        with open(
            MOVE_CACHE_FILE,
            "r",
            encoding="utf8"
        ) as f:

            move_cache = json.load(f)

    else:

        move_cache = {}

def load_tier_database():

    global TIER_DB

    if not os.path.exists(TIER_FILE):

        TIER_DB = {}

        return

    with open(

        TIER_FILE,

        "r",

        encoding="utf8"

    ) as f:

        TIER_DB = json.load(f)


def save_move_cache():

    with open(
        MOVE_CACHE_FILE,
        "w",
        encoding="utf8"
    ) as f:

        json.dump(
            move_cache,
            f,
            indent=4
        )

def build_database():

    total = 1025

    for pokemon_id in range(1,total+1):

        print(f"{pokemon_id}/{total}")

        data = fetch_pokemon(pokemon_id)

        if data is None:

            continue

        stats = get_stats(data)

        types = get_types(data)

        moves = get_moves(data)

        abilities = get_abilities(data)

        role = determine_role(stats)

        attack_category = determine_attack_category(stats)

        best_moves = select_best_moves(

            moves,

            types,

            attack_category,

            role

        )

        competitive_db[str(pokemon_id)] = {

            "name": data["name"],

            "competitive": {

                "tier": TIER_DB.get(data["name"],"Unknown"),

                "role": role,

                "battle_score": None,

                "nature": recommend_nature(role),

                "ability": recommend_ability(abilities),

                "items": [

                    recommend_item(role)

                ],

                "moves": best_moves

            }

        }

        time.sleep(0.1)

    with open(

        OUTPUT_FILE,

        "w",

        encoding="utf8"

    ) as f:

        json.dump(

            competitive_db,

            f,

            indent=4

        )

    print("Finished.")


# =====================================================
# Main
# =====================================================

if __name__ == "__main__":

    load_move_cache()

    load_tier_database()

    build_database()

    move = fetch_move("flamethrower")

    print(move)

