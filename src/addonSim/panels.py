import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs, ADDON
from .properties_global import (
    MW_global_selected,
    MW_id_utils,
    MW_global_storage,
)

from . import operators as ops
from .panels_utils import util_classes_pt

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
        layoutCol = self.layout.column()

        # draw the fracture generation ops
        self.draw_onSelected(context, layoutCol)
        self.draw_debug(context, layoutCol)

    def draw_onSelected(self, context: types.Context, layout: types.UILayout):
        prefs = getPrefs()
        col = layout.column()
        selected = MW_global_selected.last

        # Something selected, not last active
        if not selected:
            col.label(text="No selectedect selected...", icon="ERROR")
            return

        # No fracture selected
        if not MW_global_selected.root:
            col.label(text="Selected: " + selected.name, icon="INFO")

            # Check that it is a mesh
            if selected.type != 'MESH':
                col = layout.column()
                col.label(text="Select a mesh...", icon="ERROR")
                return

            # Fracture original object
            col = layout.column()
            col.operator(ops.MW_gen_OT.bl_idname, text="GEN Fracture", icon="STICKY_UVS_DISABLE")

        # Edit/info of selected
        else:
            obj = MW_global_selected.root

            # show info of root + selected
            msg = f"Root: {obj.name}"
            if selected.name != obj.name:
                msg += f" - {selected.name}"

            # button to bake the shard
            col_rowSplit = col.row().split(factor=0.90)
            col_rowSplit.label(text=msg, icon="INFO")
            col_rowSplit.operator(ops.MW_util_bake_OT.bl_idname, text="", icon="UNLINKED")

            # delete
            col_rowSplit = layout.row().split(factor=0.70)
            col_rowSplit.operator(ops.MW_util_delete_OT.bl_idname, text="DELETE rec", icon="CANCEL")
            prefs = getPrefs()
            col_rowSplit.prop(prefs, "util_delete_OT_unhideSelect")

            # dupe
            col_rowSplit = layout.row().split(factor=0.70)
            col_rowSplit.operator(ops.MW_gen_OT.bl_idname, text="DUPLICATE Fracture", icon="DUPLICATE")
            col_rowSplit.prop(prefs, "gen_duplicate_OT_hidePrev")

            # WIP:: testing
            layout.operator(ops.MW_gen_links_OT.bl_idname, icon="OUTLINER_DATA_GREASEPENCIL")
            #layout.operator(ops.MW_util_bool_OT.bl_idname, icon="MOD_BOOLEAN")
            #layout.operator(ops.MW_util_comps_OT.bl_idname, icon="NODE_COMPOSITING")

            self.draw_props(obj, selected, context, layout)

    def draw_props(self, obj, selected, context: types.Context, layout: types.UILayout):
        prefs = getPrefs()

        # inspect root or selected?
        if prefs.all_PT_meta_show_root:
            gen_cfg = obj.mw_gen
            vis_cfg = obj.mw_vis
        else:
            gen_cfg = selected.mw_gen
            vis_cfg = selected.mw_vis

        # visuals
        open, box = ui.draw_toggleBox(prefs, "gen_PT_meta_show_visuals", layout)
        if open:
            col = box.column()
            col.prop(prefs, "gen_setup_matColors")
            col.prop(prefs, "gen_setup_matAlpha")
            col.prop(gen_cfg, "struct_linksScale")
            #col.prop(prefs, "links_matAlpha")
            col.prop(prefs, "links_smoothShade")
            col.prop(prefs, "links_depth")
            col.prop(prefs, "links_width")
            col.prop(prefs, "links_widthDead")
            rowsub = col.row()
            rowsub.prop(prefs, "links_widthModLife")
            col.prop(prefs, "links_res")
            col.prop(prefs, "links_wallExtraScale")

        # visuals inspect
        #open, box = ui.draw_propsToggle(vis_cfg, prefs.vis_PT_meta_inspector, layout, "Visuals...")
        open, box = ui.draw_propsToggle_custom(vis_cfg, prefs.vis_PT_meta_inspector, layout, "Visuals...")

        # props inspect
        open, box = ui.draw_propsToggle(gen_cfg, prefs.gen_PT_meta_inspector, layout)

        # toggle inspect root
        col_rowSplit = layout.row().split()
        col_rowSplit.prop(prefs, "all_PT_meta_show_root")
        col_rowSplit.label(text=obj.name if prefs.all_PT_meta_show_root else selected.name)

    def draw_debug(self, context: types.Context, layout: types.UILayout):
        prefs = getPrefs()

        open, box = ui.draw_toggleBox(prefs.gen_PT_meta_inspector, "meta_show_debug", layout)
        if open:
            # delete all fractures
            col_rowSplit = box.row().split(factor=0.66)
            col_rowSplit.operator(ops.MW_util_delete_all_OT.bl_idname, text="DELETE all", icon="CANCEL")
            col_rowSplit.prop(prefs, "util_delete_OT_unhideSelect")

            # recalculate fracture
            boxLinks = box.box()
            boxLinks.operator(ops.MW_gen_recalc_OT.bl_idname, icon="ZOOM_PREVIOUS")

            # global storage
            col_rowSplit = boxLinks.row().split(factor=0.66)
            col_rowSplit.label(text=f"Storage: {len(MW_global_storage.id_fracts)}", icon="FORCE_CURVE")
            col_rowSplit.prop(prefs, "prefs_autoPurge")

            col = boxLinks.column()
            for id,fract in MW_global_storage.id_fracts.items():
                col.label(text=f"{id}: {len(fract.cont)} cells + {len(fract.links.link_map)} links", icon="THREE_DOTS")

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
        col = self.layout.column()

        #col.label(text=f"...")
        self.layout.operator(ops.MW_sim_step_OT.bl_idname)
        self.layout.operator(ops.MW_sim_reset_OT.bl_idname)


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

        open, box = ui.draw_toggleBox(prefs.prefs_PT_meta_inspector, "meta_show_debug", layout)
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
    MW_addon_PT,
] + util_classes_pt

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)