"""Local, move-aware Pokemon type effectiveness."""


TYPE_CHART = {
    "normal": ({}, {"rock", "steel"}, {"ghost"}),
    "fire": ({"grass", "ice", "bug", "steel"}, {"fire", "water", "rock", "dragon"}, set()),
    "water": ({"fire", "ground", "rock"}, {"water", "grass", "dragon"}, set()),
    "electric": ({"water", "flying"}, {"electric", "grass", "dragon"}, {"ground"}),
    "grass": ({"water", "ground", "rock"}, {"fire", "grass", "poison", "flying", "bug", "dragon", "steel"}, set()),
    "ice": ({"grass", "ground", "flying", "dragon"}, {"fire", "water", "ice", "steel"}, set()),
    "fighting": ({"normal", "ice", "rock", "dark", "steel"}, {"poison", "flying", "psychic", "bug", "fairy"}, {"ghost"}),
    "poison": ({"grass", "fairy"}, {"poison", "ground", "rock", "ghost"}, {"steel"}),
    "ground": ({"fire", "electric", "poison", "rock", "steel"}, {"grass", "bug"}, {"flying"}),
    "flying": ({"grass", "fighting", "bug"}, {"electric", "rock", "steel"}, set()),
    "psychic": ({"fighting", "poison"}, {"psychic", "steel"}, {"dark"}),
    "bug": ({"grass", "psychic", "dark"}, {"fire", "fighting", "poison", "flying", "ghost", "steel", "fairy"}, set()),
    "rock": ({"fire", "ice", "flying", "bug"}, {"fighting", "ground", "steel"}, set()),
    "ghost": ({"psychic", "ghost"}, {"dark"}, {"normal"}),
    "dragon": ({"dragon"}, {"steel"}, {"fairy"}),
    "dark": ({"psychic", "ghost"}, {"fighting", "dark", "fairy"}, set()),
    "steel": ({"ice", "rock", "fairy"}, {"fire", "water", "electric", "steel"}, set()),
    "fairy": ({"fighting", "dragon", "dark"}, {"fire", "poison", "steel"}, set()),
}


def get_move_multiplier(move_type, defending_types, defender_ability=None):
    """Return one move's multiplier against all of the defender's types."""
    move_type = str(move_type).lower()
    defending_types = [str(value).lower() for value in defending_types]
    ability = str(defender_ability or "").lower().replace(" ", "-")

    if (ability == "levitate" and move_type == "ground") or (
        ability == "flash-fire" and move_type == "fire"
    ):
        return 0.0

    strong, resisted, immune = TYPE_CHART.get(move_type, (set(), set(), set()))
    multiplier = 1.0
    for defend_type in defending_types:
        if defend_type in immune:
            return 0.0
        if defend_type in strong:
            multiplier *= 2
        elif defend_type in resisted:
            multiplier *= 0.5
    return multiplier


def get_type_multiplier(attacking_types, defending_types):
    """Compatibility helper: return the best single attacking type."""
    multipliers = [get_move_multiplier(t, defending_types) for t in attacking_types]
    return max(multipliers, default=1.0)
