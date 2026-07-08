"""Build local tiers and moves from Pokemon Showdown and Smogon usage stats."""

import gzip
import json
import os
import re
from datetime import date, timedelta

import httpx


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(PROJECT_DIR, "data", "smogon_competitive.json")
POKEDEX_OUTPUT_FILE = os.path.join(PROJECT_DIR, "data", "showdown_pokedex.json")
MOVE_CACHE_FILE = os.path.join(PROJECT_DIR, "cache", "move_cache.json")
FORMATS_DATA_URL = "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/formats-data.ts"
POKEDEX_URL = "https://play.pokemonshowdown.com/data/pokedex.json"
STATS_BASE = "https://www.smogon.com/stats"
FORMATS = {
    "Uber": "gen9ubers",
    "OU": "gen9ou",
    "UU": "gen9uu",
    "RU": "gen9ru",
    "NU": "gen9nu",
    "PU": "gen9pu",
    "ZU": "gen9zu",
    "LC": "gen9lc",
}


def showdown_id(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def previous_month():
    first = date.today().replace(day=1)
    return (first - timedelta(days=1)).strftime("%Y-%m")


def parse_tiers(source):
    result = {}
    pattern = re.compile(r"\n\t([a-zA-Z0-9]+): \{(.*?)\n\t\},", re.S)
    for pokemon_id, body in pattern.findall(source):
        match = re.search(r'\btier:\s*["\']([^"\']+)', body)
        if match:
            result[pokemon_id] = match.group(1)
    return result


def preferred_format(tier):
    clean = str(tier).replace("(", "").replace(")", "")
    if clean in FORMATS:
        return FORMATS[clean]
    return {
        "UUBL": "gen9ou", "RUBL": "gen9uu", "NUBL": "gen9ru",
        "PUBL": "gen9nu", "NFE": "gen9zu",
    }.get(clean)


def build(month=None):
    month = month or previous_month()
    client = httpx.Client(timeout=90, follow_redirects=True, headers={"User-Agent": "PokemonBattleEstimator/1.0"})
    formats_source = client.get(FORMATS_DATA_URL).raise_for_status().text
    tiers = parse_tiers(formats_source)
    pokedex = client.get(POKEDEX_URL).raise_for_status().json()

    with open(MOVE_CACHE_FILE, "r", encoding="utf-8") as handle:
        move_cache = json.load(handle)
    move_names = {showdown_id(name): name for name in move_cache}

    usage = {}
    for tier, format_name in FORMATS.items():
        url = f"{STATS_BASE}/{month}/chaos/{format_name}-1500.json.gz"
        response = client.get(url)
        if response.status_code != 200:
            print(f"Skipping unavailable {format_name}: HTTP {response.status_code}")
            continue
        document = json.loads(gzip.decompress(response.content))
        usage[format_name] = document.get("data", {})
        print(f"Loaded {format_name}: {len(usage[format_name])} Pokemon")

    output = {}
    all_names = set(tiers)
    for dataset in usage.values():
        all_names.update(showdown_id(name) for name in dataset)

    indexed_usage = {
        format_name: {showdown_id(name): values for name, values in dataset.items()}
        for format_name, dataset in usage.items()
    }
    for pokemon_id in sorted(all_names):
        tier = tiers.get(pokemon_id, "Unknown")
        desired = preferred_format(tier)
        candidates = []
        for format_name, dataset in indexed_usage.items():
            values = dataset.get(pokemon_id)
            if values:
                priority = 1 if format_name == desired else 0
                candidates.append((priority, values.get("Raw count", 0), format_name, values))
        moves = []
        source_format = None
        if candidates:
            _, _, source_format, values = max(candidates, key=lambda entry: (entry[0], entry[1]))
            ranked = sorted(values.get("Moves", {}).items(), key=lambda entry: entry[1], reverse=True)
            for move_id, move_usage in ranked:
                move_name = move_names.get(showdown_id(move_id))
                if move_name and move_name not in moves:
                    moves.append(move_name)
                if len(moves) == 4:
                    break
        output[pokemon_id] = {
            "tier": tier,
            "moves": moves,
            "format": source_format,
            "source_month": month,
        }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
    compact_pokedex = {}
    for pokemon_id, entry in pokedex.items():
        if entry.get("num", 0) <= 0:
            continue
        compact_pokedex[pokemon_id] = {
            "name": entry.get("name"),
            "num": entry.get("num"),
            "types": [value.lower() for value in entry.get("types", [])],
            "base_stats": entry.get("baseStats", {}),
            "tier": tiers.get(pokemon_id, entry.get("tier", "Unknown")),
            "base_species": entry.get("baseSpecies"),
        }
    with open(POKEDEX_OUTPUT_FILE, "w", encoding="utf-8") as handle:
        json.dump(compact_pokedex, handle, separators=(",", ":"), sort_keys=True)
    print(f"Saved {len(output)} entries to {OUTPUT_FILE}")
    print(f"Saved {len(compact_pokedex)} entries to {POKEDEX_OUTPUT_FILE}")


if __name__ == "__main__":
    build(os.environ.get("SMOGON_MONTH"))
