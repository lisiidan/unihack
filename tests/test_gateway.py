"""Run: python -m unittest discover -s tests -v"""
import unittest
from unittest.mock import patch

from gateway.main import (
    AIR_URL, WEATHER_URL, clamp01, demo_snapshot, live_snapshot,
    make_snapshot, parse_air, parse_weather,
)


class GatewayTests(unittest.TestCase):
    def test_clamp(self):
        self.assertEqual(clamp01(-5), 0)
        self.assertEqual(clamp01(.5), .5)
        self.assertEqual(clamp01(100), 1)

    def test_demo_is_explicitly_synthetic(self):
        packet = demo_snapshot(0)
        self.assertEqual(packet["mode"], "demo")
        self.assertEqual(packet["weather"]["kind"], "simulated")
        self.assertIsNone(packet["noise"])
        self.assertIsNone(packet["bioparticles"])
        self.assertIsNone(packet["water"])

    def test_missing_data_maps_to_null(self):
        packet = make_snapshot("live", None, None)
        self.assertIsNone(packet["visuals"]["air_severity"])
        self.assertIsNone(packet["visuals"]["wind"])

    def test_parse_weather_and_air(self):
        weather = parse_weather({
            "time": "2026-11-13T18:00", "temperature_2m": 7,
            "relative_humidity_2m": 70, "wind_speed_10m": 12,
            "precipitation": 0,
        })
        air = parse_air({
            "time": "2026-11-13T18:00", "european_aqi": 80,
            "pm2_5": 20, "pm10": 40,
        })
        packet = make_snapshot("live", weather, air)
        self.assertEqual(weather["observed_at"], "2026-11-13T18:00Z")
        self.assertEqual(packet["visuals"]["air_severity"], .8)
        self.assertEqual(packet["visuals"]["wind"], .3)

    @patch("gateway.main.fetch_json")
    def test_one_provider_down_does_not_fake_other(self, fetch):
        def side_effect(url, fields):
            if url == WEATHER_URL:
                raise OSError("offline")
            if url == AIR_URL:
                return {"time": "2026-11-13T18:00", "european_aqi": 40,
                        "pm2_5": 10, "pm10": 20}
            raise AssertionError(url)
        fetch.side_effect = side_effect
        packet = live_snapshot()
        self.assertIsNone(packet["weather"])
        self.assertEqual(packet["air"]["european_aqi"], 40)

    @patch("gateway.main.fetch_json", side_effect=OSError("offline"))
    def test_both_providers_down_errors(self, _fetch):
        with self.assertRaises(RuntimeError):
            live_snapshot()


if __name__ == "__main__":
    unittest.main()
