import bpy
import bpy.types as types
import bpy.props as props

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

from . import utils
from . import ui


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

    def execute(self, context: types.Context):
        """ Runs once and then after every property edit in the edit last action panel """
        ui.DEV_log(f"execute auto{self.cfg.meta_auto_refresh} +r{self.cfg.meta_refresh}", {'OP_FLOW'})

        # Handle refreshing
        if not self.cfg.meta_refresh and not self.cfg.meta_auto_refresh:
            ui.DEV_log("PASS_THROUGH no refresh", {'OP_FLOW'})
            return {'PASS_THROUGH'}
        self.cfg.meta_refresh = False


        # Need to copy the properties from the object if its already a fracture
        ob, cfg = utils.cfg_getRoot(context.active_object)

        # Selected object not fractured
        if not cfg:
            cfg: MW_gen_cfg = self.cfg
            cfg.meta_type = {"ROOT"}

            ob_original = ob
            cfg.struct_original = ob_original.name

            # Empty object to hold all of them
            ob_empty = bpy.data.objects.new("EmptyObject", None)
            context.scene.collection.objects.link(ob_empty)

            # Empty for the fractures
            ob_emptyFrac = bpy.data.objects.new("Fractures", None)
            ob_emptyFrac.mw_gen.meta_type = {"CHILD"}
            context.scene.collection.objects.link(ob_emptyFrac)
            ob_emptyFrac.parent = ob_empty

            # Duplicate the original object
            ob_copy: types.Object = ob_original.copy()
            ob_copy.data = ob_original.data.copy()
            ob_copy.name = "Original"
            ob_copy.parent = ob_empty
            ob_copy.mw_gen.meta_type = {"CHILD"}
            context.scene.collection.objects.link(ob_copy)

            # Hide and select
            ob_original.hide_set(True)
            ob_copy.hide_set(True)
            ob_empty.select_set(True)
            context.view_layer.objects.active = ob_empty
            ob = ob_empty

        # Copy the config to the operator once
        else:
            if "NONE" in self.cfg.meta_type:
                utils.cfg_copyProps(cfg, self.cfg)
                ui.DEV_log("PASS_THROUGH? copy props", {'OP_FLOW'})
                return {'FINISHED'}
            else:
                cfg: MW_gen_cfg = self.cfg


        # Apply
        ob.name = cfg.struct_original + "_" + cfg.struct_sufix


        # Add edited cfg to the object
        utils.cfg_copyProps(self.cfg, ob.mw_gen)
        # Keep auto meta_refresh
        if self.cfg.meta_auto_refresh is False:
            self.cfg.meta_refresh = False
        return {'FINISHED'}


# -------------------------------------------------------------------
# Blender events

classes = (
    MW_gen_OT_,
)

register, unregister = bpy.utils.register_classes_factory(classes)
