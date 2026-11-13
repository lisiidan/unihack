# TouchDesigner receiver — first integration

Integration instructions, NOT a prebuilt .toe file.

## Smoke test

1. Open TouchDesigner, create a new project.
2. Add a UDP In DAT, name it environment_udp.
3. Set local UDP network port to 7001, enable it. Make the complete received datagrams visible; parameter names may vary by build.
4. Run this from repository root:

    python -m gateway.main --mode demo --interval 1 --stdout

5. Inspect the UDP In DAT output. Demo values vary over time.
6. Stop Python with Ctrl+C.

## Extract values

A Python expression may parse the most recent JSON datagram in a Text DAT, after verifying the actual format of your UDP In DAT:

    import json
    raw = op('environment_udp').text.strip()
    packet = json.loads(raw.splitlines()[-1])
    severity = packet['visuals']['air_severity']

Some UDP In DAT configurations format messages as tables or prepend metadata. Inspect the DAT first; adapt parsing to the last received JSON payload.

## TouchDesigner signal mapping

- visuals.air_severity: atmosphere tint; modeled European AQI / 100, clamped to 0..1
- visuals.haze: opacity; modeled PM2.5 / 50, clamped
- visuals.wind: flow; modeled wind speed / 40, clamped
- noise, bioparticles, water: null until verified integrations exist
- mode: demo is synthetic; live uses retrieved modeled conditions
- weather.kind and air.kind: simulated or modeled
- observed_at: model's timestamp, explicitly UTC
- emitted_at: gateway transmission time, not measurement time

These mappings are ARTISTIC, not regulatory thresholds.

Null signals must disable corresponding effects or use an explicitly labeled artistic baseline. Never present modeled or demo numbers as physical measurements from under the bridge.

## Next milestone

- Teammate owns and commits one TouchDesigner project file (.toe).
- Webcam tracking (Video Device In TOP + blob/motion extraction).
- Particle field responding to pedestrian movement.
- Optional sound and projection calibration.
- Verified integrations for noise, bioparticles, water.
