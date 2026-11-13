# UNDERFLOW: Visual MVP (TouchDesigner)

Status: source-code prototype. Not yet verified by launching inside TouchDesigner.
The installer constructs a GPU GLSL scene from versioned source files.
No binary .toe is supplied; save the created project locally.

## 1. Checkout

From PowerShell, after PR #1 was merged:

    git fetch origin
    git switch -c feature/touchdesigner-visual-prototype --track origin/feature/touchdesigner-visual-prototype

If starting fresh:

    git clone -b feature/touchdesigner-visual-prototype https://github.com/lisiidan/unihack.git
    cd unihack

## 2. Generate scene (TouchDesigner)

1. Install TouchDesigner on Windows.
2. Open a new empty TouchDesigner project, save it as underflow.toe in the repository ROOT (same directory as README.md). This ensures project.folder is correct.
3. Open Dialogs > Textport, switch to Py (Python).
4. Enter the following, substituting your actual repository path:

       exec(open(r"D:\unihack\touchdesigner\install.py", encoding="utf-8").read())

5. Go inside /project1/UNDERFLOW. The network contains:
   - environment_glsl — GPU shader, 1280×720.
   - OUT — final TOP image; right-click and choose View.
   - environment_udp — reads UDP datagrams on port 7001.
   - camera -> camera_small — optional 64×36 webcam motion input.
   - frame_update — Execute DAT to feed uniforms every frame.
6. Save (Ctrl+S). Reopening the .toe will reload the external controller from the repo folder.

If shader output is black or shows an error, inspect /project1/UNDERFLOW/environment_glsl_info or Middle-click the GLSL TOP.
Do not add a #version declaration; TouchDesigner inserts it.

## 3. Start gateway

In another PowerShell window from the repository root:

    py -3 -m gateway.main --mode demo --interval 1 --stdout

The installation will show a flowing animated particle field,
bridge silhouette and river. The moving interaction spot follows
a synthetic orbit while camera input is disabled.

Then try real modeled weather and air quality:

    py -3 -m gateway.main --mode live --interval 300 --stdout

No third-party Python packages are required for the gateway. The source
can run even if the projector or camera is not connected.

## 4. Enable camera interaction

Inside UNDERFLOW select the camera TOP:
- Choose your webcam in Device.
- Set Active = On.
- Stand still, then walk/wave in front of the camera.
- Tracking uses FRAME DIFFERENCING on a downsampled 64×36 image sampled
  around 10 times per second. No images are written or uploaded.
- Moving parts create a centroid; nearby particles visibly repel.
- Stationary people are NOT recognized as present. It is a motion-driven
  effect, not human identification and not multi-person tracking.
- Webcam frame orientation may require a horizontal/vertical flip in
  underflow_controller.py (MotionTracker.update).

Camera OFF = automatic visual preview. Camera ON = movement-driven control,
even with no gateway connected.

## Visual refresh — pulling changes

If you already installed the first version of this branch, refresh the source files
in PowerShell from the repository root:

    git pull --ff-only

Then run the same installer again in TouchDesigner Python Textport:

    exec(open(r"D:\unihack\touchdesigner\install.py", encoding="utf-8").read())

Important: **the installer replaces /project1/UNDERFLOW**, so select your
webcam and turn it on again. Save the .toe afterwards.

The refreshed shader adds five luminous currents, a soft atmospheric glow,
a larger motion vortex, outward-moving rings and coherent particle
displacement. Camera input now smooths position and energy to reduce
flicker; this remains a procedural visual field, not fluid simulation.
If the camera is off, a moving synthetic presence demonstrates the effect.

## Timișoara city visual (current branch)

The primary visual is a new illuminated urban atlas: a continuous, wide
Bega canal, contrasted banks, procedural city blocks, weather-driven water
reflections, faint building outlines, and three abstract crossing signals. **This is an artistic schematic, NOT an OSM/GIS river map** and the
crossings do not represent surveyed bridge locations.

The output contains four Text TOPs with additive compositing (fixing
an opaque-source layering issue in older versions):
- city_title: prominent TIMIȘOARA title.
- city_subtitle: UNDERFLOW / BEGA, THE INVISIBLE CITY.
- data_label: LIVE / MODELED, DEMO / SYNTHETIC, STALE, or WAITING,
  European AQI, wind, rainfall, provider timestamps, and CAMS attribution.
- footer_label: coordinates and an explicit ARTISTIC SCHEMATIC disclaimer.

An absent measurement is displayed as "--", never fabricated as zero.
Open-Meteo air quality is a CAMS model, not a sensor on that bridge.
When the gateway has been silent over 15 minutes, the label says STALE
and the visuals transition back toward an artistic baseline.

The user motion effect keeps up to three events for several seconds,
so gestures leave expanding luminous rings in the city artwork.
This is CPU-managed event history, not a true GPU feedback buffer.

### Update an existing TouchDesigner installation

From the folder containing README.md, with this feature branch checked out:

    git pull --ff-only

Then in TouchDesigner Python Textport, using the actual local path:

    exec(open(r"D:\unihack\touchdesigner\install.py", encoding="utf-8").read())

The installer destroys and reconstructs /project1/UNDERFLOW.
It attempts to preserve the chosen camera device and Active setting.
Save a backup of manually edited nodes first. Re-save the .toe afterwards.

To feed real modeled city values, from the repo root:

    py -3 -m gateway.main --mode live --interval 300 --stdout

Important: Demo mode changes the labels to DEMO / SYNTHETIC. If no gateway
is running the display says WAITING FOR DATA, not LIVE. Use only one gateway
process at a time (demo OR live) sending to UDP port 7001.

If typography is missing, inspect city_title, city_subtitle, data_label
and footer_label. All use additive compositing (operand=add). Check the GLSL TOP Info DAT
for shader compilation errors. Tested in GitHub CI for Python behavior,
but requires local TouchDesigner runtime validation.

## 5. Known limits

- No real sensor feed for water/noise/bioparticles; the visuals use
  atmospheric particles, not measured bio-particle counts.
- Output is a single flat 1280×720 image; custom bridge projection mapping
  and brightness calibration must be configured separately.
- Not tested inside TouchDesigner in this development environment. If a
  build has different operator parameter names, note the Textport error
  and adjust the installer against the installed build.
- GLSL TOP draws a procedural animated field, NOT a physical particle
  simulation with persistent particle velocity.
- UDP packets may update faster or slower than underlying API measurements.
- Disclose camera-based motion detection and avoid recording faces.
- Do not call modeled air data a sensor under the bridge.

## Next milestone

User tests + projection calibration + refinement of camera feedback.
Avoid adding unrelated features before obtaining a working scene.

## What success looks like

The OUT view should show a clearly defined turquoise Bega ribbon across a
procedural city atlas; three bright bridge-like crossings; the large title
TIMIȘOARA in the top-left; live/model/demo status and readings at the upper
right; and a small location/source disclaimer along the bottom. Motion makes
large ripples and a local wake, rather than only shoving dots apart.

If OUT still displays the old composition, ensure you updated the checked
out feature branch (git branch --show-current), ran git pull --ff-only,
then reran touchdesigner/install.py in Textport.

If OUT is a red-blue checkerboard, check the GLSL TOP Info DAT:

    print(op('/project1/UNDERFLOW/environment_glsl_info').text)

The CI only verifies Python behavior and static shader contracts; it does NOT
run the GPU shader on your TouchDesigner version. A screenshot of the actual
OUT view is the acceptance check.
