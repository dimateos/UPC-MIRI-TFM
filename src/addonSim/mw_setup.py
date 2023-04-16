import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
)

from . import utils
from .ui import DEV_log

from mathutils import Vector, Matrix

# Using tess voro++ adaptor
from tess import Container, Cell

NAME_ORIGINAL = "Original"
NAME_ORIGINAL_BB = NAME_ORIGINAL+"_bb"
NAME_SHARDS = "Shards"
NAME_SHARDS_POINTS = "Shards_source"
NAME_LINKS = NAME_SHARDS+"_links"
NAME_LINKS_GROUP = "Links"


# -------------------------------------------------------------------

def gen_copyOriginal(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    cfg.meta_type = {"ROOT"}
    cfg.struct_nameOriginal = obj.name

    # Empty object to hold all of them set at the original obj trans
    obj_empty = bpy.data.objects.new(cfg.struct_nameOriginal, None)
    context.scene.collection.objects.link(obj_empty)

    # Duplicate the original object
    obj_copy: types.Object = obj.copy()
    obj_copy.name = NAME_ORIGINAL
    obj_copy.mw_gen.meta_type = {"CHILD"}
    context.scene.collection.objects.link(obj_copy)

    # Set the transform to the empty and parent keeping the transform of the copy
    obj_empty.matrix_world = obj.matrix_world.copy()
    utils.set_child(obj_copy, obj_empty)

    # Hide and select after link
    obj.hide_set(not cfg.struct_showOrignal)
    obj_copy.hide_set(False)
    obj_copy.show_bounds = True
    context.view_layer.objects.active = obj_empty

    #bpy.ops.outliner.show_active(execution_context='INVOKE_DEFAULT') cannot expand hierarchy from this context
    #tried context_override but no luck either...

    return obj_empty, obj_copy

def gen_naming(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    if obj.name.startswith(cfg.struct_nameOriginal):
        obj.name = cfg.struct_nameOriginal + "_" + cfg.struct_nameSufix
    else:
        obj.name += "_" + cfg.struct_nameSufix

def gen_shardsEmpty(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_shardsEmpty = utils.gen_childClean(obj, NAME_SHARDS, context, None, hide=not cfg.struct_showShards)
    return obj_shardsEmpty

def gen_linksEmpty(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_linksEmpty = utils.gen_childClean(obj, NAME_LINKS, context, None, hide=not cfg.struct_showLinks)
    return obj_linksEmpty

def gen_pointsObject(obj: types.Object, points: list[Vector], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(NAME_SHARDS_POINTS)
    mesh.from_pydata(points, [], [])
    #mesh.update()

    obj_points = utils.gen_childClean(obj, NAME_SHARDS_POINTS, context, mesh, hide=not cfg.struct_showPoints)
    # TODO: points relative to parent or world... in multiple paces: the dot when selected will be at origin atm
    # TODO: also set the matrix or only pos? test rotations etc
    obj_points.matrix_world = Matrix.Identity(4)
    return obj_points

def gen_boundsObject(obj: types.Object, bb: list[Vector, 2], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(NAME_ORIGINAL_BB)
    mesh.from_pydata(bb, [], [])

    # Generate it taking the transform as it is (points already in local space)
    obj_bb = utils.gen_childClean(obj, NAME_ORIGINAL_BB, context, mesh, keepTrans=False, hide=not cfg.struct_showBB)
    obj_bb.show_bounds = True
    return obj_bb

# -------------------------------------------------------------------

def gen_shardsObjects(obj: types.Object, cont: Container, cfg: MW_gen_cfg, context: types.Context):
    for cell in cont:
        # TODO: maybe make id match the point id instead of the container id
        name= f"{NAME_SHARDS}_{cell.id}"

        # create a static mesh for each one
        mesh = bpy.data.meshes.new(name)
        # TODO: local around centroid did not work properly
        mesh.from_pydata(vertices=cell.vertices_local_centroid(), edges=[], faces=cell.face_vertices())

        obj_shard = utils.gen_child(obj, name, context, mesh, hide=not cfg.struct_showShards)
        obj_shard.matrix_world = Matrix.Identity(4)
        obj_shard.location = cell.centroid()
        #print("cell.pos", cell.pos)

def gen_linksObjects(obj: types.Object, cont: Container, cfg: MW_gen_cfg, context: types.Context):
    # TODO: atm just hiding reps -> maybe generate using a different map instead of iterating the raw cont
    neigh_set = set()

    for cell in cont:
        # TODO: maybe merge shard/link loop

        # group the links by cell using a parent
        nameGroup= f"{NAME_LINKS_GROUP}_{cell.id}"
        obj_group = utils.gen_child(obj, nameGroup, context, None, hide=False)
        #obj_group.matrix_world = Matrix.Identity(4)
        #obj_group.location = cell.centroid()

        # TODO: position world/local?
        cell_centroid_4d = Vector(cell.centroid()).to_4d()

        # iterate the cell neighbours
        neigh = cell.neighbors()
        for n_id in neigh:
            # wall link
            if n_id < 0:
                name= f"s{cell.id}_w{-n_id}"
                obj_link = utils.gen_child(obj_group, name, context, None, hide=not cfg.struct_showLinks_walls)
                continue

            # neighbour link
            else:
                # check repetition
                key = tuple( sorted([cell.id, n_id]) )
                key_rep = key in neigh_set
                if not key_rep: neigh_set.add(key)

                # custom ordered name
                name= f"s{cell.id}_n{n_id}"


                # Create new curve per neighbour
                curve_data = bpy.data.curves.new(name, 'CURVE')
                curve_data.dimensions = '3D'

                # Add the centroid points using a poly line
                neigh_centroid_4d = Vector(cont[n_id].centroid()).to_4d()
                line = curve_data.splines.new('POLY')
                line.points.add(1)
                line.points[0].co = cell_centroid_4d
                line.points[1].co = neigh_centroid_4d

                # Set the width
                curve_data.bevel_depth = cfg.links_width
                curve_data.bevel_resolution = cfg.links_res

                obj_link = utils.gen_child(obj_group, name, curve_data, context, hide=not cfg.struct_showLinks)

                obj_link.hide_set(key_rep)
                #obj_link.location = cell.centroid()