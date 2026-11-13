"""Create the UNDERFLOW TouchDesigner network in a new .toe project.

Run from TouchDesigner's Python Textport (NOT from CPython):
    exec(open(r"D:\path\to\unihack\touchdesigner\install.py", encoding="utf-8").read())

Prerequisite: save your .toe at the root of the cloned repository, so
project.folder points to the directory containing touchdesigner/.
The installer replaces only /project1/UNDERFLOW, never other nodes.
"""
from pathlib import Path
import sys

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

from underflow_controller import reset

scene_root = op("/project1")
if scene_root is None:
    raise RuntimeError("Expected the default TouchDesigner /project1 network")

existing = scene_root.op("UNDERFLOW")
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

shader_dat = scene.op("environment_glsl_pixel")
if shader_dat is None:
    shader_dat = scene.create(textDAT, "pixel_shader")
shader_dat.text = shader_file.read_text(encoding="utf-8")
shader_dat.nodeX, shader_dat.nodeY = -230, -150
glsl.par.pixeldat = shader_dat.path

output = scene.create(nullTOP, "OUT")
glsl.outputConnectors[0].connect(output)
output.nodeX, output.nodeY = 200, -150
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

small = scene.create(resolutionTOP, "camera_small")
camera.outputConnectors[0].connect(small)
small.nodeX, small.nodeY = 210, -400
small.par.outputresolution = "custom"
small.par.resolutionw = 64
small.par.resolutionh = 36

# Lightweight per-frame callback; camera sampling happens every 6th frame.
frame_execute = scene.create(executeDAT, "frame_update")
frame_execute.nodeX, frame_execute.nodeY = 400, -150
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
print("Camera OFF initially. Enable camera.par.active after choosing device.")
print("Save the .toe with Ctrl+S. Check environment_glsl_info for shader errors.")
