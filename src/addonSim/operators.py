import bpy
import bpy.types as types
import bpy.props as props

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

from .operators_functions import (
    getRoot_cfg,
    copyProperties,
)
from .panels_functions import (
    draw_gen_cfg,
)


# -------------------------------------------------------------------

class MW_gen_OT_(types.Operator):
    bl_idname = "mw.gen"
    bl_label = "Fracture generation"
    bl_options = {'PRESET', 'REGISTER', 'UNDO'}

    cfg: props.PointerProperty(type=MW_gen_cfg)

    def draw(self, context: types.Context):
        draw_gen_cfg(self.cfg, self.layout, context)

    def invoke(self, context, event):
        """ Runs only once on operator call """
        print("invoke")
        self.cfg.meta_refresh = True
        return self.execute(context)

    def execute(self, context: types.Context):
        """ Runs once and then after every property edit in the edit last action panel """
        print("execute")

        if not self.cfg.meta_refresh:
            print("no meta_refresh")
            return {'PASS_THROUGH'}

        # Need to copy the properties from the object if its already a fracture
        ob, cfg = getRoot_cfg(context.active_object)

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
                copyProperties(cfg, self.cfg)
                print("copy propos")
                return {'FINISHED'}
            else:
                cfg: MW_gen_cfg = self.cfg


        # Apply
        ob.name = cfg.struct_original + "_" + cfg.struct_sufix


        # Add edited cfg to the object
        copyProperties(self.cfg, ob.mw_gen)
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
