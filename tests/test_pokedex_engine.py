import unittest

from engine.pokedex_engine import matchup_counters, pokemon_names


class PokedexTests(unittest.TestCase):
    def test_autocomplete_requires_prefix_and_returns_names(self):
        self.assertIn("Charizard", pokemon_names("char", limit=12))
        self.assertIn("Bulbasaur", pokemon_names("bul", limit=12))

    def test_five_counters_have_super_effective_pressure(self):
        counters = matchup_counters("Charizard")
        self.assertEqual(len(counters), 5)
        self.assertTrue(all(counter["multiplier"] >= 2 for counter in counters))


if __name__ == "__main__":
    unittest.main()
