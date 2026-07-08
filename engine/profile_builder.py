# ============================================
# Battle Profile Builder
# ============================================

# ============================================
# Battle Profile Builder
# ============================================

def build_battle_profile(pokemon):

    battle = pokemon.get("battle", {})

    stats = {}

    for stat in pokemon.get("stats", []):

        stats[stat["api_name"]] = stat["value"]

        # ============================================
        # Derived Battle Stats
        # ============================================

        attack = stats.get("attack", 0)

        special_attack = stats.get("special-attack", 0)

        defense = stats.get("defense", 0)

        special_defense = stats.get("special-defense", 0)

        speed = stats.get("speed", 0)

        if attack >= special_attack:

            attack_category = "Physical"

            offense_stat = attack

            target_defense = "defense"

        else:

            attack_category = "Special"

            offense_stat = special_attack

            target_defense = "special-defense"

    profile = {

        "version": 1,

        "id": pokemon.get("metadata", {}).get("id"),

        "name": pokemon.get("name"),

        "image": pokemon.get("images", {}).get("official_artwork")
        or pokemon.get("images", {}).get("front_default"),

        "front_image": pokemon.get("images", {}).get("showdown_front")
        or pokemon.get("images", {}).get("official_artwork")
        or pokemon.get("images", {}).get("front_default"),

        "back_image": pokemon.get("images", {}).get("showdown_back")
        or pokemon.get("images", {}).get("back_default")
        or pokemon.get("images", {}).get("official_artwork"),

        "cry": pokemon.get("audio", {}).get("cry"),

        "types": [

            t["name"]

            for t in pokemon.get("types", [])

        ],

        "stats": stats,

        "role": battle.get("role"),

        "nature": battle.get(
            "recommended_nature",
            {}
        ).get("name"),

        "ability": battle.get(
            "recommended_ability",
            {}
        ).get("name"),

        "item": battle.get(
            "recommended_item",
            {}
        ).get("name"),

        "battle_stats": {

        "attack_category": attack_category,

        "offense_stat": offense_stat,

        "target_defense": target_defense,

        "speed": speed,
    
        "defense": defense,

        "special_defense": special_defense

    },


        "tier": battle.get("tier"),

        "moves": battle.get(
            "recommended_moves",
            []
        ),

        "evs": battle.get(
            "evs",
            {}
        ),

        "ivs": battle.get(
            "ivs",
            {}
        )

    }

    return profile
