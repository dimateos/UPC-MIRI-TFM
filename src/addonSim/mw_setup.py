import bpy
import bpy.types as types
import bmesh
from mathutils import Vector, Matrix
from math import radians

from .preferences import getPrefs
from .properties_global import (
    MW_id, MW_id_utils,
)
from .properties import (
    MW_gen_cfg,
    get_struct_name, get_struct_nameNew
)

from .mw_cont import MW_Container, VORO_Container
from .mw_links import MW_Links

from . import utils, utils_scene, utils_mat, utils_mesh
from .utils_dev import DEV
from .stats import getStats


# OPT:: more docu on some methods
#-------------------------------------------------------------------

def copy_original(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    cfg.struct_nameOriginal = obj.name
    prefs = getPrefs()

    # Empty object to hold all of them set at the original obj trans
    obj_root = bpy.data.objects.new(get_struct_name(cfg), None)
    obj_root.mw_id.meta_type = {"ROOT"}
    context.scene.collection.objects.link(obj_root)

    # Duplicate the original object
    prefs.names.original = obj.name
    obj_copy = utils_scene.copy_objectRec(obj, context, namePreffix=prefs.names.original_copy)
    #MW_id_utils.setMetaType(obj_copy, {"CHILD"})

    # Scene viewport
    obj.select_set(False)
    utils_scene.hide_objectRec(obj)
    utils_scene.hide_objectRec(obj_copy)
    obj_copy.show_bounds = True

    # Set the transform to the empty and parent keeping the transform of the copy
    obj_root.matrix_world = obj.matrix_world.copy()
    utils_scene.set_child(obj_copy, obj_root)

    # Rename with prefix?
    #get_renamed(obj_root, cfg, context)

    getStats().logDt(f"generated copy object ({1+len(obj_copy.children_recursive)} object/s)")
    return obj_root, obj_copy

def copy_originalPrev(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    # Copy the root objects including its mw_cfg
    obj_root = utils_scene.copy_object(obj, context)

    # XXX:: reset more metadata?
    MW_id_utils.resetStorageId(obj_root)

    # copy the original from the previous root withou suffix
    obj_original = utils_scene.get_child(obj, getPrefs().names.original_copy+cfg.struct_nameOriginal)
    obj_copy = utils_scene.copy_objectRec(obj_original, context)
    utils_scene.set_child(obj_copy, obj_root)

    getStats().logDt("generated copy object from prev frac")
    return obj_root, obj_copy

def get_renamed(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    """ split by first _
    # NOTE:: not robust... also not used?
    """
    try:
        prefix, name = obj.name.split("_",1)
    except ValueError:
        prefix, name = "", obj.name

    # use new prefix preserving name
    obj.name = get_struct_nameNew(cfg, name)

#-------------------------------------------------------------------

def copy_convex(obj: types.Object, obj_copy: types.Object, cfg: MW_gen_cfg, context: types.Context):
    """ Make a copy and find its convex hull
    # NOTE:: not recursive
    """

    # Duplicate again the copy and set child too
    obj_c = utils_scene.copy_objectRec(obj_copy, context, keep_mods=False)
    obj_c.name = getPrefs().names.original_convex
    #MW_id_utils.setMetaType(obj_c, {"CHILD"})
    utils_scene.set_child(obj_c, obj)

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
    obj_d = utils_scene.copy_objectRec(obj_c, context, keep_mods=False)
    obj_d.name = getPrefs().names.original_dissolve
    #MW_id_utils.setMetaType(obj_d, {"CHILD"})
    utils_scene.set_child(obj_d, obj)

    # dissolve faces based on angle limit
    bmesh.ops.dissolve_limit(bm, angle_limit=radians(1.7), use_dissolve_boundaries=True, verts=bm.verts, edges=bm.edges)
    bm.to_mesh(obj_d.data)

    # Scene viewport
    utils_scene.hide_objectRec(obj_c)
    utils_scene.hide_objectRec(obj_d)

    bm.free()
    getStats().logDt("generated convex object")
    return obj_d

#-------------------------------------------------------------------

def gen_pointsObject(obj: types.Object, points: list[Vector], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(getPrefs().names.source_points)
    mesh.from_pydata(points, [], [])
    #mesh.update()

    obj_points = utils_scene.gen_child(obj, getPrefs().names.source_points, context, mesh, keepTrans=False)

    getStats().logDt("generated points object")
    return obj_points

def gen_boundsObject(obj: types.Object, bb: list[Vector, 2], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(getPrefs().names.source_wallsBB)
    mesh.from_pydata(bb, [], [])

    # Generate it taking the transform as it is (points already in local space)
    obj_bb = utils_scene.gen_child(obj, getPrefs().names.source_wallsBB, context, mesh, keepTrans=False)
    obj_bb.show_bounds = True

    getStats().logDt("generated bounds object")
    return obj_bb

#-------------------------------------------------------------------

def gen_cellsEmpty(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_cellsEmpty = utils_scene.gen_child(obj, getPrefs().names.cells, context, None, keepTrans=False)
    return obj_cellsEmpty

def gen_cellsObjects(obj: types.Object, cont: MW_Container, cfg: MW_gen_cfg, context: types.Context, scale = 1.0, flipN = False):
    prefs = getPrefs()
    prefs.names.set_IdFormated_amount(len(cont.voro_cont))

    if not prefs.gen_setup_matColors:
        color3 = utils_mat.COLORS.gray
        matCells = utils_mat.get_colorMat(color3, alpha=prefs.gen_setup_matAlpha, matName=prefs.names.cells+"Mat")

    cells = []
    for cell in cont.voro_cont:
        # skip none cells (computation error)
        if cell is None: continue
        source_id = cont.voro_cont.source_idx[cell.id]
        name= f"{prefs.names.cells[0]}{prefs.names.get_IdFormated(source_id)}"

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
        faces_blender = [ f_indices[::-1] for f_indices in faces_voro ] if flipN else faces_voro

        # build the static mesh and child object
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices=verts, edges=[], faces=faces_blender)
        obj_shard = utils_scene.gen_child(obj, name, context, mesh, keepTrans=False)
        cells.append(obj_shard)
        obj_shard.location = pos
        obj_shard.scale = [scale]*3

        obj_shard.active_material = matCells
        #utils_mat.gen_meshAttr(mesh, utils_mat.COLORS.assure_4d_alpha(color3, prefs.gen_setup_matAlpha), 1, "FLOAT_COLOR", "POINT", "alphaColor")

    getStats().logDt("generated cells objects")
    return cells

def gen_LEGACY_CONT(obj: types.Object, voro_cont: VORO_Container, cfg: MW_gen_cfg, context: types.Context):
    centroids = []
    vertices = []
    volume = []
    face_vertices = []
    surface_area = []
    normals = []
    neighbors = []

    for cell in voro_cont:
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
        name= f"{getPrefs().names.cells}_{cell.id}"
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices=vs, edges=[], faces=f)
        obj_shard = utils_scene.gen_child(obj, name, context, mesh, keepTrans=False)
        pass
    getStats().logDt("generated LEGACY cells objects")

    numVerts = [ len(vs) for vs in vertices ]
    numFaces = [ len(fs) for fs in face_vertices ]

    import numpy as np
    stVolume = np.std(volume)
    stArea = np.std(surface_area)
    getStats().logDt("calculated stats (use breakpoints to see)")

#-------------------------------------------------------------------

def gen_linksObject(obj: types.Object, links: MW_Links, cfg: MW_gen_cfg, context: types.Context):
    prefs = getPrefs()
    name = prefs.names.links
    baseColor = utils_mat.COLORS.red

    # iterate the global map and store vert pairs for the tube mesh generation
    verts: list[tuple[Vector,Vector]] = []
    lifeWidths: list[float] = []
    lifeColor: list[Vector] = []
    for l in links.internal:
        life = l.life_clamped

        verts.append((l.pos-l.dir*prefs.links_depth, l.pos+l.dir*prefs.links_depth))
        lifeColor.append( (baseColor*life).to_4d() )
        #lifeColor[-1].w = 0.5

        if prefs.links_widthModLife == {"UNIFORM"}:
            lifeWidths.append(prefs.links_widthDead * (1-life) + prefs.links_width * life)
        elif prefs.links_widthModLife == {"BINARY"}:
            lifeWidths.append(prefs.links_widthDead if life<1 else prefs.links_width)

    resFaces = utils_mesh.get_resFaces_fromCurveRes(prefs.links_res)
    mesh = utils_mesh.get_tubeMesh_pairsQuad(verts, lifeWidths, name, 1.0, resFaces, prefs.links_smoothShade)

    # color encoded attributes for viewing in viewport edit mode
    utils_mat.gen_meshAttr(mesh, lifeColor, resFaces*2, "FLOAT_COLOR", "POINT", "life")

    # potentially reuse child
    obj_links = utils_scene.gen_childReuse(obj, name, context, mesh, keepTrans=True)
    mesh.name = name

    MW_id_utils.setMetaType(obj_links, {"CHILD"}, childrenRec=False)
    getStats().logDt("generated links object")
    return obj_links

def gen_linksWallObject(obj: types.Object, links: MW_Links, cfg: MW_gen_cfg, context: types.Context, weights : list[float] = None):
    prefs = getPrefs()
    name = prefs.names.links_air
    wallsExtraScale = prefs.links_wallExtraScale

    # iterate the global map and store vert pairs for the tube mesh generation
    verts: list[tuple[Vector,Vector]] = []
    lifeWidth: list[float] = []
    for i,l in enumerate(links.external):
        #DEV.log_msg(f"life {l.life}")

        # skip drawing entry links with no probability
        #if weights and weights[i] == 0: continue

        # WIP:: also skip drawing non picked?
        if not l.picks: continue

        lifeWidth.append(prefs.links_width*wallsExtraScale*l.life)
        verts.append((l.pos, l.pos+l.dir*prefs.links_depth))

    resFaces = utils_mesh.get_resFaces_fromCurveRes(prefs.links_res+3)
    mesh = utils_mesh.get_tubeMesh_pairsQuad(verts, lifeWidth, name, 1+prefs.links_width*wallsExtraScale, resFaces, prefs.links_smoothShade)

    # potentially reuse child
    obj_wallLinks = utils_scene.gen_childReuse(obj, name, context, mesh, keepTrans=True)
    mesh.name = name

    # set global material
    color3 = utils_mat.COLORS.blue+utils_mat.COLORS.white * 0.33
    wallsMat = utils_mat.get_colorMat(color3, 1.0, "linkWallsMat")
    obj_wallLinks.active_material = wallsMat

    # WIP:: additional attr to visualize in the ame view mode
    utils_mat.gen_meshAttr(mesh, color3.to_4d(), 1, "FLOAT_COLOR", "POINT", "blueColor")

    MW_id_utils.setMetaType(obj_wallLinks, {"CHILD"}, childrenRec=False)
    getStats().logDt("generated wall links object")
    return obj_wallLinks

#-------------------------------------------------------------------
# TODO:: too many gen links...

def genWIP_linksEmpties(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_links = utils.gen_childClean(obj, getPrefs().names.links, context, None, keepTrans=False)
    obj_links_air = utils.gen_childClean(obj, getPrefs().names.links_air, context, None, keepTrans=False)
    return obj_links, obj_links_air

def genWIP_linksObjects(objLinks: types.Object, objWall: types.Object, links: MW_Links, cfg: MW_gen_cfg, context: types.Context):
    prefs = getPrefs()
    wallsMat = utils_mat.get_colorMat(utils_mat.COLORS.blue+utils_mat.COLORS.white * 0.33, 1.0, "linkWallsMat")
    #objLinks = None
    #objWall = None

    # iterate the global map
    for key,l in links.link_map.items():
        c1, c2 = l.key_cells
        f1, f2 = l.key_faces

        # links to walls
        if l.airLink:
            if not objWall: continue
            obj = objWall
            name= f"w{c1}_c{c2}-f{f2}"

            # start at the face outward
            p1 = Vector()
            p2 = l.dir*0.1
            #p3 = l.dir*0.8
            #p4 = l.dir*1.8

            # vary curve props
            res = (prefs.links_res+1) +2
            #res = prefs.links_res
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
            mat = utils_mat.get_colorMat(utils_mat.COLORS.red*l.life, alpha, name)

        res = utils_mesh.get_resFaces_fromCurveRes(res)
        curve= utils_mesh.get_tubeMesh_pairsQuad([(p1, p2)], None, name, width, res)
        obj_link = utils_scene.gen_child(obj, name, context, curve, keepTrans=True)
        obj_link.location = l.pos
        obj_link.active_material = mat

    MW_id_utils.setMetaType(objLinks.parent, {"CHILD"}, skipParent=True)
    getStats().logDt("generated links to walls objects")

def genWIP_linksEmptiesPerCell(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_links_legacy = utils.gen_childClean(obj, getPrefs().names.links_legacy, context, None, keepTrans=False)
    return obj_links_legacy

def genWIP_linksCellObjects(objParent: types.Object, voro_cont: VORO_Container, cfg: MW_gen_cfg, context: types.Context):
    prefs = getPrefs()
    prefs.names.set_IdFormated_amount(len(voro_cont))

    # WIP:: links better generated from map isntead of cont? + done in a separate op
    # WIP:: atm just hiding reps -> maybe generate using a different map instead of iterating the raw cont
    #   maybe merge cell/link loop
    neigh_set = set()

    for cell in voro_cont:
        # NOTE:: in the case of directly iterating the cont there could be missing ones
        if cell is None: continue

        # group the links by cell using a parent
        nameGroup= f"{getPrefs().names.links_group}_{prefs.names.get_IdFormated(cell.id)}"
        obj_group = utils_scene.gen_child(objParent, nameGroup, context, None, keepTrans=False, hide=False)
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
                obj_link = utils_scene.gen_child(obj_group, name, context, None, keepTrans=False)
                continue

            # TODO:: so some cells actually connect with the missing ones...
            if voro_cont[n_id] is None:
                continue

            # neighbour link -> check rep
            key = tuple( sorted([cell.id, n_id]) )
            key_rep = key in neigh_set
            if not key_rep: neigh_set.add(key)

            # custom ordered name
            name= f"s{cell.id}_n{n_id}"
            neigh_centroid = Vector(voro_cont[n_id].centroid())

            curve = utils_mesh.get_curveData([cell_centroid, neigh_centroid], name, cfg.links_width, cfg.links_res)
            obj_link = utils_scene.gen_child(obj_group, name, context, curve, keepTrans=False)

            obj_link.hide_set(key_rep)
            #obj_link.location = cell.centroid()

    MW_id_utils.setMetaType(objParent, {"CHILD"}, skipParent=False)
    getStats().logDt("generated links per cell objects")