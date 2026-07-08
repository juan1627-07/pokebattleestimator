"""Download local Pokemon artwork and battle sprites.

This script is intentionally standalone. It can be rerun safely and skips files
that already exist.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import urllib.error
import urllib.request


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POKEDEX_FILE = os.path.join(BASE_DIR, "data", "showdown_pokedex.json")
ASSET_DIR = os.path.join(BASE_DIR, "static", "pokemon-assets")
USER_AGENT = "PokemonPvPAssetDownloader/1.0"


def showdown_id(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def showdown_file_id(value):
    text = str(value or "").lower().replace("'", "").replace(".", "")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def url_exists(url, timeout=12):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            return response.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None


def download_one(target, urls):
    if os.path.exists(target) and os.path.getsize(target) > 0:
        return "skipped", target
    os.makedirs(os.path.dirname(target), exist_ok=True)
    for url in urls:
        data = url_exists(url)
        if data:
            temp = f"{target}.tmp"
            with open(temp, "wb") as handle:
                handle.write(data)
            os.replace(temp, target)
            return "downloaded", target
    return "missing", target


def asset_jobs(entry_key, entry):
    num = entry.get("num")
    name = entry.get("name") or entry_key
    sprite_id = showdown_id(entry_key)
    file_id = showdown_file_id(name)
    showdown_candidates = list(dict.fromkeys([file_id, sprite_id]))

    if isinstance(num, int) and num > 0:
        yield (
            os.path.join(ASSET_DIR, "official-artwork", f"{num}.png"),
            [f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{num}.png"],
        )
        yield (
            os.path.join(ASSET_DIR, "official-artwork-shiny", f"{num}.png"),
            [f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/shiny/{num}.png"],
        )
        yield (
            os.path.join(ASSET_DIR, "sprites", "front", f"{num}.png"),
            [f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{num}.png"],
        )
        yield (
            os.path.join(ASSET_DIR, "sprites", "back", f"{num}.png"),
            [f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/back/{num}.png"],
        )
        yield (
            os.path.join(ASSET_DIR, "sprites", "front-shiny", f"{num}.png"),
            [f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/shiny/{num}.png"],
        )
        yield (
            os.path.join(ASSET_DIR, "sprites", "back-shiny", f"{num}.png"),
            [f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/back/shiny/{num}.png"],
        )

    yield (
        os.path.join(ASSET_DIR, "showdown", "front", f"{sprite_id}.gif"),
        [f"https://play.pokemonshowdown.com/sprites/ani/{candidate}.gif" for candidate in showdown_candidates],
    )
    yield (
        os.path.join(ASSET_DIR, "showdown", "back", f"{sprite_id}.gif"),
        [f"https://play.pokemonshowdown.com/sprites/gen5ani-back/{candidate}.gif" for candidate in showdown_candidates],
    )


def main():
    with open(POKEDEX_FILE, "r", encoding="utf-8") as handle:
        pokedex = json.load(handle)

    jobs = []
    seen_targets = set()
    for entry_key, entry in pokedex.items():
        for target, urls in asset_jobs(entry_key, entry):
            if target in seen_targets:
                continue
            seen_targets.add(target)
            jobs.append((target, urls))

    counts = {"downloaded": 0, "skipped": 0, "missing": 0}
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(download_one, target, urls) for target, urls in jobs]
        for index, future in enumerate(as_completed(futures), start=1):
            status, target = future.result()
            counts[status] += 1
            if index % 100 == 0 or status == "missing":
                print(f"{index}/{len(jobs)} {status}: {os.path.relpath(target, ASSET_DIR)}")

    print("Done:", counts)
    print("Asset folder:", ASSET_DIR)


if __name__ == "__main__":
    main()
