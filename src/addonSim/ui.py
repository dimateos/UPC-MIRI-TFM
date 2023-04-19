import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

from . import utils_cfg

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
    """ Log to console if DEV.logs and type not filtered by DEV.logs_skipped """
    if not DEV.logs: return
    if type in DEV.logs_skipped: return

    print(type, msg)
    if ui: ui.report(type, msg)
    #ui.report({'INFO'}, "Operation successful!")
    #ui.report({'ERROR'}, "Operation failed!")

def DEV_drawVal(layout: types.UILayout, msg, value):
    """ Draw value with label if DEV.ui_vals is set """
    if not DEV.ui_vals: return
    layout.label(text=f"{msg}: {value}", icon="BLENDER")

# -------------------------------------------------------------------

def draw_toggleBox(data, propToggle_name:str, layout: types.UILayout) -> tuple[bool, types.UILayout]:
    """ Create a box with a toggle. Return the state of the toggle and the created layout """
    box = layout.box()
    box.prop(data, propToggle_name, toggle=True)
    open = getattr(data, propToggle_name)
    return open, box

def draw_props(data, propFilter_name:str, layout: types.UILayout):
    """ Draw all properties of an object in a sub layout. """
    # dynamic filter prop
    prop_names = utils_cfg.getProps_names(data)
    propFilter = getattr(data, propFilter_name)
    if propFilter:
        excluding = propFilter[0]=="-"
        if excluding: propFilter = propFilter[1:]
        filtered_props = propFilter.split(",")
    else:
        filtered_props = []

    for prop_name in prop_names:
        # optionally always skip the filter
        if prop_name == propFilter_name: continue
        # apply excluding/including filter
        if filtered_props:
            filterMask = [ f.strip().lower() in prop_name.strip().lower() for f in filtered_props ]
            if excluding:
                if any(filterMask): continue
            elif not any(filterMask): continue

        layout.row().prop(data, prop_name, text=prop_name)

def draw_propsToggle(data, propToggle_name:str, propFilter_name:str, propEdit_name:str, layout: types.UILayout):
    """ Draw all properties of an object under a toggleable layout. """
    open, box = draw_toggleBox(data, propToggle_name, layout)
    if open:
        split = box.split(factor=0.75)
        split.prop(data, propFilter_name)
        split.prop(data, propEdit_name)
        col = box.column()
        col.enabled = getattr(data, propEdit_name)
        draw_props(data, propFilter_name, col)

# -------------------------------------------------------------------

def draw_refresh(cfg: MW_gen_cfg, layout: types.UILayout):
    row = layout.box().row()
    row.scale_y = 1.5
    split = row.split(factor=0.75)
    split.prop(cfg, "meta_auto_refresh", toggle=True, icon_only=False, icon='FILE_REFRESH')
    split.prop(cfg, "meta_refresh", toggle=True, icon_only=True, icon='FILE_REFRESH')

def draw_inspectObject(obj: types.Object, layout: types.UILayout):
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

def draw_gen_cfg(cfg: MW_gen_cfg, layout: types.UILayout, context: types.Context):
    draw_refresh(cfg, layout)

    # TODO: apply filter here too?
    box = layout.box()
    col = box.column()

    factor = 0.4
    rowsub = col.row().split(factor=factor)
    rowsub.alignment = "LEFT"
    rowsub.label(text="Point Source:")
    split = rowsub.split()
    split.enabled = False
    split.alignment = "LEFT"
    split.label(text=cfg.struct_nameOriginal)

    rowsub = col.row().split(factor=factor)
    rowsub.alignment = "LEFT"
    rowsub.prop(cfg, "struct_namePrefix")
    split = rowsub.split()
    split.enabled = False
    split.alignment = "LEFT"
    split.label(text=cfg.get_struct_name())

    rowsub = col.row()
    rowsub.prop(cfg, "source")

    rowsub = col.row()
    rowsub.prop(cfg, "source_limit")
    rowsub.prop(cfg, "shape_useWalls")
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

    draw_gen_cfgDebug(cfg, layout)

def draw_gen_cfgDebug(cfg: MW_gen_cfg, layout: types.UILayout):
    if not DEV.debug: return
    open, box = draw_toggleBox(cfg, "meta_show_debug", layout)

    if open:
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