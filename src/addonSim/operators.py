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
    MW_vis_cfg,
    MW_resistance_cfg,
)
from . import properties_utils
from .operators_dm import _StartRefresh_OT, op_utils_classes

from . import mw_setup, mw_extraction
from .mw_links import MW_Links
from .mw_cont import MW_Cont, CELL_STATE_ENUM
from .mw_fract import MW_Fract
from .mw_sim import MW_Sim, SIM_EXIT_FLAG

from . import ui
from . import utils, utils_scene, utils_trans
from .utils_mat import gen_textureMat_DEVfix
from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

class MW_gen_OT(_StartRefresh_OT):
    bl_idname = "mw.gen"
    bl_label = "Cells generation"
    bl_description = "Voronoi cells generation (also internal links)"

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
        rowsub.prop(cfg, "shape_useWalls")
        rowsub.prop(cfg, "shape_useConvexHull")
        rowsub = col.row(align=True)
        rowsub.prop(cfg, "margin_face_bounds")
        rowsub.prop(cfg, "margin_box_bounds")

        # debug settings
        open, box = ui.draw_propsToggle_custom(cfg, getPrefs().gen_PT_meta_inspector, layout, "meta_show_debug_props", propFilter="debug,-rnd", scaleBox=0.85)
        ui.draw_debug_rnd(box, cfg.debug_rnd)

    # NOTE:: no poll because the button is removed from ui in draw instead
    #@classmethod
    #def poll(cls, context):
    #    # XXX:: required achieve edit last op but MW_global_selected is none?
    #    MW_global_selected.logSelected()
    #    return MW_global_selected.last

    def invoke(self, context, event):
        # avoid last stored operation overide and recalculating everything
        prefs = getPrefs()
        getPrefs().gen_PT_meta_inspector.reset_meta_show_toggled()

        # will copy prop from obj once
        self.invoked_once = False

        # id of last fract calculated stored (outside the operator)
        self.last_storageID = None

        # rnd seed
        s = None if self.cfg.debug_rnd.seed_regen else self.cfg.debug_rnd.seed
        self.cfg.debug_rnd.seed = utils.rnd_reset_seed(s)

        return super().invoke(context, event)

    #-------------------------------------------------------------------

    def execute(self, context: types.Context):
        self.start_op()
        self.obj_root = None
        self.context = context
        prefs = getPrefs()

        # handle refresh
        if self.checkRefresh_cancel() or prefs.gen_PT_meta_inspector.skip_meta_show_toggled():
            # BUG:: try to fix black images
            if DEV.FIX_IMAGES_QUEUE:
                gen_textureMat_DEVfix()
            # fix by reexec all OP
            if not DEV.FIX_IMAGES_REDO:
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
                properties_utils.copyProps_groups_rec(prefs.mw_vis, obj_root.mw_vis)
                return self.execute_fresh(obj_root, obj_original)

            # Fracture the same original object, copy props for a duplicated result to tweak parameters
            # NOTE:: no longer supporting edit fracture -> basically always replaces all objects in the scene which is slower than a fresh one
            else:
                # Copy the config to the op only once to allow the user to edit it afterwards
                if not self.invoked_once:
                    self.invoked_once = True
                    DEV.log_msg("cfg found once: copying props to OP", {'SETUP'})
                    properties_utils.copyProps_groups_rec(obj.mw_gen, self.cfg)

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
        properties_utils.copyProps_groups_rec(self.cfg, obj_root.mw_gen)
        cfg: MW_gen_cfg = obj_root.mw_gen
        # keep consistent seed
        cfg.debug_rnd.seed = utils.rnd_reset_seed(cfg.debug_rnd.seed, cfg.debug_rnd.seed_mod)

        # Add to global storage to generate the fracture id
        fract = MW_Fract()
        self.last_storageID = MW_global_storage.addFract(fract, obj_root)


        DEV.log_msg("Initial object setup", {'SETUP'})
        if cfg.shape_useConvexHull:
            # NOTE:: convex hull triangulates the faces... e.g. UV sphere ends with more!
            obj_toFrac = mw_setup.copy_convex(obj_root, obj_original, self.context, prefs.names.original_convex, prefs.names.original_dissolve)
        else: obj_toFrac = obj_original


        DEV.log_msg("Start calc faces", {'CALC'})
        bb, bb_center, bb_radius = utils_trans.get_bb_data(obj_toFrac, cfg.margin_box_bounds)
        getStats().logDt(f"calc bb: [{bb_center[:]}] r {bb_radius:.3f} (margin {cfg.margin_box_bounds:.4f})")
        if cfg.shape_useWalls:
            faces4D = utils_trans.get_faces_4D(obj_toFrac, cfg.margin_face_bounds)
        else: faces4D = []
        getStats().logDt(f"calc faces4D: {len(faces4D)} (n_disp {cfg.margin_face_bounds:.4f})")


        DEV.log_msg("Start calc points", {'CALC'})
        mw_extraction.detect_points_from_object(obj_original, cfg, self.context)
        points = mw_extraction.get_points_from_object_fallback(obj_original, cfg, self.context)
        cfg.source_numFound = len(points)
        if not points:
            return self.end_op_error("found no points...")

        # Limit and rnd a bit the points
        mw_extraction.points_transformCfg(points, cfg, bb_radius)

        # Add some reference of the points to the scene
        obj_points = mw_setup.gen_pointsObject(obj_root, points, self.context, prefs.names.source_points)
        utils_scene.hide_objectRec(obj_points, prefs.mw_vis.cell_hide_points)
        mw_setup.gen_boundsObject(obj_root, bb, self.context, prefs.names.source_wallsBB)
        getStats().logDt("generated point and bound objects")


        DEV.log_msg("Start calc cont", {'CALC', 'CONT'})
        fract.cont = cont = MW_Cont(obj_root, points, bb, faces4D, precision=cfg.debug_precisionWalls)
        if not cont.initialized:
            return self.end_op_error("found no cont or cells... recalc different params?")

        #test some legacy or statistics cont stuff
        if DEV.LEGACY_CONT_GEN:
            mw_setup.gen_cells_LEGACY(cont.voro_cont, obj_root, self.context)
            return self.end_op("DEV.LEGACY_CONT_GEN stop...")

        # precalculate/query neighs and other data with generated cells mesh
        cells = mw_setup.gen_cellsObjects(fract, obj_root, self.context, scale=obj_root.mw_vis.cell_scale, flipN=cfg.debug_flipCellNormals)
        cont.precalculations(cells)
        if not cont.precalculated:
            return self.end_op_error("error during container precalculations!")


        DEV.log_msg("Start calc links", {'CALC', 'LINKS'})
        fract.links = links = MW_Links(cont)
        if not links.initialized:
            return self.end_op_error("found no links... recalc different params?")


        # create an empty simulation too
        fract.sim = MW_Sim(fract.cont, fract.links)

        return self.end_op()

    def end_op(self, msg="", skipLog=False, retPass=False):
        """ # OVERRIDE:: end_op to perform stuff at the end """
        #DEV.log_msg("end_op", {'SETUP'})

        if self.obj_root:
            DEV.log_msg("end_op: copy props etc", {'SETUP'})
            # copy any cfg that may have changed during execute
            properties_utils.copyProps_groups_rec(self.obj_root.mw_gen, self.cfg)
            # set the meta type to all objects at once
            MW_id_utils.setMetaType_rec(self.obj_root, {"CHILD"}, skipParent=True)
            utils_scene.select_unhide(self.obj_root, self.context)

        # keep the panel updated
        MW_global_selected.recheckSelected()

        if MW_global_selected.root:
            # optional links direct generation
            if getPrefs().gen_calc_OT_links:
                mw_setup.gen_linksAll(self.context)

            # optional field visualiztion
            cfg : MW_resistance_cfg = getPrefs().resist_cfg
            if cfg.vis__show:
                DEV.log_msg("Visual field R", {'SETUP'})
                mw_setup.gen_field_R(MW_global_selected.root, self.context, cfg.vis_res, cfg.vis_smoothShade, cfg.vis_flipN)
                #self.FIX_fieldR_obj = obj_root

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
        else: obj_toFrac = utils_scene.get_child(obj_root, prefs.names.original_copy, mode="STARTS_WITH")

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
        if not cont.initialized:
            return self.end_op_error("found no cont or cells... recalc different params?")

        # precalculate/query neighs and other data
        cont.precalculations(obj_cells_root.children)

        # calculate links and store in the external storage
        fract.links = links = MW_Links(cont)
        if not links.initialized:
            return self.end_op_error("found no links... recalc different params?")

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
        self.set_state = {CELL_STATE_ENUM.to_str(cell_state)}

        # set args before execution to confirm
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context: types.Context):
        # override parent class drawing, just the enum
        self.layout.prop(self, "set_state")

    def execute(self, context: types.Context):
        self.start_op()
        state = CELL_STATE_ENUM.from_str(self.set_state.pop())
        recalc = getPrefs().util_comps_OT_recalc
        links : MW_Links = MW_global_selected.fract.links

        # get target cells id + potentially direlcty set the state
        cells_id = mw_setup.set_cellsState(MW_global_selected.fract.cont, MW_global_selected.root, MW_global_selected.selection, state, not recalc)

        # set the cell state through the links and recalculate changes in graphs
        if cells_id and recalc:
            links.setState_cells_check(cells_id, state)
            mw_setup.update_cellsState(MW_global_selected.fract.cont, MW_global_selected.root)
            mw_setup.gen_linksAll(context)

        return self.end_op()

#-------------------------------------------------------------------

class MW_gen_links_OT(_StartRefresh_OT):
    bl_idname = "mw.gen_links"
    bl_label = "Update links"
    bl_description = "Generate the visual representation of the links of a fracture object"

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

        # check potentially deleted cells etc
        MW_global_selected.fract.sanitize(MW_global_selected.root)

        # update dir from scene arrow
        if MW_global_selected.root.mw_sim.dir_entry_fromArrow:
            mw_setup.update_arrow_dir(MW_global_selected.root)

        # for this OP, delete all meshes before regen
        mw_setup.gen_linksDelete()

        # update cells too
        mw_setup.update_cellsState(MW_global_selected.fract.cont, MW_global_selected.root)

        mw_setup.gen_linksAll(context)
        return self.end_op()

class MW_gen_field_r_OT(_StartRefresh_OT):
    bl_idname = "mw.gen_field_r"
    bl_label = "Update field"
    bl_description = "Generate or update the visual representation of the resistance field"

    bl_options = {'INTERNAL', 'UNDO'}

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...

    @classmethod
    def poll(cls, context):
        return MW_global_selected.root

    def execute(self, context: types.Context):
        self.start_op()

        # will generate or update it
        cfg : MW_resistance_cfg = getPrefs().resist_cfg
        mw_setup.gen_field_R(MW_global_selected.root, context, cfg.vis_res, cfg.vis_smoothShade, cfg.vis_flipN)

        # update links R
        if  MW_global_selected.fract and MW_global_selected.fract.links:
            links :MW_Links = MW_global_selected.fract.links
            for key in links.links_graph.nodes():
                l = links.get_link(key)
                l.update_resistance()

        return self.end_op()

#-------------------------------------------------------------------

class MW_sim_step_OT(_StartRefresh_OT):
    bl_idname = "mw.sim_step"
    bl_label = "sim step"
    bl_description = "Simulate a series of water infiltrations"

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
        col.prop(cfg, "water__start")
        col.prop(cfg, "water_deg")
        row = col.split()
        row.prop(cfg, "water_abs_solid")
        row.prop(cfg, "water_abs_air")
        col.prop(cfg, "link_deg")
        col.prop(cfg, "link_resist_weight")

        sim : MW_Sim = MW_global_selected.fract.sim
        if sim.step_path:
            col.label(text=sim.step_log_ui(), icon="OUTLINER_OB_GREASEPENCIL")

        # params and debug
        prefs = getPrefs()
        paramFilter = "-step,-debug,-water__start,-water_abs,-link,"
        open, box = ui.draw_propsToggle_custom(cfg, prefs.sim_PT_meta_inspector, layout, "meta_show_1", text="Parameters", propFilter=paramFilter)
        open, box = ui.draw_propsToggle_custom(cfg, prefs.sim_PT_meta_inspector, layout, "meta_show_debug_props", propFilter="debug,-rnd", scaleBox=0.85)
        ui.draw_debug_rnd(box, cfg.debug_rnd)

    @classmethod
    def poll(cls, context):
        return MW_global_selected.fract and MW_global_selected.fract.sim

    def invoke(self, context, event):
        # avoid last stored operation overide and recalculating everything
        prefs = getPrefs()
        prefs.gen_PT_meta_inspector.reset_meta_show_toggled()

        # copy props once
        self.invoked_once = False

        # store current state
        sim : MW_Sim = MW_global_selected.fract.sim
        sim.backup_state()
        return super().invoke(context, event)

    def execute(self, context: types.Context):
        self.start_op()
        prefs = getPrefs()
        sim : MW_Sim = MW_global_selected.fract.sim

        # handle refresh
        if self.checkRefresh_cancel() or prefs.sim_PT_meta_inspector.skip_meta_show_toggled():
            # BUG:: try to fix black images
            if DEV.FIX_IMAGES_QUEUE:
                gen_textureMat_DEVfix()
            # fix by reexec all OP
            if not DEV.FIX_IMAGES_REDO:
                return self.end_op_refresh(skipLog=True)

        # copy the params config from the object once, later copy all cfg to it from op
        if not self.invoked_once:
            self.invoked_once = True
            DEV.log_msg("cfg found once: copying props to OP", {'SIM'})
            properties_utils.copyProps_groups_rec(MW_global_selected.root.mw_sim, self.cfg)
        else:
            properties_utils.copyProps_groups_rec(self.cfg, MW_global_selected.root.mw_sim)
            sim.cfg = MW_global_selected.root.mw_sim

            # restore state to get constructive results withing the mod last op panel
            sim.backup_state_restore()

        # steps
        sim_cfg : MW_sim_cfg= self.cfg
        DEV.log_msg(f"step_infiltrations({sim_cfg.step_infiltrations}), step_maxDepth({sim_cfg.step_maxDepth}), step_stopBreak({sim_cfg.step_stopBreak})", {'SIM'})
        for step_id in range(sim_cfg.step_infiltrations):
            log_step = sim_cfg.debug_log and step_id+1 > sim_cfg.step_infiltrations-sim_cfg.debug_log_lastIters
            if not sim_cfg.debug_util_uniformDeg: sim.step(log_step)
            else: sim.step_degradeAll() # alternative see erosion on all

            # no entry link due to direction
            if sim.exit_flag == SIM_EXIT_FLAG.NO_ENTRY_LINK:
                return self.end_op_error("No entry link found... (probably due dir_entry)")

            # skip the rest of steps
            if sim.exit_flag >= SIM_EXIT_FLAG.STOP_ON_LINK_BREAK:
                break

        getStats().logDt("completed simulation steps")

        # redraw links and cells
        mw_setup.update_cellsState(MW_global_selected.fract.cont, MW_global_selected.root)
        if prefs.sim_calc_OT_links:
            mw_setup.gen_linksAll(context)
        return self.end_op()

class MW_sim_reset_OT(_StartRefresh_OT):
    bl_idname = "mw.sim_reset"
    bl_label = "sim reset"
    bl_description = "Reset the simulation state, both links and cells"

    bl_options = {'INTERNAL', 'UNDO'}

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...

    @classmethod
    def poll(cls, context):
        return MW_global_selected.root and MW_global_selected.fract and MW_global_selected.fract.sim

    def execute(self, context: types.Context):
        self.start_op()

        sim : MW_Sim = MW_global_selected.fract.sim
        sim.reset(MW_global_selected.root.mw_sim.debug_util_rndState)

        # redraw links and cells
        mw_setup.update_cellsState(MW_global_selected.fract.cont, MW_global_selected.root)
        mw_setup.gen_linksAll(context)
        return self.end_op()

class MW_sim_resetCFG_OT(_StartRefresh_OT):
    bl_idname = "mw.sim_reset_cfg"
    bl_label = "sim reset cfg"
    bl_description = "Reset the simulation config (without having to execute it)"

    bl_options = {'INTERNAL', 'UNDO'}

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...

    @classmethod
    def poll(cls, context):
        return MW_global_selected.root and MW_global_selected.fract and MW_global_selected.fract.sim

    def execute(self, context: types.Context):
        self.start_op()
        properties_utils.resetProps(MW_global_selected.root.mw_sim, "-step,-debug")
        return self.end_op()

#-------------------------------------------------------------------

class MW_util_comps_OT(_StartRefresh_OT):
    bl_idname = "mw.util_comps"
    bl_label = "check comps"
    bl_description = "DEV:: check connected components"

    bl_options = {'INTERNAL', 'UNDO'}

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...

    @classmethod
    def poll(cls, context):
        return MW_global_selected.fract and MW_global_selected.fract.links

    def execute(self, context: types.Context):
        self.start_op()
        #comps = mw_extraction.get_connected_comps_unionFind(MW_global_selected.fract)

        # query comps from links
        links : MW_Links = MW_global_selected.fract.links
        DEV.log_msg(f"Prev components: {links.comps_len}")

        # check potentially deleted cells etc
        MW_global_selected.fract.sanitize(MW_global_selected.root)
        links.comps_recalc()

        if getPrefs().util_comps_OT_recalc:
            mw_setup.update_cellsState(MW_global_selected.fract.cont, MW_global_selected.root)
            mw_setup.gen_linksAll(context)

        return self.end_op()

class MW_util_bool_OT(_StartRefresh_OT):
    bl_idname = "mw.util_bool"
    bl_label = "bool mod"
    bl_description = "DEV:: bool modifier to cells to clip inside original model"

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
            mw_extraction.boolean_mod_add(context, obj_original, obj_cells, prefs.util_bool_OT_apply)

        return self.end_op()

class MW_util_bake_OT(_StartRefresh_OT):
    bl_idname = "mw.util_bake"
    bl_label = "Bake"
    bl_description = "Copy and unlink the cell from the fracture, e.g. to recursive fracture it"

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return MW_global_selected.current and MW_id_utils.isMetaChild(MW_global_selected.current)

    def execute(self, context: types.Context):
        self.start_op(skipStats=True)
        cell = utils_scene.copy_object(MW_global_selected.current, context)

        cell.parent = None
        MW_id_utils.resetMetaType(cell)
        utils_scene.select_nothing()
        utils_scene.select_unhide(cell, context)
        return self.end_op(skipLog=True)

#-------------------------------------------------------------------

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
        bpy.ops.dm.util_delete_orphan('INVOKE_DEFAULT')
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
            # manual override MW_global_selected.root to avoid touching the context between operators
            MW_global_selected.root = obj_root
            bpy.ops.mw.util_delete()

        #MW_global_selected.resetSelected()
        MW_global_selected.setSelected(context.selected_objects)
        bpy.ops.dm.util_delete_orphan('INVOKE_DEFAULT')
        return self.end_op()

class MW_util_resetCFG_OT(_StartRefresh_OT):
    bl_idname = "mw.reset_cfg"
    bl_label = "Reset all CFG"
    bl_description = "Reset config and preferences"

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...

    def execute(self, context: types.Context):
        self.start_op()
        prefs = getPrefs()

        # does not seem to work from inside the OP execute
        #bpy.ops.wm.operator_defaults()
        #layout.operator("wm.operator_defaults")

        # reset ALL props, but cannot access the operators
        #properties_utils.resetProps(prefs)
        #properties_utils.resetProps_groups(prefs, "", "dev")
        properties_utils.resetProps_rec(prefs)

        # reset ALL props -> will also set OT_clearCfg that will clear stuff later
        if MW_global_selected.root:
            properties_utils.resetProps(MW_global_selected.root.mw_sim)

        return self.end_op()


#-------------------------------------------------------------------
# Blender events

classes = [
    MW_gen_OT,
    MW_gen_recalc_OT,

    MW_cell_state_OT,
    MW_gen_links_OT,
    MW_gen_field_r_OT,

    MW_sim_step_OT,
    MW_sim_reset_OT,
    MW_sim_resetCFG_OT,

    MW_util_comps_OT,
    MW_util_bool_OT,
    MW_util_bake_OT,

    MW_util_delete_OT,
    MW_util_delete_all_OT,
    MW_util_resetCFG_OT,
] + op_utils_classes

register, unregister = bpy.utils.register_classes_factory(classes)
