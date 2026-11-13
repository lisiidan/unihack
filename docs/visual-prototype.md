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
