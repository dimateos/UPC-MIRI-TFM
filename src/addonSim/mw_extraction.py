import bpy
import bpy.types as types
from mathutils import Vector
import mathutils.noise as bl_rnd
import random as rnd
INF_FLOAT = float("inf")

from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
    MW_gen_source_options,
)

from .mw_fract import MW_Fract
from .unionfind import UnionFind

from . import utils_scene, utils_trans
from .utils_dev import DEV
from .stats import getStats


# OPT:: not recursive + query obj.children a lot
#-------------------------------------------------------------------

def detect_points_from_object(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    """ Attempts to retrieve a point per option and disables them when none is found """
    cfg.meta_source_enabled = set()

    def check_point_from_verts(ob):
        if ob.type == 'MESH':
            return bool(len(ob.data.vertices))
        else:
            depsgraph = context.evaluated_depsgraph_get()
            obj_eval = ob.evaluated_get(depsgraph)
            try:
                mesh = obj_eval.to_mesh()
                return  bool(len(mesh.vertices))
            except:
                return False

    # geom own
    if check_point_from_verts(obj): cfg.meta_source_enabled|= {"VERT_OWN"}
    # geom children
    for obj_child in obj.children:
        if check_point_from_verts(obj_child):
            cfg.meta_source_enabled|= {"VERT_CHILD"}
            break

    def check_point_from_particles(ob):
        depsgraph = context.evaluated_depsgraph_get()
        ob_eval = ob.evaluated_get(depsgraph)

        if not ob_eval.particle_systems:
            return False
        else:
            sys_particles = [bool(psys.particles) for psys in ob_eval.particle_systems]
            DEV.log_msg(f"check parts: {ob.name} -> {len(ob_eval.particle_systems[0].particles)} -> {sys_particles}", {"CALC", "SOURCE"})
            return any(sys_particles)

    # geom own particles
    if check_point_from_particles(obj): cfg.meta_source_enabled|= {"PARTICLE_OWN"}

    # geom children particles
    for obj_child in obj.children:
        if check_point_from_particles(obj_child):
            cfg.meta_source_enabled|= {"PARTICLE_CHILD"}
            break

    # grease pencil
    if "PENCIL" in MW_gen_source_options.all_keys:
        def check_points_from_splines(gp):
            if not gp.layers.active:
                return False
            else:
                frame = gp.layers.active.active_frame
                stroke_points = [stroke.points for stroke in frame.strokes]
                return any(stroke_points)

        scene = context.scene
        gp = scene.grease_pencil
        if gp:
            if check_points_from_splines(gp): cfg.meta_source_enabled |= {"PENCIL"}

    getStats().logDt(f"detected points: {cfg.meta_source_enabled}")

def get_points_from_object_fallback(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    if not cfg.meta_source_enabled:
        cfg.source = { MW_gen_source_options.error_key }
        DEV.log_msg("No points found...", {"CALC", "SOURCE", "ERROR"})
        return []

    points = get_points_from_object(obj, cfg, context)
    getStats().logDt(f"retrieved points: {len(points)}")
    return points

def get_points_from_object(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    """ Retrieves point using the method selected
        * REF: some get_points from original cell fracture modifier
    """
    # try set default source or fallback
    if not cfg.source:
        if MW_gen_source_options.default_key in cfg.meta_source_enabled:
            cfg.source = { MW_gen_source_options.default_key }
        else: cfg.source = { MW_gen_source_options.fallback_key }

    # return in local space
    points = []
    world_toLocal = obj.matrix_world.inverted()

    def points_from_verts(ob: types.Object, isChild=False):
        """Takes points from _any_ object with geometry"""
        if ob.type == 'MESH':
            verts = utils_trans.get_verts(ob, worldSpace=False)
        else:
            # NOTE:: unused because atm limited to mesh in ui/operator anyway
            depsgraph = context.evaluated_depsgraph_get()
            obj_eval = ob.evaluated_get(depsgraph)
            try:
                mesh = obj_eval.to_mesh()
            except:
                mesh = None

            if mesh is not None:
                verts = [v.co for v in mesh.vertices]
                obj_eval.to_mesh_clear()
            else:
                verts = []

        # Child points need to be in parent local space
        if isChild:
            matrix = world_toLocal @ ob.matrix_world
            #matrix = ob.matrix_parent_inverse @ ob.matrix_basis
            utils_trans.transform_points(verts, matrix)
        points.extend(verts)

    # geom own
    if 'VERT_OWN' in cfg.source:
        points_from_verts(obj)
    # geom children
    if 'VERT_CHILD' in cfg.source:
        for obj_child in obj.children:
            points_from_verts(obj_child, isChild=True)

    def points_from_particles(ob: types.Object):
        depsgraph = context.evaluated_depsgraph_get()
        obj_eval = ob.evaluated_get(depsgraph)

        # NOTE: chained list comprehension
        points.extend([world_toLocal @ p.location.copy()
                       for psys in obj_eval.particle_systems
                       for p in psys.particles])

    # geom own particles
    if 'PARTICLE_OWN' in cfg.source:
        points_from_particles(obj)
    # geom child particles
    if 'PARTICLE_CHILD' in cfg.source:
        for obj_child in obj.children:
            points_from_particles(obj_child)

    # grease pencil
    if 'PENCIL' in cfg.source:
        def points_from_stroke(stroke):
            return [world_toLocal @ point.co.copy() for point in stroke.points]
        def points_from_splines(gp):
            if gp.layers.active:
                frame = gp.layers.active.active_frame
                return [points_from_stroke(stroke) for stroke in frame.strokes]
            else:
                return []

        # Used to be from object in 2.7x, now from scene.
        scene = context.scene
        gp = scene.grease_pencil
        if gp:
            points.extend([p for spline in points_from_splines(gp) for p in spline])

    return points

def get_points_from_fracture(obj_root: types.Object, cfg: MW_gen_cfg):
    prefs = getPrefs()
    obj_points = utils_scene.get_child(obj_root, prefs.names.source_points)

    points = utils_trans.get_verts(obj_points, worldSpace=False)
    getStats().logDt(f"retrieved points: {len(points)} (from {obj_points.name})")
    return points

#-------------------------------------------------------------------

def points_limitNum(points: list[Vector], cfg: MW_gen_cfg):
    source_limit = cfg.source_limit

    if source_limit > 0 and source_limit < len(points):
        if cfg.source_shuffle:
            rnd.shuffle(points)
        points[source_limit:] = []

def points_addNoise(points: list[Vector], cfg: MW_gen_cfg, bb_radius: float):
    noise = cfg.source_noise

    if noise:
        # aprox the random max displacement
        approxR = bb_radius**3 / len(points)
        scalar = noise * approxR
        points[:] = [p + (bl_rnd.random_unit_vector() * scalar * rnd.random()) for p in points]

    if DEV.DEBUG_MODEL:
        # collapse to the plane (non uniform random side effect)
        points[:] = [p * Vector((1,1,0)) for p in points]

def points_noDoubles(points: list[Vector], cfg: MW_gen_cfg):
    points_set = {Vector.to_tuple(p, 4) for p in points}
    points = list(points_set)

def points_transformCfg(points: list[Vector], cfg: MW_gen_cfg, bb_radius: float):
    """ Applies all transformations to the set of points obtained
        # OPT:: do it while extracting to limit operations on unused data -> also check valid inside cont
    """
    points_limitNum(points, cfg)
    points_addNoise(points, cfg, bb_radius)
    points_noDoubles(points, cfg)
    getStats().logDt(f"transform/limit points: {len(points)} (noise {cfg.source_noise:.4f})")

#-------------------------------------------------------------------

# TODO:: check already have it? faster to add to all at once too
def boolean_mod_add(obj_original: types.Object, obj_cells_root: types.Object, context: types.Context):
    c = obj_cells_root.children
    for obj_cell in c:
        mod = obj_cell.modifiers.new(name="Boolean", type='BOOLEAN')
        mod.object = obj_original
        mod.operation = 'INTERSECT'
        mod.solver = "FAST"

    DEV.log_msg(f"Applied boolean to {len(c)} cells)", {"CALC", "MOD"})

    # Calculates all booleans at once (faster).
    depsgraph = context.evaluated_depsgraph_get()

def get_connected_comps(fract: MW_Fract):
    """ # NOTE:: old method, now done with networkx """
    cell_union = UnionFind(len(fract.cont.foundId))

    for l in fract.links.internal:
        cell_union.union(*l.key_cells)

    DEV.log_msg(f"Extracted {cell_union.num_components} components", {"CALC", "COMP"})
    return cell_union