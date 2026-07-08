import unittest
from unittest.mock import patch

import app as application
from engine.team_battle import create_team_battle


MOVE = {
    "name": "tackle", "type": "normal", "power": 40,
    "accuracy": 100, "priority": 0, "damage_class": "physical",
}


def member(index, speed=80):
    return {
        "name": f"Pokemon {index}", "types": ["normal"],
        "stats": {"hp": 70, "attack": 90, "defense": 80,
                  "special-attack": 70, "special-defense": 80, "speed": speed},
        "ability": None, "item": None, "moves": [dict(MOVE)],
        "image": None, "front_image": None, "back_image": None,
    }


class ApplicationTests(unittest.TestCase):
    def test_databases_initialize_when_module_is_imported(self):
        self.assertGreater(len(application.pokemon_cache), 0)
        self.assertEqual(len(application.COMPETITIVE_DB), 1025)

    def test_current_cache_is_used_without_network(self):
        self.assertEqual(application.pokemon_cache["charizard"]["_cache_version"], application.CACHE_VERSION)
        with patch.object(application.client, "get", side_effect=AssertionError("network called")):
            pokemon = application.fetch_pokemon("charizard")
        self.assertEqual(pokemon["name"], "Charizard")
        self.assertEqual(pokemon["battle"]["tier"], "ZU")
        self.assertEqual(
            pokemon["battle"]["recommended_moves"],
            ["flamethrower", "hurricane", "focus-blast", "scorching-sands"],
        )

    def test_uncached_showdown_pokemon_falls_back_without_api_success(self):
        application.pokemon_cache.pop("rampardos", None)
        response = type("Response", (), {"status_code": 404})()
        with patch.object(application.client, "get", return_value=response):
            pokemon = application.fetch_pokemon("Rampardos")
        self.assertIsNotNone(pokemon)
        self.assertEqual(pokemon["name"], "Rampardos")
        self.assertEqual(pokemon["metadata"]["id"], 409)
        self.assertEqual(pokemon["types"][0]["name"], "rock")

    def test_battle_api_starts_and_plays_a_turn(self):
        cached = application.pokemon_cache["charizard"]
        with patch.object(application, "fetch_pokemon", return_value=cached):
            with application.app.test_client() as client:
                started = client.post("/api/battle/start", json={"user": "charizard", "opponent": "charizard"})
                self.assertEqual(started.status_code, 200)
                payload = started.get_json()
                move = payload["battle"]["user"]["moves"][0]["name"]
                turn = client.post(f"/api/battle/{payload['battle_id']}/turn", json={"move": move})
                self.assertEqual(turn.status_code, 200)
                self.assertEqual(turn.get_json()["battle"]["turn"], 1)

    def test_random_team_api_creates_distinct_six_member_teams_and_switches(self):
        with application.app.test_client() as client:
            started = client.post("/api/team-battle/start")
            self.assertEqual(started.status_code, 200)
            payload = started.get_json()
            state = payload["battle"]
            self.assertEqual(len(state["user_team"]), 6)
            self.assertEqual(len(state["opponent_team"]), 6)
            ids = {member["id"] for member in state["user_team"] + state["opponent_team"]}
            self.assertEqual(len(ids), 12)
            switched = client.post(
                f"/api/team-battle/{payload['battle_id']}/turn",
                json={"switch_index": 1},
            )
            self.assertEqual(switched.status_code, 200)
            switched_state = switched.get_json()["battle"]
            self.assertEqual(switched_state["user_active"], 1)
            self.assertEqual(switched_state["turn"], 1)
            self.assertLessEqual(
                switched_state["user"]["current_hp"],
                switched_state["user"]["max_hp"],
            )

    def test_pvp_turn_waits_for_both_players_before_resolution(self):
        users = [member(i, 100) for i in range(1, 7)]
        opponents = [member(i, 50) for i in range(7, 13)]
        room_id = "LOCK01"
        application.PVP_ROOMS[room_id] = {
            "id": room_id,
            "status": "battle",
            "players": {
                "p1": {"id": "P1", "name": "One", "ready": True, "team": users},
                "p2": {"id": "P2", "name": "Two", "ready": True, "team": opponents},
            },
            "battle": create_team_battle(users, opponents),
            "choices": {},
            "turn_deadline": application.time.time() + 30,
        }
        try:
            with application.app.test_client() as client:
                first = client.post(f"/api/pvp/{room_id}/turn", json={"player_id": "P1", "move": "tackle"})
                self.assertEqual(first.status_code, 200)
                first_payload = first.get_json()["room"]
                self.assertEqual(first_payload["battle"]["turn"], 0)
                self.assertEqual(first_payload["choices"]["you"]["type"], "move")

                second = client.post(f"/api/pvp/{room_id}/turn", json={"player_id": "P2", "move": "tackle"})
                self.assertEqual(second.status_code, 200)
                second_payload = second.get_json()["room"]
                self.assertEqual(second_payload["battle"]["turn"], 1)
                self.assertEqual(application.PVP_ROOMS[room_id]["choices"], {})
        finally:
            application.PVP_ROOMS.pop(room_id, None)

    def test_autocomplete_endpoint_starts_after_three_characters(self):
        with application.app.test_client() as client:
            short = client.get("/api/pokemon-names?q=ch").get_json()
            complete = client.get("/api/pokemon-names?q=char").get_json()
        self.assertEqual(short["names"], [])
        self.assertIn("Charizard", complete["names"])


if __name__ == "__main__":
    unittest.main()
