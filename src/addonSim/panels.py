import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)
from .operators import (
    MW_gen_OT_
)

PANEL_CATEGORY = "Dev"



# -------------------------------------------------------------------

class MW_gen_Panel(types.Panel):
    bl_category = PANEL_CATEGORY
    bl_label = "MW_gen"
    bl_idname = "MW_PT_gen"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_options = {'HEADER_LAYOUT_EXPAND'}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return (ob and ob.type == 'MESH')

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        cfg : MW_gen_cfg = ob.mw_gen

        # Fracture object
        if not cfg.generated:
            col = layout.column()
            col.label(text="no mw")
            col.operator(MW_gen_OT_.bl_idname, text="GEN Fracture", icon="STICKY_UVS_DISABLE")

        # Edit/info of selected
        else:
            col = layout.column()
            col.label(text="mw")
            col.operator(MW_gen_OT_.bl_idname, text="EDIT Fracture", icon="STICKY_UVS_VERT")

            box = layout.box()
            col = box.column()
            col.label(text="Summary")
            # TODO hide original


# -------------------------------------------------------------------
# Blender events

classes = (
    MW_gen_Panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)