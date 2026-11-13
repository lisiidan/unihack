"""Pure-Python UNDERFLOW controls for a TouchDesigner frame callback.

No dependency on the TouchDesigner Python environment at import time.
Movement detection is frame-differencing, NOT person identification.
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def normalized(value):
    """Return 0..1 or None; null input is meaningful."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(number):
        return None
    return clamp(number)


def parse_packet(raw: str) -> dict:
    """Validate the environmental gateway's versioned wire format."""
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported gateway packet")
    mode = data.get("mode")
    if mode not in ("demo", "live"):
        raise ValueError("Unknown gateway mode")
    visuals = data.get("visuals")
    if not isinstance(visuals, dict):
        raise ValueError("Missing visuals")
    return {
        "mode": mode,
        "air": normalized(visuals.get("air_severity")),
        "haze": normalized(visuals.get("haze")),
        "wind": normalized(visuals.get("wind")),
    }


@dataclass
class Motion:
    x: float = 0.5
    y: float = 0.5
    strength: float = 0.0


class MotionTracker:
    """Track moving pixels in downsampled RGB frames (64x36 recommended).

    Never records frames; stores only the previous frame's grayscale data.
    Detects motion, not the presence or count of people.
    """

    def __init__(self, threshold: float = 0.12, minimum_ratio: float = 0.009):
        self.previous = None
        self.threshold = threshold
        self.minimum_ratio = minimum_ratio
        self.motion = Motion()

    def update(self, frame) -> Motion:
        """Accepts numpy HxWxC array or nested RGB lists; 0..1 values."""
        if frame is None:
            return self.motion
        # Float conversion happens only on a 64x36 frame at about 10 Hz.
        h = len(frame)
        w = len(frame[0]) if h else 0
        if not h or not w:
            return self.motion
        current = []
        for row in frame:
            current.append([
                (float(pixel[0]) + float(pixel[1]) + float(pixel[2])) / 3.0
                for pixel in row
            ])
        if self.previous is None or len(self.previous) != h or len(self.previous[0]) != w:
            self.previous = current
            self.motion.strength = 0.0
            return self.motion

        count = 0
        sum_x = 0.0
        sum_y = 0.0
        for y, row in enumerate(current):
            old_row = self.previous[y]
            for x, lum in enumerate(row):
                if abs(lum - old_row[x]) > self.threshold:
                    count += 1
                    sum_x += x
                    sum_y += y
        self.previous = current
        fraction = count / (w * h)
        if fraction < self.minimum_ratio:
            self.motion.strength *= 0.65
        else:
            target_x = sum_x / count / max(1, w - 1)
            # Video orientation is installation-dependent; flip here if needed.
            target_y = 1.0 - sum_y / count / max(1, h - 1)
            self.motion.x += 0.35 * (target_x - self.motion.x)
            self.motion.y += 0.35 * (target_y - self.motion.y)
            self.motion.strength = clamp(fraction * 8.0)
        return self.motion


_RUNTIME = {}


class Runtime:
    def __init__(self):
        self.started = time.monotonic()
        self.last_packet = ""
        self.last_packet_at = -1e9
        self.env = None
        self.tracker = MotionTracker()
        self.frame_no = 0
        self.last_motion_at = -1e9

    def read_udp(self, comp, now: float) -> None:
        dat = comp.op("environment_udp")
        if dat is None or dat.numRows == 0:
            return
        try:
            row = dat.row(dat.numRows - 1)
            raw = next((c.val for c in row if c.val.lstrip().startswith("{")), "")
            if raw and raw != self.last_packet:
                packet = parse_packet(raw)
                self.env = packet
                self.last_packet = raw
                self.last_packet_at = now
        except (ValueError, TypeError, IndexError, KeyError) as err:
            # Keep the previous valid packet; do not spam Textport each frame.
            if self.last_packet != "INVALID":
                print("UNDERFLOW ignored invalid UDP message:", err)
            self.last_packet = "INVALID"

    def read_camera(self, comp, now: float) -> bool:
        camera = comp.op("camera")
        if camera is None or not bool(camera.par.active.eval()):
            return False
        if self.frame_no % 6 != 0:
            return True
        small = comp.op("camera_small")
        try:
            image = small.numpyArray(delayed=True)
            if image is not None:
                motion = self.tracker.update(image)
                if motion.strength >= 0.08:
                    self.last_motion_at = now
        except Exception as err:
            # Hardware/camera issue should not break the visual scene.
            if self.frame_no % 300 == 0:
                print("UNDERFLOW camera unavailable:", err)
        return True

    def frame(self, comp) -> None:
        now = time.monotonic()
        self.frame_no += 1
        self.read_udp(comp, now)
        has_camera = self.read_camera(comp, now)

        # Gateway defaults: artistic baseline, not sensor measurements.
        air, haze, wind = 0.38, 0.22, 0.25
        if self.env is not None and now - self.last_packet_at < 900:
            for key, fallback in (("air", air), ("haze", haze), ("wind", wind)):
                value = self.env[key]
                if value is not None:
                    if key == "air":
                        air = value
                    elif key == "haze":
                        haze = value
                    else:
                        wind = value

        t = now - self.started
        if has_camera:
            motion = self.tracker.motion
            x, y = motion.x, motion.y
            # Fade smoothly after the person stops moving.
            strength = motion.strength * clamp(1.0 - (now - self.last_motion_at) / 3.0)
        else:
            # Explicit motion preview when camera is disabled.
            x = 0.5 + 0.23 * math.sin(t * 0.4)
            y = 0.52 + 0.18 * math.cos(t * 0.25)
            strength = 0.72

        shader = comp.op("environment_glsl")
        if shader is None:
            return
        shader.par.vec0valuex = t
        shader.par.vec0valuey = air
        shader.par.vec0valuez = haze
        shader.par.vec0valuew = wind
        shader.par.vec1valuex = x
        shader.par.vec1valuey = y
        shader.par.vec1valuez = strength
        shader.par.vec1valuew = 0.0


def reset(path: str) -> None:
    _RUNTIME.pop(path, None)


def step(comp) -> None:
    runtime = _RUNTIME.setdefault(comp.path, Runtime())
    runtime.frame(comp)
