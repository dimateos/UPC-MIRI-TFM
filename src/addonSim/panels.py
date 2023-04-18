import bpy
import bpy.types as types
import bpy.props as props

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)
from . import operators as ops

from . import utils
from . import utils_cfg
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
            col.operator(ops.MW_gen_OT_.bl_idname, text="GEN Fracture", icon="STICKY_UVS_DISABLE")

        # Edit/info of selected
        else:
            col = layout.column()
            col.label(text="Root: " + obj.name_full, icon="INFO")

            col = layout.column()
            col.operator(ops.MW_gen_OT_.bl_idname, text="EDIT Fracture", icon="STICKY_UVS_VERT")

            col_rowSplit = col.row().split(factor=0.8)
            col_rowSplit.operator(ops.MW_util_delete_OT_.bl_idname, text="DELETE Fracture", icon="CANCEL")
            #col_rowSplit.prop(ops.MW_util_delete_OT_, "unhide_original")
            #col_rowSplit.prop(self, "cfg_util_delete_unhide")
            #col_rowSplit.label(str(self.cfg_util_delete_unhide))
            #self.layout.prop(self, "cfg_util_delete_unhide")

            prefs = utils_cfg.getPrefs(context)
            self.layout.prop(prefs, "my_bool_pref")

            ui.draw_propsToggle(cfg, layout)


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

            ui.draw_inspectObject(obj, layout)
            col.operator(ops.MW_info_matrices_OT_.bl_idname, text="Print Matrices", icon="LATTICE_DATA")

            if obj.type == 'MESH':
                col = layout.column()
                col.operator(ops.MW_info_data_OT_.bl_idname, text="Print mesh Data", icon="HELP")
                col.operator(ops.MW_info_API_OT_.bl_idname, text="Print mesh API", icon="HELP")

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