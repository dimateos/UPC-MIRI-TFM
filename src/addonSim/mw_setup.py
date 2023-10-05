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
    MW_sim_cfg,
    MW_vis_cfg,
)

from .mw_cont import MW_Cont, VORO_Container, CELL_STATE_ENUM, CELL_ERROR_ENUM
from .mw_links import MW_Links
from .mw_sim import MW_Sim, SIM_EXIT_FLAG
from .mw_fract import MW_Fract # could import all from here
from .mw_resistance import field_R_current

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

def gen_pointsObject(obj: types.Object, points: list[Vector], context: types.Context, name:str, reuse=True, keepTrans=False):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], [])
    #mesh.update()

    if reuse:   obj_points = utils_scene.gen_childReuse(obj, name, context, mesh, keepTrans=keepTrans)
    else:       obj_points = utils_scene.gen_child(obj, name, context, mesh, keepTrans=keepTrans)
    return obj_points

def gen_boundsObject(obj: types.Object, bb: list[Vector, 2], context: types.Context, name:str, reuse=True, keepTrans=False):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(bb, [], [])

    # Generate it taking the transform as it is (points already in local space)
    if reuse:   obj_bb = utils_scene.gen_childReuse(obj, name, context, mesh, keepTrans=keepTrans)
    else:       obj_bb = utils_scene.gen_child(obj, name, context, mesh, keepTrans=keepTrans)

    obj_bb.show_bounds = True
    return obj_bb

def gen_arrowObject(obj: types.Object, vdir:Vector, pos:Vector, context: types.Context, name:str, scale=1.0, reuse=True):
    # in this case just delete the child object
    if reuse: utils_scene.delete_objectChild(obj, name)

    obj_arrow = utils_scene.getEmpty_arrowDir(context, vdir, pos, scale=2.0, name=name)
    utils_scene.set_child(obj_arrow, obj)
    obj_arrow.scale = [scale]*3
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
    mat_cells = utils_mat.gen_colorMat(vis_cfg.cell_color, name=prefs.names.cells)
    root_cells.active_material = mat_cells
    mat_core = utils_mat.gen_colorMat(vis_cfg.cell_color_core, name=prefs.names.cells_core)
    root_core.active_material = mat_core
    mat_air = utils_mat.gen_colorMat(vis_cfg.cell_color_air, name=prefs.names.cells_air)
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
        if DEV.LEGACY_CONT_ASSERT:
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

def set_cellsState(cont: MW_Cont, root: types.Object, cells: list[types.Object], state:int, apply = True):
    """ Iterate selection and filter non cells or cells already as state, optionally apply state """
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
        # skip already set
        if state == cell.mw_id.cell_state: continue

        # list to return
        cells_id.append(cell.mw_id.cell_id)

        # set the parent and its mat
        cell.active_material = root_cells.active_material
        cell.parent = root_cells

        # actually change the internal state (potentially done by links backend to trigger more detachmensts instead)
        if apply:
            cont.setCell_state(cell.mw_id.cell_id, state)

    return cells_id

def update_cellsState(cont: MW_Cont, root: types.Object):
    """ Iterate all cells and update scene to match the internal state """
    prefs = getPrefs()

    # take respective parent object
    root_cells = utils_scene.get_child(root, prefs.names.cells)
    root_core = utils_scene.get_child(root, prefs.names.cells_core)
    root_air = utils_scene.get_child(root, prefs.names.cells_air)

    # iterate just the valid ones
    ok, broken, error = cont.getCells_splitID_needsSanitize()
    for idx in ok:
        cell = cont.cells_objs[idx]
        state = cont.cells_state[idx]
        #state = cell.mw_id.cell_state

        # shift material and parent
        if state == CELL_STATE_ENUM.SOLID:
            cell.active_material = root_cells.active_material
            cell.parent = root_cells
            cell.mw_id.cell_state = state
        elif state == CELL_STATE_ENUM.CORE:
            cell.active_material = root_core.active_material
            cell.parent = root_core
            cell.mw_id.cell_state = state
        elif state == CELL_STATE_ENUM.AIR:
            cell.active_material = root_air.active_material
            cell.parent = root_air
            cell.mw_id.cell_state = state

#-------------------------------------------------------------------

DEV.RELOAD_FLAGS["rnd_links"] = False

def gen_linksAll(context: types.Context):
    if not MW_global_selected.fract.links or not MW_global_selected.fract.links.initialized:
        return

    #vis_cfg : MW_vis_cfg = MW_global_selected.root.mw_vis
    vis_cfg : MW_vis_cfg = getPrefs().mw_vis

    # regenerate the mesh
    if vis_cfg.links__show:
        gen_linksMesh(MW_global_selected.fract, MW_global_selected.root, context)

    if vis_cfg.wall_links__show:
        gen_linksMesh_air(MW_global_selected.fract, MW_global_selected.root, context, vis_cfg.wall_links_show_picks)

    # inner links
    if vis_cfg.neighs__show:
        gen_linksMesh_neighs(MW_global_selected.fract, MW_global_selected.root, context)

    # additional last path
    if vis_cfg.path__show:
        if MW_global_selected.fract.sim and MW_global_selected.fract.sim.step_path:
            gen_linksMesh_path(MW_global_selected.fract, MW_global_selected.root, context, MW_global_selected.fract.sim.step_path)
        else:
            # delete all paths
            paths = utils_scene.get_child(MW_global_selected.root, getPrefs().names.water_paths)
            if paths: utils_scene.delete_objectRec(paths)

    # water dir
    if vis_cfg.water_dir__show:
        gen_arrow_dir(MW_global_selected.root, context)

def gen_linksDelete():
    prefs = getPrefs()
    links_ALL = utils_scene.get_children(MW_global_selected.root, prefs.names.links_ALL+prefs.names.water_ALL)
    for obj in links_ALL:
        if obj:
            utils_scene.delete_object(obj)
    getStats().logDt("deleted all links mesh")

def gen_linksMesh(fract: MW_Fract, root: types.Object, context: types.Context):
    prefs = getPrefs()
    cfg : MW_vis_cfg = root.mw_vis
    sim : MW_Sim     = MW_global_selected.fract.sim

    #if DEV.RELOAD_FLAGS_check("rnd_links"):
    #    sim.state_reset_rnd()
    #    #sim.reset_links(0.1, 8)

    # NOTE:: some just used to create some vis, so disabled for final implementation
    numLinks = len(fract.links.internal)
    points       : list[Vector]               = [None]*numLinks
    verts        : list[tuple[Vector,Vector]] = [None]*numLinks
    id_life      : list[tuple[int,float]]     = [None]*numLinks
    lifeWidths   : list[float]                = [None]*numLinks
    #id_resist    : list[tuple[int,float]]     = [None]*numLinks
    #dirX_dirZ    : list[tuple[float,float]]   = [None]*numLinks
    #id_area      : list[tuple[int,float]]     = [None]*numLinks

    if DEV.DEBUG_GEODATA_PICKS:
        id_picks   : list[tuple[int,int]]     = [None]*numLinks
    if DEV.DEBUG_GEODATA:
        k1_k2 : list[tuple[int,int]]          = [None]*numLinks
        f1_f2 : list[tuple[int,int]]          = [None]*numLinks

    # iterate the global map and store vert pairs for the tube mesh generation
    for id, l in enumerate(fract.links.internal):
        id_normalized = id / float(numLinks) if not DEV.DEBUG_GEODATA_ID_RAW else id

        # original center
        points[id]= l.pos

        # point from face to face
        p1,p2 = fract.cont.getFaces_pos(l.key_cells, l.key_faces)

        # pick a valid normal
        pdir : Vector= p2-p1
        if utils_trans.almostNull(pdir):
            pdir = l.dir
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
        #id_resist[id]= (id_normalized, l.resistance)
        #dirX_dirZ[id]=(abs(pdir.x), abs(pdir.z))
        #id_area[id] = (id_normalized, (l.area-fract.links.min_area) / (fract.links.max_area-fract.links.min_area))

        if DEV.DEBUG_GEODATA_PICKS:
            id_picks[id]= (id_normalized, l.picks)
        # query info keys
        if DEV.DEBUG_GEODATA:
            k1_k2[id] = l.key_cells
            f1_f2[id] = l.key_faces

    # single mesh with tubes
    name = prefs.names.links
    resFaces = utils_mesh.get_resFaces_fromCurveRes(cfg.wall_links_res)
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
    #utils_mat.gen_meshUV(mesh, id_resist, "id_resist", repMatchCorners)
    #obj_links.active_material = utils_mat.gen_gradientMat("id_resist", name+"_R", colorFn=GRADIENTS.lerp_common(COLORS.warm))
    #utils_mat.gen_meshUV(mesh, dirX_dirZ, "dirX_dirZ", repMatchCorners)
    #obj_links.active_material = utils_mat.gen_textureMat("dirX_dirZ", name+"_dir", colorFn=GRADIENTS.red_2D_green) #red_2D_blue
    #utils_mat.gen_meshUV(mesh, id_area, "id_area", repMatchCorners)
    #obj_links.active_material = utils_mat.gen_gradientMat("id_area", name+"_area", colorFn=GRADIENTS.lerp_common(COLORS.red, COLORS.white_cw))

    if DEV.DEBUG_GEODATA_PICKS:
        utils_mat.gen_meshUV(mesh, id_picks, "id_picks", repMatchCorners)
    if DEV.DEBUG_GEODATA:
        utils_mat.gen_meshUV(mesh, k1_k2, "k1_k2", repMatchCorners)
        utils_mat.gen_meshUV(mesh, f1_f2, "f1_f2", repMatchCorners)

    # add points object too
    obj_points = gen_pointsObject(root, points, context, prefs.names.links_points, reuse=True, keepTrans=True)
    utils_scene.hide_objectRec(obj_points, prefs.mw_vis.links_hide_points)
    MW_id_utils.setMetaChild(obj_points)

    getStats().logDt("generated internal links mesh object")
    return obj_links

def gen_linksMesh_air(fract: MW_Fract, root: types.Object, context: types.Context, picksToo = False):
    prefs = getPrefs()
    cfg : MW_vis_cfg = root.mw_vis
    sim : MW_Sim     = MW_global_selected.fract.sim

    # NOTE:: some just used to create some vis, so disabled for final implementation
    numLinks = len(fract.links.external) # not sized cause some may be skipped
    verts      : list[tuple[Vector,Vector]]   = []
    verts_entry  : list[tuple[Vector,Vector]] = []
    id_prob    : list[tuple[int,float]]       = []
    #dirX_dirZ    : list[tuple[float,float]]   = [None]*numLinks

    if DEV.DEBUG_GEODATA_PICKS:
        id_picks   : list[tuple[int,int]]     = []
        id_entries : list[tuple[int,int]]     = []
    if DEV.DEBUG_GEODATA:
        k1_k2 : list[tuple[int,int]]          = []
        f1_f2 : list[tuple[int,int]]          = []

    # max prob for normalizeing probabilty
    probs = [ sim.get_entryProbability(l) for l in fract.links.external ]
    probsMax = max(probs) if probs else 1
    if probsMax == 0: probsMax = 1
    #probsMax = fract.links.max_area # visualize area instead

    # two bars so half the w
    w2 = cfg.wall_links_width_base * 0.5

    # iterate the global map and store vert pairs for the tube mesh generation
    for id, l in enumerate(fract.links.external):
        #if MW_Links.skip_link_debugModel(l): continue # just not generated
        id_normalized = id / float(numLinks) if not DEV.DEBUG_GEODATA_ID_RAW else id

        # represent picks with point from original global pos + normal + offset a bit
        perp = utils_trans.getPerpendicular_stable(l.dir)
        p1 = l.pos - perp * w2
        p2 = p1 + l.dir * (cfg.wall_links_depth_base + l.picks * cfg.wall_links_depth_incr)
        verts.append((p1, p2))

        # query props
        if DEV.DEBUG_GEODATA_PICKS:
            id_picks.append((id_normalized, l.picks))
        # query info keys
        if DEV.DEBUG_GEODATA:
            k1_k2.append(l.key_cells)
            f1_f2.append(l.key_faces)

        # check non prob for entry links visualization
        prob = sim.get_entryProbability(l)
        #prob = l.area+fract.links.min_area
        #prob = 1
        if prob == 0 and not DEV.DEBUG_UNREACH_ENTRY:
            continue

        # represent entry picks similarly
        p1 = l.pos + perp * w2
        p2 = p1 + l.dir * (cfg.wall_links_depth_base + l.picks_entry * cfg.wall_links_depth_incr)
        verts_entry.append((p1, p2))

        # also store more props
        prob_normalized = prob / probsMax
        id_prob.append((id_normalized, prob_normalized))
        if DEV.DEBUG_GEODATA_PICKS:
            id_entries.append((id_normalized, l.picks_entry))
        #dirX_dirZ[id]=(abs(l.dir.x), abs(l.dir.z))

    # two mesh with tubes to represent entry picks / regular traverse picks
    resFaces = utils_mesh.get_resFaces_fromCurveRes(cfg.wall_links_res)
    name_entry = prefs.names.links_air_entry
    mesh_entry = utils_mesh.get_tubeMesh_pairsQuad(verts_entry, None, name_entry, w2, resFaces, cfg.links_smoothShade)

    # potentially reuse child and clean mesh
    obj_linksAir_entry = utils_scene.gen_childReuse(root, name_entry, context, mesh_entry, keepTrans=True)
    MW_id_utils.setMetaChild(obj_linksAir_entry)

    # color encoded attributes for viewing in viewport edit mode
    repMatchCorners=resFaces*4
    utils_mat.gen_meshUV(mesh_entry, id_prob, "id_prob", repMatchCorners)
    utils_mat.gen_meshUV(mesh_entry, id_entries, "id_entries", repMatchCorners)
    obj_linksAir_entry.active_material = utils_mat.gen_gradientMat("id_prob", name_entry, colorFn=GRADIENTS.lerp_common(COLORS.pink))
    obj_linksAir_entry.active_material.diffuse_color = COLORS.pink

    # NOTE:: additional props -> to visualize seems like setting UV map in texture node is not enough, requires active UV too
    #utils_mat.gen_meshUV(mesh_entry, dirX_dirZ, "dirX_dirZ", repMatchCorners)
    #obj_linksAir_entry.active_material = utils_mat.gen_textureMat("dirX_dirZ", name_entry+"_dir", colorFn=GRADIENTS.red_2D_green) #red_2D_blue

    if DEV.DEBUG_GEODATA:
        utils_mat.gen_meshUV(mesh_entry, k1_k2, "k1_k2", repMatchCorners)
        utils_mat.gen_meshUV(mesh_entry, f1_f2, "f1_f2", repMatchCorners)

    obj_linksAir_picks = None
    if picksToo:
        # regen obj and mesh
        name_picks = prefs.names.links_air
        mesh_picks = utils_mesh.get_tubeMesh_pairsQuad(verts, None, name_picks, w2, resFaces, cfg.links_smoothShade)
        obj_linksAir_picks = utils_scene.gen_childReuse(root, name_picks, context, mesh_picks, keepTrans=True)
        MW_id_utils.setMetaChild(obj_linksAir_picks)
        # attrs
        obj_linksAir_picks.active_material = utils_mat.gen_colorMat(COLORS.green, name_picks)
        obj_linksAir_picks.active_material.diffuse_color = COLORS.green
        utils_mat.gen_meshUV(mesh_picks, id_picks, "id_picks", repMatchCorners)

    getStats().logDt("generated external links mesh object")
    return obj_linksAir_picks, obj_linksAir_entry

def gen_linksMesh_neighs(fract: MW_Fract, root: types.Object, context: types.Context):
    prefs = getPrefs()
    cfg : MW_vis_cfg = root.mw_vis
    sim : MW_Sim     = MW_global_selected.fract.sim

    # some external links only connect to ohter external
    linkSet = fract.links.internal+fract.links.external
    #linkSet = fract.links.internal

    numLinks = len(linkSet) # not sized cause some may be skipped
    verts     : list[tuple[Vector,Vector]]  = []
    id_grav   : list[tuple[int,float]]      = []

    if DEV.DEBUG_GEODATA:
        l1k1_l1k2 : list[tuple[int,int]]    = []
        l2k1_l2k2 : list[tuple[int,int]]    = []
        l1f1_l1f2 : list[tuple[int,int]]    = []
        l2f1_l2f2 : list[tuple[int,int]]    = []

    # avoid repetitions
    checked = set()

    # iterate the global map and store vert pairs for the tube mesh generation
    for id, l in enumerate(linkSet):
        id_normalized = id / float(numLinks) if not DEV.DEBUG_GEODATA_ID_RAW else id

        # allow once from outer loop
        checked.add(l.key_cells)
        for ln in fract.links.get_link_neighs(l.key_cells):
            if ln.key_cells in checked: continue

            # skip links with no solid end
            if not fract.links.solid_link_check(ln):
                continue

            # point from links pos
            p1 = l.pos
            p2 = ln.pos
            verts.append((p1, p2))

            # grav mod
            g = sim.get_nextAlign( (p1-p2).normalized(), bothDir=True)
            id_grav.append((id_normalized, g))
            #id_grav.append((id_normalized, 0))

            # query info keys
            if DEV.DEBUG_GEODATA:
                l1k1_l1k2.append(l.key_cells)
                l2k1_l2k2.append(ln.key_cells)
                l1f1_l1f2.append(l.key_faces)
                l2f1_l2f2.append(ln.key_faces)

    # single mesh with tubes
    name = prefs.names.links_neighs
    resFaces = utils_mesh.get_resFaces_fromCurveRes(cfg.neighs_res)
    mesh = utils_mesh.get_tubeMesh_pairsQuad(verts, None, name, cfg.neighs_width, resFaces, cfg.links_smoothShade)

    # potentially reuse child and clean mesh
    obj_neighs = utils_scene.gen_childReuse(root, name, context, mesh, keepTrans=True)
    MW_id_utils.setMetaChild(obj_neighs)

    # color encoded attributes for viewing in viewport edit mode
    repMatchCorners=resFaces*4
    utils_mat.gen_meshUV(mesh, id_grav, "id_grav", repMatchCorners)
    obj_neighs.active_material = utils_mat.gen_gradientMat("id_grav", name, colorFn=GRADIENTS.lerp_common(COLORS.white))
    obj_neighs.active_material.diffuse_color = COLORS.white

    if DEV.DEBUG_GEODATA:
        utils_mat.gen_meshUV(mesh, l1k1_l1k2, "l1k1_l1k2", repMatchCorners)
        utils_mat.gen_meshUV(mesh, l2k1_l2k2, "l2k1_l2k2", repMatchCorners)
        utils_mat.gen_meshUV(mesh, l1f1_l1f2, "l1f1_l1f2", repMatchCorners)
        utils_mat.gen_meshUV(mesh, l2f1_l2f2, "l2f1_l2f2", repMatchCorners)

    getStats().logDt("generated neighs links mesh object")
    return obj_neighs

def gen_linksMesh_path(fract: MW_Fract, root: types.Object, context: types.Context, path):
    cfg : MW_vis_cfg = root.mw_vis
    sim : MW_Sim     = fract.sim

    maxDepth = len(path)
    verts : list[tuple[Vector,Vector]]      = [None]*maxDepth
    waterWidths : list[float]               = [None]*maxDepth
    depth_water : list[tuple[int,float]]    = [None]*maxDepth
    depth_norm : list[tuple[int,float]]     = [None]*maxDepth

    if DEV.DEBUG_GEODATA:
        l1k1_l1k2 : list[tuple[int,int]]    = [None]*maxDepth
        l2k1_l2k2 : list[tuple[int,int]]    = [None]*maxDepth
        l1f1_l1f2 : list[tuple[int,int]]    = [None]*maxDepth
        l2f1_l2f2 : list[tuple[int,int]]    = [None]*maxDepth

    # path with pairs, but could use the triFAN
    l_prev = None
    l_prev_key_NONE = (CELL_ERROR_ENUM.MISSING, CELL_ERROR_ENUM.MISSING)

    # iterate the global map and store vert pairs for the tube mesh generation
    for depth, step in enumerate(path):
        depth_normalized = depth / float(maxDepth)
        depth_id = depth_normalized if not DEV.DEBUG_GEODATA_ID_RAW else depth
        l = fract.links.get_link(step[0])
        w = step[1]

        # end point at the link pos
        p2 = l.pos

        # prev point might be an initial point from outside
        if l_prev:
            p1 = l_prev.pos
        else:
            p1 = p2 + cfg.path_outside_start * -sim.cfg.dir_entry

        verts[depth] = (p1, p2)

        # store props
        depth_water[depth] = (depth_id, w)
        depth_norm[depth] = (depth_id, depth_normalized)

        # lerp with with the water -> could go over 1 water__start
        #w_normalized = w / sim.cfg.water__start
        waterWidths[depth]= cfg.path_width_start * max(w, 0) + cfg.path_width_end * max(1-w, 0)

        # query info keys
        if DEV.DEBUG_GEODATA:
            l1k1_l1k2[depth] = l_prev.key_cells if l_prev else l_prev_key_NONE
            l2k1_l2k2[depth] = l.key_cells
            l1f1_l1f2[depth] = l_prev.key_faces if l_prev else l_prev_key_NONE
            l2f1_l2f2[depth] = l.key_faces
        l_prev = l

    # additional step to show exit clearly at an outer wall
    if sim.exit_flag == SIM_EXIT_FLAG.NO_NEXT_LINK_WALL and cfg.path_outside_end:
        depth += 1
        depth_normalized = depth / float(maxDepth)
        depth_id = depth_normalized if not DEV.DEBUG_GEODATA_ID_RAW else depth

        # last point outside
        p1 = l_prev.pos
        p2 = p1 + cfg.path_outside_start * sim.cfg.dir_next
        verts.append((p1, p2))

        # use new next id
        depth_water.append((depth_id, w))
        depth_norm.append((depth_id, depth_normalized))

        # store repeated props
        waterWidths.append(waterWidths[-1])
        if DEV.DEBUG_GEODATA:
            l1k1_l1k2.append(l1k1_l1k2[-1])
            l2k1_l2k2.append(l2k1_l2k2[-1])
            l1f1_l1f2.append(l1f1_l1f2[-1])
            l2f1_l2f2.append(l2f1_l2f2[-1])

    # single mesh with tubes
    name = getPrefs().names.water_paths
    resFaces = utils_mesh.get_resFaces_fromCurveRes(cfg.path_res)
    mesh = utils_mesh.get_tubeMesh_pairsQuad(verts, waterWidths, name, 1.0, resFaces, cfg.links_smoothShade)

    # potentially reuse child and clean mesh
    if cfg.path_lastOnly:
        obj_path = utils_scene.gen_childClean(root, name, context, mesh, keepTrans=True)
    else:
        # keep multiple paths for vis -> delete when found with no mesh
        obj_path_parent = utils_scene.get_child(root, name)
        if obj_path_parent and obj_path_parent.data:
            utils_scene.delete_object(obj_path_parent)
            obj_path_parent = None
        if not obj_path_parent:
            obj_path_parent = utils_scene.gen_child(root, name, context, None, keepTrans=True)
        obj_path = utils_scene.gen_childReuse(obj_path_parent, f"path_{sim.step_id}", context, mesh, keepTrans=True)
    MW_id_utils.setMetaChild(obj_path)

    # color encoded attributes for viewing in viewport edit mode
    repMatchCorners=resFaces*4
    utils_mat.gen_meshUV(mesh, depth_water, "depth_water", repMatchCorners) # just info
    #obj_path.active_material = utils_mat.gen_colorMat(c1, name) # just reduce the size
    #obj_path.active_material = utils_mat.gen_gradientMat("depth_water", name, colorFn=GRADIENTS.lerp_common(c1, c2))

    if DEV.DEBUG_GEODATA:
        utils_mat.gen_meshUV(mesh, l1k1_l1k2, "l1k1_l1k2", repMatchCorners)
        utils_mat.gen_meshUV(mesh, l2k1_l2k2, "l2k1_l2k2", repMatchCorners)
        utils_mat.gen_meshUV(mesh, l1f1_l1f2, "l1f1_l1f2", repMatchCorners)
        utils_mat.gen_meshUV(mesh, l2f1_l2f2, "l2f1_l2f2", repMatchCorners)

    # shade along path
    utils_mat.gen_meshUV(mesh, depth_norm, "depth_norm", repMatchCorners)
    utils_mat.set_meshUV_active(mesh, "depth_norm")
    c1 = COLORS.with_alpha(COLORS.sky, cfg.path_alpha)
    c2 = c1.copy()
    c2.xyz *= cfg.path_dark_end
    obj_path.active_material = utils_mat.gen_gradientMat("depth_norm", name, colorFn=GRADIENTS.lerp_common(c2, c1), forceNew=True)

    # see through and name
    obj_path.show_in_front = True
    #obj_path.show_name = True

    getStats().logDt("generated path mesh object")
    return obj_path

def gen_LEGACY_links(objParent: types.Object, voro_cont: VORO_Container, context: types.Context):
    prefs = getPrefs()
    prefs.names.fmt_setAmount(len(voro_cont))

    # will detect repeated and hide one of each pair, but add to the scene to have the info
    neigh_set = set()

    for cell in voro_cont:
        if cell is None: continue

        # group the links by cell using a parent
        nameGroup= f"{getPrefs().names.LEGACY_links_group}_{prefs.names.fmt_id(cell.id)}"
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

def update_arrow_dir(root: types.Object):
    sim_cfg : MW_sim_cfg = root.mw_sim
    name = getPrefs().names.water_dir

    # water dir from arrow
    obj_arrow = utils_scene.get_child(root, name)
    if obj_arrow:
        newDir = (obj_arrow.matrix_world @ utils_trans.VECTORS.upZ).to_3d().normalized()
        prevDir = Vector(obj_arrow["dir_entry"]).to_3d()
        diff = newDir-prevDir
        # compare with pre dir
        if not utils_trans.almostNull(diff):
            DEV.log_msg(f"Updating water dir with {newDir}", {"SETUP", "DIR"})
            sim_cfg.dir_entry = newDir

def gen_arrow_dir(root: types.Object, context: types.Context):
    vis_cfg : MW_vis_cfg = getPrefs().mw_vis
    sim_cfg : MW_sim_cfg = root.mw_sim
    name = getPrefs().names.water_dir

    # generate the visual arrow
    obj_arrow = gen_arrowObject(root, sim_cfg.dir_entry, utils_trans.VECTORS.O,
                            context, name, vis_cfg.water_dir_scale)
    obj_arrow["dir_entry"] = sim_cfg.dir_entry.normalized()
    obj_arrow.show_in_front = True
    #arrow.show_name = True

    MW_id_utils.setMetaChild(obj_arrow)

#-------------------------------------------------------------------

def gen_field_R(root: types.Object, context: types.Context, res = 8, smooth = False, flipN = False):
    """ Generate or reuse a grid mesh and texture to vis the field. res ==-1 reuse whatever available """
    name = getPrefs().names.field_resist
    regen = False

    # check reuse and update existing obj + mesh
    obj_field = utils_scene.get_child(root, name)
    if obj_field and obj_field.data:
        mesh = obj_field.data
        prev_res = mesh["res"]
        if res != prev_res and res != -1:
            regen = True

        # also check other props
        else:
            if smooth != bool(mesh["smooth"]) or flipN != bool(mesh["flipN"]):
                regen = True

    else:
        regen = True
        assert(res != -1)

    # potential regen including the object (deletes mat, mesh, etc)
    if regen:
        mesh = gen_field_mesh(res, name, smooth, flipN)
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
    id_resist : list[tuple[int,float]] = [None]*numCornerVerts
    mToWorld = obj_field.matrix_world
    for id, l in enumerate(mesh.loops):
        id_normalized = id / float(numCornerVerts)
        v = mToWorld @ mesh.vertices[l.vertex_index].co
        id_resist[id]= (id_normalized, field_R_current().get2D(v.x, v.z))

    # reset instead of creating!
    utils_mat.set_meshUV(mesh, mesh.uv_layers.get("id_resist"), id_resist)

def gen_field_mesh(res = 8, name="grid", smooth=False, flipN = False):
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

    # flip normals reverse the faces in place
    if flipN:
        for fid,f in enumerate(faces):
            faces[fid].reverse()

    # points direclty in world space
    utils_trans.transform_points(verts, trans)
    mesh.from_pydata(verts, edges, faces)

    # store the resolution used
    mesh["res"] = res
    mesh["resX"] = resX
    mesh["resZ"] = resZ
    mesh["smooth"] = smooth
    mesh["flipN"] = flipN
    mesh["flipN"] = flipN

    # smoothing commonly disabled, does not seem to affect lighting tho
    utils_mesh.set_smoothShading(mesh, smooth)
    return mesh