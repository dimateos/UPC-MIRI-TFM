import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)
from .operators import (
    MW_gen_OT_,
    MW_infoData_OT_,
    MW_infoAPI_OT_
)

from . import utils
from . import ui

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

        obj, cfg = utils.cfg_getRoot(context.active_object)

        # No fracture selected
        if not cfg:
            col = layout.column()
            col.label(text="Selected: " + obj.name_full, icon="INFO")

            # Check that it is a mesh
            if obj.type != 'MESH':
                col = layout.column()
                col.label(text="Select a mesh...", icon="ERROR")
                return

            # Fracture original object
            col = layout.column()
            col.operator(MW_gen_OT_.bl_idname, text="GEN Fracture", icon="STICKY_UVS_DISABLE")

        # Edit/info of selected
        else:
            col = layout.column()
            col.label(text="Root: " + obj.name_full, icon="INFO")

            col = layout.column()
            col.operator(MW_gen_OT_.bl_idname, text="EDIT Fracture", icon="STICKY_UVS_VERT")

            ui.draw_summary(cfg, layout)


class MW_info_Panel(types.Panel):
    bl_category = PANEL_CATEGORY
    bl_label = "MW_info"
    bl_idname = "MW_PT_info"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_options = {'HEADER_LAYOUT_EXPAND'}

    def draw(self, context):
        layout = self.layout

        # Something selected, not last active
        if not context.selected_objects:
            pass
            #col = layout.column()
            #col.label(text="No object selected...", icon="ERROR")

        else:
            obj = context.active_object
            col = layout.column()

            ui.draw_inspect(obj, layout)

            if obj.type == 'MESH':
                col = layout.column()
                col.operator(MW_infoData_OT_.bl_idname, text="Inspect Data", icon="HELP")
                col.operator(MW_infoAPI_OT_.bl_idname, text="Inspect API", icon="HELP")

        # check region width
        box = layout.box()
        col = box.column()
        col.label(text="Debug...")
        ui.DEV_drawVal(col, "context.region.width", context.region.width)

# -------------------------------------------------------------------
# Blender events

classes = (
    MW_gen_Panel,
    MW_info_Panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)