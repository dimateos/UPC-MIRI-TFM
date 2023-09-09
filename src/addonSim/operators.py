import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs
from .properties_global import (
    MW_id,
    MW_id_utils,
    MW_global_selected,
    MW_global_storage
)
from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
)
from .properties_utils import copyProps
from .operators_dm import _StartRefresh_OT, util_classes_op

from . import mw_setup, mw_extraction
from .mw_links import MW_Links
from .mw_cont import MW_Cont, STATE_ENUM
from .mw_fract import MW_Fract
from . import mw_sim

from . import ui
from . import utils, utils_scene, utils_trans
from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

class MW_gen_OT(_StartRefresh_OT):
    bl_idname = "mw.gen"
    bl_label = "Cells generation"
    bl_description = "Voronoi cells generation using voro++"

    # REGISTER + UNDO pops the edit last op window
    bl_options = {'PRESET', 'REGISTER', 'UNDO'}
    cfg: props.PointerProperty(type=MW_gen_cfg)
    invoked_once = False

    def __init__(self) -> None:
        super().__init__(init_log=True)
        # config some base class log flags...
        self.invoke_log  = True
        self.refresh_log = True
        self.end_log     = True

    def draw(self, context: types.Context):
        super().draw(context)
        cfg : MW_gen_cfg = self.cfg
        layout = self.layout
        box = layout.box()
        col = box.column()

        # source points
        factor = 0.4
        rowsub = col.row().split(factor=factor)
        rowsub.alignment = "LEFT"
        rowsub.label(text="Point Source:")
        split = rowsub.split()
        split.enabled = False
        split.alignment = "LEFT"
        split.label(text=cfg.struct_nameOriginal)

        rowsub = col.row().split(factor=factor)
        rowsub.alignment = "LEFT"
        rowsub.prop(cfg, "struct_namePrefix")
        split = rowsub.split()
        split.enabled = False
        split.alignment = "LEFT"
        split.label(text=f"{cfg.struct_namePrefix}_{cfg.struct_nameOriginal}")

        rowsub = col.row()
        rowsub.prop(cfg, "source")

        rowsub = col.row().split(factor=0.8)
        rowsub.prop(cfg, "source_limit")
        rowsub.label(text=f"/ {cfg.source_numFound}")

        rowsub = col.row()
        rowsub.prop(cfg, "source_noise")
        rowsub.prop(cfg, "source_shuffle")

        # container faces
        box = layout.box()
        col = box.column()
        col.label(text="Generation:")
        rowsub = col.row(align=True)
        rowsub.prop(cfg, "shape_useConvexHull")
        rowsub.prop(cfg, "shape_useWalls")
        rowsub = col.row(align=True)
        rowsub.prop(cfg, "margin_box_bounds")
        rowsub.prop(cfg, "margin_face_bounds")

        # debug settings
        open, box = ui.draw_propsToggle_custom(cfg, getPrefs().gen_PT_meta_inspector, layout, "meta_show_debug_props", propFilter="debug", scaleBox=0.85)

    # NOTE:: no poll because the button is removed from ui in draw instead
    #@classmethod
    #def poll(cls, context):
    #    # XXX:: required achieve edit last op but MW_global_selected is none?
    #    MW_global_selected.logSelected()
    #    return MW_global_selected.last

    def invoke(self, context, event):
        # avoid last stored operation overide and recalculating everything
        self.invoked_once = False
        getPrefs().gen_PT_meta_inspector.reset_meta_show_toggled()
        # id of last fract calculated stored (outside the operator)
        self.last_storageID = None
        return super().invoke(context, event)

    #-------------------------------------------------------------------

    def execute(self, context: types.Context):
        self.start_op()
        self.obj_root = None
        self.ctx = context
        prefs = getPrefs()

        # handle refresh
        if self.checkRefresh_cancel() or prefs.gen_PT_meta_inspector.skip_meta_show_toggled():
            return self.end_op_refresh(skipLog=True)

        # Potentially free existing storage -> now purged on undo callback dynamically (called by uperator redo)
        if self.last_storageID is not None:
            MW_global_storage.freeFract_fromID(self.last_storageID)

        # Retrieve root
        obj = MW_global_selected.root
        getStats().logDt("retrieved root object")
        try:
            # Selected object not fractured, fresh execution
            if obj is None:
                DEV.log_msg("cfg NOT found: new frac", {'SETUP'})
                obj_root, obj_original = mw_setup.copy_original(MW_global_selected.current, self.cfg, context, prefs.names.original_copy)
                # Sync prefs panel with the object -> ok callbacks because obj is None
                copyProps(prefs.mw_vis, obj_root.mw_vis)
                return self.execute_fresh(obj_root, obj_original)

            # Fracture the same original object, copy props for a duplicated result to tweak parameters
            # NOTE:: no longer supporting edit fracture -> basically always replaces all objects in the scene which is slower than a fresh one
            else:
                # Copy the config to the op only once to allow the user to edit it afterwards
                if not self.invoked_once:
                    self.invoked_once = True
                    DEV.log_msg("cfg found once: copying props to OP", {'SETUP'})
                    copyProps(obj.mw_gen, self.cfg)

                # optionally unhide the original fracture object but always unselect
                obj.select_set(False)
                if (prefs.gen_duplicate_OT_hidePrev):
                    utils_scene.hide_objectRec(obj)

                DEV.log_msg("cfg found: duplicating frac", {'SETUP'})
                obj_root, obj_original = mw_setup.copy_originalPrev(obj, context, prefs.names.original_copy)
                return self.execute_fresh(obj_root, obj_original)

        # catch exceptions to at least mark as child and copy props
        except Exception as e:
            if not DEV.HANDLE_GLOBAL_EXCEPT: raise e
            return self.end_op_error("unhandled exception...")


    def execute_fresh(self, obj_root:types.Object, obj_original:types.Object ):
        prefs = getPrefs()

        # work with the properties stored in the object
        self.obj_root = obj_root
        copyProps(self.cfg, obj_root.mw_gen)
        cfg: MW_gen_cfg = obj_root.mw_gen
        cfg.debug_rnd_seed = utils.debug_rnd_seed(cfg.debug_rnd_seed)


        # Add to global storage to generate the fracture id
        fract = MW_Fract()
        self.last_storageID = MW_global_storage.addFract(fract, obj_root)


        DEV.log_msg("Initial object setup", {'SETUP'})
        if cfg.shape_useConvexHull:
            # NOTE:: convex hull triangulates the faces... e.g. UV sphere ends with more!
            obj_toFrac = mw_setup.copy_convex(obj_root, obj_original, self.ctx, prefs.names.original_convex, prefs.names.original_dissolve)
        else: obj_toFrac = obj_original


        DEV.log_msg("Start calc faces", {'CALC'})
        bb, bb_center, bb_radius = utils_trans.get_bb_data(obj_toFrac, cfg.margin_box_bounds)
        getStats().logDt(f"calc bb: [{bb_center[:]}] r {bb_radius:.3f} (margin {cfg.margin_box_bounds:.4f})")
        if cfg.shape_useWalls:
            faces4D = utils_trans.get_faces_4D(obj_toFrac, cfg.margin_face_bounds)
        else: faces4D = []
        getStats().logDt(f"calc faces4D: {len(faces4D)} (n_disp {cfg.margin_face_bounds:.4f})")


        DEV.log_msg("Start calc points", {'CALC'})
        mw_extraction.detect_points_from_object(obj_original, cfg, self.ctx)
        points = mw_extraction.get_points_from_object_fallback(obj_original, cfg, self.ctx)
        cfg.source_numFound = len(points)
        if not points:
            return self.end_op_error("found no points...")

        # Limit and rnd a bit the points
        mw_extraction.points_transformCfg(points, cfg, bb_radius)

        # Add some reference of the points to the scene
        mw_setup.gen_pointsObject(obj_root, points, self.ctx, prefs.names.source_points)
        mw_setup.gen_boundsObject(obj_root, bb, self.ctx, prefs.names.source_wallsBB)
        getStats().logDt("generated point and bound objects")


        DEV.log_msg("Start calc cont", {'CALC', 'CONT'})
        fract.cont = cont = MW_Cont(obj_root, points, bb, faces4D, precision=cfg.debug_precisionWalls)
        if not cont.initialized:
            return self.end_op_error("found no cont... recalc different params?")

        #test some legacy or statistics cont stuff
        if DEV.LEGACY_CONT:
            mw_setup.gen_cells_LEGACY(cont.voro_cont, obj_root, self.ctx)
            return self.end_op("DEV.LEGACY_CONT stop...")

        # precalculate/query neighs and other data with generated cells mesh
        cells = mw_setup.gen_cellsObjects(fract, obj_root, self.ctx, scale=obj_root.mw_vis.cell_scale, flipN=cfg.debug_flipCellNormals)
        cont.precalculations(cells)
        if not cont.precalculated:
            return self.end_op_error("error during container precalculations!")


        DEV.log_msg("Start calc links", {'CALC', 'LINKS'})
        fract.links = links = MW_Links(cont)
        if not links.initialized:
            return self.end_op_error("found no links... recalc different params?")

        return self.end_op()

    def end_op(self, msg="", skipLog=False, retPass=False):
        """ # OVERRIDE:: end_op to perform stuff at the end """

        if self.obj_root:
            # copy any cfg that may have changed during execute
            copyProps(self.obj_root.mw_gen, self.cfg)
            # set the meta type to all objects at once
            MW_id_utils.setMetaType(self.obj_root, {"CHILD"}, skipParent=True)
            utils_scene.select_unhide(self.obj_root, self.ctx)

        # keep the panel updated
        MW_global_selected.recheckSelected()
        return super().end_op(msg, skipLog, retPass)


class MW_gen_recalc_OT(_StartRefresh_OT):
    bl_idname = "mw.gen_recalc"
    bl_label = "Recalculate facture"
    bl_description = "For selected root. Useful after a module reload etc..."

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return MW_global_selected.root

    def execute(self, context: types.Context):
        self.start_op()
        prefs = getPrefs()
        obj_root = MW_global_selected.root
        gen_cfg = obj_root.mw_gen

        # Add to global storage to generate the fracture id (also potentially free existing storage to reduce max memory)
        MW_global_storage.freeFract_attempt(obj_root)
        fract = MW_Fract()
        MW_global_storage.addFract(fract, obj_root) # no need to store, there is no mod last op panel

        DEV.log_msg("Retrieving fracture data (objects and points)", {'SETUP'})
        if gen_cfg.shape_useConvexHull:
            obj_toFrac = utils_scene.get_child(obj_root, prefs.names.original_dissolve)
        else: obj_toFrac = utils_scene.get_child(obj_root, prefs.names.original_copy)

        points = mw_extraction.get_points_from_fracture(obj_root)
        if not points:
            return self.end_op_error("found no points...")

        obj_cells_root = utils_scene.get_child(obj_root, prefs.names.cells)
        if not obj_cells_root:
            return self.end_op_error("found no cells...")

        # Get more data from the points
        bb, bb_center, bb_radius = utils_trans.get_bb_data(obj_toFrac, gen_cfg.margin_box_bounds)
        getStats().logDt(f"calc bb: [{bb_center[:]}] r {bb_radius:.3f} (margin {gen_cfg.margin_box_bounds:.4f})")
        if gen_cfg.shape_useWalls:
            faces4D = utils_trans.get_faces_4D(obj_toFrac, gen_cfg.margin_face_bounds)
        else: faces4D = []
        getStats().logDt(f"calc faces4D: {len(faces4D)} (n_disp {gen_cfg.margin_face_bounds:.4f})")


        DEV.log_msg("Calc cont and links (cells not regenerated!)", {'CALC'})
        fract.cont = cont = MW_Cont(obj_root, points, bb, faces4D, precision=gen_cfg.debug_precisionWalls)
        if not cont:
            return self.end_op_error("found no cont... but could try recalculate!")

        # precalculate/query neighs and other data
        cont.precalculations(obj_cells_root.children)

        # calculate links and store in the external storage
        fract.links = links = MW_Links(cont)
        if not links.initialized:
            return self.end_op_error("found no links... but could try recalculate!")

        return self.end_op()

    def end_op(self, msg="", skipLog=False, retPass=False):
        """ # OVERRIDE:: end_op to perform stuff at the end """
        MW_global_selected.recheckSelected()
        return super().end_op(msg, skipLog, retPass)

#-------------------------------------------------------------------

class MW_cell_state_OT(_StartRefresh_OT):
    bl_idname = "mw.cell_state"
    bl_label = "Set cell state"
    bl_description = "Set the selected cells state"

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}

    # example of how to do the enum as a blender prop, but then is would have to be stored inside the cell
    # blender provides some way to add id to enum props but is not well documented
    set_state: bpy.props.EnumProperty(
        name="STATE",
        description="Set cells state",
        items=(
            ('SOLID', "Solid",  "Initial cell state"),
            ('CORE', "Core",    "Immutable cells that cannot be removed"),
            ('AIR', "Air",      "Detached cells that have been removed")
        ),
        default={'SOLID'},
        options={'ENUM_FLAG'},
    )

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...
        self.invoke_log = True

    @classmethod
    def poll(cls, context):
        # NOTE:: the cells store the state so could be extracted from there, but better with just the cont
        return MW_global_selected.fract and MW_id_utils.hasCellId(MW_global_selected.current)

    def invoke(self, context, event):
        # set to current state
        cell_id = MW_global_selected.current.mw_id.cell_id
        cell_state = MW_global_selected.fract.cont.cells_state[cell_id]
        self.set_state = {STATE_ENUM.to_str(cell_state)}

        # set args before execution to confirm
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context: types.Context):
        # override parent class drawing, just the enum
        self.layout.prop(self, "set_state")

    def execute(self, context: types.Context):
        self.start_op()
        DEV.log_msg(f"arg_state: {self.set_state}")
        state = STATE_ENUM.from_str(self.set_state.pop())
        mw_setup.set_cellsState(MW_global_selected.fract, MW_global_selected.root, MW_global_selected.selection, state)
        # TODO:: recalc some link stuff + components
        return self.end_op()

#-------------------------------------------------------------------

class MW_gen_links_OT(_StartRefresh_OT):
    bl_idname = "mw.gen_links"
    bl_label = "Generate links object"
    bl_description = "Generate a visual representation of the links of a fracture object"

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...
        self.invoke_log = True

    @classmethod
    def poll(cls, context):
        return MW_global_selected.fract

    def execute(self, context: types.Context):
        self.start_op()
        mw_setup.gen_linksMesh(MW_global_selected.fract, MW_global_selected.root, context)
        #mw_setup.gen_linksWallObject(MW_global_selected.fract, MW_global_selected.root, context)
        return self.end_op()

    def end_op(self, msg="", skipLog=False, retPass=False):
        """ # OVERRIDE:: end_op to perform assign child to all """
        obj = MW_global_selected.root
        if obj: MW_id_utils.setMetaType(obj, {"CHILD"}, skipParent=True)
        return super().end_op(msg, skipLog, retPass)

#-------------------------------------------------------------------

class MW_sim_step_OT(_StartRefresh_OT):
    bl_idname = "mw.sim_step"
    bl_label = "sim step"
    bl_description = "WIP: sim steps"

    bl_options = {'PRESET', 'REGISTER', 'UNDO'}
    cfg: props.PointerProperty(type=MW_sim_cfg)

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...
        self.invoke_log  = True
        self.refresh_log = True
        self.end_log     = True

    def draw(self, context: types.Context):
        super().draw(context)
        cfg : MW_gen_cfg = self.cfg
        layout = self.layout
        col = layout.box().column()

        # step
        col.prop(cfg, "step_infiltrations")
        col.prop(cfg, "step_maxDepth")
        col.prop(cfg, "step_deg")

        # debug
        open, box = ui.draw_propsToggle_custom(cfg, getPrefs().sim_PT_meta_inspector, layout, "meta_show_debug_props", propFilter="debug", scaleBox=0.85)

    @classmethod
    def poll(cls, context):
        return MW_global_selected.fract

    def invoke(self, context, event):
        getPrefs().gen_PT_meta_inspector.reset_meta_show_toggled()
        # TODO:: rework create simulation object
        self.links = MW_global_selected.fract.links
        self.sim = mw_sim.MW_Sim(self.links)
        return super().invoke(context, event)

    def execute(self, context: types.Context):
        self.start_op()
        prefs = getPrefs()

        # handle refresh
        if self.checkRefresh_cancel() or prefs.gen_PT_meta_inspector.skip_meta_show_toggled():
            return self.end_op_refresh(skipLog=True)

        # achieve constructive results during adjust op menu
        sim_cfg : MW_sim_cfg= self.cfg
        self.sim.resetSim(sim_cfg.debug_addSeed)
        self.sim.set_deg(sim_cfg.step_deg)
        DEV.log_msg(f"step_infiltrations({sim_cfg.step_infiltrations}) step_maxDepth({sim_cfg.step_maxDepth}) step_deg({sim_cfg.step_deg})", {'SETUP'})

        for step in range(sim_cfg.step_infiltrations):
            if sim_cfg.debug_uniformDeg: self.sim.stepAll()
            else: self.sim.step(sim_cfg.step_maxDepth)

        # IDEA:: store copy or original or button to recalc links from start? -> set all life to 1 but handle any dynamic list
        mw_setup.gen_linksMesh(MW_global_selected.fract, MW_global_selected.root, context)
        mw_setup.gen_linksWallObject(MW_global_selected.fract, MW_global_selected.root, context,
                                    self.sim.step_trace.entryL_candidatesW if self.sim.trace else None)

        return self.end_op()

class MW_sim_reset_OT(_StartRefresh_OT):
    bl_idname = "mw.sim_reset"
    bl_label = "sim reset"
    bl_description = "WIP: sim reset"

    bl_options = {'INTERNAL', 'UNDO'}

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...

    @classmethod
    def poll(cls, context):
        return MW_global_selected.fract

    def execute(self, context: types.Context):
        self.start_op()

        # TODO:: global sim atm
        self.links = MW_global_selected.fract.links
        mw_sim.resetLife(self.links)

        mw_setup.gen_linksMesh(MW_global_selected.fract, MW_global_selected.root, context)
        mw_setup.gen_linksWallObject(MW_global_selected.fract, MW_global_selected.root, context)
        return self.end_op()

#-------------------------------------------------------------------

class MW_util_comps_OT(_StartRefresh_OT):
    bl_idname = "mw.util_comps"
    bl_label = "check comps"
    bl_description = "UTIL: check connected components"

    bl_options = {'INTERNAL', 'UNDO'}

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...

    @classmethod
    def poll(cls, context):
        return MW_global_selected.fract

    def execute(self, context: types.Context):
        self.start_op()
        mw_extraction.get_connected_comps(MW_global_selected.fract)
        return self.end_op()

class MW_util_bool_OT(_StartRefresh_OT):
    bl_idname = "mw.util_bool"
    bl_label = "bool mod"
    bl_description = "WIP: add bool modifier to original"

    bl_options = {'INTERNAL', 'UNDO'}

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...

    @classmethod
    def poll(cls, context):
        return MW_global_selected.root

    def execute(self, context: types.Context):
        self.start_op()
        obj = MW_global_selected.root

        if obj:
            prefs = getPrefs()
            obj_original = utils_scene.get_child(obj, prefs.names.original_copy, mode="STARTS_WITH")
            obj_cells = utils_scene.get_child(obj, prefs.names.cells)
            mw_extraction.boolean_mod_add(obj_original, obj_cells, context, prefs.util_bool_OT_apply)

        return self.end_op()

class MW_util_delete_OT(_StartRefresh_OT):
    bl_idname = "mw.util_delete"
    bl_label = "Delete fracture object"
    bl_description = "Instead of Blender 'delete hierarchy' which seems to fail to delete all recusively..."

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return MW_global_selected.root

    def execute(self, context: types.Context):
        self.start_op()
        prefs = getPrefs()
        obj = MW_global_selected.root
        gen_cfg = obj.mw_gen

        # optionally unhide the original object
        if (prefs.util_delete_OT_unhideSelect):
            obj_original = utils_scene.get_object_fromScene(context.scene, gen_cfg.struct_nameOriginal)
            if not obj_original:
                self.logReport("obj_original not found -> wont unhide")
            else:
                utils_scene.select_unhideRec(obj_original, context, selectChildren=False)

        # potentially free memory from storage
        if prefs.prefs_autoPurge and MW_global_storage.hasFract(obj):
            MW_global_storage.freeFract(obj)

        # finally delete the fracture object recusively
        utils_scene.delete_objectRec(obj, logAmount=True)
        return self.end_op()

class MW_util_delete_all_OT(_StartRefresh_OT):
    bl_idname = "mw.util_delete_all"
    bl_label = "Delete all fracture objects"
    bl_description = "Instead of Blender 'delete hierarchy' which seems to fail to delete all recusively..."

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context: types.Context):
        self.start_op()

        # iterate and delete roots
        roots = MW_id_utils.getSceneRoots(context.scene)
        for obj_root in roots:
            MW_global_selected.setSelected([obj_root])
            bpy.ops.mw.util_delete()

        #MW_global_selected.resetSelected()
        MW_global_selected.setSelected(context.selected_objects)
        return self.end_op()

#-------------------------------------------------------------------

class MW_util_bake_OT(_StartRefresh_OT):
    bl_idname = "mw.util_bake"
    bl_label = "Bake"
    bl_description = "Unlink the cell from the fracture, e.g. to recursive fracture it"

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return MW_global_selected.current and MW_id_utils.isChild(MW_global_selected.current)

    def execute(self, context: types.Context):
        self.start_op(skipStats=True)
        cell = utils_scene.copy_object(MW_global_selected.current, context)

        cell.parent = None
        MW_id_utils.resetMetaType(cell)
        utils_scene.select_nothing()
        utils_scene.select_unhide(cell, context)
        return self.end_op(skipLog=True)

#-------------------------------------------------------------------
# Blender events

classes = [
    MW_gen_OT,
    MW_gen_recalc_OT,

    MW_cell_state_OT,
    MW_gen_links_OT,

    MW_sim_step_OT,
    MW_sim_reset_OT,

    MW_util_comps_OT,
    MW_util_bool_OT,
    MW_util_delete_OT,
    MW_util_delete_all_OT,
    MW_util_bake_OT,
] + util_classes_op

register, unregister = bpy.utils.register_classes_factory(classes)
