import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs, ADDON
from .properties import (
    MW_gen_cfg,
)
from . import operators as ops
from .panels_utils import util_classes_pt

from .mw_links import Links_storage

from . import ui
from .utils_dev import DEV


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
        layout = self.layout
        prefs = getPrefs()

        # draw the fracture generation ops
        self.draw_onSelected(context, layout)

        open, box = ui.draw_toggleBox(prefs, "gen_PT_meta_show_tmpDebug", layout)
        if open:
            # links storage
            boxLinks = box.box()
            col_rowSplit = boxLinks.row().split(factor=0.66)
            links = Links_storage.bl_links
            col_rowSplit.label(text=f"Storage links: {len(links)}", icon="FORCE_CURVE")
            col_rowSplit.prop(prefs, "prefs_links_undoPurge")

            col = boxLinks.column()
            for k,l in links.items():
                col.label(text=f"{k}: {len(l.link_map)} links {len(l.cont)} cells", icon="THREE_DOTS")

            box.operator(ops.MW_util_delete_all_OT.bl_idname, text="DELETE all Fractures", icon="CANCEL")

    def draw_onSelected(self, context, layout):
        prefs = getPrefs()
        obj, cfg = MW_gen_cfg.getSelectedRoot()
        col = layout.column()

        # Something selected, not last active
        if not obj:
            col.label(text="No object selected...", icon="ERROR")
            return

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

            #col.operator(ops.MW_gen_OT.bl_idname, text="EDIT Fracture", icon="STICKY_UVS_VERT")
            col.operator(ops.MW_gen_OT.bl_idname, text="DUPLICATE Fracture", icon="STICKY_UVS_VERT")

            col_rowSplit = col.row().split(factor=0.66)
            col_rowSplit.operator(ops.MW_util_delete_OT.bl_idname, text="DELETE rec", icon="CANCEL")
            prefs = getPrefs()
            col_rowSplit.prop(prefs, "util_delete_OT_unhideSelect")

            ui.draw_propsToggle(cfg, prefs, "gen_PT_meta_show_summary", "gen_PT_meta_propFilter", "gen_PT_meta_propEdit", "get_PT_meta_propShowId", col)
            col.operator(ops.MW_gen_links_OT.bl_idname)




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

        ui.draw_propsToggle(prefs, prefs, "prefs_PT_meta_show_prefs", "prefs_PT_meta_propFilter", "prefs_PT_meta_propEdit", "get_PT_meta_propShowId", col)

        open, box = ui.draw_toggleBox(prefs, "prefs_PT_meta_show_tmpDebug", layout)
        if open:
            col = box.column()
            # check region width
            DEV.draw_val(col, "context.region.width", context.region.width)


#-------------------------------------------------------------------
# Blender events

# sort to set default order
classes = [
    MW_gen_PT,
#] + util_classes_pt + [
    MW_addon_PT,
] + util_classes_pt

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)