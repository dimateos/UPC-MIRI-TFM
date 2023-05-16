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

from .mw_links import LinkCollection
from tess import Container

from . import utils
from . import utils_render
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
    obj.select_set(False)
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
    obj_original = utils.get_child(obj, getPrefs().names.original_copy+cfg.struct_nameOriginal)
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
    prefs = getPrefs()
    if not prefs.gen_setup_matColors:
        matShards = utils_render.get_colorMat(utils_render.COLORS.gray, alpha=prefs.gen_setup_matAlpha, matName=prefs.names.shards+"Mat")

    for cell in cont:
        # skip none cells (computation error)
        if cell is None: continue
        source_id = cont.source_idx[cell.id]
        name= f"{prefs.names.shards}_{prefs.names.get_IdFormated(source_id)}"

        # assert some voro properties, the more varied test cases the better: center of mass at the center of volume
        if DEV.ASSERT_CELL_POS:
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
        obj_shard.scale = [cfg.struct_shardScale]*3

        # IDEA:: test visuals alternatives -> add to dm utils
        #if DEV.VISUAL_TESTS:
        if prefs.gen_setup_matColors:
            uv = utils_render.gen_meshUV(mesh, [Vector([0.66, 0.66]), Vector([0.33, 0.33])])
            utils_render.set_meshUV_rnd(mesh, uv.name)

            vc_old = utils_render.gen_meshVC_legacy(mesh, utils_render.COLORS.pink)
            utils_render.set_meshVC_legacy(mesh, vc_old, utils_render.COLORS.list_gray)
            utils_render.set_meshVC_legacy_rnd(mesh, vc_old)
            vc = utils_render.gen_meshVC(mesh, utils_render.COLORS.list_rgb4D )
            vcFace = utils_render.gen_meshVC(mesh, utils_render.COLORS.list_rgb4D, adomain="CORNER")

            ac = utils_render.gen_meshAC(mesh, utils_render.COLORS.list_fade, adomain="CORNER", name="ACtestcolor")
            ac2 = utils_render.gen_meshAC(mesh, adomain="FACE")
            ac3 = utils_render.gen_meshAC(mesh, utils_render.COLORS.red, adomain="EDGE")

            at = utils_render.gen_meshAttr(mesh, adomain="FACE")
            utils_render.set_meshAttr_rnd(mesh, at)
            atc = utils_render.gen_meshAttr(mesh, utils_render.COLORS.blue.to_4d(), adomain="CORNER", atype="FLOAT_COLOR", name="ATtestcolor")
            utils_render.set_meshAttr_rnd(mesh, atc)

            # NOTE:: materials can also by aded to the object instead of the data?
            obj_shard.active_material = utils_render.get_randomMat(alpha=prefs.gen_setup_matAlpha, matName=name)

        else:
            obj_shard.active_material = matShards

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

def gen_linksObjects(objLinks: types.Object, objWall: types.Object, links: LinkCollection, cfg: MW_gen_cfg, context: types.Context):
    #objLinks = None
    #objWall = None
    prefs = getPrefs()
    wallsMat = utils_render.get_colorMat(utils_render.COLORS.blue+utils_render.COLORS.white * 0.33, 1.0, "linkWallsMat")

    # iterate the global map
    for key,l in links.link_map.items():
        c1, c2 = l.key_cells
        f1, f2 = l.key_faces

        # links to walls
        if l.toWall:
            if not objWall: continue
            obj = objWall
            name= f"w{c1}_c{c2}-f{f2}"

            # start at the face outward
            p1 = Vector()
            p2 = l.dir*0.1

            # vary curve props
            res = (prefs.links_res+1) +2
            width = prefs.links_width * 1.5
            mat = wallsMat

        # regular links
        else:
            if not objLinks: continue
            obj = objLinks
            name= f"c{c1}_c{c2}-f{f1}_f{f2}"

            # two points around the face
            p1 = +l.dir*0.1
            p2 = -l.dir*0.1

            # vary curve props
            res = prefs.links_res
            width = prefs.links_widthDead * (1-l.life) + prefs.links_width * l.life
            alpha = l.life+0.1 if prefs.links_matAlpha else 1.0
            mat = utils_render.get_colorMat(utils_render.COLORS.red*l.life, alpha, name)

        # Create new curve per link and spawn
        if l.toWall:
            curve= utils_render.get_tubeMesh([p1, p2], [(0,1)], name, width, res+1)
            utils_render.set_smoothShading(curve)
        else:
            curve = utils_render.get_curveData([p1, p2], name, width, res)

        obj_link = utils.gen_child(obj, name, context, curve, keepTrans=True, hide=not cfg.struct_showLinks)
        obj_link.location = l.pos
        obj_link.active_material = mat

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

            curve = utils_render.get_curveData([cell_centroid, neigh_centroid], name, cfg.links_width, cfg.links_res)
            obj_link = utils.gen_child(obj_group, name, context, curve, keepTrans=False, hide=not cfg.struct_showLinks)

            obj_link.hide_set(key_rep or not cfg.struct_showLinks_perCell)
            #obj_link.location = cell.centroid()

    MW_gen_cfg.setMetaType(obj, {"CHILD"}, skipParent=False)
    getStats().logDt("generated links per cell objects")
