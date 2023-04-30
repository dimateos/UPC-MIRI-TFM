import bpy
import bpy.types as types
import bpy.props as props
from mathutils import Vector, Matrix

from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
)
from .operators_utils import _StartRefresh_OT, util_classes_op

from . import mw_setup
from . import mw_calc
from .mw_links import Links, Link
from tess import Container, Cell

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
        super().__init__()
        # config some base class log flags...
        self.invoke_log = True
        self.refresh_log = True
        self.end_log = True

    # NOTE:: no poll because the button is removed from ui isntead

    def draw(self, context: types.Context):
        super().draw(context)
        ui.draw_gen_cfg(self.cfg, self.layout, context)

    def invoke(self, context, event):
        # avoid last stored operation overide
        self.cfg.meta_type = {"NONE"}
        return super().invoke(context, event)

    #-------------------------------------------------------------------

    # OPT:: GEN: more error handling of user deletion of intermediate objects?
    # OPT:: automatically add particles -> most interesting method...
    # IDEA:: GEN: support for non meshes (e.g. curves)
    # IDEA:: GEN: disabled pencil too, should check points are close enugh/inside
    # IDEA:: GEN: atm only a single selected object + spawning direclty on the scene collection
    # IDEA:: GEN: recursiveness of shards?
    # NOTE:: GEN: avoid convex hull from voro++
    # OPT:: RENDER: interior handle for materials

    # IDEA:: SIM: shrink here or as part of sim, e.g. smoothing? -> support physics interspace
    # IDEA:: SIM: add mass add rigid body proportional to volume? from voro++?

    def execute(self, context: types.Context):
        self.start_op()
        cancel = self.checkRefresh_cancel()
        if cancel: return self.end_op_refresh(skipLog=True)

        # TODO:: store cont across simulations in the object or info from it
        # TODO:: run again more smartly, like detect no need for changes (e.g. name change or prefs debug show) -> compare both props, or use prop update func self ref? also for spawn indices
        # IDEA:: move all visual toggles to the side panel to avoid recalculations...
        # OPT:: separate simulation and scene generation: option to no store inter meshes
        # IDEA:: divide execute in function? sim/vis

        # OPT:: avoid recursion with pointer to parent instead of search by name
        # IDEA:: decimate before/after convex, test perf?


        # Retrieve root
        obj, cfg = utils.cfg_getRoot(context.active_object)
        getStats().logDt("retrieved root object")

        # Selected object not fractured, fresh execution
        if not cfg:
            DEV.log_msg("cfg NOT found: new frac", {'SETUP'})
            obj_root, obj_original = mw_setup.gen_copyOriginal(obj, self.cfg, context)
            return self.execute_fresh(context, obj_root, obj_original)

        # fracture the same original object for an alternative result
        else:
            DEV.log_msg("cfg found: duplicating frac", {'SETUP'})
            copyProps(cfg, self.cfg)
            obj_original = utils.get_child(obj, mw_setup.CONST_NAMES.original_copy)
            obj_copu = utils.copy_objectRec(obj_original, context)
            obj_original.name = cfg.struct_nameOriginal
            return self.execute_fresh(context, obj_root, obj_original)

        # NOTE:: no longer supporting edit fracture -> basically always replacing geometry hence being slower
        ## Config found in the object
        #else:
        #    # First execute just copy the cfg
        #    if "NONE" in self.cfg.meta_type:
        #        DEV.log_msg("cfg found: copying props to OP", {'SETUP'})
        #        copyProps(cfg, self.cfg)
        #        return self.end_op("PASS_THROUGH init copy of props")

        #    # Later runs edit optimized
        #    else:
        #        return self.execute_edit(context, obj)

    def execute_fresh(self, context: types.Context, obj_root:types.Object, obj_original:types.Object ):
        cfg: MW_gen_cfg = self.cfg
        prefs = getPrefs()
        cfg.rnd_seed = utils.rnd_seed(cfg.rnd_seed)



        DEV.log_msg("Initial object setup", {'SETUP'})
        # TODO:: convex hull triangulates the faces... e.g. UV sphere ends with more!
        if cfg.shape_useConvexHull:
            obj_toFrac = mw_setup.gen_copyConvex(obj_root, obj_original, cfg, context)
        else: obj_toFrac = obj_original

        # Rename and select the root
        mw_setup.gen_renaming(obj_root, cfg, context)
        utils.select_unhide(obj_root, context)

        # Add edited cfg to the object
        copyProps(self.cfg, obj_root.mw_gen)
        getStats().logDt("copied prop to root object")
        return self.end_op()



        DEV.log_msg("Start calc points", {'CALC'})
        # Get the points and transform to local space when needed
        mw_calc.detect_points_from_object(obj_original, cfg, context)
        points = mw_calc.get_points_from_object_fallback(obj_original, cfg, context)
        if not points:
            return self.end_op_error("found no points...")

        # Get more data from the points
        bb, bb_radius = utils.get_bb_radius(obj_toFrac, cfg.margin_box_bounds)
        if cfg.shape_useWalls:
            faces4D = utils.get_faces_4D(obj_toFrac, cfg.margin_face_bounds)
        else: faces4D = []
        # XXX:: 2D objects should use the boundary? limits walls per axis
        # XXX:: limit particles axis too?
        # XXX:: child verts / partilces should be checked inside?

        # Limit and rnd a bit the points
        mw_calc.points_transformCfg(points, cfg, bb_radius)

        # Add some reference of the points to the scene
        mw_setup.gen_pointsObject(obj, points, self.cfg, context)
        mw_setup.gen_boundsObject(obj, bb, self.cfg, context)
        getStats().logDt("spawned points objs")



        DEV.log_msg("Start calc cont and links", {'CALC'})

        # IDEA:: mesh conecting input points + use single mesh instead of one per link?
        # XXX:: detect meshes with no volume? test basic shape for crashes...
        # XXX:: voro++ has some static constant values that have to be edited in compile time...
        #e.g. max_wall_size, tolerance for vertices,

        cont = mw_calc.cont_fromPoints(points, bb, faces4D, precision=prefs.calc_precisionWalls)
        if not cont:
            return self.end_op_error("found no cont... but could try recalculate!")

        #cfg.nbl_cont = cont
        obj_shards = mw_setup.gen_shardsEmpty(obj, cfg, context)

        #test some legacy or statistics cont stuff
        if DEV.LEGACY_CONT:
            mw_setup._gen_LEGACY_CONT(obj_shards, cont, cfg, context)
            return self.end_op("DEV.LEGACY_CONT stop...")
        mw_setup.gen_shardsObjects(obj_shards, cont, cfg, context, invertOrientation=prefs.gen_invert_shardNormals)

        links = Links(cont, obj_shards)


        ## WIP:: links better generated from map isntead of cont? + done in a separate op
        #obj_links, obj_links_toWall, obj_links_perCell = mw_setup.gen_linksEmpties(obj, cfg, context)
        #if links.link_map:
        #    mw_setup.gen_linksObjects(obj_links, obj_links_toWall, links, cfg, context)
        #else:
        #    utils.delete_objectRec(obj_links)
        #    utils.delete_objectRec(obj_links_toWall)
        #mw_setup.gen_linksCellObjects(obj_links_perCell, cont, cfg, context)

        return self.end_op()

#-------------------------------------------------------------------

class MW_gen_links_OT(_StartRefresh_OT):
    bl_idname = "mw.gen_links"
    bl_label = "Generate links object"
    bl_description = "Generate a visual representation of the links of a fracture object"

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # poll execute on ui draw, so only check if has root, dont extract it
        obj = context.active_object
        return (obj and utils.cfg_hasRoot(obj))

    def execute(self, context: types.Context):
        self.start_op()
        obj, cfg = utils.cfg_getRoot(context.active_object)
        prefs = getPrefs()

        #todo

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
        # poll execute on ui draw, so only check if has root, dont extract it
        obj = context.active_object
        return (obj and utils.cfg_hasRoot(obj))

    def execute(self, context: types.Context):
        self.start_op()
        obj, cfg = utils.cfg_getRoot(context.active_object)
        prefs = getPrefs()

        # optional unhide flag
        if (prefs.util_delete_OT_unhideSelect):
            obj_original = utils.get_object_fromScene(context.scene, cfg.struct_nameOriginal)
            if not obj_original:
                self.logReport("obj_original not found -> wont unhide")
            else:
                utils.select_unhideRec(obj_original, context, selectChildren=False)

        utils.delete_objectRec(obj, logAmount=True)

        return self.end_op()


#-------------------------------------------------------------------
# Blender events

classes = [
    MW_gen_OT,
    MW_util_delete_OT,
] + util_classes_op

register, unregister = bpy.utils.register_classes_factory(classes)
