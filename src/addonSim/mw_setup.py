import bpy
import bpy.types as types
import bmesh
from mathutils import Vector, Matrix
from math import radians

from .preferences import getPrefs
from .properties_global import (
    MW_id, MW_id_utils, MW_global_selected
)
from .properties import (
    MW_gen_cfg,
    MW_vis_cfg,
)

from .mw_cont import MW_Cont, VORO_Container, CELL_STATE_ENUM
from .mw_links import MW_Links
from .mw_fract import MW_Fract, MW_Sim # could import all from here
from .mw_resistance import MW_field_R

from . import utils, utils_scene, utils_trans, utils_mat, utils_mesh
from . import sv_geom_primitives
from .utils_mat import GRADIENTS, COLORS
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
    #MW_id_utils.setMetaType_rec(obj_copy, {"CHILD"})

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

def copy_convex(obj: types.Object, obj_copy: types.Object, context: types.Context, nameConvex:str, nameDissolved:str, angleRad = 10):
    """ Make a copy and find its convex hull
        # NOTE:: not recursive! but copies the child objects too
    """

    # Duplicate again the copy and set child too
    obj_c = utils_scene.copy_objectRec(obj_copy, context, keep_mods=False)
    obj_c.name = nameConvex
    #MW_id_utils.setMetaType_rec(obj_c, {"CHILD"})
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
    #MW_id_utils.setMetaType_rec(obj_d, {"CHILD"})
    utils_scene.set_child(obj_d, obj)

    # dissolve faces based on angle limit
    try:
        bmesh.ops.dissolve_limit(bm, angle_limit=radians(angleRad), use_dissolve_boundaries=True, verts=bm.verts, edges=bm.edges)
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

def gen_pointsObject(obj: types.Object, points: list[Vector], context: types.Context, name:str, reuse=True):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], [])
    #mesh.update()

    if reuse:   obj_points = utils_scene.gen_childReuse(obj, name, context, mesh, keepTrans=False)
    else:       obj_points = utils_scene.gen_child(obj, name, context, mesh, keepTrans=False)
    return obj_points

def gen_boundsObject(obj: types.Object, bb: list[Vector, 2], context: types.Context, name:str, reuse=True):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(bb, [], [])

    # Generate it taking the transform as it is (points already in local space)
    if reuse:   obj_bb = utils_scene.gen_childReuse(obj, name, context, mesh, keepTrans=False)
    else:       obj_bb = utils_scene.gen_child(obj, name, context, mesh, keepTrans=False)

    obj_bb.show_bounds = True
    return obj_bb

def gen_arrowObject(obj: types.Object, vdir:Vector, pos:Vector, context: types.Context, name:str, reuse=True):
    if reuse:
        find = utils_scene.get_object_fromScene(context.scene, name)
        if find:
            utils_scene.delete_object(find)

    obj_arrow = utils_scene.getEmpty_arrowDir(context, vdir, pos, scale=2.0, name=name)
    utils_scene.set_child(obj_arrow, obj)
    return obj_arrow

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

def set_cellsState(cont: MW_Cont, root: types.Object, cells: list[types.Object], state:int):
    prefs = getPrefs()
    assert(state in CELL_STATE_ENUM.all)

    # take respective parent object
    if state == CELL_STATE_ENUM.SOLID:
        root_cells = utils_scene.get_child(root, prefs.names.cells)
    elif state == CELL_STATE_ENUM.CORE:
        root_cells = utils_scene.get_child(root, prefs.names.cells_core)
    elif state == CELL_STATE_ENUM.AIR:
        root_cells = utils_scene.get_child(root, prefs.names.cells_air)

    cells_id = []
    for cell in cells:
        # some selection could be an outside obj or a cell from other fract!
        if not MW_id_utils.hasCellId(cell): continue
        if not MW_id_utils.sameStorageId(root, cell): continue

        # set the state and the parent (also the same mat as the parent)
        cont.setCell_state(cell.mw_id.cell_id, state)
        #fract.cont.cells_state[cell.mw_id.cell_id] = state
        #cell.mw_id.cell_state = state
        cell.active_material = root_cells.active_material
        cell.parent = root_cells

        cells_id.append(cell.mw_id.cell_id)
    return cells_id

def update_cellsState(cont: MW_Cont, root: types.Object):
    prefs = getPrefs()

    # take respective parent object
    root_cells = utils_scene.get_child(root, prefs.names.cells)
    root_core = utils_scene.get_child(root, prefs.names.cells_core)
    root_air = utils_scene.get_child(root, prefs.names.cells_air)

    # iterate just the valid ones
    ok, broken, error = cont.getCells_splitID_needsSanitize()
    for idx in ok:
        cell = cont.cells_objs[idx]
        state = cell.mw_id.cell_state

        # shift material and parent
        if state == CELL_STATE_ENUM.SOLID:
            cell.active_material = root_cells.active_material
            cell.parent = root_cells
        elif state == CELL_STATE_ENUM.CORE:
            cell.active_material = root_core.active_material
            cell.parent = root_core
        elif state == CELL_STATE_ENUM.AIR:
            cell.active_material = root_air.active_material
            cell.parent = root_air


#-------------------------------------------------------------------

DEV.RELOAD_FLAGS["rnd_links"] = False

def gen_linksAll(context: types.Context):

    # regenerate the mesh
    gen_linksMesh(MW_global_selected.fract, MW_global_selected.root, context)
    gen_linksMesh_air(MW_global_selected.fract, MW_global_selected.root, context)
    if DEV.DEBUG_LINKS_NEIGHS:
        gen_linksMesh_neighs(MW_global_selected.fract, MW_global_selected.root, context)

    # additional arrows
    #gen_arrowObject(MW_global_selected.root, MW_global_selected.root.mw_sim.water_entry_dir,
    #                            utils_trans.VECTORS.O, context, getPrefs().names.links_waterDir)

def gen_linksMesh(fract: MW_Fract, root: types.Object, context: types.Context):
    prefs = getPrefs()
    cfg : MW_vis_cfg = root.mw_vis
    sim : MW_Sim     = MW_global_selected.fract.sim

    if DEV.RELOAD_FLAGS_check("rnd_links"):
        sim.reset_links_rnd()
        #sim.reset_links(0.1, 8)

    # NOTE:: some just used to create some vis, so disabled for final implementation
    numLinks = len(fract.links.internal)
    points       : list[Vector]               = [None]*numLinks
    verts        : list[tuple[Vector,Vector]] = [None]*numLinks
    id_life      : list[tuple[int,float]]     = [None]*numLinks
    lifeWidths   : list[float]                = [None]*numLinks
    #id_picks     : list[tuple[int,int]]       = [None]*numLinks
    #id_resist    : list[tuple[int,float]]     = [None]*numLinks
    #dirX_dirZ    : list[tuple[float,float]]   = [None]*numLinks
    #id_area      : list[tuple[int,float]]     = [None]*numLinks

    if DEV.DEBUG_LINKS_GEODATA:
        k1_k2 : list[tuple[int,int]]          = []
        f1_f2 : list[tuple[int,int]]          = []

    # iterate the global map and store vert pairs for the tube mesh generation
    for id, l in enumerate(fract.links.internal):
        id_normalized = id / float(numLinks)

        # original center
        points[id]= l.pos

        # point from face to face
        k1, k2 = l.key_cells
        kf1, kf2 = l.key_faces
        c1 = fract.cont.cells_objs[k1]
        f1 = fract.cont.getFaces(k1,kf1)
        c2 = fract.cont.cells_objs[k2]
        f2 = fract.cont.getFaces(k2,kf2)
        p1 = c1.matrix_world @ f1.center
        p2 = c2.matrix_world @ f2.center

        # pick a valid normal
        pdir : Vector= p2-p1
        if utils_trans.almostNull(pdir):
            pdir = f1.normal
        else:
            pdir.normalize()

        # add a bit of additional depth
        p1 -= pdir*cfg.links_depth*0.5
        p2 += pdir*cfg.links_depth*0.5
        verts[id]= (p1, p2)

        # lerp the width
        life = l.life_clamped
        if cfg.links_width__mode == {"UNIFORM"}:
            lifeWidths[id]= cfg.links_width_broken * (1-life) + cfg.links_width_base * life
        elif cfg.links_width__mode == {"BINARY"}:
            lifeWidths[id]= cfg.links_width_broken if life<1 else cfg.links_width_base

        # query props
        id_life[id]= (id_normalized, life)
        #id_picks[id]= (id_normalized, l.picks)
        #id_resist[id]= (id_normalized, l.resistance)
        #dirX_dirZ[id]=(abs(pdir.x), abs(pdir.z))
        #id_area[id] = (id_normalized, (l.area-fract.links.min_area) / (fract.links.max_area-fract.links.min_area))

        # query info keys
        if DEV.DEBUG_LINKS_GEODATA:
            k1_k2.append(l.key_cells)
            f1_f2.append(l.key_faces)

    # single mesh with tubes
    name = prefs.names.links
    resFaces = utils_mesh.get_resFaces_fromCurveRes(cfg.links_res)
    mesh = utils_mesh.get_tubeMesh_pairsQuad(verts, lifeWidths, name, 1.0, resFaces, cfg.links_smoothShade)

    # potentially reuse child and clean mesh
    obj_links = utils_scene.gen_childReuse(root, name, context, mesh, keepTrans=True)
    MW_id_utils.setMetaChild(obj_links)

    # color encoded attributes for viewing in viewport edit mode
    repMatchCorners=resFaces*4
    utils_mat.gen_meshUV(mesh, id_life, "id_life", repMatchCorners)
    obj_links.active_material = utils_mat.gen_gradientMat("id_life", name, colorFn=GRADIENTS.red)
    obj_links.active_material.diffuse_color = COLORS.red

    # NOTE:: additional props -> to visualize seems like setting UV map in texture node is not enough, requires active UV too
    #utils_mat.gen_meshUV(mesh, id_picks, "id_picks", repMatchCorners)
    #utils_mat.gen_meshUV(mesh, id_resist, "id_resist", repMatchCorners)
    #obj_links.active_material = utils_mat.gen_gradientMat("id_resist", name+"_R", colorFn=GRADIENTS.lerp_common(COLORS.warm))
    #utils_mat.gen_meshUV(mesh, dirX_dirZ, "dirX_dirZ", repMatchCorners)
    #obj_links.active_material = utils_mat.gen_textureMat("dirX_dirZ", name+"_dir", colorFn=GRADIENTS.red_2D_green) #red_2D_blue
    #utils_mat.gen_meshUV(mesh, id_area, "id_area", repMatchCorners)
    #obj_links.active_material = utils_mat.gen_gradientMat("id_area", name+"_area", colorFn=GRADIENTS.lerp_common(COLORS.red, COLORS.white_cw))

    if DEV.DEBUG_LINKS_GEODATA:
        utils_mat.gen_meshUV(mesh, k1_k2, "k1_k2", repMatchCorners)
        utils_mat.gen_meshUV(mesh, f1_f2, "f1_f2", repMatchCorners)

    # add points object too
    obj_points = gen_pointsObject(root, points, context, prefs.names.links_points, reuse=True)
    MW_id_utils.setMetaChild(obj_points)

    getStats().logDt("generated internal links mesh object")
    return obj_links

def gen_linksMesh_air(fract: MW_Fract, root: types.Object, context: types.Context):
    prefs = getPrefs()
    cfg : MW_vis_cfg = root.mw_vis
    sim : MW_Sim     = MW_global_selected.fract.sim

    # NOTE:: some just used to create some vis, so disabled for final implementation
    numLinks = len(fract.links.external) # not sized cause some may be skipped
    verts      : list[tuple[Vector,Vector]]   = []
    verts_entry  : list[tuple[Vector,Vector]] = []
    id_prob    : list[tuple[int,float]]       = []
    #id_picks   : list[tuple[int,int]]         = []
    #id_entries : list[tuple[int,int]]         = []
    #dirX_dirZ    : list[tuple[float,float]]   = [None]*numLinks

    if DEV.DEBUG_LINKS_GEODATA:
        k1_k2 : list[tuple[int,int]]          = []
        f1_f2 : list[tuple[int,int]]          = []

    # max prob for normalizeing probabilty
    probs = [ sim.get_entryWeight(l) for l in fract.links.external ]
    probsMax = max(probs) if probs else 1
    if probsMax == 0: probsMax = 1
    #probsMax = fract.links.max_area # visualize area instead

    # two bars so half the w
    w2 = cfg.wall_links_width_base * 0.5

    # iterate the global map and store vert pairs for the tube mesh generation
    for id, l in enumerate(fract.links.external):
        #if MW_Links.skip_link_debugModel(l): continue # just not generated
        id_normalized = id / float(numLinks)

        # represent picks with point from original global pos + normal + offset a bit
        perp = utils_trans.getPerpendicular_stable(l.dir)
        p1 = l.pos - perp * w2
        p2 = p1 + l.dir * (cfg.wall_links_depth_base + l.picks * cfg.wall_links_depth_incr)
        verts.append((p1, p2))

        # query props
        #id_picks.append((id_normalized, l.picks))

        # query info keys
        if DEV.DEBUG_LINKS_GEODATA:
            k1_k2.append(l.key_cells)
            f1_f2.append(l.key_faces)

        # check non prob for entry links visualization
        prob = sim.get_entryWeight(l)
        #prob = l.area+fract.links.min_area
        #prob = 1
        if not sim.cfg.link_entry_visAll and prob == 0:
            continue

        # represent entry picks similarly
        p1 = l.pos + perp * w2
        p2 = p1 + l.dir * (cfg.wall_links_depth_base + l.picks_entry * cfg.wall_links_depth_incr)
        verts_entry.append((p1, p2))

        # also store more props
        prob_normalized = prob / probsMax
        id_prob.append((id_normalized, prob_normalized))
        #id_entries.append((id_normalized, l.picks_entry))
        #dirX_dirZ[id]=(abs(l.dir.x), abs(l.dir.z))

    # two mesh with tubes to represent entry picks / regular traverse picks
    resFaces = utils_mesh.get_resFaces_fromCurveRes(cfg.walls_links_res)
    name = prefs.names.links_air
    name_entry = prefs.names.links_air + "_entry"
    mesh = utils_mesh.get_tubeMesh_pairsQuad(verts, None, name, w2, resFaces, cfg.links_smoothShade)
    mesh_entry = utils_mesh.get_tubeMesh_pairsQuad(verts_entry, None, name_entry, w2, resFaces, cfg.links_smoothShade)

    # potentially reuse child and clean mesh
    obj_linksAir = utils_scene.gen_childReuse(root, name, context, mesh, keepTrans=True)
    obj_linksAir_entry = utils_scene.gen_childReuse(root, name_entry, context, mesh_entry, keepTrans=True)
    MW_id_utils.setMetaChild(obj_linksAir)
    MW_id_utils.setMetaChild(obj_linksAir_entry)

    # color encoded attributes for viewing in viewport edit mode
    obj_linksAir.active_material = utils_mat.get_colorMat(COLORS.blue, name)
    obj_linksAir.active_material.diffuse_color = COLORS.blue
    # entries have encoded the probabilty
    repMatchCorners=resFaces*4
    utils_mat.gen_meshUV(mesh_entry, id_prob, "id_prob", repMatchCorners)
    obj_linksAir_entry.active_material = utils_mat.gen_gradientMat("id_prob", name_entry, colorFn=GRADIENTS.lerp_common(COLORS.red, COLORS.white_cw))
    obj_linksAir_entry.active_material.diffuse_color = COLORS.white_cw

    # NOTE:: additional props -> to visualize seems like setting UV map in texture node is not enough, requires active UV too
    #utils_mat.gen_meshUV(mesh, id_picks, "id_picks", repMatchCorners)
    #utils_mat.gen_meshUV(mesh_entry, id_entries, "id_entries", repMatchCorners)
    #utils_mat.gen_meshUV(mesh_entry, dirX_dirZ, "dirX_dirZ", repMatchCorners)
    #obj_linksAir_entry.active_material = utils_mat.gen_textureMat("dirX_dirZ", name+"_dir", colorFn=GRADIENTS.red_2D_green) #red_2D_blue

    if DEV.DEBUG_LINKS_GEODATA:
        utils_mat.gen_meshUV(mesh, k1_k2, "k1_k2", repMatchCorners)
        utils_mat.gen_meshUV(mesh, f1_f2, "f1_f2", repMatchCorners)

    getStats().logDt("generated external links mesh object")
    return obj_linksAir, obj_linksAir_entry

def gen_linksMesh_neighs(fract: MW_Fract, root: types.Object, context: types.Context):
    prefs = getPrefs()
    cfg : MW_vis_cfg = root.mw_vis
    sim : MW_Sim     = MW_global_selected.fract.sim

    numLinks = len(fract.links.internal+fract.links.external) # not sized cause some may be skipped
    verts     : list[tuple[Vector,Vector]] = []
    id_grav   : list[tuple[int,float]]     = []

    if DEV.DEBUG_LINKS_GEODATA:
        l1k1_l1k2 : list[tuple[int,int]]       = []
        l1f1_l1f2 : list[tuple[int,int]]       = []
        l2k1_l2k2 : list[tuple[int,int]]       = []
        l2f1_l2f2 : list[tuple[int,int]]       = []

    # avoid repetitions
    checked = set()

    # iterate the global map and store vert pairs for the tube mesh generation
    for id, l in enumerate(fract.links.internal+fract.links.external):
        id_normalized = id / float(numLinks)

        # allow once from outer loop
        checked.add(l.key_cells)
        for ln in fract.links.get_link_neighs(l.key_cells):
            if ln.key_cells in checked: continue

            # point from links
            p1 = l.pos
            p2 = ln.pos
            verts.append((p1, p2))

            # grav mod
            g = sim.get_nextAlign( (p1-p2).normalized(), bothDir=True)
            id_grav.append((id_normalized, g))

            # query info keys
            if DEV.DEBUG_LINKS_GEODATA:
                l1k1_l1k2.append(l.key_cells)
                l1f1_l1f2.append(l.key_faces)
                l2k1_l2k2.append(ln.key_cells)
                l2f1_l2f2.append(ln.key_faces)

    # single mesh with tubes
    name = prefs.names.links_neighs
    resFaces = utils_mesh.get_resFaces_fromCurveRes(-1)
    mesh = utils_mesh.get_tubeMesh_pairsQuad(verts, None, name, cfg.neigh_links_width, resFaces, cfg.links_smoothShade)

    # potentially reuse child and clean mesh
    obj_neighs = utils_scene.gen_childReuse(root, name, context, mesh, keepTrans=True)
    MW_id_utils.setMetaChild(obj_neighs)

    # color encoded attributes for viewing in viewport edit mode
    repMatchCorners=resFaces*4
    utils_mat.gen_meshUV(mesh, id_grav, "id_grav", repMatchCorners)
    obj_neighs.active_material = utils_mat.gen_gradientMat("id_grav", name, colorFn=GRADIENTS.lerp_common(COLORS.green))
    obj_neighs.active_material.diffuse_color = COLORS.green

    if DEV.DEBUG_LINKS_GEODATA:
        utils_mat.gen_meshUV(mesh, l1k1_l1k2, "l1k1_l1k2", repMatchCorners)
        utils_mat.gen_meshUV(mesh, l1f1_l1f2, "l1f1_l1f2", repMatchCorners)
        utils_mat.gen_meshUV(mesh, l2k1_l2k2, "l2k1_l2k2", repMatchCorners)
        utils_mat.gen_meshUV(mesh, l2f1_l2f2, "l2f1_l2f2", repMatchCorners)

    getStats().logDt("generated neighs links mesh object")
    return obj_neighs

def gen_links_LEGACY(objParent: types.Object, voro_cont: VORO_Container, context: types.Context):
    prefs = getPrefs()
    prefs.names.fmt_setAmount(len(voro_cont))

    # will detect repeated and hide one of each pair, but add to the scene to have the info
    neigh_set = set()

    for cell in voro_cont:
        if cell is None: continue

        # group the links by cell using a parent
        nameGroup= f"{getPrefs().names.links_group}_{prefs.names.fmt_id(cell.id)}"
        obj_group = utils_scene.gen_child(objParent, nameGroup, context, None, keepTrans=False, hide=False)
        #obj_group.matrix_world = Matrix.Identity(4)
        #obj_group.location = cell.centroid()

        cell_centroid = Vector(cell.centroid())

        # iterate the cell neighbours
        neigh = cell.neighbors()
        for n_id in neigh:
            # wall link
            if n_id < 0:
                name= f"s{cell.id}_w{-n_id}"
                obj_link = utils_scene.gen_child(obj_group, name, context, None, keepTrans=False)
                continue

            # potential assymetries
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

    MW_id_utils.setMetaType_rec(objParent, {"CHILD"}, skipParent=False)
    getStats().logDt("generated legacy links per cell objects")

#-------------------------------------------------------------------

def gen_field_R(root: types.Object, context: types.Context, res = 8):
    """ Generate or reuse a grid mesh and texture to vis the field. res ==-1 reuse whatever available """
    name = getPrefs().names.fielt_resist
    regen = False

    # check reuse and update existing obj + mesh
    obj_field = utils_scene.get_child(root, name)
    if obj_field and obj_field.data:
        mesh = obj_field.data
        prev_res = mesh["res"]
        if res != prev_res and res != -1:
            regen = True
    else:
        regen = True
        assert(res != -1)

    # potential regen including the object (deletes mat, mesh, etc)
    if regen:
        mesh = gen_field_mesh(res, name)
        utils_mat.gen_meshUV(mesh, name="id_resist")
        obj_field = utils_scene.gen_childReuse(root, name, context, mesh, keepTrans=True)
        MW_id_utils.setMetaChild(obj_field)

        # size of the image depends on resolution used
        resX = mesh["resX"]
        resZ = mesh["resZ"]
        # basic linear gradient material
        obj_field.active_material = utils_mat.gen_gradientMat("id_resist", name, resX, resZ, colorFn=GRADIENTS.lerp_common(COLORS.warm))
        obj_field.active_material.diffuse_color = utils_mat.COLORS.warm

    # Encode resistance in world pos as UV and use texture for vis
    numCornerVerts = len(mesh.loops)
    id_resist : list[tuple[int,float]]     = [None]*numCornerVerts
    mToWorld = obj_field.matrix_world
    for id, l in enumerate(mesh.loops):
        id_normalized = id / float(numCornerVerts)
        v = mToWorld @ mesh.vertices[l.vertex_index].co
        id_resist[id]= (id_normalized, MW_field_R.get2D(v.x, v.z))

    # reset instead of creating!
    utils_mat.set_meshUV(mesh, mesh.uv_layers.get("id_resist"), id_resist)

def gen_field_mesh(res = 8, name="grid"):
    """ Generate a grid plane mesh, stores res, resX, resZ used as custom props """
    sizeX = 20 # Aprox size for DEBUG_MODEL
    sizeZ = 10
    rot = Matrix.Rotation(radians(-90), 4, "X")
    trans =  rot @ Matrix.Translation(Vector([0.5, -4, 0.5])) # relative to original axis
    #trans = rot

    # util grid from SV +fixes
    resX = int(res*sizeX)
    resZ = int(res*sizeZ)
    mesh = bpy.data.meshes.new(name)
    verts, edges, faces = sv_geom_primitives.grid(sizeX,sizeZ, resX,resZ)

    # points direclty in world space
    utils_trans.transform_points(verts, trans)
    mesh.from_pydata(verts, edges, faces)

    # store the resolution used
    mesh["res"] = res
    mesh["resX"] = resX
    mesh["resZ"] = resZ
    return mesh