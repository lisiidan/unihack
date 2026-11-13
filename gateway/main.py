"""UNDERFLOW: environment data -> JSON over UDP. Python 3.10+, stdlib only."""
from __future__ import annotations

import argparse
import json
import math
import socket
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CITY = {"name": "Timisoara", "latitude": 45.7489, "longitude": 21.2087}
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def fetch_json(base_url: str, fields: str) -> dict[str, Any]:
    params = urlencode({
        "latitude": CITY["latitude"],
        "longitude": CITY["longitude"],
        "current": fields,
        "timezone": "UTC",
    })
    request = Request(
        f"{base_url}?{params}",
        headers={"User-Agent": "underflow-hackathon/0.1"},
    )
    with urlopen(request, timeout=10) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not isinstance(data.get("current"), dict):
        raise ValueError("Invalid API response: missing 'current' object")
    return data["current"]


def reading_time(value: Any) -> str:
    """Open-Meteo UTC local timestamp lacks an offset; append Z."""
    if not isinstance(value, str) or not value:
        raise ValueError("Missing model timestamp")
    return value if value.endswith("Z") else value + "Z"


def parse_weather(current: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "Open-Meteo Weather API",
        "kind": "modeled",
        "observed_at": reading_time(current.get("time")),
        "temperature_c": float(current["temperature_2m"]),
        "humidity_pct": float(current["relative_humidity_2m"]),
        "wind_kmh": float(current["wind_speed_10m"]),
        "precipitation_mm": float(current["precipitation"]),
    }


def parse_air(current: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "Open-Meteo / CAMS",
        "kind": "modeled",
        "observed_at": reading_time(current.get("time")),
        "european_aqi": float(current["european_aqi"]),
        "pm2_5_ug_m3": float(current["pm2_5"]),
        "pm10_ug_m3": float(current["pm10"]),
    }


def make_snapshot(mode: str, weather: dict[str, Any] | None,
                  air: dict[str, Any] | None) -> dict[str, Any]:
    """Null means missing data. Never substitute fake sensor values."""
    return {
        "schema_version": 1,
        "project": "UNDERFLOW",
        "mode": mode,
        "emitted_at": utc_now(),
        "location": CITY,
        "weather": weather,
        "air": air,
        "noise": None,
        "bioparticles": None,
        "water": None,
        "visuals": {
            # Artistic mappings, not regulatory thresholds.
            "air_severity": clamp01(air["european_aqi"] / 100) if air else None,
            "haze": clamp01(air["pm2_5_ug_m3"] / 50) if air else None,
            "wind": clamp01(weather["wind_kmh"] / 40) if weather else None,
        },
    }


def live_snapshot() -> dict[str, Any]:
    weather = None
    air = None
    try:
        weather = parse_weather(fetch_json(
            WEATHER_URL,
            "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
        ))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[weather] unavailable: {exc}", file=sys.stderr)
    try:
        air = parse_air(fetch_json(AIR_URL, "european_aqi,pm2_5,pm10"))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[air] unavailable: {exc}", file=sys.stderr)
    if weather is None and air is None:
        raise RuntimeError("No live data; refusing to send fabricated values")
    return make_snapshot("live", weather, air)


def demo_snapshot(elapsed_seconds: float) -> dict[str, Any]:
    """Synthetic animation values, explicitly labeled demo."""
    aqi = 55.0 + 35.0 * math.sin(elapsed_seconds / 14)
    wind = 13.0 + 9.0 * math.sin(elapsed_seconds / 11)
    weather = {
        "source": "synthetic", "kind": "simulated",
        "observed_at": utc_now(),
        "temperature_c": 18.0, "humidity_pct": 65.0,
        "wind_kmh": round(wind, 2), "precipitation_mm": 0.0,
    }
    air = {
        "source": "synthetic", "kind": "simulated",
        "observed_at": utc_now(),
        "european_aqi": round(aqi, 2),
        "pm2_5_ug_m3": round(15.0 + aqi / 5, 2),
        "pm10_ug_m3": round(25.0 + aqi / 4, 2),
    }
    return make_snapshot("demo", weather, air)


def run(mode: str, host: str, port: int, interval: float,
        once: bool, stdout: bool) -> None:
    start = time.monotonic()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        while True:
            try:
                snapshot = (demo_snapshot(time.monotonic() - start)
                            if mode == "demo" else live_snapshot())
                payload = json.dumps(snapshot, separators=(",", ":"), allow_nan=False)
                udp.sendto(payload.encode("utf-8"), (host, port))
                if stdout:
                    print(payload, flush=True)
                else:
                    print(f"{snapshot['emitted_at']} sent {mode} -> {host}:{port}",
                          flush=True)
            except (OSError, ValueError, RuntimeError) as exc:
                print(f"[gateway] {exc}", file=sys.stderr, flush=True)
            if once:
                break
            time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="UNDERFLOW -> TouchDesigner UDP")
    parser.add_argument("--mode", choices=("demo", "live"), default="demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7001)
    parser.add_argument("--interval", type=float, default=None,
                        help="seconds; defaults: 1 demo, 300 live")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be 1..65535")
    interval = (1.0 if args.mode == "demo" else 300.0) if args.interval is None else args.interval
    if interval <= 0:
        parser.error("--interval must be positive")
    run(args.mode, args.host, args.port, interval, args.once, args.stdout)


if __name__ == "__main__":
    main()
