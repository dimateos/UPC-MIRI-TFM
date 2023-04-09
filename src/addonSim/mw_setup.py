import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
)

from . import utils


# -------------------------------------------------------------------

def gen_copyOriginal(cfg : MW_gen_cfg, ob: types.Object, context: types.Context):
    cfg.meta_type = {"ROOT"}
    cfg.struct_original = ob.name

    # Empty object to hold all of them
    ob_empty = bpy.data.objects.new(cfg.struct_original, None)
    context.scene.collection.objects.link(ob_empty)

    # Duplicate the original object
    ob_copy: types.Object = ob.copy()
    ob_copy.data = ob.data.copy()
    ob_copy.name = "Original"
    ob_copy.parent = ob_empty
    ob_copy.mw_gen.meta_type = {"CHILD"}
    context.scene.collection.objects.link(ob_copy)

    # Hide and select
    ob.hide_set(True)
    ob_copy.hide_set(True)
    ob_empty.select_set(True)
    context.view_layer.objects.active = ob_empty
    #bpy.ops.outliner.show_active(execution_context='INVOKE_DEFAULT') cannot expand hierarchy...

    return ob_empty

def gen_naming(cfg : MW_gen_cfg, ob: types.Object, context: types.Context):
    if ob.name.startswith(cfg.struct_original):
        ob.name = cfg.struct_original + "_" + cfg.struct_sufix
    else:
        ob.name += "_" + cfg.struct_sufix

def gen_shardsEmpty(cfg : MW_gen_cfg, ob: types.Object, context: types.Context):
    # Delete if exists along its shard children
    ob_emptyFrac = utils.get_child(ob, "Shards")
    if ob_emptyFrac:
        utils.delete_object(ob_emptyFrac)

    # Generate empty for the fractures
    ob_emptyFrac = bpy.data.objects.new("Shards", None)
    ob_emptyFrac.mw_gen.meta_type = {"CHILD"}
    ob_emptyFrac.parent = ob
    context.scene.collection.objects.link(ob_emptyFrac)