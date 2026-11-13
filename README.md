# UNDERFLOW — The Invisible City

Interactive immersive-art installation concept for UniHack / Timișoara.

The space beneath a bridge becomes a living expression of the city's normally invisible environment. Air conditions change color and haze, wind guides movement, and pedestrians disturb a field of particles.

## Architecture (48-hour MVP)

    Open-Meteo (weather + modeled air quality)
                 |
          Python data gateway
                 | JSON / UDP (127.0.0.1:7001)
                 v
          TouchDesigner .toe
          |       |         |
        GLSL   Particles   Webcam tracking
                 |
              Projector

TouchDesigner project is NOT built yet. This repository currently contains the gateway, a wire format, unit tests and setup notes.

## Visual prototype (Step 2)

This branch includes a TouchDesigner scene **installer**, a GLSL particle/river
shader, camera motion tracking, and environment-driven color controls.
The .toe binary is not generated until you run the installer inside TouchDesigner.

1. Save a new .toe inside the repository root.
2. From TouchDesigner's Python Textport execute touchdesigner/install.py.
3. Start the Python gateway in demo or live mode.
4. View the /project1/UNDERFLOW/OUT TOP and optionally enable the webcam.

Complete instructions: [docs/visual-prototype.md](docs/visual-prototype.md).

## Quick start

Requires Python 3.10+. No pip install needed. From repository root:

    python -m gateway.main --mode demo --interval 1 --stdout

Demo data is SYNTHETIC and explicitly marked as mode=demo.

Fetch modeled weather + air quality for Timișoara:

    python -m gateway.main --mode live --interval 300 --stdout

Send one packet and stop:

    python -m gateway.main --mode demo --once --stdout

Override UDP target: --host 192.168.x.x --port 7001

Run tests:

    python -m unittest discover -s tests -v

## Data protocol

Each UDP datagram is one UTF-8 JSON object. Main fields:

- mode: demo or live
- emitted_at: UTC timestamp of gateway transmission
- weather: modeled estimates or null
- air: modeled estimates or null
- noise, bioparticles, water: null (no verified feed connected)
- visuals.air_severity, visuals.haze, visuals.wind: 0..1 or null

A missing provider never triggers invented sensor values. When all live providers fail, no misleading packet is sent.

Air quality is a CAMS model estimate, NOT a measurement from a physical sensor under the bridge. Open-Meteo model results may change less often than packet transmissions. Inspect observed_at.

## Docs

- [TouchDesigner receiver setup](docs/touchdesigner.md)
- [Open-Meteo Weather API](https://open-meteo.com/en/docs)
- [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api)

Attribution: Weather data by Open-Meteo. Air-quality model data via Open-Meteo and CAMS ENSEMBLE. Review use conditions before public/commercial deployment.

## Scope boundaries

No verified live water, noise or bioparticle feed has been connected. These must stay disabled until the source is validated. Camera tracking and projection mapping are planned for subsequent PRs.
