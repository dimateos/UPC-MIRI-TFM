import bpy
import bpy.types as types
import bpy.props as props

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

from . import mw_setup
#from . import mw_calc

from . import utils
from . import ui

from mathutils import Vector


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
        ui.DEV_log("invoke", {'OP_FLOW'})

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
        ui.DEV_log(f"execute auto{self.cfg.meta_auto_refresh} +r{self.cfg.meta_refresh}", {'OP_FLOW'})

        # TODO: atm only a single selected object + spawning direclty on the scene collection

        # Handle refreshing
        if not self.cfg.meta_refresh and not self.cfg.meta_auto_refresh:
            ui.DEV_log("PASS_THROUGH no refresh", {'OP_FLOW'})
            return {'PASS_THROUGH'}
        self.cfg.meta_refresh = False


        # Need to copy the properties from the object if its already a fracture
        obj, cfg = utils.cfg_getRoot(context.active_object)

        # Selected object not fractured
        if not cfg:
            cfg: MW_gen_cfg = self.cfg
            obj, obj_copy = mw_setup.gen_copyOriginal(obj, cfg, context)

        # Copy the config to the operator once
        else:
            if "NONE" in self.cfg.meta_type:
                utils.cfg_copyProps(cfg, self.cfg)
                ui.DEV_log("PASS_THROUGH? copy props", {'OP_FLOW'})
                return {'FINISHED'}
            else:
                cfg: MW_gen_cfg = self.cfg
                obj_copy = utils.get_child(obj, "Original")


        # Seed simulation random
        utils.rnd_seed(cfg.rnd_seed)

        # Finish scene setup
        mw_setup.gen_naming(obj, cfg, context)
        mw_setup.gen_shardsEmpty(obj, cfg, context)


        # Setup calc
        from .stats import Stats
        stats = Stats()
        #stats.testStats()
        stats.log_full("start setup points")

        # Get the points and bb
        points = mw_setup.get_points_from_object_fallback(obj_copy, cfg, context)
        if not points:
            return self.ret_failed()

        verts_world = utils.get_worldVerts(obj_copy)
        bb_world, bb_radius = utils.get_worldBB_radius(obj_copy)

        # Limit and rnd a bit the points and add them to the scene
        mw_setup.points_limitNum(points, cfg)
        mw_setup.points_noDoubles(points, cfg)
        mw_setup.points_addNoise(points, cfg, bb_radius)

        mw_setup.gen_pointsObject(obj, points, context)

        # Calc voronoi
        stats.log_full("start calc voro")


        # TODO: seeded random
        # TODO: recenter shards origin
        # TODO: add mass too
        # TODO: add interior handle?
        # TODO: recursiveness?
        # TODO: improved stats, later for comparison tho

        # Add edited cfg to the object
        utils.cfg_copyProps(self.cfg, obj.mw_gen)
        return {'FINISHED'}


# -------------------------------------------------------------------
# Blender events

classes = (
    MW_gen_OT_,
)

register, unregister = bpy.utils.register_classes_factory(classes)
