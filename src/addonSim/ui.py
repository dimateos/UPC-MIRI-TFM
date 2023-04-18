import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

from . import utils
from mathutils import Vector, Matrix

# TODO: some access from UI to toggle dynamically?
class DEV:
    debug = True

    ui_vals = True
    logs = True
    logs_skipped = [
        #{'OP_FLOW'}
    ]


# -------------------------------------------------------------------

def DEV_log(msg, type = {'DEV'}, ui = None):
    if not DEV.logs: return
    if type in DEV.logs_skipped: return

    print(type, msg)
    if ui: ui.report(type, msg)
    #ui.report({'INFO'}, "Operation successful!")
    #ui.report({'ERROR'}, "Operation failed!")

def DEV_drawVal(layout: types.UILayout, msg, value):
    if not DEV.ui_vals: return
    layout.label(text=f"{msg}: {value}", icon="BLENDER")

# -------------------------------------------------------------------

def draw_refresh(cfg : MW_gen_cfg, layout: types.UILayout):
    row = layout.box().row()
    row.scale_y = 1.5
    split = row.split(factor=0.75)
    split.prop(cfg, "meta_auto_refresh", toggle=True, icon_only=False, icon='FILE_REFRESH')
    split.prop(cfg, "meta_refresh", toggle=True, icon_only=True, icon='FILE_REFRESH')

def draw_summary(cfg : MW_gen_cfg, layout: types.UILayout):
    # TODO: maybe scene prop to togggle show instead of object

    box = layout.box()
    box.prop(cfg, "meta_show_summary", toggle=True)
    if cfg.meta_show_summary:
        col = box.column()
        col.enabled = False

        # filter out some properties shown
        filtered_props = [ "meta", "name" ]
        for prop_name in cfg.keys():
            if utils.match_anySub(prop_name, filtered_props):
                continue

            col.row().prop(cfg, prop_name, text=prop_name)
            #prop_value = cfg[prop_name]
            #col.row().label(text=prop_name + ": " + str(prop_value))

def draw_inspect(obj: types.Object, layout: types.UILayout):
    mainBox = layout.box()
    mainCol = mainBox.column()
    mainCol.label(text="Inspect: " + obj.name_full)

    # TODO: maybe for vertices too, not just whole objects
    box = mainCol.box()
    col = box.column()
    col.label(text="Type: " + obj.type, icon="MESH_DATA")
    if obj.type == "MESH":
        mesh: types.Mesh = obj.data
        col.label(text=f"V: {len(mesh.vertices)}   E: {len(mesh.edges)}   F: {len(mesh.polygons)}   T: {len(mesh.loop_triangles)}")

    # shared decimal format
    fmt = ">6.3f"
    fmt_vec = f"({{:{fmt}}}, {{:{fmt}}}, {{:{fmt}}})"
    from math import degrees

    # group world
    box = mainCol.box()
    col = box.column()
    col.label(text="World transform")

    matrix: Matrix = obj.matrix_world
    pos = matrix.to_translation()
    col.label(text=f"pos: {fmt_vec}".format(*pos))
    rot = matrix.to_euler()
    rot_deg = tuple(degrees(r) for r in rot)
    col.label(text=f"rot:  {fmt_vec}".format(*rot_deg))
    sca = matrix.to_scale()
    col.label(text=f"sca: {fmt_vec}".format(*sca))

    # group local
    box = col.box()
    col = box.column()
    col.label(text="Local transform")

    matrix: Matrix = obj.matrix_basis
    pos = matrix.to_translation()
    col.label(text=f"pos: {fmt_vec}".format(*pos))
    rot = matrix.to_euler()
    rot_deg = tuple(degrees(r) for r in rot)
    col.label(text=f"rot:  {fmt_vec}".format(*rot_deg))
    sca = matrix.to_scale()
    col.label(text=f"sca: {fmt_vec}".format(*sca))


# -------------------------------------------------------------------

def draw_gen_cfg(cfg : MW_gen_cfg, layout: types.UILayout, context: types.Context):
    draw_refresh(cfg, layout)

    box = layout.box()
    col = box.column()

    rowsub = col.row()
    rowsub.alignment = "LEFT"
    rowsub.label(text="Point Source:")
    split = rowsub.split()
    split.enabled = False
    split.alignment = "LEFT"
    split.label(text=cfg.struct_nameOriginal)
    col.prop(cfg, "struct_nameSufix")

    rowsub = col.row()
    rowsub.prop(cfg, "source")

    rowsub = col.row()
    rowsub.prop(cfg, "source_limit")
    rowsub = col.row()
    rowsub.prop(cfg, "source_noise")
    rowsub.prop(cfg, "rnd_seed")

    box = layout.box()
    col = box.column()
    col.label(text="Generation:")
    rowsub = col.row(align=True)
    rowsub.prop(cfg, "margin_box_bounds")
    rowsub.prop(cfg, "margin_face_bounds")
    rowsub = col.row(align=True)
    rowsub.prop(cfg, "links_width")
    rowsub.prop(cfg, "links_res")

    DEV_drawDebug(cfg, layout)

def DEV_drawDebug(cfg : MW_gen_cfg, layout: types.UILayout):
    if not DEV.debug: return

    # Toggle debug
    box = layout.box()
    box.prop(cfg, "meta_show_debug", toggle=True)
    if cfg.meta_show_debug:
        col = box.column()
        col.label(text="Show:")
        rowsub = col.row(align=True)
        rowsub.prop(cfg, "struct_showShards")
        rowsub.prop(cfg, "struct_showLinks")
        rowsub.prop(cfg, "struct_showLinks_walls")
        rowsub = col.row(align=True)
        rowsub.prop(cfg, "struct_showOrignal")
        rowsub.prop(cfg, "struct_showPoints")
        rowsub.prop(cfg, "struct_showBB")