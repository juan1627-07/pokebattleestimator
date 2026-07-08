import json
import os
import httpx
from bs4 import BeautifulSoup

OUTPUT_FILE = "../data/tier_database.json"

URL = "https://www.smogon.com/dex/sv/formats/ou/"

client = httpx.Client(timeout=30)

tier_db = {}


def fetch_tier_list(url, tier):

    print(f"Downloading {tier}...")

    response = client.get(url)

    if response.status_code != 200:

        print("Failed:", tier)

        return

    soup = BeautifulSoup(

        response.text,

        "html.parser"

    )

    links = soup.select("a[href*='/dex/sv/pokemon/']")

    for link in links:

        name = link.text.strip().lower()

        if name:

            tier_db[name] = tier


def build():

    fetch_tier_list(

        "https://www.smogon.com/dex/sv/formats/ou/",

        "OU"

    )

    fetch_tier_list(

        "https://www.smogon.com/dex/sv/formats/uu/",

        "UU"

    )

    fetch_tier_list(

        "https://www.smogon.com/dex/sv/formats/ru/",

        "RU"

    )

    fetch_tier_list(

        "https://www.smogon.com/dex/sv/formats/nu/",

        "NU"

    )

    fetch_tier_list(

        "https://www.smogon.com/dex/sv/formats/pu/",

        "PU"

    )

    with open(

        OUTPUT_FILE,

        "w",

        encoding="utf8"

    ) as f:

        json.dump(

            tier_db,

            f,

            indent=4,

            sort_keys=True

        )

    print("Saved", len(tier_db), "Pokemon")


if __name__ == "__main__":

    build()