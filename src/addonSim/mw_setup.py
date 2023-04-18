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

class CONST_NAMES:
    original = "Original_"
    original_bb = original+"bb"
    shards = "Shards"
    shards_points = "Shards_source"
    links = shards+"_links"
    links_group = "Links"


# -------------------------------------------------------------------

def gen_copyOriginal(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    cfg.meta_type = {"ROOT"}
    cfg.struct_nameOriginal = obj.name

    # Empty object to hold all of them set at the original obj trans
    obj_empty = bpy.data.objects.new(cfg.get_struct_name(), None)
    context.scene.collection.objects.link(obj_empty)

    # Duplicate the original object
    obj_copy = utils.copy_objectRec(obj, context, namePreffix=CONST_NAMES.original)
    utils.cfg_setMetaTypeRec(obj_copy, {"CHILD"})

    # Set the transform to the empty and parent keeping the transform of the copy
    obj_empty.matrix_world = obj.matrix_world.copy()
    utils.set_child(obj_copy, obj_empty)

    # Hide and select after link
    obj.hide_set(not cfg.struct_showOrignal)
    obj_copy.hide_set(True)
    obj_copy.show_bounds = True
    context.view_layer.objects.active = obj_empty

    #bpy.ops.outliner.show_active(execution_context='INVOKE_DEFAULT') cannot expand hierarchy from this context
    #tried context_override but no luck either...

    return obj_empty, obj_copy

def gen_renaming(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    # split by first _
    try:
        prefix, name = obj.name.split("_",1)
    except ValueError:
        prefix, name = "", obj.name

    # use new prefix preserving name
    obj.name = cfg.get_struct_nameNew(name)

def gen_shardsEmpty(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_shardsEmpty = utils.gen_childClean(obj, CONST_NAMES.shards, context, None, keepTrans=False, hide=not cfg.struct_showShards)
    return obj_shardsEmpty

def gen_linksEmpty(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_linksEmpty = utils.gen_childClean(obj, CONST_NAMES.links, context, None, keepTrans=False, hide=not cfg.struct_showLinks)
    return obj_linksEmpty

def gen_pointsObject(obj: types.Object, points: list[Vector], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(CONST_NAMES.shards_points)
    mesh.from_pydata(points, [], [])
    #mesh.update()

    obj_points = utils.gen_childClean(obj, CONST_NAMES.shards_points, context, mesh, keepTrans=False, hide=not cfg.struct_showPoints)
    return obj_points

def gen_boundsObject(obj: types.Object, bb: list[Vector, 2], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(CONST_NAMES.original_bb)
    mesh.from_pydata(bb, [], [])

    # Generate it taking the transform as it is (points already in local space)
    obj_bb = utils.gen_childClean(obj, CONST_NAMES.original_bb, context, mesh, keepTrans=False, hide=not cfg.struct_showBB)
    obj_bb.show_bounds = True
    return obj_bb

# -------------------------------------------------------------------

def gen_shardsObjects(obj: types.Object, cont: Container, cfg: MW_gen_cfg, context: types.Context):
    for cell in cont:
        source_id = cont.source_idx[cell.id]
        name= f"{CONST_NAMES.shards}_{source_id}"

        # TODO: the centroid is not at the center of mass? problem maybe related to margins etc
        # pos center of volume
        pos = cell.centroid()
        #pos = cell.pos
        #posC = cell.centroid()
        #posCl = cell.centroid_local()

        # TODO: world do not match local + pos?
        # create a static mesh with vertices relative to the center of mass
        verts = cell.vertices_local_centroid()
        #verts = cell.vertices_local()
        #vertsW = cell.vertices()
        #vertsW2 = [ Vector(v)+Vector(pos) for v in verts ]
        #vertsC = cell.vertices_local_centroid()


        # build the static mesh and child object
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices=verts, edges=[], faces=cell.face_vertices())
        obj_shard = utils.gen_child(obj, name, context, mesh, keepTrans=False, hide=not cfg.struct_showShards)
        obj_shard.location = pos

def gen_linksObjects(obj: types.Object, cont: Container, cfg: MW_gen_cfg, context: types.Context):
    # TODO: atm just hiding reps -> maybe generate using a different map instead of iterating the raw cont
    neigh_set = set()

    for cell in cont:
        # TODO: maybe merge shard/link loop

        # group the links by cell using a parent
        nameGroup= f"{CONST_NAMES.links_group}_{cell.id}"
        obj_group = utils.gen_child(obj, nameGroup, context, None, keepTrans=False, hide=False)
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
                obj_link = utils.gen_child(obj_group, name, context, None, keepTrans=False, hide=not cfg.struct_showLinks_walls)
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

                obj_link = utils.gen_child(obj_group, name, context, curve_data, keepTrans=False, hide=not cfg.struct_showLinks)

                obj_link.hide_set(key_rep)
                #obj_link.location = cell.centroid()