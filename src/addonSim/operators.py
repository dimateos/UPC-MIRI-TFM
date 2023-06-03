import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
)
from .operators_utils import _StartRefresh_OT, util_classes_op

from . import mw_setup
from . import mw_cont
from .mw_links import LinkCollection, LinkStorage
from tess import Container
from . import mw_sim

from . import ui
from . import utils
from .utils_cfg import copyProps
from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

class MW_gen_OT(_StartRefresh_OT):
    bl_idname = "mw.gen"
    bl_label = "Fracture generation"
    bl_description = "Fracture generation using voro++"

    # REGISTER + UNDO pops the edit last op window
    bl_options = {'PRESET', 'REGISTER', 'UNDO'}
    cfg: props.PointerProperty(type=MW_gen_cfg)

    def __init__(self) -> None:
        super().__init__(init_log=True)
        # config some base class log flags...
        self.invoke_log  = True
        self.refresh_log = True
        self.end_log     = True

    # NOTE:: no poll because the button is removed from ui isntead

    def draw(self, context: types.Context):
        super().draw(context)
        ui.draw_gen_cfg(self.cfg, self.layout, context)

    def invoke(self, context, event):
        # avoid last stored operation overide
        self.cfg.meta_type = {"NONE"}
        # clean memory ptr leftovers
        self.last_ptrID_links = ""
        return super().invoke(context, event)

    #-------------------------------------------------------------------

    # OPT:: GEN: more error handling of user deletion of intermediate objects?
    # OPT:: automatically add particles/child parts -> most interesting method... -> util OP not part of flow
    # IDEA:: GEN: support for non meshes (e.g. curves)
    # IDEA:: GEN: disabled pencil too, should check points are close enugh/inside
    # IDEA:: GEN: atm only a single selected object + spawning direclty on the scene collection
    # IDEA:: GEN: recursiveness of shards? at least fracture existing fract obj instead of root -> bake button?
    # NOTE:: GEN: avoid convex hull from voro++ -> break in convex pieces, or test cells uniformly distrib? aprox or exact?
    # OPT:: RENDER: interior handle for materials

    # IDEA:: SIM: shrink here or as part of sim, e.g. smoothing? -> support physics interspace
    # IDEA:: SIM: add mass add rigid body proportional to volume? from voro++?
    # IDEA:: recalculate cont after reload from cfg exact params -> precision used stored? all props stored but some in side panel? e.g. visual and precision
    # OPT:: assets with msg

    def execute(self, context: types.Context):
        self.start_op()
        self.obj_root = None
        self.ctx = context

        # handle refresh
        cancel = self.checkRefresh_cancel()
        if cancel: return self.end_op_refresh(skipLog=True)

        # TODO:: run again more smartly, like detect no need for changes (e.g. name change or prefs debug show) -> compare both props, or use prop update func self ref? also for spawn indices
        # IDEA:: move all visual toggles to the side panel to avoid recalculations...
        # OPT:: separate simulation and scene generation: option to no store inter meshes
        # IDEA:: decimate before/after convex, test perf? sep operator?

        # Free existing link memory -> now purged on undo callback dynamically
        prefs = getPrefs()
        if self.last_ptrID_links and not prefs.prefs_links_undoPurge:
            LinkStorage.freeLinks(self.last_ptrID_links)


        # Retrieve root
        obj, cfg = MW_gen_cfg.getSelectedRoot()
        getStats().logDt("retrieved root object")
        try:
            # Selected object not fractured, fresh execution
            if not cfg:
                DEV.log_msg("cfg NOT found: new frac", {'SETUP'})
                obj_root, obj_original = mw_setup.copy_original(obj, self.cfg, context)
                return self.execute_fresh(obj_root, obj_original)

            # Fracture the same original object, copy props for a duplicated result to tweak parameters
            # NOTE:: no longer supporting edit fracture -> basically always replaces all objects in the scene which is slower than a fresh one
            else:
                # Copy the config to the op only once to allow the user to edit it afterwards
                if "NONE" in self.cfg.meta_type:
                    DEV.log_msg("cfg found once: copying props to OP", {'SETUP'})
                    copyProps(cfg, self.cfg)

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
        cfg: MW_gen_cfg = self.cfg
        cfg.rnd_seed = utils.rnd_seed(cfg.rnd_seed)
        prefs = getPrefs()


        DEV.log_msg("Initial object setup", {'SETUP'})
        # TODO:: convex hull triangulates the faces... e.g. UV sphere ends with more!
        if cfg.shape_useConvexHull:
            obj_toFrac = mw_setup.copy_convex(obj_root, obj_original, cfg, self.ctx)
        else: obj_toFrac = obj_original

        # TODO:: visual panel impro
        # TODO:: scale shards to see links better + add material random color with alpha + ui callback?
        # this callbacks to shard maps seem to need a global map access -> links.cont / links.objs? check non valid root

        DEV.log_msg("Start calc points", {'CALC'})
        # Get the points and transform to local space when needed
        mw_cont.detect_points_from_object(obj_original, cfg, self.ctx)
        points = mw_cont.get_points_from_object_fallback(obj_original, cfg, self.ctx)
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
        # XXX:: child verts / partilces should be checked inside?

        # Limit and rnd a bit the points
        mw_cont.points_transformCfg(points, cfg, bb_radius)

        # Add some reference of the points to the scene
        mw_setup.gen_pointsObject(obj_root, points, self.cfg, self.ctx)
        mw_setup.gen_boundsObject(obj_root, bb, self.cfg, self.ctx)


        DEV.log_msg("Start calc cont and links", {'CALC'})
        # IDEA:: mesh conecting input points + use single mesh instead of one per link?
        # XXX:: detect meshes with no volume? test basic shape for crashes...
        # XXX:: voro++ has some static constant values that have to be edited in compile time...
        #e.g. max_wall_size, tolerance for vertices,

        cont:Container = mw_cont.cont_fromPoints(points, bb, faces4D, precision=prefs.gen_calc_precisionWalls)
        if not cont:
            return self.end_op_error("found no cont... but could try recalculate!")

        # shards are always added to the scene
        obj_shards = mw_setup.gen_shardsEmpty(obj_root, cfg, self.ctx)

        #test some legacy or statistics cont stuff
        if DEV.LEGACY_CONT:
            mw_setup.gen_LEGACY_CONT(obj_shards, cont, cfg, self.ctx)
            return self.end_op("DEV.LEGACY_CONT stop...")
        mw_setup.gen_shardsObjects(obj_shards, cont, cfg, self.ctx, invertOrientation=prefs.gen_setup_invertShardNormals)

        #obj_links_legacy = mw_setup.genWIP_linksEmptiesPerCell(obj_root, cfg, self.ctx)
        #mw_setup.genWIP_linksCellObjects(obj_links_legacy, cont, cfg, self.ctx)

        # calculate links and store in the external storage
        links:LinkCollection = LinkCollection(cont, obj_shards)
        if not links.initialized:
            return self.end_op_error("found no links... but could try recalculate!")

        # use links storage
        self.last_ptrID_links = cfg.ptrID_links = obj_root.name
        LinkStorage.addLinks(links, cfg.ptrID_links, obj_root)


        return self.end_op()

    def end_op(self, msg="", skipLog=False, retPass=False):
        """ OVERRIDE:: end_op to perform stuff at the end """

        if self.obj_root:
            utils.select_unhide(self.obj_root, self.ctx)

            # copy any cfg that may have changed during execute
            self.cfg.name = self.obj_root.name
            copyProps(self.cfg, self.obj_root.mw_gen)
            # set the meta type to all objects at once
            MW_gen_cfg.setMetaType(self.obj_root, {"CHILD"}, skipParent=True)

        return super().end_op(msg, skipLog, retPass)


class MW_gen_recalc_OT(_StartRefresh_OT):
    bl_idname = "mw.gen_recalc"
    bl_label = "Recalculate links"
    bl_description = "For selected root. Useful after a module reload etc..."

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return MW_gen_cfg.hasSelectedRoot()

    def execute(self, context: types.Context):
        self.start_op()
        prefs = getPrefs()
        obj_root, cfg = MW_gen_cfg.getSelectedRoot()

        # delete current cont when found
        if cfg.ptrID_links:
            LinkStorage.freeLinks(cfg.ptrID_links)


        DEV.log_msg("Retrieving fracture data (objects and points)", {'SETUP'})
        if cfg.shape_useConvexHull:
            obj_toFrac = utils.get_child(obj_root, prefs.names.original_dissolve)
        else: obj_toFrac = utils.get_child(obj_root, prefs.names.original_copy)

        points = mw_cont.get_points_from_fracture(obj_root, cfg)
        if not points:
            return self.end_op_error("found no points...")

        obj_shards = utils.get_child(obj_root, prefs.names.shards)
        if not obj_shards:
            return self.end_op_error("found no shards...")

        # Get more data from the points
        bb, bb_center, bb_radius = utils.get_bb_data(obj_toFrac, cfg.margin_box_bounds)
        getStats().logDt(f"calc bb: [{bb_center[:]}] r {bb_radius:.3f} (margin {cfg.margin_box_bounds:.4f})")
        if cfg.shape_useWalls:
            faces4D = utils.get_faces_4D(obj_toFrac, cfg.margin_face_bounds)
        else: faces4D = []
        getStats().logDt(f"calc faces4D: {len(faces4D)} (n_disp {cfg.margin_face_bounds:.4f})")


        DEV.log_msg("Calc cont and links (shards not regenerated!)", {'CALC'})
        cont:Container = mw_cont.cont_fromPoints(points, bb, faces4D, precision=prefs.gen_calc_precisionWalls)
        if not cont:
            return self.end_op_error("found no cont... but could try recalculate!")

        # calculate links and store in the external storage
        links:LinkCollection = LinkCollection(cont, obj_shards)
        if not links.initialized:
            return self.end_op_error("found no links... but could try recalculate!")

        # use links storage
        self.last_ptrID_links = cfg.ptrID_links = obj_root.name
        LinkStorage.addLinks(links, cfg.ptrID_links, obj_root)


        return self.end_op()


    @staticmethod
    def getSelectedRoot_links():
        obj, cfg = MW_gen_cfg.getSelectedRoot()
        links = None

        if not cfg.ptrID_links:
            DEV.log_msg("Found no links in incomplete fracture", {'LINKS'})
        else:
            links = LinkStorage.getLinks(cfg.ptrID_links)
            if not links:
                DEV.log_msg("Found no links in storage", {'LINKS'})
        return obj, cfg, links

    @staticmethod
    def getSelectedRoot_links_autoRecalc() -> tuple[types.Object, "MW_gen_cfg", LinkCollection|None]:
        """ Retrieves links or recalculates them automatically """

        # attempt to retrieve links
        obj, cfg, links = MW_gen_recalc_OT.getSelectedRoot_links()

        # call recalc op once
        if not links and getPrefs().util_recalc_OT_auto:
            bpy.ops.mw.gen_recalc()
            obj, cfg, links = MW_gen_recalc_OT.getSelectedRoot_links()

        return obj, cfg, links

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
        return MW_gen_cfg.hasSelectedRoot()

    def execute(self, context: types.Context):
        self.start_op()

        obj, cfg, links = MW_gen_recalc_OT.getSelectedRoot_links_autoRecalc()
        if not links:
            return self.end_op_error("No links storage found...")

        ## WIP:: per cell no need but atm cont ref is inside LinkCollection structure
        #obj_links_legacy = mw_setup.genWIP_linksEmptiesPerCell(obj, cfg, context)
        #mw_setup.genWIP_linksCellObjects(obj_links_legacy, links.cont, cfg, context)

        #obj_links, obj_links_air = mw_setup.genWIP_linksEmpties(obj, cfg, context)
        ##mw_setup.genWIP_linksObjects(obj_links, obj_links_air, links, cfg, context)
        #mw_setup.gen_linksSingleObject(obj_links, obj_links_air, links, cfg, context)

        mw_setup.gen_linksObject(obj, links, cfg, context)
        mw_setup.gen_linksWallObject(obj, links, cfg, context)

        return self.end_op()

    def end_op(self, msg="", skipLog=False, retPass=False):
        """ OVERRIDE:: end_op to perform assign child to all """
        obj, cfg = MW_gen_cfg.getSelectedRoot()
        if obj: MW_gen_cfg.setMetaType(obj, {"CHILD"}, skipParent=True)
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
        return MW_gen_cfg.hasSelectedRoot()

    def invoke(self, context, event):
        obj, cfgGen, self.links = MW_gen_recalc_OT.getSelectedRoot_links_autoRecalc()
        if not self.links:
            return self.end_op_error("No links storage found...")

        # create simulation object
        self.sim = mw_sim.Simulation(self.links)

        return super().invoke(context, event)

    def execute(self, context: types.Context):
        self.start_op()
        cfg : MW_sim_cfg= self.cfg

        # achieve constructive results during adjust op menu
        self.sim.resetSim(cfg.addSeed)
        self.sim.set_deg(cfg.deg)

        for step in range(cfg.steps):
            if cfg.steps_uniformDeg: self.sim.stepAll()
            else: self.sim.step(cfg.subSteps)

        # IDEA:: store copy or original or button to recalc links from start? -> set all life to 1 but handle any dynamic list
        obj, cfgGen = MW_gen_cfg.getSelectedRoot()
        if obj:
            mw_setup.gen_linksObject(obj, self.links, cfgGen, context)
            mw_setup.gen_linksWallObject(obj, self.links, cfgGen, context, self.sim.step_trace.entryL_candidatesW if self.sim.trace else None)

        return self.end_op()

class MW_sim_reset_OT(_StartRefresh_OT):
    bl_idname = "mw.sim_reset"
    bl_label = "sim reset"
    bl_description = "WIP: sim reset"

    bl_options = {'INTERNAL', 'UNDO'}
    links: LinkCollection = None

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...

    @classmethod
    def poll(cls, context):
        return MW_gen_cfg.hasSelectedRoot()

    def invoke(self, context, event):
        obj, cfgGen, self.links = MW_gen_recalc_OT.getSelectedRoot_links()
        if not self.links:
            return self.end_op_error("No links storage found...")

        return super().invoke(context, event)

    def execute(self, context: types.Context):
        mw_sim.resetLife(self.links)

        obj, cfgGen = MW_gen_cfg.getSelectedRoot()
        if obj:
            mw_setup.gen_linksObject(obj, self.links, cfgGen, context)
            mw_setup.gen_linksWallObject(obj, self.links, cfgGen, context)
        return self.end_op()

#-------------------------------------------------------------------

class MW_util_delete_OT(_StartRefresh_OT):
    bl_idname = "mw.util_delete"
    bl_label = "Delete fracture object"
    bl_description = "Instead of Blender 'delete hierarchy' which seems to fail to delete all recusively..."

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return MW_gen_cfg.hasSelectedRoot()

    def execute(self, context: types.Context):
        self.start_op()
        obj, cfg = MW_gen_cfg.getSelectedRoot()
        prefs = getPrefs()

        # optionally unhide the original object
        if (prefs.util_delete_OT_unhideSelect):
            obj_original = utils.get_object_fromScene(context.scene, cfg.struct_nameOriginal)
            if not obj_original:
                self.logReport("obj_original not found -> wont unhide")
            else:
                utils.select_unhideRec(obj_original, context, selectChildren=False)

        # free memory from potential links map
        if cfg.ptrID_links and prefs.prefs_links_undoPurge:
            LinkStorage.freeLinks(cfg.ptrID_links)

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
        roots = MW_gen_cfg.getSceneRoots(context.scene)
        for obj_root in roots:
            MW_gen_cfg.setSelectedRoot([obj_root])
            bpy.ops.mw.util_delete()

        #MW_gen_cfg.resetSelectedRoot()
        MW_gen_cfg.setSelectedRoot(context.selected_objects)
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
        return context.selected_objects and MW_gen_cfg.isChild(context.selected_objects[-1])

    def execute(self, context: types.Context):
        self.start_op(skipStats=True)
        obj = context.selected_objects[-1]
        obj.parent = None
        MW_gen_cfg.setMetaType(obj, {"NONE"})
        MW_gen_cfg.setSelectedRoot(context.selected_objects)
        return self.end_op(skipLog=True)

#-------------------------------------------------------------------
# Blender events

classes = [
    MW_gen_OT,
    MW_gen_recalc_OT,
    MW_gen_links_OT,

    MW_sim_step_OT,
    MW_sim_reset_OT,

    MW_util_delete_OT,
    MW_util_delete_all_OT,
    MW_util_bake_OT,
] + util_classes_op

register, unregister = bpy.utils.register_classes_factory(classes)
