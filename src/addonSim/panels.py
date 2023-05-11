import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs, ADDON
from .properties import (
    MW_gen_cfg,
)
from . import operators as ops
from .panels_utils import util_classes_pt

from .mw_links import LinkStorage

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
            # delete all fractures
            col_rowSplit = box.row().split(factor=0.66)
            col_rowSplit.operator(ops.MW_util_delete_all_OT.bl_idname, text="DELETE all", icon="CANCEL")
            col_rowSplit.prop(prefs, "util_delete_OT_unhideSelect")

            # recalculate fracture
            boxLinks = box.box()
            boxLinks.operator(ops.MW_gen_recalc_OT.bl_idname, icon="ZOOM_PREVIOUS")

            # links storage
            col_rowSplit = boxLinks.row().split(factor=0.66)
            links = LinkStorage.bl_links
            col_rowSplit.label(text=f"Storage links: {len(links)}", icon="FORCE_CURVE")
            col_rowSplit.prop(prefs, "prefs_links_undoPurge")

            col = boxLinks.column()
            for k,l in links.items():
                col.label(text=f"{k}: {len(l.link_map)} links {len(l.cont)} cells", icon="THREE_DOTS")

    def draw_onSelected(self, context: types.Context, layout: types.UILayout):
        prefs = getPrefs()
        obj, cfg = MW_gen_cfg.getSelectedRoot()
        col = layout.column()

        # Something selected, not last active
        if not obj:
            col.label(text="No object selected...", icon="ERROR")
            return

        # No fracture selected
        if not cfg:
            col.label(text="Selected: " + obj.name, icon="INFO")

            # Check that it is a mesh
            if obj.type != 'MESH':
                col = layout.column()
                col.label(text="Select a mesh...", icon="ERROR")
                return

            # Fracture original object
            col = layout.column()
            col.operator(ops.MW_gen_OT.bl_idname, text="GEN Fracture", icon="STICKY_UVS_DISABLE")

            ## inspect props
            #cfg = obj.mw_gen
            #ui.draw_propsToggle(cfg, prefs, "gen_PT_meta_show_summary", "gen_PT_meta_propFilter", "gen_PT_meta_propEdit", "get_PT_meta_propShowId", layout)

        # Edit/info of selected
        else:
            # show info of root + selected
            msg = f"Root: {obj.name}"
            selected = context.selected_objects[-1]
            if selected.name != obj.name:
                msg += f" - {selected.name}"

            # button to bake the shard
            col_rowSplit = col.row().split(factor=0.90)
            col_rowSplit.label(text=msg, icon="INFO")
            col_rowSplit.operator(ops.MW_util_bake_OT.bl_idname, text="", icon="UNLINKED")

            # delete
            mainCol = layout.column()
            col_rowSplit = mainCol.row().split(factor=0.70)
            col_rowSplit.operator(ops.MW_util_delete_OT.bl_idname, text="DELETE rec", icon="CANCEL")
            prefs = getPrefs()
            col_rowSplit.prop(prefs, "util_delete_OT_unhideSelect")

            # dupe
            col_rowSplit = mainCol.row().split(factor=0.70)
            col_rowSplit.operator(ops.MW_gen_OT.bl_idname, text="DUPLICATE Fracture", icon="DUPLICATE")
            col_rowSplit.prop(prefs, "gen_duplicate_OT_hidePrev")

            # WIP:: testing
            layout.operator(ops.MW_gen_links_OT.bl_idname, icon="OUTLINER_DATA_GREASEPENCIL")

            # visuals
            open, box = ui.draw_toggleBox(prefs, "gen_PT_meta_show_visuals", layout)
            if open:
                col = box.column()
                col.prop(cfg, "struct_shardScale")
                col.prop(prefs, "gen_setup_matColors")
                col.prop(prefs, "gen_setup_matAlpha")
                col.prop(cfg, "struct_linksScale")
                col.prop(prefs, "links_width")
                col.prop(prefs, "links_widthDead")
                col.prop(prefs, "links_res")


            # inspect props
            if not prefs.gen_PT_meta_show_root: cfg = selected.mw_gen
            open, box = ui.draw_propsToggle(cfg, prefs, "gen_PT_meta_show_summary", "gen_PT_meta_propFilter", "gen_PT_meta_propEdit", "get_PT_meta_propShowId", layout)
            col_rowSplit = box.row().split()
            if open:
                col_rowSplit.prop(prefs, "gen_PT_meta_show_root")
                col_rowSplit.label(text=obj.name if prefs.gen_PT_meta_show_root else selected.name)

#-------------------------------------------------------------------

class MW_sim_PT(types.Panel):
    bl_idname = "MW_PT_sim"

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = ADDON.panel_cat

    bl_label = "MW_sim"
    bl_options = {'HEADER_LAYOUT_EXPAND'}

    def draw(self, context):
        prefs = getPrefs()
        obj, cfg = MW_gen_cfg.getSelectedRoot()
        col = self.layout.column()

        #col.label(text=f"...")
        self.layout.operator(ops.MW_sim_step_OT.bl_idname)


#-------------------------------------------------------------------

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
    MW_sim_PT,
#] + util_classes_pt + [
    MW_addon_PT,
] + util_classes_pt

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)