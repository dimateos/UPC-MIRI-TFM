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

from . import ui
from . import utils
from .utils_cfg import copyProps
from .utils_dev import DEV

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

    def ret_failed(self):
        self.report({'ERROR'}, "Operation failed!")
        return {"FINISHED"}


    def execute(self, context: types.Context):
        """ Runs once and then after every property edit in the edit last action panel """
        DEV.log_msg(f"execute auto{self.cfg.meta_auto_refresh} +r{self.cfg.meta_refresh}", {'OP_FLOW'})

        # TODO: atm only a single selected object + spawning direclty on the scene collection
        # TODO: also limited to mesh, no properly tested with curves etc
        # TODO: disabled pencil too, should check points are close enugh/inside

        # Handle refreshing
        if not self.cfg.meta_refresh and not self.cfg.meta_auto_refresh:
            DEV.log_msg("PASS_THROUGH no refresh", {'OP_FLOW'})
            return {'PASS_THROUGH'}
        self.cfg.meta_refresh = False


        # Need to copy the properties from the object if its already a fracture
        obj, cfg = utils.cfg_getRoot(context.active_object)

        # Selected object not fractured
        if not cfg:
            cfg: MW_gen_cfg = self.cfg
            obj, obj_toFrac = mw_setup.gen_copyOriginal(obj, cfg, context)
            if cfg.shape_useConvexHull:
                obj_toFrac = mw_setup.gen_copyConvex(obj, obj_toFrac, cfg, context)

        # Copy the config to the operator once
        else:
            if "NONE" in self.cfg.meta_type:
                copyProps(cfg, self.cfg)
                DEV.log_msg("PASS_THROUGH? copy props", {'OP_FLOW'})
                return {'FINISHED'}
            else:
                cfg: MW_gen_cfg = self.cfg

                # TODO: better name search / pointer store etc, also carful with . added by blender
                if cfg.shape_useConvexHull:
                    name_toFrac = mw_setup.CONST_NAMES.original_convex
                else:
                    name_toFrac = f"{mw_setup.CONST_NAMES.original}{cfg.struct_nameOriginal}"

                obj_toFrac = utils.get_child(obj, name_toFrac)


        # Seed simulation randomness + store it
        cfg.rnd_seed = utils.rnd_seed(cfg.rnd_seed)


        # Finish scene setup
        mw_setup.gen_renaming(obj, cfg, context)
        obj.select_set(True)
        obj_toFrac.select_set(True)
        #context.active_object = obj
        # TODO: renaming in a edit fracture unselects from active_object, also changing any prop?
        # TODO: some more error handling on unexpected deleted objects?


        # Setup calc
        from .stats import Stats
        stats = Stats()
        #stats.testStats()
        stats.log("start setup points")

        # Get the points and transform to local space when needed
        # TODO: particles and pencil are in world position...
        # TODO: seems like not letting pick others?
        mw_calc.detect_points_from_object(obj_toFrac, cfg, context)
        points = mw_calc.get_points_from_object_fallback(obj_toFrac, cfg, context)
        if not points:
            return self.ret_failed()

        # Get more data
        bb, bb_radius = utils.get_bb_radius(obj_toFrac, cfg.margin_box_bounds)
        if cfg.shape_useWalls:
            faces4D = utils.get_faces_4D(obj_toFrac, cfg.margin_face_bounds)
        else: faces4D = []

        # Limit and rnd a bit the points and add them to the scene
        mw_calc.points_limitNum(points, cfg)
        mw_calc.points_noDoubles(points, cfg)
        mw_calc.points_addNoise(points, cfg, bb_radius)

        mw_setup.gen_pointsObject(obj, points, cfg, context)
        mw_setup.gen_boundsObject(obj, bb, cfg, context)


        # Calc voronoi
        stats.log("start calc voro cells")
        # TODO: get n faces too etc cont info -> store the info in the object
        # TODO: go back to no attempt on convex fix, plus error when no particles inside
        cont = mw_calc.cont_fromPoints(points, bb, faces4D)

        stats.log("start build bl cells")
        obj_shards = mw_setup.gen_shardsEmpty(obj, cfg, context)
        mw_setup.gen_shardsObjects(obj_shards, cont, cfg, context)

        obj_links = mw_setup.gen_linksEmpty(obj, cfg, context)
        mw_setup.gen_linksObjects(obj_links, cont, cfg, context)

        # TODO: store the cont inside the property pointer
        # TODO: get volume from cells/cont?
        # TODO: BL:: detect property changes and avoid regen -> maybe some vis can go to panel etc
        ## TEST: check out some cell properties and API
        #if 1:
        #    from . import info_inspect as ins
        #    ins.print_data(cont[0], False)

        # TODO: GEN:: decimation applied -> create another object
        # TODO: GEN:: convex hull applied -> create another object
        # TODO: PHYS:: add mass + cell inter-space (or shrink) + add rigid body?
        # TODO: RENDER:: add interior handle for materials
        # TODO: GEN:: recursiveness?
        # TODO: GEN:: avoid convex hull?
        stats.log("completed execution...")

        # Add edited cfg to the object
        copyProps(self.cfg, obj.mw_gen)
        return {'FINISHED'}


# -------------------------------------------------------------------

class MW_util_delete_OT_(types.Operator):
    bl_idname = "mw.util_delete"
    bl_label = "Delete fracture object"
    bl_options = {'INTERNAL'}
    bl_description = "Blender delete hierarchy seems to fail to delete all"
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

        utils.delete_objectRec(obj)
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
