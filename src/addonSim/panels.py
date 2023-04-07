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

from .operators_functions import (
    getRoot_cfg
)
from .panels_functions import (
    DEV_writeVal,
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

    def draw(self, context):
        layout = self.layout

        # Something selected, not last active
        if not context.selected_objects:
            col = layout.column()
            col.label(text="No object selected...", icon="ERROR")
            return

        ob, cfg = getRoot_cfg(context.active_object)

        # No fracture selected
        if not cfg:
            col = layout.column()
            col.label(text="Selected: " + ob.name_full, icon="INFO")

            # Check that it is a mesh
            if ob.type != 'MESH':
                col = layout.column()
                col.label(text="Select a mesh...", icon="ERROR")
                return

            # Fracture original object
            col = layout.column()
            col.operator(MW_gen_OT_.bl_idname, text="GEN Fracture", icon="STICKY_UVS_DISABLE")

        # Edit/info of selected
        else:
            col = layout.column()
            col.label(text="Root: " + ob.name_full, icon="INFO")

            col = layout.column()
            col.operator(MW_gen_OT_.bl_idname, text="EDIT Fracture", icon="STICKY_UVS_VERT")

            box = layout.box()
            col = box.column()
            col.label(text="Summary...")

            box = layout.box()
            col = box.column()
            col.label(text="DEBUG:")
            DEV_writeVal(col, context.region.width, "w")


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