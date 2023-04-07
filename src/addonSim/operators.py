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

    def execute(self, context: types.Context):
        ob, cfg = getRoot_cfg(context.active_object)

        # Selected object not fractured
        if not cfg:
            ob_original = ob

            # Empty object to hold all of them
            ob_empty = bpy.data.objects.new("EmptyObject", None)
            ob_empty.name = ob_original.name + self.cfg.copy_sufix
            context.scene.collection.objects.link(ob_empty)

            # Duplicate the original object
            ob_copy: types.Object = ob_original.copy()
            ob_copy.data = ob_original.data.copy()
            ob_copy.name = "Original"
            ob_copy.parent = ob_empty
            ob_copy.mw_gen.type = {"CHILD"}
            context.scene.collection.objects.link(ob_copy)

            # Hide and select
            ob_original.hide_set(True)
            ob_copy.hide_set(True)
            ob_empty.select_set(True)
            context.view_layer.objects.active = ob_empty

            self.cfg.type = {"ROOT"}
            ob = ob_empty
            cfg = ob_empty.mw_gen
            #return {'FINISHED'}

        ## Copy the config to the operator once
        #elif "NONE_OPERATOR" in self.cfg:
        #    copyProperties(cfg, self.cfg)
        #    return {'FINISHED'}


        #ob.name = ob.name.replace(cfg.copy_sufix) + cfg.copy_sufix

        # Add edited cfg to the object
        copyProperties(self.cfg, cfg)
        return {'FINISHED'}


# -------------------------------------------------------------------
# Blender events

classes = (
    MW_gen_OT_,
)

register, unregister = bpy.utils.register_classes_factory(classes)
