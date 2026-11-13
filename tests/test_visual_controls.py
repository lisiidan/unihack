"""Pure-Python tests: no TouchDesigner installation required."""
import ast
import json
import unittest
from pathlib import Path

from touchdesigner.underflow_controller import MotionTracker, normalized, parse_packet


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
        self.assertGreater(motion.x, 0.5)
        self.assertGreater(motion.y, 0.5)
        self.assertLess(tracker.update(changed).strength, motion.strength)

    def test_touchdesigner_installer_parses_without_runtime(self):
        root = Path(__file__).resolve().parents[1]
        for file in ("touchdesigner/install.py", "touchdesigner/underflow_controller.py"):
            ast.parse((root / file).read_text(encoding="utf-8"), filename=file)

    def test_shader_has_required_td_contract(self):
        shader = (Path(__file__).resolve().parents[1] /
                  "touchdesigner/shaders/underflow.frag").read_text(encoding="utf-8")
        self.assertFalse(any(line.lstrip().startswith("#version") for line in shader.splitlines()))
        for token in ("uniform vec4 uState;", "uniform vec4 uPerson;",
                      "TDOutputSwizzle", "fragColor"):
            self.assertIn(token, shader)


if __name__ == "__main__":
    unittest.main()
