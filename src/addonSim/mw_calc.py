import bpy
import bpy.types as types
from mathutils import Vector
import mathutils.noise as bl_rnd
import random as rnd
INF_FLOAT = float("inf")

from .properties import (
    MW_gen_cfg,
)

# Using tess voro++ adaptor
from tess import Container, Cell

from . import utils
from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

def detect_points_from_object(obj: types.Object, cfg: MW_gen_cfg, context):
    """ Attempts to retrieve a point per option and disables them when none is found """
    enabled = cfg.sourceOptions.enabled
    for key in enabled.keys(): enabled[key] = False

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
    enabled["VERT_OWN"] = check_point_from_verts(obj)
    # geom children
    for obj_child in obj.children:
        if check_point_from_verts(obj_child):
            enabled["VERT_CHILD"] = True
            break

    def check_point_from_particles(ob):
        depsgraph = context.evaluated_depsgraph_get()
        ob_eval = ob.evaluated_get(depsgraph)

        if not ob_eval.particle_systems:
            return False
        else:
            sys_particles = [bool(psys.particles) for psys in ob_eval.particle_systems]
            DEV.log_msg(f"check parts: {ob.name} -> {len(ob_eval.particle_systems[0].particles)} -> {sys_particles}")
            return any(sys_particles)

    # geom own particles
    enabled["PARTICLE_OWN"] = check_point_from_particles(obj)

    # geom children particles
    for obj_child in obj.children:
        if check_point_from_particles(obj_child):
            enabled["PARTICLE_CHILD"] = True
            break

    # grease pencil
    if "PENCIL" in cfg.sourceOptions.all_keys:
        def check_points_from_splines(gp):
            if not gp.layers.active:
                return False
            else:
                frame = gp.layers.active.active_frame
                stroke_points = [stroke.points for stroke in frame.strokes]
                return any(stroke_points)

        enabled["PENCIL"] = False
        scene = context.scene
        gp = scene.grease_pencil
        if gp:
            enabled["PENCIL"] = check_points_from_splines(gp)

    getStats().logDt(f"detected points: {enabled}")

def get_points_from_object_fallback(obj: types.Object, cfg: MW_gen_cfg, context):
    points = get_points_from_object(obj, cfg, context)

    # OPT:: wont happen anymore?
    if not points:
        DEV.log_msg(f"No points found... changing to fallback ({cfg.sourceOptions.fallback_key})", {"SETUP"})
        cfg.source = { cfg.sourceOptions.fallback_key }
        points = get_points_from_object(obj, cfg, context)
    if not points:
        DEV.log_msg("No points found either...", {"SETUP"})
        points = []

    getStats().logDt(f"retrieved points: {len(points)}")
    return points

def get_points_from_object(obj: types.Object, cfg: MW_gen_cfg, context):
    """ Retrieves point using the method selected
        * REF: some get_points from original cell fracture modifier
    """
    source = cfg.source
    if not source:
        if cfg.sourceOptions.enabled[cfg.sourceOptions.default_key]:
            source = { cfg.sourceOptions.default_key }
        else: source = { cfg.sourceOptions.fallback_key }
        cfg.source = source

    # return in local space
    points = []
    world_toLocal = obj.matrix_world.inverted()

    def points_from_verts(ob: types.Object, isChild=False):
        """Takes points from _any_ object with geometry"""
        if ob.type == 'MESH':
            verts = utils.get_verts(ob, worldSpace=False)
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
            utils.transform_points(verts, matrix)
        points.extend(verts)

    # geom own
    if 'VERT_OWN' in source:
        points_from_verts(obj)
    # geom children
    if 'VERT_CHILD' in source:
        # NOTE:: not recursive atm
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
    if 'PARTICLE_OWN' in source:
        points_from_particles(obj)
    # geom child particles
    if 'PARTICLE_CHILD' in source:
        # NOTE:: not recursive either
        for obj_child in obj.children:
            points_from_particles(obj_child)

    # grease pencil
    if 'PENCIL' in source:
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

#-------------------------------------------------------------------

def points_limitNum(points: list[Vector], cfg: MW_gen_cfg):
    source_limit = cfg.source_limit

    if source_limit > 0 and source_limit < len(points):
        rnd.shuffle(points)
        points[source_limit:] = []

def points_noDoubles(points: list[Vector], cfg: MW_gen_cfg):
    points_set = {Vector.to_tuple(p, 4) for p in points}
    points = list(points_set)

def points_addNoise(points: list[Vector], cfg: MW_gen_cfg, bb_radius: float):
    noise = cfg.source_noise

    if noise:
        scalar = noise * bb_radius # boundbox radius to aprox scale
        points[:] = [p + (bl_rnd.random_unit_vector() * scalar * rnd.random()) for p in points]

def points_transformCfg(points: list[Vector], cfg: MW_gen_cfg, bb_radius: float):
    """ Applies all transformations to the set of points obtained """
    points_limitNum(points, cfg)
    points_noDoubles(points, cfg)
    points_addNoise(points, cfg, bb_radius)
    getStats().logDt(f"transform/limit points: {len(points)} (noise {cfg.source_noise:.4f})")

#-------------------------------------------------------------------

def cont_fromPoints(points: list[Vector], bb: list[Vector, 6], faces4D: list[Vector], precision: int) -> Container:
    """ Build a voro++ container using the points and the faces as walls """
    # Container bounds expected as tuples
    bb_tuples = [ p.to_tuple() for p in bb ]

    #Legacy cont some tests mid operator
    if DEV.LEGACY_CONT:
        cont = Container(points=points, limits=bb_tuples)
        DEV.log_msg(f"Found {len(cont)} cells (NO walls - {len(faces4D)} faces)", {"CALC-LEGACY"})
        return cont

    # Set wall planes precision used
    if precision != Container.custom_walls_precision_default:
        Container.custom_walls_precision = precision
        DEV.log_msg(f"Set Container.custom_walls_precision: {precision}", {"CALC"})
    else:
        Container.custom_walls_precision = Container.custom_walls_precision_default

    try:
        # Build the container and cells
        cont = Container(points=points, limits=bb_tuples, walls=faces4D)
        # TODO:: log verts outside?

        # Check non empty
        getStats().logDt("calculated cont")
        logType = {"CALC"} if cont else {"CALC", "ERROR"}
        DEV.log_msg(f"Found {len(cont)} cells ({len(cont.walls)} walls from {len(faces4D)} faces)", logType)
        return cont

    # XXX:: container creation might fail do to some voro++ config params... hard to tweak for all?
    # XXX:: also seems that if the mesh vertices/partilces are further appart if behaves better?
    except Exception as e:
        DEV.log_msg(f"exception cont >> {str(e)}", {"CALC", "ERROR"})
        return []