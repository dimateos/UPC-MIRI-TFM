import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

from .panels_functions import (
    draw_gen_cfg,
)


# -------------------------------------------------------------------

class MW_gen_OT_(types.Operator):
    bl_idname = "mw.gen"
    bl_label = "Fracture generation"
    bl_options = {'PRESET', 'REGISTER', 'UNDO'}

    def draw(self, context):
        ob = context.active_object
        cfg : MW_gen_cfg = ob.mw_gen
        draw_gen_cfg(cfg, self.layout, context)

    def execute(self, context):
        ob = context.active_object
        cfg : MW_gen_cfg = ob.mw_gen

        cfg.generated = True
        return {'FINISHED'}


# -------------------------------------------------------------------
# Blender events

classes = (
    MW_gen_OT_,
)

register, unregister = bpy.utils.register_classes_factory(classes)
