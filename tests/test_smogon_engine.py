import unittest

from engine.smogon_engine import get_smogon_build


class SmogonDataTests(unittest.TestCase):
    def test_current_showdown_tier_is_loaded(self):
        self.assertEqual(get_smogon_build("Garganacl")["tier"], "OU")
        self.assertEqual(get_smogon_build("Mewtwo")["tier"], "Uber")

    def test_top_usage_moves_are_loaded(self):
        build = get_smogon_build("Garganacl")
        self.assertEqual(build["source_month"], "2026-06")
        self.assertEqual(build["moves"], ["salt-cure", "recover", "protect", "stealth-rock"])


if __name__ == "__main__":
    unittest.main()
