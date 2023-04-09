import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

from . import utils
DEV_DEBUG = True
DEV_VALS = True
DEV_LOGS = True
DEV_LOGS_SKIPS = [
    #{'OP_FLOW'}
]


# -------------------------------------------------------------------

def DEV_log(msg, type = {'DEV'}, ui = None):
    if not DEV_LOGS: return
    if type in DEV_LOGS_SKIPS: return

    print(type, msg)
    if ui: ui.report(type, msg)
    #ui.report({'INFO'}, "Operation successful!")
    #ui.report({'ERROR'}, "Operation failed!")

def DEV_drawVal(layout: types.UILayout, value, name):
    if not DEV_VALS: return
    layout.label(text=f"{name}: {value}", icon="BLENDER")


def draw_refresh(cfg : MW_gen_cfg, layout: types.UILayout):
    row = layout.box().row()
    row.scale_y = 1.5
    split = row.split(factor=0.75)
    split.prop(cfg, "meta_auto_refresh", toggle=True, icon_only=False, icon='FILE_REFRESH')
    split.prop(cfg, "meta_refresh", toggle=True, icon_only=True, icon='FILE_REFRESH')

def draw_summary(cfg : MW_gen_cfg, layout: types.UILayout):
    # TODO maybe scene prop to togggle show instead of object

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


def DEV_drawDebug(cfg : MW_gen_cfg, layout: types.UILayout, context: types.Context):
    if not DEV_DEBUG: return

    # Toggle debug
    box = layout.box()
    box.prop(cfg, "meta_show_debug", toggle=True)
    if cfg.meta_show_debug:
        col = box.column()

        # check region width
        DEV_drawVal(col, context.region.width, "w")

def draw_gen_cfg(cfg : MW_gen_cfg, layout: types.UILayout, context: types.Context):
    draw_refresh(cfg, layout)

    box = layout.box()
    col = box.column()
    col.label(text="Point Source:")
    rowsub = col.row()
    rowsub.prop(cfg, "source")
    rowsub = col.row()
    rowsub.prop(cfg, "source_limit")
    rowsub.prop(cfg, "source_noise")
    #rowsub = col.row()
    #rowsub.prop(cfg, "cell_scale")
    col.prop(cfg, "struct_sufix")

    box = layout.box()
    col = box.column()
    col.label(text="Margins:")
    rowsub = col.row(align=True)
    rowsub.prop(cfg, "margin_box_bounds")
    rowsub.prop(cfg, "margin_face_bounds")

    # TODO convex hull options?
    # TODO decimation too -> original faces / later

