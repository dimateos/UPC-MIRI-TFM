import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

DEV_VALS = True

# -------------------------------------------------------------------

def DEV_writeVal(layout: types.UILayout, value, name):
    if DEV_VALS:
        layout.label(text=f"{name}: {value}", icon="BLENDER")

def draw_gen_cfg(cfg : MW_gen_cfg, layout: types.UILayout, context: types.Context):
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
    col.prop(cfg, "copy_sufix")

    box = layout.box()
    col = box.column()
    col.label(text="Margins:")
    rowsub = col.row(align=True)
    rowsub.prop(cfg, "margin_box_bounds")
    rowsub.prop(cfg, "margin_face_bounds")

    box = layout.box()
    col = box.column()
    col.label(text="Summary...")
    # TODO toggleable sections? + summary in sidebar too
    # TODO hide original

    box = layout.box()
    col = box.column()
    col.label(text="DEBUG:")
    DEV_writeVal(col, context.region.width, "w")

    # TODO convex hull options?
    # TODO decimation too -> original faces / later