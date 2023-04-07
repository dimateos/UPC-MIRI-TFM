import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

DEV_DEBUG = True
DEV_VALS = True

# -------------------------------------------------------------------

def DEV_drawVal(layout: types.UILayout, value, name):
    if not DEV_VALS: return
    layout.label(text=f"{name}: {value}", icon="BLENDER")


def draw_refresh(cfg : MW_gen_cfg, layout: types.UILayout):
    if cfg.meta_auto_refresh is False:
        cfg.meta_refresh = False
    elif cfg.meta_auto_refresh is True:
        cfg.meta_refresh = True
    row = layout.box().row()
    split = row.split()
    split.scale_y = 1.5
    split.prop(cfg, "meta_auto_refresh", toggle=True, icon_only=True, icon='AUTO')
    split.prop(cfg, "meta_refresh", toggle=True, icon_only=True, icon='FILE_REFRESH')

def draw_summary(cfg : MW_gen_cfg, layout: types.UILayout):
    box = layout.box()
    box.prop(cfg, "meta_show_summary", toggle=True)
    if cfg.meta_show_summary:
        col = box.column()
        col.enabled = False

        filtered_props = [ "meta", "name" ]
        for prop_name in cfg.keys():
            filtered = False
            for filter in filtered_props:
                if filter in prop_name:
                    filtered = True
                    break
            if filtered: continue

            col.row().prop(cfg, prop_name)
            #prop_value = cfg[prop_name]
            #col.row().label(text=prop_name + ": " + str(prop_value))


def DEV_drawDebug(cfg : MW_gen_cfg, layout: types.UILayout, context: types.Context):
    if not DEV_DEBUG: return
    box = layout.box()

    box.prop(cfg, "meta_show_debug", toggle=True)
    if cfg.meta_show_debug:
        col = box.column()
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

    DEV_drawDebug(cfg, layout, context)


