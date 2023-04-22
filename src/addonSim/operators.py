import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

from . import mw_setup
from . import mw_calc
from .mw_links import Links, Link

from . import ui
from . import utils
from .utils_cfg import copyProps
from .utils_dev import DEV
from .stats import Stats

from mathutils import Vector
from tess import Container, Cell


# -------------------------------------------------------------------

class MW_gen_OT_(types.Operator):
    bl_idname = "mw.gen"
    bl_label = "Fracture generation"
    bl_options = {'PRESET', 'REGISTER', 'UNDO'}
    bl_description = "Fracture generation using voro++"

    cfg: props.PointerProperty(type=MW_gen_cfg)

    def draw(self, context: types.Context):
        ui.draw_gen_cfg(self.cfg, self.layout, context)

    def invoke(self, context, event):
        """ Runs only once on operator call """
        DEV.log_msg("invoke", {'OP_FLOW'})

        # refresh at least once
        self.cfg.meta_refresh = True
        # avoid last stored operation overide
        self.cfg.meta_type = {"NONE"}

        return self.execute(context)


    def __init__(self) -> None:
        super().__init__()
        self.stats = Stats()

    def start_op(self, msg = ""):
        self.stats.reset()
        #self.stats.testStats()
        DEV.log_msg(msg, {'SETUP'})
        DEV.log_msg(f"execute auto_refresh:{self.cfg.meta_auto_refresh} refresh:{self.cfg.meta_refresh}", {'OP_FLOW'})

    def end_op(self, msg = "", skip=False):
        DEV.log_msg(f"END: {msg}", {'OP_FLOW'})
        self.stats.log("finished execution")
        return {"FINISHED"} if not skip else {'PASS_THROUGH'}

    def end_op_error(self, msg = "", skip=False):
        self.report({'ERROR'}, f"Operation failed: {msg}")
        self.end_op(msg, skip)

    # IDEA:: changelog / todo file to take notes there instead of all in the code?

    # OPT::  GEN: more error handling of user deletion of intermediate objects?
    # IDEA:: GEN: support for non meshes (e.g. curves)
    # IDEA:: GEN: disabled pencil too, should check points are close enugh/inside
    # IDEA:: GEN: atm only a single selected object + spawning direclty on the scene collection
    # IDEA:: GEN: recursiveness of shards?
    # NOTE:: GEN: avoid convex hull from voro++
    # OPT:: RENDER: interior handle for materials

    # IDEA:: SIM: shrink here or as part of sim, e.g. smoothing? -> support physics interspace
    # IDEA:: SIM: add mass add rigid body proportional to volume? from voro++?

    def execute(self, context: types.Context):
        """ Runs once and then after every property edit in the edit last action panel """
        self.start_op("START: fracture OP")

        # TODO:: store cont across simulations in the object or info from it
        # TODO:: run again more smartly, like detect no need for changes or only name changed -> compare both props
        # XXX:: particles are in world position?
        # XXX:: refresh is slow, maybe related to other ui doing recursive access to root?? maybe panel with ok before?
        # OPT:: separate simulation and scene generation: option to no store inter meshes
        # OPT:: avoid recursion with pointer to parent instead of search by name
        # IDEA:: decimate before/after convex, test perf?

        # Handle refreshing
        if not self.cfg.meta_refresh and not self.cfg.meta_auto_refresh:
            return self.end_op("PASS_THROUGH no refresh", skip=True)
        self.cfg.meta_refresh = False

        # TODO:: divide execute in functions?

        # Need to copy the properties from the object if its already a fracture
        obj, cfg = utils.cfg_getRoot(context.active_object)
        self.stats.log("retrieved root object")

        # Selected object not fractured
        if not cfg:
            DEV.log_msg("cfg NOT found: new frac", {'SETUP'})
            cfg: MW_gen_cfg = self.cfg

            obj, obj_toFrac = mw_setup.gen_copyOriginal(obj, cfg, context)
            self.stats.log("generated copy object")
            if cfg.shape_useConvexHull:
                obj_toFrac = mw_setup.gen_copyConvex(obj, obj_toFrac, cfg, context)
                self.stats.log("generated convex object")

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
                    name_toFrac = mw_setup.CONST_NAMES.original_convex
                else:
                    name_toFrac = f"{mw_setup.CONST_NAMES.original}{cfg.struct_nameOriginal}"

                obj_toFrac = utils.get_child(obj, name_toFrac)
                self.stats.log("retrieved toFrac object")

        DEV.log_msg(f"cfg {cfg.meta_show_debug}")
        try: DEV.log_msg(f" obj { obj.mw_gen.meta_show_debug }")
        except: pass



        DEV.log_msg("Start calc points", {'SETUP'})
        cfg.rnd_seed = utils.rnd_seed(cfg.rnd_seed) # seed common random gen

        # Get the points and transform to local space when needed
        mw_calc.detect_points_from_object(obj_toFrac, cfg, context)
        points = mw_calc.get_points_from_object_fallback(obj_toFrac, cfg, context)
        self.stats.log("retrieved points")
        if not points:
            return self.end_op_error("found no points...")

        # Get more data
        bb, bb_radius = utils.get_bb_radius(obj_toFrac, cfg.margin_box_bounds)
        if cfg.shape_useWalls:
            faces4D = utils.get_faces_4D(obj_toFrac, cfg.margin_face_bounds)
        else: faces4D = []
        self.stats.log("retrieved shape data")

        # Limit and rnd a bit the points and add them to the scene
        mw_calc.points_limitNum(points, cfg)
        mw_calc.points_noDoubles(points, cfg)
        mw_calc.points_addNoise(points, cfg, bb_radius)
        self.stats.log("transform/limit points")


        # Calc voronoi
        DEV.log_msg("Start calc cont", {'SETUP'})
        cont = mw_calc.cont_fromPoints(points, bb, faces4D)
        self.stats.log("calculated cont")

        obj_shards = mw_setup.gen_shardsEmpty(obj, cfg, context)
        mw_setup.gen_shardsObjects(obj_shards, cont, cfg, context)
        self.stats.log("generated shards objects")


        DEV.log_msg("Start calc links", {'SETUP'})
        links = Links(cont, obj_shards)
        self.stats.log("calculated links")
        # NOTE:: links better generated from map isntead of cont
        obj_links = mw_setup.gen_linksEmpty(obj, cfg, context)
        mw_setup.gen_linksObjects(obj_links, cont, cfg, context)
        self.stats.log("generated links objects")



        DEV.log_msg("Do some more scene setup", {'SETUP'})
        # Finish scene setup and select after optional renaming
        mw_setup.gen_renaming(obj, cfg, context)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        #context.active_object = obj
        self.stats.log("renamed and selected")

        mw_setup.gen_pointsObject(obj, points, cfg, context)
        mw_setup.gen_boundsObject(obj, bb, cfg, context)
        self.stats.log("generated points and bounds object")

        # Add edited cfg to the object
        copyProps(self.cfg, obj.mw_gen)
        return self.end_op("completed...")


# -------------------------------------------------------------------

class MW_util_delete_OT_(types.Operator):
    bl_idname = "mw.util_delete"
    bl_label = "Delete fracture object"
    bl_options = {'INTERNAL', 'UNDO'}
    bl_description = "Instead of Blender 'delete hierarchy' which seems to fail to delete all recusively..."
    _obj, _cfg = None, None

    @classmethod
    def poll(cls, context):
        obj, cfg = utils.cfg_getRoot(context.active_object)
        MW_util_delete_OT_._obj, MW_util_delete_OT_._cfg = obj, cfg
        return (obj and cfg)

    def execute(self, context: types.Context):
        obj, cfg = MW_util_delete_OT_._obj, MW_util_delete_OT_._cfg
        prefs = getPrefs(context)

        # optionally hide
        if (prefs.OT_util_delete_unhide):
            obj_original = utils.get_object_fromScene(context.scene, cfg.struct_nameOriginal)
            obj_original.hide_set(False)

        # log the timing
        stats = Stats()
        stats.logMsg("START: REC delete frac...")

        utils.delete_objectRec(obj, logAmount=True)
        stats.log("END: REC delete frac...")

        # UNDO as part of bl_options will cancel any edit last operation pop up
        return {'FINISHED'}

# -------------------------------------------------------------------

class MW_info_data_OT_(types.Operator):
    bl_idname = "mw.info_data"
    bl_label = "Inspect mesh data"
    bl_options = {'INTERNAL'}
    bl_description = "DEBUG print in the console some mesh data etc"

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return (obj and obj.type == 'MESH')

    def execute(self, context: types.Context):
        obj = bpy.context.active_object
        from . import info_mesh
        info_mesh.desc_mesh_data(obj.data)
        return {'FINISHED'}

class MW_info_API_OT_(types.Operator):
    bl_idname = "mw.info_api"
    bl_label = "Inspect mesh API"
    bl_options = {'INTERNAL'}
    bl_description = "DEBUG print in the console some mesh API etc"

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return (obj and obj.type == 'MESH')

    def execute(self, context: types.Context):
        obj = bpy.context.active_object
        from . import info_mesh
        info_mesh.desc_mesh_inspect(obj.data)
        return {'FINISHED'}

class MW_info_matrices_OT_(types.Operator):
    bl_idname = "mw.info_matrices"
    bl_label = "Inspect obj matrices"
    bl_options = {'INTERNAL'}
    bl_description = "DEBUG print in the console the matrices etc"

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return obj

    def execute(self, context: types.Context):
        obj = bpy.context.active_object
        utils.trans_printMatrices(obj)
        return {'FINISHED'}

# -------------------------------------------------------------------
# Blender events

classes = (
    MW_gen_OT_,
    MW_util_delete_OT_,
    MW_info_data_OT_,
    MW_info_API_OT_,
    MW_info_matrices_OT_
)

register, unregister = bpy.utils.register_classes_factory(classes)
