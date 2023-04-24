import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
)

from . import utils
from .utils_dev import DEV
from .stats import getStats

from mathutils import Vector, Matrix

# Using tess voro++ adaptor
from tess import Container, Cell


class CONST_NAMES:
    original = "Original_"
    original_bb = original+"bb"
    original_convex = original+"convex"
    original_low = original+"low"
    shards = "Shards"
    shards_points = "Shards_source"
    links = shards+"_links"
    links_group = "Links"


# OPT:: more docu on methods
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

    # Scene viewport
    obj.hide_set(not cfg.struct_showOrignal_scene)
    obj_copy.hide_set(not cfg.struct_showOrignal)
    obj_copy.show_bounds = True

    # Set the transform to the empty and parent keeping the transform of the copy
    obj_empty.matrix_world = obj.matrix_world.copy()
    utils.set_child(obj_copy, obj_empty)

    getStats().logDt("generated copy object")
    return obj_empty, obj_copy

def gen_copyConvex(obj: types.Object, obj_copy: types.Object, cfg: MW_gen_cfg, context: types.Context):
    # Duplicate again the copy and set child too
    obj_convex = utils.copy_objectRec(obj_copy, context)
    obj_convex.name = CONST_NAMES.original_convex
    utils.cfg_setMetaTypeRec(obj_copy, {"CHILD"})
    utils.set_child(obj_convex, obj)

    # Scene viewport
    obj_convex.hide_set(not cfg.struct_showConvex)

    # Apply convex hull to the mesh
    # NOTE:: not recursive?
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj_convex.data)

    ch = bmesh.ops.convex_hull(bm, input=bm.verts)

    # either delete unused and interior or build another mesh with "geom"
    bmesh.ops.delete(
            bm,
            geom=ch["geom_unused"] + ch["geom_interior"],
            context='VERTS',
            )
    bm.to_mesh(obj_convex.data)

    getStats().logDt("generated convex object")
    return obj_convex

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

    getStats().logDt("generated points object")
    return obj_points

def gen_boundsObject(obj: types.Object, bb: list[Vector, 2], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(CONST_NAMES.original_bb)
    mesh.from_pydata(bb, [], [])

    # Generate it taking the transform as it is (points already in local space)
    obj_bb = utils.gen_childClean(obj, CONST_NAMES.original_bb, context, mesh, keepTrans=False, hide=not cfg.struct_showBB)
    obj_bb.show_bounds = True

    getStats().logDt("generated bounds object")
    return obj_bb

# -------------------------------------------------------------------

def gen_shardsObjects(obj: types.Object, cont: Container, cfg: MW_gen_cfg, context: types.Context):
    for cell in cont:
        source_id = cont.source_idx[cell.id]
        name= f"{CONST_NAMES.shards}_{source_id}"

        # XXX:: the centroid is not at the center of mass? problem maybe related to margins etc
        posC = cell.centroid()
        posCL = cell.centroid_local()
        vertsCL = cell.vertices_local_centroid()

        # assert some voro properties, the more varied test cases the better
        if DEV.assert_voro_posW:
            posW = cell.pos
            vertsW = cell.vertices()
            vertsL = cell.vertices_local()
            vertsW2 = [ Vector(v)+Vector(posW) for v in vertsL ]
            vertsWd_diff = [ Vector(v1)-Vector(v2) for v1,v2 in zip(vertsW,vertsW2) ]
            vertsW_check = [ d.length_squared > 0.0005 for d in vertsWd_diff ]
            assert(not any(vertsW_check))

        # pos center of volume
        pos = cell.centroid()
        # create a static mesh with vertices relative to the center of mass
        verts = cell.vertices_local_centroid()

        # build the static mesh and child object
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices=verts, edges=[], faces=cell.face_vertices())
        obj_shard = utils.gen_child(obj, name, context, mesh, keepTrans=False, hide=not cfg.struct_showShards)
        obj_shard.location = pos

    getStats().logDt("generated shards objects")


def gen_linksObjects(obj: types.Object, cont: Container, cfg: MW_gen_cfg, context: types.Context):
    # WIP:: atm just hiding reps -> maybe generate using a different map instead of iterating the raw cont
    #   maybe merge shard/link loop
    neigh_set = set()

    for cell in cont:
        # group the links by cell using a parent
        nameGroup= f"{CONST_NAMES.links_group}_{cell.id}"
        obj_group = utils.gen_child(obj, nameGroup, context, None, keepTrans=False, hide=False)
        #obj_group.matrix_world = Matrix.Identity(4)
        #obj_group.location = cell.centroid()

        # WIP:: position world/local?
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

    getStats().logDt("generated links objects")
