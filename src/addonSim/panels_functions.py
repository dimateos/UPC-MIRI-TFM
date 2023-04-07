import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

# -------------------------------------------------------------------

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

    box = layout.box()
    col = box.column()
    col.label(text="Margins:")
    rowsub = col.row(align=True)
    rowsub.prop(cfg, "margin_box_bounds")
    rowsub.prop(cfg, "margin_face_bounds")

    box = layout.box()
    col = box.column()
    col.label(text="Summary:")
    col.prop(cfg, "copy_sufix")
    # TODO toggleable sections? + summary in sidebar too
    # TODO hide original

    box = layout.box()
    col = box.column()
    col.label(text="DEBUG:")
    # TODO convex hull options?
    # TODO decimation too -> original faces / later