"""Pure-Python tests: no TouchDesigner installation required."""
import ast
import json
import unittest
from pathlib import Path

from touchdesigner.underflow_controller import (MotionTracker, normalized, parse_packet, parse_scene_packet, format_hud, data_time_label)


class VisualControlsTests(unittest.TestCase):
    def test_demo_wire_packet(self):
        raw = json.dumps({
            "schema_version": 1, "mode": "demo",
            "visuals": {"air_severity": 0.8, "haze": 0.4, "wind": 0.2},
        })
        packet = parse_packet(raw)
        self.assertEqual(packet, {
            "mode": "demo", "air": 0.8, "haze": 0.4, "wind": 0.2
        })

    def test_null_and_bad_numbers_are_not_fabricated(self):
        self.assertIsNone(normalized(None))
        self.assertIsNone(normalized("NaN"))
        self.assertIsNone(normalized(True))
        self.assertEqual(normalized(1.7), 1.0)
        self.assertEqual(normalized(-0.4), 0.0)
        packet = parse_packet(json.dumps({
            "schema_version": 1, "mode": "live",
            "visuals": {"air_severity": None, "haze": "NaN"},
        }))
        self.assertIsNone(packet["air"])
        self.assertIsNone(packet["haze"])
        self.assertIsNone(packet["wind"])

    def test_real_packet_metadata_and_hud(self):
        raw = json.dumps({
            "schema_version": 1, "mode": "live",
            "visuals": {"air_severity": 0.62, "haze": 0.42, "wind": 0.15},
            "weather": {
                "wind_kmh": 6.5, "precipitation_mm": 1.0,
                "observed_at": "2026-11-13T18:00:00+00:00"
            },
            "air": {
                "european_aqi": 62, "observed_at": "2026-11-13T17:00Z"
            }
        })
        packet = parse_scene_packet(raw)
        self.assertEqual(packet["rain"], 0.25)
        self.assertEqual(packet["wind_kmh"], 6.5)
        self.assertIn("LIVE / MODELED", format_hud(packet, 3))
        self.assertIn("AIR AQI 62", format_hud(packet, 3))
        self.assertIn("RAIN 1.0 mm", format_hud(packet, 3))
        self.assertIn("STALE / LAST PACKET", format_hud(packet, 901))
        self.assertEqual(data_time_label("2026-11-13T17:00Z"),
                         "13 Nov 17:00 UTC")

    def test_demo_is_not_labeled_live(self):
        packet = parse_scene_packet(json.dumps({
            "schema_version": 1, "mode": "demo",
            "visuals": {"air_severity": 0.5},
            "weather": None, "air": None,
        }))
        hud = format_hud(packet, 0)
        self.assertIn("DEMO / SYNTHETIC", hud)
        self.assertNotIn("LIVE / MODELED", hud)
        self.assertIn("WIND --", hud)
        self.assertIsNone(packet["rain"])
        self.assertIn("WAITING FOR DATA", format_hud(None, 100))

    def test_invalid_and_missing_readings(self):
        packet = parse_scene_packet(json.dumps({
            "schema_version": 1, "mode": "live",
            "visuals": {},
            "weather": {"wind_kmh": "nan", "precipitation_mm": None},
            "air": {"european_aqi": "bad", "observed_at": "not-a-date"},
        }))
        self.assertIsNone(packet["wind_kmh"])
        self.assertIsNone(packet["rain"])
        self.assertIn("AIR AQI --", format_hud(packet, 0))
        self.assertEqual(data_time_label("not-a-date"), "N/A")

    def test_rejects_wrong_versions(self):
        for raw in ["{}", "[]", '{"schema_version":2,"mode":"demo","visuals":{}}',
                    '{"schema_version":1,"mode":"fake","visuals":{}}']:
            with self.assertRaises(ValueError):
                parse_packet(raw)

    def test_motion_from_frame_difference(self):
        tracker = MotionTracker()
        empty = [[(0.0, 0.0, 0.0) for _ in range(20)] for _ in range(20)]
        changed = [[(0.0, 0.0, 0.0) for _ in range(20)] for _ in range(20)]
        for y in range(6, 12):
            for x in range(12, 18):
                changed[y][x] = (1.0, 1.0, 1.0)
        self.assertEqual(tracker.update(empty).strength, 0.0)
        motion = tracker.update(changed)
        self.assertGreater(motion.strength, 0.0)
        self.assertGreater(motion.x, 0.58)  # First update reacts without a long lag.
        self.assertGreater(motion.y, 0.5)
        prior_strength = motion.strength
        self.assertLess(tracker.update(changed).strength, prior_strength)

    def test_touchdesigner_installer_parses_without_runtime(self):
        root = Path(__file__).resolve().parents[1]
        for file in ("touchdesigner/install.py", "touchdesigner/underflow_controller.py"):
            ast.parse((root / file).read_text(encoding="utf-8"), filename=file)
        installer = (root / "touchdesigner/install.py").read_text(encoding="utf-8")
        controller = (root / "touchdesigner/underflow_controller.py").read_text(encoding="utf-8")
        self.assertIn("importlib.reload(underflow_controller)", installer)
        self.assertIn("self.frame_no % 2", controller)
        self.assertIn('scene.create(textTOP, "data_label")', installer)
        self.assertIn("glsl.par.vec = 6", installer)

    def test_shader_has_required_td_contract(self):
        shader = (Path(__file__).resolve().parents[1] /
                  "touchdesigner/shaders/underflow.frag").read_text(encoding="utf-8")
        self.assertFalse(any(line.lstrip().startswith("#version") for line in shader.splitlines()))
        for token in ("uniform vec4 uState;", "uniform vec4 uPerson;",
                      "uniform vec4 uEnv;", "uniform vec4 uTrail0;",
                      "begaCenter", "TDOutputSwizzle", "fragColor"):
            self.assertIn(token, shader)


if __name__ == "__main__":
    unittest.main()
