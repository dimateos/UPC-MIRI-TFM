import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
)

from . import utils
from .ui import DEV_log

from mathutils import Vector

# Using tess voro++ adaptor
from tess import Container, Cell

NAME_ORIGINAL = "Original"
NAME_ORIGINAL_BB = NAME_ORIGINAL+"_bb"
NAME_SHARDS = "Shards"
NAME_SHARDS_POINTS = "Shards_source"
NAME_LINKS = NAME_SHARDS+"_links"


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
    obj_copy.show_bounds = True
    context.view_layer.objects.active = obj_empty
    #bpy.ops.outliner.show_active(execution_context='INVOKE_DEFAULT') cannot expand hierarchy...

    return obj_empty, obj_copy

def gen_naming(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    if obj.name.startswith(cfg.struct_nameOriginal):
        obj.name = cfg.struct_nameOriginal + "_" + cfg.struct_nameSufix
    else:
        obj.name += "_" + cfg.struct_nameSufix

def gen_shardsEmpty(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_shardsEmpty = utils.gen_childClean(obj, NAME_SHARDS, None, not cfg.struct_showShards, context)
    return obj_shardsEmpty

def gen_linksEmpty(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_linksEmpty = utils.gen_childClean(obj, NAME_LINKS, None, not cfg.struct_showLinks, context)
    return obj_linksEmpty

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

# -------------------------------------------------------------------

def gen_shardsObjects(obj: types.Object, cont: Container, cfg: MW_gen_cfg, context: types.Context):
    for cell in cont:
        # TODO maybe make id match the point id instead of the container id
        name= f"{NAME_SHARDS}_{cell.id}"

        # create a static mesh for each one
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices=cell.vertices_local_centroid(), edges=[], faces=cell.face_vertices())

        obj_shard = utils.gen_childClean(obj, name, mesh, not cfg.struct_showShards, context)
        obj_shard.location = cell.centroid()
        #print("cell.pos", cell.pos)

#def gen_linksObjects(obj: types.Object, cont: Container, cfg: MW_gen_cfg, context: types.Context):
#    return
#    for cell in cont:
#        # TODO maybe make id match the point id instead of the container id
#        name= f"{NAME_SHARDS}_{cell.id}"

#        # create a static mesh for each one
#        # TODO global-local space vertices?
#        mesh = bpy.data.meshes.new(name)
#        mesh.from_pydata(vertices=cell.vertices_local_centroid(), edges=[], faces=cell.face_vertices())

#        obj_shard = utils.gen_childClean(obj, name, mesh, not cfg.struct_showShards, context)
#        obj_shard.location = cell.centroid()
#        #print("cell.pos", cell.pos)