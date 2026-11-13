"""Pure-Python UNDERFLOW controls for a TouchDesigner frame callback.

No dependency on the TouchDesigner Python environment at import time.
Movement detection is frame-differencing, NOT person identification.
"""
from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime
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


def optional_number(value):
    """Finite number or None; do not mistake missing readings for zero."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def parse_scene_packet(raw: str) -> dict:
    """Extend the stable shader controls with optional source metadata."""
    basic = parse_packet(raw)
    data = json.loads(raw)
    weather = data.get("weather") if isinstance(data.get("weather"), dict) else {}
    air = data.get("air") if isinstance(data.get("air"), dict) else {}
    rain = optional_number(weather.get("precipitation_mm"))
    basic.update({
        "aqi": optional_number(air.get("european_aqi")),
        "wind_kmh": optional_number(weather.get("wind_kmh")),
        "rain_mm": rain,
        "rain": clamp(max(0.0, rain) / 4.0) if rain is not None else None,
        "air_time": air.get("observed_at"),
        "weather_time": weather.get("observed_at"),
    })
    return basic


def data_time_label(value) -> str:
    """Show provider's observation/model time, not when UDP was sent."""
    if not isinstance(value, str) or not value:
        return "N/A"
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return when.strftime("%d %b %H:%M UTC")
    except ValueError:
        return "N/A"


def format_hud(packet: dict | None, age: float) -> str:
    if packet is None:
        return ("WAITING FOR DATA  |  ARTISTIC BASELINE\n"
                "AIR AQI --  /  WIND --  /  RAIN --\n"
                "Run: python -m gateway.main --mode live")
    stale = age > 900.0
    label = ("STALE / LAST PACKET" if stale else
             "DEMO / SYNTHETIC" if packet["mode"] == "demo" else
             "LIVE / MODELED")
    aqi = f'{packet["aqi"]:.0f}' if packet["aqi"] is not None else "--"
    wind = f'{packet["wind_kmh"]:.0f}' if packet["wind_kmh"] is not None else "--"
    rain = f'{packet["rain_mm"]:.1f}' if packet["rain_mm"] is not None else "--"
    return (
        f"{label}   |   AIR AQI {aqi}   |   WIND {wind} km/h   |   RAIN {rain} mm\n"
        f"AIR {data_time_label(packet['air_time'])}   /   "
        f"WEATHER {data_time_label(packet['weather_time'])}\n"
        "Open-Meteo / CAMS model; visual interpretation, not a bridge sensor"
    )



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

    def __init__(self, threshold: float = 0.10, minimum_ratio: float = 0.006):
        self.previous = None
        self.threshold = threshold
        self.minimum_ratio = minimum_ratio
        self.motion = Motion()

    def update(self, frame) -> Motion:
        """Accepts numpy HxWxC array or nested RGB lists; 0..1 values."""
        if frame is None:
            return self.motion
        # Convert only a small 64x36 image; normally sampled at ~30 Hz.
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
            # Smooth release: sudden drops to zero made the old repulsion pop.
            self.motion.strength *= 0.88
        else:
            target_x = sum_x / count / max(1, w - 1)
            # Video orientation is installation-dependent; flip here if needed.
            target_y = 1.0 - sum_y / count / max(1, h - 1)
            # Faster target response; retain enough smoothing to suppress jitter.
            self.motion.x += 0.34 * (target_x - self.motion.x)
            self.motion.y += 0.34 * (target_y - self.motion.y)
            target_strength = clamp(fraction * 9.0)
            self.motion.strength += 0.55 * (target_strength - self.motion.strength)
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
        self.last_trail_at = -1e9
        self.trails = []  # (x, y, strength, timestamp) for 3 visible ripples
        self.smoothed_env = [0.38, 0.22, 0.25, 0.0]
        self.last_frame_at = self.started
        self.last_hud_at = -1e9

    def read_udp(self, comp, now: float) -> None:
        dat = comp.op("environment_udp")
        if dat is None or dat.numRows == 0:
            return
        try:
            row = dat.row(dat.numRows - 1)
            raw = next((c.val for c in row if c.val.lstrip().startswith("{")), "")
            if raw and raw != self.last_packet:
                packet = parse_scene_packet(raw)
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
        if self.frame_no % 2 != 0:
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

        # No packet = explicitly artistic baseline. Smooth transitions to avoid
        # changes in model data causing abrupt flashes.
        target = [0.38, 0.22, 0.25, 0.0]
        packet_age = now - self.last_packet_at
        if self.env is not None and packet_age < 900:
            for i, key in enumerate(("air", "haze", "wind", "rain")):
                value = self.env.get(key)
                if value is not None:
                    target[i] = value
        dt = clamp(now - self.last_frame_at, 0.0, 0.1)
        self.last_frame_at = now
        alpha = 1.0 - math.exp(-dt / 2.5)
        for i in range(4):
            self.smoothed_env[i] += alpha * (target[i] - self.smoothed_env[i])
        air, haze, wind, rain = self.smoothed_env

        t = now - self.started
        if has_camera:
            motion = self.tracker.motion
            x, y = motion.x, motion.y
            # Energy decays smoothly; rings move outward after the gesture.
            strength = motion.strength
            since_motion = clamp(now - self.last_motion_at, 0.0, 4.0)
        else:
            # Explicit motion preview when camera is disabled.
            x = 0.5 + 0.23 * math.sin(t * 0.4)
            y = 0.52 + 0.18 * math.cos(t * 0.25)
            strength = 0.88
            since_motion = t % 3.2

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
        shader.par.vec1valuew = since_motion
        shader.par.vec2valuex = rain
        shader.par.vec2valuey = 1.0 if self.env is not None and packet_age < 900 else 0.0

        # Event memory gives a visually persistent gesture trail WITHOUT
        # requiring GPU frame feedback or storing camera recordings.
        last_x, last_y = (self.trails[0][0], self.trails[0][1]) if self.trails else (-1, -1)
        far_enough = (x - last_x) ** 2 + (y - last_y) ** 2 > 0.0007
        if strength >= 0.14 and now - self.last_trail_at > 0.16 and far_enough:
            self.trails.insert(0, (x, y, strength, now))
            self.trails = self.trails[:3]
            self.last_trail_at = now
        for i in range(3):
            values = (self.trails[i] if i < len(self.trails) else None)
            fields = [0.0, 0.0, 0.0, 5.0] if values is None else [
                values[0], values[1], values[2], min(now - values[3], 5.0)
            ]
            for suffix, value in zip("xyzw", fields):
                getattr(shader.par, f"vec{i + 3}value{suffix}").val = value

        # Text TOPs only need refresh when the actual HUD string changes.
        # Do not force text texture rerender on every frame.
        if now - self.last_hud_at >= 0.5:
            self.last_hud_at = now
            hud = comp.op("data_label")
            if hud is not None:
                label = format_hud(self.env, packet_age)
                if hud.par.text.eval() != label:
                    hud.par.text = label


def reset(path: str) -> None:
    _RUNTIME.pop(path, None)


def step(comp) -> None:
    runtime = _RUNTIME.setdefault(comp.path, Runtime())
    runtime.frame(comp)
