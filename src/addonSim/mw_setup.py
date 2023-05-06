import bpy
import bpy.types as types
import bmesh
from mathutils import Vector, Matrix
from math import radians

# IDEA:: global prefs might not be so good
#from .preferences import prefs
from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
)

from .mw_links import Links, Link
from tess import Container, Cell

from . import utils
from .utils_dev import DEV
from .stats import getStats


# OPT:: more docu on methods
#-------------------------------------------------------------------

def copy_original(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    cfg.meta_type = {"ROOT"}
    cfg.struct_nameOriginal = obj.name

    # Empty object to hold all of them set at the original obj trans
    obj_root = bpy.data.objects.new(cfg.get_struct_name(), None)
    context.scene.collection.objects.link(obj_root)

    # Duplicate the original object
    obj_copy = utils.copy_objectRec(obj, context, namePreffix=getPrefs().names.original_copy)
    #MW_gen_cfg.setMetaType(obj_copy, {"CHILD"})

    # Scene viewport
    utils.hide_objectRec(obj, not cfg.struct_showOrignal_scene)
    utils.hide_objectRec(obj_copy, not cfg.struct_showOrignal)
    obj_copy.show_bounds = True

    # Set the transform to the empty and parent keeping the transform of the copy
    obj_root.matrix_world = obj.matrix_world.copy()
    utils.set_child(obj_copy, obj_root)

    # Rename with prefix?
    get_renamed(obj_root, cfg, context)

    getStats().logDt(f"generated copy object ({1+len(obj_copy.children_recursive)} object/s)")
    return obj_root, obj_copy

def copy_originalPrev(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    # Copy the root objects including its mw_cfg
    obj_root = utils.copy_object(obj, context)

    # copy the original from the previous root withou suffix
    obj_original = utils.get_child(obj, getPrefs().names.original_copy)
    obj_copy = utils.copy_objectRec(obj_original, context)
    utils.set_child(obj_copy, obj_root)

    getStats().logDt("generated copy object from prev frac")
    return obj_root, obj_copy

# OPT:: not robust...
def get_renamed(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    # split by first _
    try:
        prefix, name = obj.name.split("_",1)
    except ValueError:
        prefix, name = "", obj.name

    # use new prefix preserving name
    obj.name = cfg.get_struct_nameNew(name)

#-------------------------------------------------------------------

def copy_convex(obj: types.Object, obj_copy: types.Object, cfg: MW_gen_cfg, context: types.Context):
    # Duplicate again the copy and set child too
    obj_c = utils.copy_objectRec(obj_copy, context, keep_mods=False)
    obj_c.name = getPrefs().names.original_convex
    #MW_gen_cfg.setMetaType(obj_c, {"CHILD"})
    utils.set_child(obj_c, obj)

    # XXX:: need to mesh update? + decimate before more perf? but need to change EDIT/OBJ modes?
    # NOTE:: not recursive hull...

    # build convex hull with only verts
    bm = bmesh.new()
    bm.from_mesh(obj_c.data)
    ch = bmesh.ops.convex_hull(bm, input=bm.verts)
    # either delete unused and interior or build another mesh with "geom"
    bmesh.ops.delete(
            bm,
            geom=ch["geom_unused"] + ch["geom_interior"],
            context='VERTS',
            )
    bm.to_mesh(obj_c.data)

    # Second copy with the face dissolve
    obj_d = utils.copy_objectRec(obj_c, context, keep_mods=False)
    obj_d.name = getPrefs().names.original_dissolve
    #MW_gen_cfg.setMetaType(obj_d, {"CHILD"})
    utils.set_child(obj_d, obj)

    # dissolve faces based on angle limit
    bmesh.ops.dissolve_limit(bm, angle_limit=radians(1.7), use_dissolve_boundaries=True, verts=bm.verts, edges=bm.edges)
    bm.to_mesh(obj_d.data)

    # Scene viewport
    utils.hide_objectRec(obj_c)
    utils.hide_objectRec(obj_d, not cfg.struct_showConvex)

    bm.free()
    getStats().logDt("generated convex object")
    return obj_d

#-------------------------------------------------------------------

def gen_pointsObject(obj: types.Object, points: list[Vector], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(getPrefs().names.source_points)
    mesh.from_pydata(points, [], [])
    #mesh.update()

    obj_points = utils.gen_child(obj, getPrefs().names.source_points, context, mesh, keepTrans=False, hide=not cfg.struct_showPoints)

    getStats().logDt("generated points object")
    return obj_points

def gen_boundsObject(obj: types.Object, bb: list[Vector, 2], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(getPrefs().names.source_wallsBB)
    mesh.from_pydata(bb, [], [])

    # Generate it taking the transform as it is (points already in local space)
    obj_bb = utils.gen_child(obj, getPrefs().names.source_wallsBB, context, mesh, keepTrans=False, hide=not cfg.struct_showBB)
    obj_bb.show_bounds = True

    getStats().logDt("generated bounds object")
    return obj_bb

#-------------------------------------------------------------------

def gen_shardsEmpty(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_shardsEmpty = utils.gen_child(obj, getPrefs().names.shards, context, None, keepTrans=False, hide=not cfg.struct_showShards)
    return obj_shardsEmpty

def gen_shardsObjects(obj: types.Object, cont: Container, cfg: MW_gen_cfg, context: types.Context, invertOrientation = False):
    for cell in cont:
        if cell is None: continue
        source_id = cont.source_idx[cell.id]
        name= f"{getPrefs().names.shards}_{getPrefs().names.get_IdFormated(source_id)}"

        # assert some voro properties, the more varied test cases the better: center of mass at the center of volume
        if DEV.assert_voro_posW:
            posC = cell.centroid()
            posCL = cell.centroid_local()
            vertsCL = cell.vertices_local_centroid()
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

        # maybe reorient faces
        faces_voro = cell.face_vertices()
        faces_blender = [ f_indices[::-1] for f_indices in faces_voro ] if invertOrientation else faces_voro

        # build the static mesh and child object
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices=verts, edges=[], faces=faces_blender)
        obj_shard = utils.gen_child(obj, name, context, mesh, keepTrans=False, hide=not cfg.struct_showShards)
        obj_shard.location = pos
        obj_shard.scale = [0.9]*3

    getStats().logDt("generated shards objects")

def gen_LEGACY_CONT(obj: types.Object, cont: Container, cfg: MW_gen_cfg, context: types.Context):
    centroids = []
    vertices = []
    volume = []
    face_vertices = []
    surface_area = []
    normals = []
    neighbors = []

    for cell in cont:
        if cell is None: continue
        c = cell.centroid()
        vs = cell.vertices()
        v = cell.volume()
        f = cell.face_vertices()
        s = cell.surface_area()
        n = cell.normals()
        ns = cell.neighbors()

        centroids += [c]
        vertices += [vs]
        volume += [v]
        face_vertices += [f]
        surface_area += [s]
        normals += [n]
        neighbors += [ns]

        # build the static mesh and child object just at the origin
        name= f"{getPrefs().names.shards}_{cell.id}"
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices=vs, edges=[], faces=f)
        obj_shard = utils.gen_child(obj, name, context, mesh, keepTrans=False, hide=not cfg.struct_showShards)
        pass
    getStats().logDt("generated LEGACY shards objects")

    numVerts = [ len(vs) for vs in vertices ]
    numFaces = [ len(fs) for fs in face_vertices ]

    import numpy as np
    stVolume = np.std(volume)
    stArea = np.std(surface_area)
    getStats().logDt("calculated stats (use breakpoints to see)")

#-------------------------------------------------------------------

# WIP:: links empties,..
def gen_linksEmpties(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_links = utils.gen_childClean(obj, getPrefs().names.links, context, None, keepTrans=False, hide=not cfg.struct_showLinks)
    obj_links_toWall = utils.gen_childClean(obj, getPrefs().names.links_toWalls, context, None, keepTrans=False, hide=not cfg.struct_showLinks_toWalls)
    return obj_links, obj_links_toWall

def gen_linksEmptiesPerCell(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_links_perCell = utils.gen_childClean(obj, getPrefs().names.links_perCell, context, None, keepTrans=False, hide=not cfg.struct_showLinks_perCell)
    return obj_links_perCell

def gen_linksObjects(objLinks: types.Object, objWall: types.Object, links: Links, cfg: MW_gen_cfg, context: types.Context):
    # iterate the global map
    for key,l in links.link_map.items():
        c1, c2 = l.key_cells
        f1, f2 = l.key_faces

        # links to walls
        if l.toWall:
            name= f"w{c1}_c{c2}-f{f2}"
            obj = objWall

            # start at the face outward
            p1 = Vector()
            p2 = l.dir*0.1

        # regular links
        else:
            name= f"c{c1}_c{c2}-f{f1}_f{f2}"
            obj = objLinks

            # two points around the face
            p1 = +l.dir*0.1
            p2 = -l.dir*0.1

        # Create new curve per link and spawn
        curve = utils.get_curveData([p1, p2], name, cfg.links_width, cfg.links_res)
        obj_link = utils.gen_child(obj, name, context, curve, keepTrans=True, hide=not cfg.struct_showLinks)
        obj_link.location = l.pos

    getStats().logDt("generated links to walls objects")


def gen_linksCellObjects(obj: types.Object, cont: Container, cfg: MW_gen_cfg, context: types.Context):
    # WIP:: links better generated from map isntead of cont? + done in a separate op
    # WIP:: atm just hiding reps -> maybe generate using a different map instead of iterating the raw cont
    #   maybe merge shard/link loop
    neigh_set = set()

    for cell in cont:
        # NOTE:: in the case of directly iterating the cont there could be missing ones
        if cell is None: continue

        # group the links by cell using a parent
        nameGroup= f"{getPrefs().names.links_group}_{getPrefs().names.get_IdFormated(cell.id)}"
        obj_group = utils.gen_child(obj, nameGroup, context, None, keepTrans=False, hide=False)
        #obj_group.matrix_world = Matrix.Identity(4)
        #obj_group.location = cell.centroid()

        # WIP:: position world/local?
        cell_centroid = Vector(cell.centroid())

        # iterate the cell neighbours
        neigh = cell.neighbors()
        for n_id in neigh:
            # wall link
            if n_id < 0:
                name= f"s{cell.id}_w{-n_id}"
                obj_link = utils.gen_child(obj_group, name, context, None, keepTrans=False, hide=not cfg.struct_showLinks_toWalls)
                continue

            # TODO:: so some cells actually connect with the missing ones...
            if cont[n_id] is None:
                continue

            # neighbour link -> check rep
            key = tuple( sorted([cell.id, n_id]) )
            key_rep = key in neigh_set
            if not key_rep: neigh_set.add(key)

            # custom ordered name
            name= f"s{cell.id}_n{n_id}"
            neigh_centroid = Vector(cont[n_id].centroid())

            curve = utils.get_curveData([cell_centroid, neigh_centroid], name, cfg.links_width, cfg.links_res)
            obj_link = utils.gen_child(obj_group, name, context, curve, keepTrans=False, hide=not cfg.struct_showLinks)

            obj_link.hide_set(key_rep or not cfg.struct_showLinks_perCell)
            #obj_link.location = cell.centroid()

    MW_gen_cfg.setMetaType(obj, {"CHILD"}, skipParent=False)
    getStats().logDt("generated links per cell objects")
