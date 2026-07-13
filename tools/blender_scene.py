"""Runs INSIDE Blender: import GLB, gold material, studio setup, render views.

Invoked by tools/render.py as:
  blender -b -P tools/blender_scene.py -- <glb> <outdir> <views_csv> <WxH> <samples>
Dependency-free on purpose: only bpy/mathutils are available.
"""
import os
import sys

import bpy
import mathutils

argv = sys.argv[sys.argv.index("--") + 1 :]
glb_path, outdir, views_csv, res_str, samples_str = argv
views = views_csv.split(",")
res_x, res_y = (int(v) for v in res_str.split("x"))
samples = int(samples_str)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()

bpy.ops.import_scene.gltf(filepath=glb_path)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    print("RENDER_ERROR no meshes imported", file=sys.stderr)
    sys.exit(1)

# gold material (base color: commonly used measured gold albedo)
gold = bpy.data.materials.new("Gold")
gold.use_nodes = True
bsdf = gold.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (1.0, 0.766, 0.336, 1.0)
bsdf.inputs["Metallic"].default_value = 1.0
bsdf.inputs["Roughness"].default_value = 0.22
for o in meshes:
    o.data.materials.clear()
    o.data.materials.append(gold)
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.shade_auto_smooth()

# scene bounds
mins = mathutils.Vector((1e18,) * 3)
maxs = mathutils.Vector((-1e18,) * 3)
for o in meshes:
    for corner in o.bound_box:
        wc = o.matrix_world @ mathutils.Vector(corner)
        mins = mathutils.Vector(map(min, mins, wc))
        maxs = mathutils.Vector(map(max, maxs, wc))
center = (mins + maxs) / 2
size = max((maxs - mins).length, 1e-6)

# lighting: uniform gray world as a giant softbox + two suns for definition.
# Suns are distance-independent, so this works at any model scale.
world = bpy.data.worlds.new("Studio")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.35, 0.35, 0.36, 1.0)
bg.inputs["Strength"].default_value = 1.0


def add_sun(name, direction, energy):
    """direction = the way the light travels (sun local -Z points along it)."""
    data = bpy.data.lights.new(name, type="SUN")
    data.energy = energy
    data.angle = 0.3  # soft shadows
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    d = mathutils.Vector(direction).normalized()
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return obj


add_sun("Key", (-0.6, 0.6, -1.0), 4.0)   # from upper front-left, pointing down-back
add_sun("Rim", (0.2, -1.0, -0.4), 2.0)

cam_data = bpy.data.cameras.new("Cam")
cam_data.clip_start = size / 1000
cam_data.clip_end = size * 20
cam = bpy.data.objects.new("Cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = samples
scene.cycles.use_denoising = True
scene.render.resolution_x = res_x
scene.render.resolution_y = res_y

VIEW_DIRS = {
    "persp": mathutils.Vector((1.0, -1.0, 0.7)),
    "top": mathutils.Vector((0.001, -0.001, 1.0)),
    "front": mathutils.Vector((0.0, -1.0, 0.25)),
    "detail": mathutils.Vector((1.0, -1.0, 0.7)),
}


def aim(target, direction, dist):
    cam.location = target + direction.normalized() * dist
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()


for view in views:
    direction = VIEW_DIRS[view]
    if view == "detail":
        # zoom onto the +X edge of the model (a few links of a chain)
        aim(mathutils.Vector((maxs.x, center.y, center.z)), direction, size * 0.45)
    else:
        aim(center, direction, size * 1.6)
    out = os.path.join(outdir, f"{view}.png")
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print(f"RENDER_DONE {out}")
