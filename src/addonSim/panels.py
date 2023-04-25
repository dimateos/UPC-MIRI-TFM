import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs, ADDON
from .properties import (
    MW_gen_cfg,
)
from . import operators as ops
from . import operators_utils as ops_util
from .panels_utils import util_classes_pt

from . import ui
from . import utils
from .utils_dev import DEV


# OPT:: split panel utils from main
#-------------------------------------------------------------------

class MW_gen_PT(types.Panel):
    bl_idname = "MW_PT_gen"

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = ADDON.panel_cat

    bl_label = "MW_gen"
    bl_options = {'HEADER_LAYOUT_EXPAND'}

    def draw(self, context):
        prefs = getPrefs()
        layout = self.layout
        col = layout.column()

        # Something selected, not last active
        if not context.selected_objects:
            col.label(text="No object selected...", icon="ERROR")
            return

        if not context.active_object:
            col.label(text="Selected but removed active?", icon="ERROR")
            return

        obj, cfg = utils.cfg_getRoot(context.active_object)

        # No fracture selected
        if not cfg:
            col.label(text="Selected: " + obj.name_full, icon="INFO")

            # Check that it is a mesh
            if obj.type != 'MESH':
                col = layout.column()
                col.label(text="Select a mesh...", icon="ERROR")
                return

            # Fracture original object
            col = layout.column()
            col.operator(ops.MW_gen_OT.bl_idname, text="GEN Fracture", icon="STICKY_UVS_DISABLE")

        # Edit/info of selected
        else:
            col = layout.column()
            col.label(text="Root: " + obj.name_full, icon="INFO")

            col.operator(ops.MW_gen_OT.bl_idname, text="EDIT Fracture", icon="STICKY_UVS_VERT")

            col_rowSplit = col.row().split(factor=0.66)
            col_rowSplit.operator(ops.MW_util_delete_OT.bl_idname, text="DELETE rec", icon="CANCEL")
            prefs = getPrefs()
            col_rowSplit.prop(prefs, "OT_util_delete_unhide")

            ui.draw_propsToggle(cfg, prefs, "PT_gen_show_summary", "PT_gen_propFilter", "PT_gen_propEdit", col)

class MW_addon_PT(types.Panel):
    bl_idname = "MW_PT_addon"

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    #bl_context = "objectmode"
    bl_category = ADDON.panel_cat

    bl_label = "MW_addon"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        prefs = getPrefs()
        layout = self.layout
        col = layout.column()

        ui.draw_propsToggle(prefs, prefs, "meta_show_prefs", "meta_propFilter", "meta_propEdit", col)

        open, box = ui.draw_toggleBox(prefs, "meta_show_tmpDebug", layout)
        if open:
            col = box.column()
            # check region width
            DEV.draw_val(col, "context.region.width", context.region.width)


#-------------------------------------------------------------------
# Blender events

# sort to set default order?
classes = [
    MW_gen_PT,
] + util_classes_pt + [
    MW_addon_PT,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)