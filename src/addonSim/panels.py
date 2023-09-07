import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs, ADDON
from .properties_global import (
    MW_id_utils,
    MW_global_storage,
    MW_global_selected,
)
from .mw_fract import MW_Fract
from .mw_cont import MW_Container, STATE_ENUM

from . import operators as ops
from .panels_dm import util_classes_pt

from . import ui
from . import utils_scene
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

        # more options
        self.draw_debug(context, layoutCol)

    def draw_onSelected(self, context: types.Context, layout: types.UILayout):
        prefs = getPrefs()
        col = layout.column()
        curr = MW_global_selected.current

        # Something selected, not last active
        if not curr:
            col.label(text="No object selected...", icon="ERROR")
            return

        # No fracture selected
        if not MW_global_selected.root:
            col.label(text="Selected: " + curr.name, icon="INFO")

            # Check that it is a mesh
            if curr.type != 'MESH':
                col = layout.column()
                col.label(text="Select a mesh...", icon="ERROR")
                return

            # Fracture original object
            col = layout.column()
            col.operator(ops.MW_gen_OT.bl_idname, text="GEN Fracture", icon="STICKY_UVS_DISABLE")

        # Edit/info of selected
        else:
            root = MW_global_selected.root

            # show info of root + selected
            msg = f"Fract: {root.name}"
            if curr.name != root.name:
                msg += f" - {curr.name}"

            # button to bake the cell
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
            col_rowSplit.operator(ops.MW_gen_OT.bl_idname, text="DUPLICATE", icon="DUPLICATE")
            col_rowSplit.prop(prefs, "gen_duplicate_OT_hidePrev")

            self.draw_props(root, curr, context, layout)

    def draw_props(self, root, selected, context: types.Context, layout: types.UILayout):
        prefs = getPrefs()

        # inspect root or selected?
        gen_cfg = root.mw_gen if prefs.all_PT_meta_show_root else selected.mw_gen

        open, box = ui.draw_propsToggle(gen_cfg, prefs.gen_PT_meta_inspector, layout, text="Container props")
        if open:
            col_rowSplit = layout.row().split()
            col_rowSplit.prop(prefs, "all_PT_meta_show_root", text="Root props:" if prefs.all_PT_meta_show_root else "Child props:")
            col_rowSplit.label(text=root.name if prefs.all_PT_meta_show_root else selected.name)

        # example of how to edit op parameters from the panel before execution (but better done inside invoke, in this case)
        op = layout.operator(ops.MW_set_state_OT.bl_idname, icon="PIVOT_CURSOR")
        #if MW_global_selected.fract and MW_global_selected.fract.cont:
        #    if MW_id_utils.hasCellId(MW_global_selected.current):
        #        cell_id = MW_global_selected.current.mw_id.cell_id
        #        cell_state = MW_global_selected.fract.cont.cells_state[cell_id]
        #        op.set_state = ops.MW_set_state_OT.set_state_toEnum[cell_state]

        # more actions
        layout.operator(ops.MW_gen_links_OT.bl_idname, icon="OUTLINER_DATA_GREASEPENCIL")

        # warning no fract
        if not MW_global_selected.fract:
            layout.label(text="Root without storage! Recalc...", icon="ERROR")

        # visuals inspect
        #vis_cfg = context.scene.mw_vis -> scene data is affected by operator undo
        vis_cfg = prefs.mw_vis
        open, box = ui.draw_propsToggle_custom(vis_cfg, prefs.vis_PT_meta_inspector, layout, "Visuals...")

    def draw_debug(self, context: types.Context, layout: types.UILayout):
        prefs = getPrefs()
        curr = MW_global_selected.current
        fract : MW_Fract = MW_global_selected.fract
        cont : MW_Container = MW_global_selected.fract.cont if fract else None

        open, box = ui.draw_toggleBox(prefs.gen_PT_meta_inspector, "meta_show_debug", layout, scaleBox=0.85, returnCol=False)
        if open:
            # recalculate fracture
            box.operator(ops.MW_gen_recalc_OT.bl_idname, icon="ZOOM_PREVIOUS")

            # cell data
            if curr:
                boxSelected = box.box().column()
                col_rowSplit = boxSelected.row().split(factor=0.5)
                col_rowSplit.label(text=f"{curr.mw_id.meta_type}", icon="COPY_ID")
                col_rowSplit.label(text=f"s: {curr.mw_id.storage_id}")
                cell_id = curr.mw_id.cell_id
                col_rowSplit.label(text=f"c: {cell_id}")
                # state data from cont or the cell
                col_rowSplit = boxSelected.row()
                col_rowSplit = boxSelected.row().split(factor=0.6)
                col_rowSplit.label(text=f"State: {STATE_ENUM.to_str(curr.mw_id.cell_state)}", icon="CON_PIVOT")
                if fract and cont:
                    col_rowSplit.label(text=f"c: {STATE_ENUM.to_str(MW_global_selected.fract.cont.cells_state[cell_id])}")


            # cont POV
            if fract:
                if cont:
                    boxCont = box.box().column()
                    boxCont.label(text=f"Root:  {cont.root.name if not utils_scene.needsSanitize(cont.root) else '~'}")
                    boxCont.label(text=f"Cells: { cont.cells_objs[0].name if not utils_scene.needsSanitize(cont.cells_objs[0]) else '~'} ({len(cont.cells_objs)})")
                    boxCont.label(text=f"Meshes: { cont.cells_meshes[0].name if not utils_scene.needsSanitize(cont.cells_meshes[0]) else '~'} ({len(cont.cells_meshes)})")

            # global selected
            boxSelected = box.box().column()
            col_rowSplit = boxSelected.row().split(factor=0.6)
            col_rowSplit.label(text=f"Root:  {MW_global_selected.root.name if MW_global_selected.root else '~'}", icon="RESTRICT_SELECT_ON")
            col_rowSplit.label(text=f"{MW_global_selected.prevalid_root.name if MW_global_selected.prevalid_root else '~'}", icon="FRAME_PREV")
            col_rowSplit = boxSelected.row().split(factor=0.6)
            col_rowSplit.label(text=f"Current: {curr.name if curr else '~'}", icon="RESTRICT_SELECT_OFF")
            col_rowSplit.label(text=f"{MW_global_selected.prevalid_last.name if MW_global_selected.prevalid_last else '~'}", icon="FRAME_PREV")
            col_rowSplit = boxSelected.row().split(factor=0.6)
            col_rowSplit.label(text=f"Active: {context.active_object.name if context.active_object else '~'}", icon="SELECT_INTERSECT")
            col_rowSplit.label(text=f"{len(MW_global_selected.selection) if MW_global_selected.selection else '~'}", icon="SELECT_SET")

            # delete all fractures
            boxLinks = box.box()
            col_rowSplit = boxLinks.row().split(factor=0.66)
            col_rowSplit.operator(ops.MW_util_delete_all_OT.bl_idname, text="DELETE all", icon="CANCEL")
            col_rowSplit.prop(prefs, "util_delete_OT_unhideSelect")

            # global storage
            col_rowSplit = boxLinks.row().split(factor=0.66)
            col_rowSplit.label(text=f"Storage: {len(MW_global_storage.id_fracts)}", icon="FORCE_CURVE")
            col_rowSplit.prop(prefs, "prefs_autoPurge")

            col = boxLinks.column()
            for id,fract in MW_global_storage.id_fracts.items():
                obj = MW_global_storage.id_fracts_obj[id]
                icon = "X" if utils_scene.needsSanitize(obj) else "CHECKMARK"
                col.label(text=f"{id}: {len(fract.cont.voro_cont)} cells + {len(fract.links.link_map)} links", icon=icon)


            # more stuff
            col = layout.column()
            col.operator(ops.MW_util_comps_OT.bl_idname, icon="NODE_COMPOSITING")
            col.operator(ops.MW_util_bool_OT.bl_idname, icon="MOD_BOOLEAN")


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
        layout = self.layout.column()

        #ui.draw_propsToggle(prefs, prefs.prefs_PT_meta_inspector, layout)
        ui.draw_propsToggle_custom(prefs.dev_PT_meta_cfg, prefs.dev_PT_meta_cfg, layout, text="DEV", splitDebug=False)

        open, box = ui.draw_toggleBox(prefs.prefs_PT_meta_inspector, "meta_show_debug", layout, scaleBox=0.85)
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