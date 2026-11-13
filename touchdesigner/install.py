r"""Create the UNDERFLOW TouchDesigner network in a new .toe project.

Run from TouchDesigner's Python Textport (NOT from CPython):
    exec(open(r"D:\path\to\unihack\touchdesigner\install.py", encoding="utf-8").read())

Prerequisite: save your .toe at the root of the cloned repository, so
project.folder points to the directory containing touchdesigner/.
The installer replaces only /project1/UNDERFLOW, never other nodes.
"""
from pathlib import Path
import sys
import importlib

repo_root = Path(project.folder)
source_dir = repo_root / "touchdesigner"
shader_file = source_dir / "shaders" / "underflow.frag"
controller_file = source_dir / "underflow_controller.py"
if not (shader_file.is_file() and controller_file.is_file()):
    raise RuntimeError(
        "Save the TouchDesigner .toe in the repository root BEFORE installing. "
        "Expected: " + str(shader_file)
    )
if str(source_dir) not in sys.path:
    sys.path.insert(0, str(source_dir))

import underflow_controller
# Without reload, TouchDesigner keeps the old camera-tracking code in sys.modules.
importlib.reload(underflow_controller)
reset = underflow_controller.reset

scene_root = op("/project1")
if scene_root is None:
    raise RuntimeError("Expected the default TouchDesigner /project1 network")

existing = scene_root.op("UNDERFLOW")
old_camera_active = False
old_camera_device = None
if existing is not None and existing.op("camera") is not None:
    previous_camera = existing.op("camera")
    old_camera_active = bool(previous_camera.par.active.eval())
    try:
        old_camera_device = previous_camera.par.device.eval()
    except AttributeError:
        pass
if existing is not None:
    reset(existing.path)
    existing.destroy()

scene = scene_root.create(baseCOMP, "UNDERFLOW")
scene.nodeX, scene.nodeY = 0, 0

# Pixel shader output; all drawing takes place on GPU.
glsl = scene.create(glslTOP, "environment_glsl")
glsl.nodeX, glsl.nodeY = 0, -150
glsl.par.mode = "vertexpixel"
glsl.par.outputresolution = "custom"
glsl.par.resolutionw = 1280
glsl.par.resolutionh = 720
glsl.par.vec = 6  # environment, visitor, rain, three recent gesture ripples
glsl.par.vec0name = "uState"
glsl.par.vec0valuex = 0.0
glsl.par.vec0valuey = 0.38
glsl.par.vec0valuez = 0.22
glsl.par.vec0valuew = 0.25
glsl.par.vec1name = "uPerson"
glsl.par.vec1valuex = 0.5
glsl.par.vec1valuey = 0.5
glsl.par.vec1valuez = 0.7
glsl.par.vec1valuew = 0.0
glsl.par.vec2name = "uEnv"
glsl.par.vec2valuex = 0.0
glsl.par.vec2valuey = 0.0
for i in range(3):
    index = i + 3
    getattr(glsl.par, f"vec{index}name").val = f"uTrail{i}"
    getattr(glsl.par, f"vec{index}valuex").val = 0.0
    getattr(glsl.par, f"vec{index}valuey").val = 0.0
    getattr(glsl.par, f"vec{index}valuez").val = 0.0
    getattr(glsl.par, f"vec{index}valuew").val = 5.0

shader_dat = scene.op("environment_glsl_pixel")
if shader_dat is None:
    shader_dat = scene.create(textDAT, "pixel_shader")
shader_dat.text = shader_file.read_text(encoding="utf-8")
shader_dat.nodeX, shader_dat.nodeY = -230, -150
glsl.par.pixeldat = shader_dat.path

# Two minimal museum labels composited OVER the live visual.
# Text TOP's Comp Over Input avoids the need for an additional Composite TOP.
title = scene.create(textTOP, "city_title")
title.nodeX, title.nodeY = 200, -150
glsl.outputConnectors[0].connect(title)
title.par.compoverinput = True
title.par.operand = "over"
title.par.text = "TIMIȘOARA  /  UNDERFLOW\nCANALUL BEGA · THE INVISIBLE CITY"
title.par.outputresolution = "useinput"
title.par.fontautosize = "nofit"
title.par.fontsizex = 25
title.par.keepfontratio = True
title.par.alignx = "left"
title.par.aligny = "top"
title.par.positionunit = "fraction"
title.par.position1 = 0.045
title.par.position2 = 0.94
title.par.fontcolorr = 0.84
title.par.fontcolorg = 0.96
title.par.fontcolorb = 0.97
title.par.fontalpha = 0.94
title.par.bgalpha = 0.0

data_label = scene.create(textTOP, "data_label")
data_label.nodeX, data_label.nodeY = 380, -150
title.outputConnectors[0].connect(data_label)
data_label.par.compoverinput = True
data_label.par.operand = "over"
data_label.par.text = "WAITING FOR DATA  /  ARTISTIC BASELINE"
data_label.par.outputresolution = "useinput"
data_label.par.fontautosize = "nofit"
data_label.par.fontsizex = 14
data_label.par.keepfontratio = True
data_label.par.alignx = "left"
data_label.par.aligny = "top"
data_label.par.positionunit = "fraction"
data_label.par.position1 = 0.045
data_label.par.position2 = 0.80
data_label.par.fontcolorr = 0.64
data_label.par.fontcolorg = 0.83
data_label.par.fontcolorb = 0.87
data_label.par.fontalpha = 0.96
data_label.par.bgalpha = 0.0

output = scene.create(nullTOP, "OUT")
data_label.outputConnectors[0].connect(output)
output.nodeX, output.nodeY = 570, -150
try:
    output.viewerActive = True
except AttributeError:
    pass

# An independent Python process supplies environment JSON.
udp = scene.create(udpinDAT, "environment_udp")
udp.nodeX, udp.nodeY = -230, -400
udp.par.active = False
udp.par.port = 7001
udp.par.format = "permessage"
udp.par.clamp = True
udp.par.maxlines = 5
udp.par.active = True

# Optional camera: OFF until the operator chooses an actual webcam.
camera = scene.create(videodeviceinTOP, "camera")
camera.nodeX, camera.nodeY = 0, -400
camera.par.active = False
if old_camera_device is not None:
    try:
        camera.par.device = old_camera_device
    except (AttributeError, ValueError):
        pass
camera.par.active = old_camera_active

small = scene.create(resolutionTOP, "camera_small")
camera.outputConnectors[0].connect(small)
small.nodeX, small.nodeY = 210, -400
small.par.outputresolution = "custom"
small.par.resolutionw = 64
small.par.resolutionh = 36

# Lightweight per-frame callback; camera sampling happens every 2nd frame.
frame_execute = scene.create(executeDAT, "frame_update")
frame_execute.nodeX, frame_execute.nodeY = 765, -150
frame_execute.par.framestart = False
frame_execute.text = '''def onFrameStart(frame):
    import sys
    from pathlib import Path
    scripts = str(Path(project.folder) / 'touchdesigner')
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from underflow_controller import step
    step(me.parent())
    return
'''
frame_execute.par.active = True
frame_execute.par.framestart = True

print("UNDERFLOW installed:", scene.path)
print("Visual output:", output.path)
print("Data receiver: UDP 127.0.0.1:7001")
print("Camera state restored if it existed. Otherwise choose device and set Active = On.")
print("Save the .toe with Ctrl+S. Check environment_glsl_info for shader errors.")
