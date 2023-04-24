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

    def draw(self, context: types.Context):
        super().draw(context)
        ui.draw_gen_cfg(self.cfg, self.layout, context)

    def invoke(self, context, event):
        # avoid last stored operation overide
        self.cfg.meta_type = {"NONE"}
        return super().invoke(context, event)

    #-------------------------------------------------------------------

    # IDEA:: changelog / todo file to take notes there instead of all in the code?
    # NOTE:: no poll because the button is removed from ui isntead

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
        if cancel: return self.end_op_refresh()

        # TODO:: store cont across simulations in the object or info from it
        # TODO:: run again more smartly, like detect no need for changes (e.g. name change or prefs debug show) -> compare both props, or use prop update func self ref?
        # OPT:: separate simulation and scene generation: option to no store inter meshes
        # IDEA:: divide execute in function? sim/vis
        # XXX:: particles are in world position?
        # XXX:: refresh is slow, maybe related to other ui doing recursive access to root?? maybe panel with ok before?
        # OPT:: adding many objects to the scene takes most of the time -> single global mesh?
        # OPT:: avoid recursion with pointer to parent instead of search by name
        # IDEA:: decimate before/after convex, test perf?


        # Need to copy the properties from the object if its already a fracture
        obj, cfg = utils.cfg_getRoot(context.active_object)
        getStats().logDt("retrieved root object")

        # Selected object not fractured
        if not cfg:
            DEV.log_msg("cfg NOT found: new frac", {'SETUP'})
            cfg: MW_gen_cfg = self.cfg

            # TODO:: convex hull triangulates the faces... just decimate pls
            obj, obj_toFrac = mw_setup.gen_copyOriginal(obj, cfg, context)
            if cfg.shape_useConvexHull:
                obj_toFrac = mw_setup.gen_copyConvex(obj, obj_toFrac, cfg, context)

        # Copy the config to the operator once
        else:
            if "NONE" in self.cfg.meta_type:
                DEV.log_msg("cfg found: copying props to OP", {'SETUP'})
                copyProps(cfg, self.cfg)
                return self.end_op("PASS_THROUGH init copy of props")

            else:
                DEV.log_msg("cfg found: getting toFrac child", {'SETUP'})
                cfg: MW_gen_cfg = self.cfg

                if cfg.shape_useConvexHull:
                    name_toFrac = mw_setup.CONST_NAMES.original_c
                else:
                    name_toFrac = f"{mw_setup.CONST_NAMES.original}{cfg.struct_nameOriginal}"

                obj_toFrac = utils.get_child(obj, name_toFrac)
                getStats().logDt("retrieved toFrac object")


        DEV.log_msg("Start calc points", {'SETUP'})
        cfg.rnd_seed = utils.rnd_seed(cfg.rnd_seed) # seed common random gen

        # Get the points and transform to local space when needed
        mw_calc.detect_points_from_object(obj_toFrac, cfg, context)
        points = mw_calc.get_points_from_object_fallback(obj_toFrac, cfg, context)
        if not points:
            return self.end_op_error("found no points...")

        # Get more data
        bb, bb_radius = utils.get_bb_radius(obj_toFrac, cfg.margin_box_bounds)
        if cfg.shape_useWalls:
            faces4D = utils.get_faces_4D(obj_toFrac, cfg.margin_face_bounds)
        else: faces4D = []

        # Limit and rnd a bit the points and add them to the scene
        mw_calc.points_transformCfg(points, cfg, bb_radius)


        # Calc voronoi
        DEV.log_msg("Start calc cont", {'SETUP'})
        cont = mw_calc.cont_fromPoints(points, bb, faces4D)

        obj_shards = mw_setup.gen_shardsEmpty(obj, cfg, context)
        mw_setup.gen_shardsObjects(obj_shards, cont, cfg, context)

        # XXX:: there is a hard limit in the number of voro++ walls
        #/** The maximum size for the wall pointer array. */
        #const int max_wall_size=2048;

        DEV.log_msg("Start calc links", {'SETUP'})
        #links = Links(cont, obj_shards)
        # NOTE:: links better generated from map isntead of cont
        obj_links = mw_setup.gen_linksEmpty(obj, cfg, context)
        mw_setup.gen_linksObjects(obj_links, cont, cfg, context)


        DEV.log_msg("Do some more scene setup", {'SETUP'})
        # Finish scene setup and select after optional renaming
        mw_setup.gen_renaming(obj, cfg, context)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        #context.active_object = obj
        getStats().logDt("renamed and selected")

        mw_setup.gen_pointsObject(obj, points, cfg, context)
        mw_setup.gen_boundsObject(obj, bb, cfg, context)

        # Add edited cfg to the object
        copyProps(self.cfg, obj.mw_gen)
        return self.end_op()


#-------------------------------------------------------------------

# OPT:: maybe delete hierarchy fail due to some issue caused by me
class MW_util_delete_OT(_StartRefresh_OT):
    bl_idname = "mw.util_delete"
    bl_label = "Delete fracture object"
    bl_description = "Instead of Blender 'delete hierarchy' which seems to fail to delete all recusively..."

    # UNDO as part of bl_options will cancel any edit last operation pop up
    bl_options = {'INTERNAL', 'UNDO'}
    _obj: types.Object = None
    _cfg: MW_gen_cfg = None

    def __init__(self) -> None:
        super().__init__()
        # config some base class log flags...
        self.start_resetStats = False

    @classmethod
    def poll(cls, context):
        obj, cfg = utils.cfg_getRoot(context.active_object)
        MW_util_delete_OT._obj, MW_util_delete_OT._cfg = obj, cfg
        return (obj and cfg)

    def execute(self, context: types.Context):
        self.start_op()
        obj, cfg = MW_util_delete_OT._obj, MW_util_delete_OT._cfg
        prefs = getPrefs()

        # optionally hide
        if (prefs.OT_util_delete_unhide):
            obj_original = utils.get_object_fromScene(context.scene, cfg.struct_nameOriginal)
            obj_original.hide_set(False)

        utils.delete_objectRec(obj, logAmount=True)
        return self.end_op()


#-------------------------------------------------------------------
# Blender events

classes = [
    MW_gen_OT,
    MW_util_delete_OT,
] + util_classes_op

register, unregister = bpy.utils.register_classes_factory(classes)
