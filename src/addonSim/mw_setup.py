import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
)

from . import utils
from .ui import DEV_log

from mathutils import Vector

NAME_ORIGINAL = "Original"
NAME_ORIGINAL_BB = "Original_bb"
NAME_SHARDS = "Shards"
NAME_SHARDS_POINTS = "Shards_source"


# -------------------------------------------------------------------

def gen_copyOriginal(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    cfg.meta_type = {"ROOT"}
    cfg.struct_nameOriginal = obj.name

    # Empty object to hold all of them
    obj_empty = bpy.data.objects.new(cfg.struct_nameOriginal, None)
    context.scene.collection.objects.link(obj_empty)

    # Duplicate the original object
    obj_copy: types.Object = obj.copy()
    obj_copy.data = obj.data.copy()
    obj_copy.name = NAME_ORIGINAL
    obj_copy.parent = obj_empty
    obj_copy.mw_gen.meta_type = {"CHILD"}
    context.scene.collection.objects.link(obj_copy)

    # Hide and select after link
    obj.hide_set(not cfg.struct_showOrignal)
    obj_copy.hide_set(True)
    obj_empty.select_set(True)
    context.view_layer.objects.active = obj_empty
    #bpy.ops.outliner.show_active(execution_context='INVOKE_DEFAULT') cannot expand hierarchy...

    return obj_empty, obj_copy

def gen_naming(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    if obj.name.startswith(cfg.struct_nameOriginal):
        obj.name = cfg.struct_nameOriginal + "_" + cfg.struct_nameSufix
    else:
        obj.name += "_" + cfg.struct_nameSufix

def gen_shardsEmpty(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_emptyFrac = utils.gen_childClean(obj, NAME_SHARDS, None, not cfg.struct_showShards, context)
    return obj_emptyFrac

def gen_pointsObject(obj: types.Object, points: list[Vector], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(NAME_SHARDS_POINTS)
    mesh.from_pydata(points, [], [])
    #mesh.update()

    obj_points = utils.gen_childClean(obj, NAME_SHARDS_POINTS, mesh, not cfg.struct_showPoints, context)
    return obj_points

def gen_boundsObject(obj: types.Object, bb: list[Vector, 2], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(NAME_ORIGINAL_BB)
    mesh.from_pydata(bb, [], [])

    obj_bb = utils.gen_childClean(obj, NAME_ORIGINAL_BB, mesh, not cfg.struct_showBB, context)
    obj_bb.show_bounds = True
    return obj_bb
