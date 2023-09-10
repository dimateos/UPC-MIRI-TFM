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
    MW_vis_cfg,
)

from .mw_cont import MW_Cont, VORO_Container, STATE_ENUM
from .mw_links import MW_Links
from .mw_fract import MW_Fract # could import all from here

from . import utils, utils_scene, utils_mat, utils_mesh
from .utils_dev import DEV
from .stats import getStats


# OPT:: more docu on some methods
#-------------------------------------------------------------------

def copy_original(obj: types.Object, cfg: MW_gen_cfg, context: types.Context, namePreffix:str):
    # Empty object to hold all of them set at the original obj trans
    cfg.struct_nameOriginal = obj.name
    obj_root = bpy.data.objects.new(f"{cfg.struct_namePrefix}_{cfg.struct_nameOriginal}", None)
    obj_root.mw_id.meta_type = {"ROOT"}
    context.scene.collection.objects.link(obj_root)

    # Duplicate the original object
    obj_copy = utils_scene.copy_objectRec(obj, context, namePreffix=namePreffix)
    #MW_id_utils.setMetaType(obj_copy, {"CHILD"})

    # Scene viewport
    obj.select_set(False)
    utils_scene.hide_objectRec(obj)
    utils_scene.hide_objectRec(obj_copy)
    obj_copy.show_bounds = True

    # Set the transform to the empty and parent keeping the transform of the copy
    obj_root.matrix_world = obj.matrix_world.copy()
    utils_scene.set_child(obj_copy, obj_root)

    getStats().logDt(f"generated copy object ({1+len(obj_copy.children_recursive)} object/s)")
    return obj_root, obj_copy

def copy_originalPrev(obj: types.Object, context: types.Context, namePreffix:str):
    # Copy the root objects including its mw_cfg
    obj_root = utils_scene.copy_object(obj, context)

    # XXX:: reset more metadata?
    MW_id_utils.resetStorageId(obj_root)

    # copy the original from the previous root withou suffix
    obj_original = utils_scene.get_child(obj, namePreffix, mode="STARTS_WITH")
    obj_copy = utils_scene.copy_objectRec(obj_original, context)
    utils_scene.set_child(obj_copy, obj_root)

    getStats().logDt("generated copy object from prev frac")
    return obj_root, obj_copy

def copy_convex(obj: types.Object, obj_copy: types.Object, context: types.Context, nameConvex:str, nameDissolved:str):
    """ Make a copy and find its convex hull
        # NOTE:: not recursive!
    """

    # Duplicate again the copy and set child too
    obj_c = utils_scene.copy_objectRec(obj_copy, context, keep_mods=False)
    obj_c.name = nameConvex
    #MW_id_utils.setMetaType(obj_c, {"CHILD"})
    utils_scene.set_child(obj_c, obj)

    # build convex hull with only verts
    bm = bmesh.new()
    bm.from_mesh(obj_c.data)
    try:
        ch = bmesh.ops.convex_hull(bm, input=bm.verts)
    except RuntimeError:
        import traceback
        traceback.print_exc()

    # either delete unused and interior or build another mesh with "geom"
    bmesh.ops.delete(
            bm,
            geom=ch["geom_unused"] + ch["geom_interior"],
            context='VERTS',
            )
    bm.to_mesh(obj_c.data)

    # Second copy with the face dissolve
    obj_d = utils_scene.copy_objectRec(obj_c, context, keep_mods=False)
    obj_d.name = nameDissolved
    #MW_id_utils.setMetaType(obj_d, {"CHILD"})
    utils_scene.set_child(obj_d, obj)

    # dissolve faces based on angle limit
    try:
        bmesh.ops.dissolve_limit(bm, angle_limit=radians(1.7), use_dissolve_boundaries=True, verts=bm.verts, edges=bm.edges)
    except RuntimeError:
        import traceback
        traceback.print_exc()
    bm.to_mesh(obj_d.data)

    # Scene viewport
    utils_scene.hide_objectRec(obj_c)
    utils_scene.hide_objectRec(obj_d)

    bm.free()
    getStats().logDt("generated convex object")
    return obj_d

#-------------------------------------------------------------------

def gen_pointsObject(obj: types.Object, points: list[Vector], context: types.Context, name:str, reuse=False):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], [])
    #mesh.update()

    if reuse:   obj_points = utils_scene.gen_childReuse(obj, name, context, mesh, keepTrans=False)
    else:       obj_points = utils_scene.gen_child(obj, name, context, mesh, keepTrans=False)
    return obj_points

def gen_boundsObject(obj: types.Object, bb: list[Vector, 2], context: types.Context, name:str, reuse=False):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(bb, [], [])

    # Generate it taking the transform as it is (points already in local space)
    if reuse:   obj_bb = utils_scene.gen_childReuse(obj, name, context, mesh, keepTrans=False)
    else:       obj_bb = utils_scene.gen_child(obj, name, context, mesh, keepTrans=False)

    obj_bb.show_bounds = True
    return obj_bb

#-------------------------------------------------------------------

def gen_cellsObjects(fract: MW_Fract, root: types.Object, context: types.Context, scale = 1.0, flipN = False):
    prefs = getPrefs()
    prefs.names.fmt_setAmount(len(fract.cont.voro_cont))
    vis_cfg : MW_vis_cfg= root.mw_vis

    # create empty objects holding them (add empty data to )
    # NOTE:: cannot add materials to empty objects, yo just add some data (one for each, or they will share the material)
    root_cells = utils_scene.gen_child(root, prefs.names.cells, context, utils_mesh.getEmpty_curveData("empty-curve"), keepTrans=False)
    root_core = utils_scene.gen_child(root, prefs.names.cells_core, context, utils_mesh.getEmpty_curveData("empty-curve-core"), keepTrans=False)
    root_air = utils_scene.gen_child(root, prefs.names.cells_air, context, utils_mesh.getEmpty_curveData("empty-curve-air"), keepTrans=False)

    # create shared materials, will only asign one to the cells (initial state is solid)
    mat_cells = utils_mat.get_colorMat(vis_cfg.cell_color, matName=prefs.names.fmt_mat(prefs.names.cells))
    root_cells.active_material = mat_cells
    mat_core = utils_mat.get_colorMat(vis_cfg.cell_color_core, matName=prefs.names.fmt_mat(prefs.names.cells_core))
    root_core.active_material = mat_core
    mat_air = utils_mat.get_colorMat(vis_cfg.cell_color_air, matName=prefs.names.fmt_mat(prefs.names.cells_air))
    root_air.active_material = mat_air

    cells = []
    for cell in fract.cont.voro_cont:
        # skip none cells (computation error)
        if cell is None: continue

        # name respect to the original point, better the internal cell?
        #source_id = cont.voro_cont.source_idx[cell.id]
        source_id = cell.id
        name= f"{prefs.names.cells[0]}{prefs.names.fmt_id(source_id)}"

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

        # create the object
        obj_cell = utils_scene.gen_child(root_cells, name, context, mesh, keepTrans=False)
        obj_cell.active_material = mat_cells
        cells.append(obj_cell)

        # postion afterwards
        obj_cell.location = pos
        obj_cell.scale = [scale]*3

    getStats().logDt("generated cells objects")
    return cells

def gen_cells_LEGACY(voro_cont: VORO_Container, root: types.Object, context: types.Context):
    root_cells = utils_scene.gen_child(root, getPrefs().names.cells, context, None, keepTrans=False)

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
        obj_shard = utils_scene.gen_child(root_cells, name, context, mesh, keepTrans=False)
        pass #breakpoint here to see stats

    getStats().logDt("generated LEGACY cells objects")

    numVerts = [ len(vs) for vs in vertices ]
    numFaces = [ len(fs) for fs in face_vertices ]

    import numpy as np
    stVolume = np.std(volume)
    stArea = np.std(surface_area)
    getStats().logDt("calculated stats (use breakpoints to see)")

def set_cellsState(fract: MW_Fract, root: types.Object, cells: list[types.Object], state:int):
    prefs = getPrefs()
    assert(state in STATE_ENUM.all)

    # take respective parent object
    if state == STATE_ENUM.SOLID:
        root_cells = utils_scene.get_child(root, prefs.names.cells)
    elif state == STATE_ENUM.CORE:
        root_cells = utils_scene.get_child(root, prefs.names.cells_core)
    elif state == STATE_ENUM.AIR:
        root_cells = utils_scene.get_child(root, prefs.names.cells_air)

    for cell in cells:
        # some selection could be an outside obj or a cell from other fract!
        if not MW_id_utils.hasCellId(cell): continue
        if not MW_id_utils.sameStorageId(root, cell): continue

        # set the state and the parent (also the same mat as the parent)
        fract.cont.cells_state[cell.mw_id.cell_id] = state
        cell.mw_id.cell_state = state
        cell.active_material = root_cells.active_material
        cell.parent = root_cells

#-------------------------------------------------------------------

def gen_linksMesh(fract: MW_Fract, root: types.Object, context: types.Context):
    vis_cfg : MW_vis_cfg= root.mw_vis
    name = getPrefs().names.links
    baseColor = utils_mat.COLORS.red

    # some undo could break it

    # iterate the global map and store vert pairs for the tube mesh generation
    verts: list[tuple[Vector,Vector]] = []
    lifeWidths: list[float] = []
    lifeColor: list[Vector] = []
    points: list[Vector] = []
    for l in fract.links.internal:
        life = l.life_clamped

        k1, k2 = l.key_cells
        kf1, kf2 = l.key_faces
        c1 = fract.cont.cells_objs[k1]
        f1 = fract.cont.getFaces(k1,kf1)
        c2 = fract.cont.cells_objs[k2]
        f2 = fract.cont.getFaces(k2,kf2)

        # TODO:: avoid p1 p2 being equial

        p1 = c1.matrix_world @ f1.center
        p2 = c2.matrix_world @ f2.center
        verts.append((p1, p2))

        # original center
        points.append(l.pos)

        #verts.append((l.pos-l.dir*vis_cfg.links_depth, l.pos+l.dir*vis_cfg.links_depth))
        lifeColor.append( (baseColor*life).to_4d() )
        #lifeColor[-1].w = 0.5

        if vis_cfg.links_widthModLife == {"UNIFORM"}:
            lifeWidths.append(vis_cfg.links_widthDead * (1-life) + vis_cfg.links_width * life)
        elif vis_cfg.links_widthModLife == {"BINARY"}:
            lifeWidths.append(vis_cfg.links_widthDead if life<1 else vis_cfg.links_width)

    resFaces = utils_mesh.get_resFaces_fromCurveRes(vis_cfg.debug_links_res)

    # single mesh with tubes
    mesh = utils_mesh.get_tubeMesh_pairsQuad(verts, lifeWidths, name, 1.0, resFaces, vis_cfg.links_smoothShade)
    # TODO:: delete prev

    # color encoded attributes for viewing in viewport edit mode
    utils_mat.gen_meshAttr(mesh, lifeColor, resFaces*2, "FLOAT_COLOR", "POINT", "life")

    # potentially reuse child
    obj_links = utils_scene.gen_childReuse(root, name, context, mesh, keepTrans=True)
    mesh.name = name

    # add points
    gen_pointsObject(root, points, context, getPrefs().names.links_points, reuse=True)

    MW_id_utils.setMetaType(obj_links, {"CHILD"}, childrenRec=False)
    getStats().logDt("generated links object")
    return obj_links

def gen_linksWallObject(fract: MW_Fract, root: types.Object, context: types.Context, weights : list[float] = None):
    vis_cfg : MW_vis_cfg= root.mw_vis
    name = getPrefs().names.links_air
    wallsExtraScale = vis_cfg.links_wallExtraScale

    # iterate the global map and store vert pairs for the tube mesh generation
    verts: list[tuple[Vector,Vector]] = []
    lifeWidth: list[float] = []
    for i,l in enumerate(fract.links.external):
        #DEV.log_msg(f"life {l.life}")

        # skip drawing entry links with no probability
        #if weights and weights[i] == 0: continue

        # WIP:: also skip drawing non picked?
        if not l.picks: continue

        lifeWidth.append(vis_cfg.links_width*wallsExtraScale*l.life)
        verts.append((l.pos, l.pos+l.dir*vis_cfg.links_depth))

    resFaces = utils_mesh.get_resFaces_fromCurveRes(vis_cfg.debug_links_res)
    mesh = utils_mesh.get_tubeMesh_pairsQuad(verts, lifeWidth, name, 1+vis_cfg.links_width*wallsExtraScale, resFaces, vis_cfg.links_smoothShade)

    # potentially reuse child
    obj_wallLinks = utils_scene.gen_childReuse(root, name, context, mesh, keepTrans=True)
    mesh.name = name

    # set global material
    color = utils_mat.COLORS.blue+utils_mat.COLORS.white * 0.33
    wallsMat = utils_mat.get_colorMat(color, "linkWallsMat")
    obj_wallLinks.active_material = wallsMat

    # WIP:: additional attr to visualize in the ame view mode
    utils_mat.gen_meshAttr(mesh, color, 1, "FLOAT_COLOR", "POINT", "blueColor")

    MW_id_utils.setMetaType(obj_wallLinks, {"CHILD"}, childrenRec=False)
    getStats().logDt("generated wall links object")
    return obj_wallLinks

#-------------------------------------------------------------------

def genWIP_linksObjects(objLinks: types.Object, objWall: types.Object, links: MW_Links, context: types.Context):
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
            res = (prefs.prop_links_res+1) +2
            #res = prefs.prop_links_res
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
            res = prefs.prop_links_res
            width = prefs.links_widthDead * (1-l.life) + prefs.links_width * l.life
            color = utils_mat.COLORS.red.copy() *l.life
            #alpha = l.life+0.1 if prefs.links_matAlpha else 1.0
            #color.w = alpha
            mat = utils_mat.get_colorMat(color, name)

        res = utils_mesh.get_resFaces_fromCurveRes(res)
        curve= utils_mesh.get_tubeMesh_pairsQuad([(p1, p2)], None, name, width, res)
        obj_link = utils_scene.gen_child(obj, name, context, curve, keepTrans=True)
        obj_link.location = l.pos
        obj_link.active_material = mat

    MW_id_utils.setMetaType(objLinks.parent, {"CHILD"}, skipParent=True)
    getStats().logDt("generated links to walls objects")

def genWIP_linksCellObjects(objParent: types.Object, voro_cont: VORO_Container, context: types.Context):
    prefs = getPrefs()
    prefs.names.fmt_setAmount(len(voro_cont))

    # WIP:: links better generated from map isntead of cont? + done in a separate op
    # WIP:: atm just hiding reps -> maybe generate using a different map instead of iterating the raw cont
    #   maybe merge cell/link loop
    neigh_set = set()

    for cell in voro_cont:
        # NOTE:: in the case of directly iterating the cont there could be missing ones
        if cell is None: continue

        # group the links by cell using a parent
        nameGroup= f"{getPrefs().names.links_group}_{prefs.names.fmt_id(cell.id)}"
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

            curve = utils_mesh.get_curveData([cell_centroid, neigh_centroid], name, prefs.links_width, prefs.prop_links_res)
            obj_link = utils_scene.gen_child(obj_group, name, context, curve, keepTrans=False)

            obj_link.hide_set(key_rep)
            #obj_link.location = cell.centroid()

    MW_id_utils.setMetaType(objParent, {"CHILD"}, skipParent=False)
    getStats().logDt("generated links per cell objects")