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

from .operators_utils import _StartRefresh_OT, util_classes_op

from . import mw_setup
from . import mw_extraction
from .mw_links import LinkCollection
from .mw_cont import MW_Container
from .mw_fract import MW_Fract
from . import mw_sim

from . import ui
from . import utils
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

    # NOTE:: no poll because the button is removed from ui in draw instead

    def draw(self, context: types.Context):
        super().draw(context)
        ui.draw_gen_cfg(self.cfg, self.layout, context)

    def invoke(self, context, event):
        # avoid last stored operation overide
        self.invoked_once = False
        getPrefs().gen_PT_meta_inspector.reset_meta_show_toggled()

        # TODO:: potentially clean memory ptr leftovers?
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

        # Potentially free existing storage -> now purged on undo callback dynamically too
        if self.last_storageID is not None:
            MW_global_storage.freeFract_fromID(self.last_storageID)


        # Retrieve root
        obj = MW_global_selected.root
        getStats().logDt("retrieved root object")
        try:
            # Selected object not fractured, fresh execution
            if obj is None:
                DEV.log_msg("cfg NOT found: new frac", {'SETUP'})
                obj_root, obj_original = mw_setup.copy_original(context.selected_objects[-1], self.cfg, context)
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
                    utils.hide_objectRec(obj)

                DEV.log_msg("cfg found: duplicating frac", {'SETUP'})
                obj_root, obj_original = mw_setup.copy_originalPrev(obj, self.cfg, context)
                return self.execute_fresh(obj_root, obj_original)

        # catch exceptions to at least mark as child and copy props
        except Exception as e:
            if not DEV.HANDLE_GLOBAL_EXCEPT: raise e
            return self.end_op_error("unhandled exception...")


    def execute_fresh(self, obj_root:types.Object, obj_original:types.Object ):
        self.obj_root = obj_root
        prefs = getPrefs()

        # TODO:: cfg_vis?
        cfg: MW_gen_cfg = self.cfg
        cfg.rnd_seed = utils.rnd_seed(cfg.rnd_seed)


        DEV.log_msg("Initial object setup", {'SETUP'})
        # NOTE:: convex hull triangulates the faces... e.g. UV sphere ends with more!
        if cfg.shape_useConvexHull:
            obj_toFrac = mw_setup.copy_convex(obj_root, obj_original, cfg, self.ctx)
        else: obj_toFrac = obj_original

        DEV.log_msg("Start calc points", {'CALC'})
        # Get the points and transform to local space when needed
        mw_extraction.detect_points_from_object(obj_original, cfg, self.ctx)
        points = mw_extraction.get_points_from_object_fallback(obj_original, cfg, self.ctx)
        if not points:
            return self.end_op_error("found no points...")

        # Get more data from the points
        bb, bb_center, bb_radius = utils.get_bb_data(obj_toFrac, cfg.margin_box_bounds)
        getStats().logDt(f"calc bb: [{bb_center[:]}] r {bb_radius:.3f} (margin {cfg.margin_box_bounds:.4f})")
        if cfg.shape_useWalls:
            faces4D = utils.get_faces_4D(obj_toFrac, cfg.margin_face_bounds)
        else: faces4D = []
        getStats().logDt(f"calc faces4D: {len(faces4D)} (n_disp {cfg.margin_face_bounds:.4f})")

        # XXX:: 2D objects should use the boundary? limits walls per axis
        # XXX:: limit particles axis too?

        # Limit and rnd a bit the points
        mw_extraction.points_transformCfg(points, cfg, bb_radius)

        # Add some reference of the points to the scene
        mw_setup.gen_pointsObject(obj_root, points, self.cfg, self.ctx)
        mw_setup.gen_boundsObject(obj_root, bb, self.cfg, self.ctx)


        DEV.log_msg("Start calc cont and links", {'CALC'})
        # IDEA:: mesh conecting input points + use single mesh instead of one per link?
        # IDEA:: generate in phases? only cont, then links, etc...
        # XXX:: detect meshes with no volume? test basic shape for crashes...

        cont = MW_Container(points, bb, faces4D, precision=prefs.gen_calc_precisionWalls)
        if not cont:
            return self.end_op_error("found no cont... but could try recalculate!")

        # shards are always added to the scene
        obj_shards = mw_setup.gen_shardsEmpty(obj_root, cfg, self.ctx)

        #test some legacy or statistics cont stuff
        if DEV.LEGACY_CONT:
            mw_setup.gen_LEGACY_CONT(obj_shards, cont, cfg, self.ctx)
            return self.end_op("DEV.LEGACY_CONT stop...")
        mw_setup.gen_shardsObjects(obj_shards, cont, cfg, self.ctx, scale=obj_root.mw_vis.cell_scale, invertOrientation=prefs.gen_setup_invertShardNormals)

        # calculate links and store in the external storage
        links:LinkCollection = LinkCollection(cont, obj_shards)
        if not links.initialized:
            return self.end_op_error("found no links... but could try recalculate!")


        # use global storage
        fract = MW_Fract()
        fract.cont = cont
        fract.links = links
        self.last_storageID = MW_global_storage.addFract(fract, obj_root)

        return self.end_op()

    def end_op(self, msg="", skipLog=False, retPass=False):
        """ OVERRIDE:: end_op to perform stuff at the end """

        if self.obj_root:
            # copy any cfg that may have changed during execute
            self.cfg.name = self.obj_root.name
            copyProps(self.cfg, self.obj_root.mw_gen)
            # set the meta type to all objects at once
            MW_id_utils.setMetaType(self.obj_root, {"CHILD"}, skipParent=True)
            utils.select_unhide(self.obj_root, self.ctx)

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

        # Potentially free existing storage (less max memory)
        MW_global_storage.freeFract_attempt(obj_root)

        DEV.log_msg("Retrieving fracture data (objects and points)", {'SETUP'})
        if gen_cfg.shape_useConvexHull:
            obj_toFrac = utils.get_child(obj_root, prefs.names.original_dissolve)
        else: obj_toFrac = utils.get_child(obj_root, prefs.names.original_copy)

        points = mw_extraction.get_points_from_fracture(obj_root, gen_cfg)
        if not points:
            return self.end_op_error("found no points...")

        obj_shards = utils.get_child(obj_root, prefs.names.shards)
        if not obj_shards:
            return self.end_op_error("found no shards...")

        # Get more data from the points
        bb, bb_center, bb_radius = utils.get_bb_data(obj_toFrac, gen_cfg.margin_box_bounds)
        getStats().logDt(f"calc bb: [{bb_center[:]}] r {bb_radius:.3f} (margin {gen_cfg.margin_box_bounds:.4f})")
        if gen_cfg.shape_useWalls:
            faces4D = utils.get_faces_4D(obj_toFrac, gen_cfg.margin_face_bounds)
        else: faces4D = []
        getStats().logDt(f"calc faces4D: {len(faces4D)} (n_disp {gen_cfg.margin_face_bounds:.4f})")


        DEV.log_msg("Calc cont and links (shards not regenerated!)", {'CALC'})
        cont = MW_Container(points, bb, faces4D, precision=prefs.gen_calc_precisionWalls)
        if not cont:
            return self.end_op_error("found no cont... but could try recalculate!")

        # calculate links and store in the external storage
        links:LinkCollection = LinkCollection(cont, obj_shards)
        if not links.initialized:
            return self.end_op_error("found no links... but could try recalculate!")


        # use global storage
        fract = MW_Fract()
        fract.cont = cont
        fract.links = links
        self.last_storageID = MW_global_storage.addFract(fract, obj_root)

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
        obj = MW_global_selected.root
        gen_cfg = obj.mw_gen
        links = MW_global_selected.fract.links

        ## WIP:: per cell no need but atm cont ref is inside LinkCollection structure
        #obj_links_legacy = mw_setup.genWIP_linksEmptiesPerCell(obj, cfg, context)
        #mw_setup.genWIP_linksCellObjects(obj_links_legacy, links.cont, cfg, context)

        #obj_links, obj_links_air = mw_setup.genWIP_linksEmpties(obj, cfg, context)
        ##mw_setup.genWIP_linksObjects(obj_links, obj_links_air, links, cfg, context)
        #mw_setup.gen_linksSingleObject(obj_links, obj_links_air, links, cfg, context)

        mw_setup.gen_linksObject(obj, links, gen_cfg, context)
        mw_setup.gen_linksWallObject(obj, links, gen_cfg, context)

        return self.end_op()

    def end_op(self, msg="", skipLog=False, retPass=False):
        """ OVERRIDE:: end_op to perform assign child to all """
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
    sim: mw_sim.Simulation = None
    links: LinkCollection = None

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...
        self.invoke_log  = True
        self.refresh_log = True
        self.end_log     = True

    def draw(self, context: types.Context):
        super().draw(context)
        ui.draw_props(self.cfg, "", self.layout.box(), True)

    @classmethod
    def poll(cls, context):
        return MW_global_selected.fract

    def invoke(self, context, event):
        # create simulation object
        self.links = MW_global_selected.fract.links
        self.sim = mw_sim.Simulation(self.links)

        return super().invoke(context, event)

    def execute(self, context: types.Context):
        self.start_op()
        sim_cfg : MW_sim_cfg= self.cfg

        # handle refresh
        cancel = self.checkRefresh_cancel()
        if cancel: return self.end_op_refresh(skipLog=True)

        # achieve constructive results during adjust op menu
        self.sim.resetSim(sim_cfg.addSeed)
        self.sim.set_deg(sim_cfg.deg)
        DEV.log_msg(f"steps({sim_cfg.steps}) subSteps({sim_cfg.subSteps}) deg({sim_cfg.deg})", {'SETUP'})

        for step in range(sim_cfg.steps):
            if sim_cfg.steps_uniformDeg: self.sim.stepAll()
            else: self.sim.step(sim_cfg.subSteps)

        # IDEA:: store copy or original or button to recalc links from start? -> set all life to 1 but handle any dynamic list
        obj = MW_global_selected.root
        if obj:
            gen_cfg = obj.mw_gen
            mw_setup.gen_linksObject(obj, self.links, gen_cfg, context)
            mw_setup.gen_linksWallObject(obj, self.links, gen_cfg, context, self.sim.step_trace.entryL_candidatesW if self.sim.trace else None)

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

        obj = MW_global_selected.root
        if obj:
            gen_cfg = obj.mw_gen
            mw_setup.gen_linksObject(obj, self.links, gen_cfg, context)
            mw_setup.gen_linksWallObject(obj, self.links, gen_cfg, context)
        return self.end_op()

#-------------------------------------------------------------------

class MW_util_comps_OT(_StartRefresh_OT):
    bl_idname = "mw.util_omps"
    bl_label = "check comps"
    bl_description = "WIP: check connected components"

    bl_options = {'INTERNAL', 'UNDO'}

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...

    @classmethod
    def poll(cls, context):
        return MW_global_selected.fract

    def execute(self, context: types.Context):
        self.start_op()
        mw_extraction.get_connected_comps(MW_global_selected.fract.links)
        return self.end_op()

class MW_util_bool_OT(_StartRefresh_OT):
    bl_idname = "mw.util_bool"
    bl_label = "bool mod"
    bl_description = "WIP: add bool modifier"

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
            obj_original = utils.get_child(obj, prefs.names.original_copy + prefs.names.original)
            obj_shards = utils.get_child(obj, prefs.names.shards)
            mw_extraction.boolean_mod_add(obj_original, obj_shards, context)

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
        cfg = obj.mw_gen

        # optionally unhide the original object
        if (prefs.util_delete_OT_unhideSelect):
            obj_original = utils.get_object_fromScene(context.scene, cfg.struct_nameOriginal)
            if not obj_original:
                self.logReport("obj_original not found -> wont unhide")
            else:
                utils.select_unhideRec(obj_original, context, selectChildren=False)

        # potentially free memory from storage
        if prefs.prefs_autoPurge and MW_global_storage.hasFract(obj):
            MW_global_storage.freeFract(obj)

        # finally delete the fracture object recusively
        utils.delete_objectRec(obj, logAmount=True)
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
    bl_description = "Unlink the shard from the fracture, e.g. to recursive fracture it"

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return MW_global_selected.last and MW_id_utils.isChild(MW_global_selected.last)

    def execute(self, context: types.Context):
        self.start_op(skipStats=True)
        cell = utils.copy_object(MW_global_selected.last, context)

        cell.parent = None
        MW_id_utils.resetMetaType(cell)
        utils.select_nothing()
        utils.select_unhide(cell, context)
        return self.end_op(skipLog=True)

#-------------------------------------------------------------------
# Blender events

classes = [
    MW_gen_OT,
    MW_gen_recalc_OT,
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
