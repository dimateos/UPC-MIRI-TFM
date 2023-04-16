import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
)

from . import utils
from .ui import DEV_log

from mathutils import Vector
INF_FLOAT = float("inf")
import mathutils.noise as bl_rnd
import random as rnd

# Using tess voro++ adaptor
from tess import Container, Cell


# -------------------------------------------------------------------
# ref: original cell fracture modifier

def get_points_from_object_fallback(obj: types.Object, cfg: MW_gen_cfg, context):
    points = get_points_from_object(obj, cfg, context)

    if not points:
        DEV_log("No points found... changing to fallback (own vertices)", {"SETUP"})
        cfg.source = { cfg.sourceOptions.default_key }
        points = get_points_from_object(obj, cfg, context)
    if not points:
        DEV_log("No points found either...", {"SETUP"})
        return []

    return points

def get_points_from_object(obj: types.Object, cfg: MW_gen_cfg, context):
    source = cfg.source
    if not source:
        cfg.source = source = { cfg.sourceOptions.default_key }

    # return in local space
    points = []
    matrix_toLocal = obj.matrix_world.inverted()

    def points_from_verts(obj):
        """Takes points from _any_ object with geometry"""
        if obj.type == 'MESH':
            points.extend(utils.get_verts(obj, worldSpace=False))
        else:
            # TODO: unused because atm limited to mesh anyway
            depsgraph = context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depsgraph)
            try:
                mesh = obj_eval.to_mesh()
            except:
                mesh = None

            if mesh is not None:
                verts = [v.co for v in mesh.vertices]
                points.extend(verts)
                obj_eval.to_mesh_clear()

    def points_from_particles(obj):
        depsgraph = context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)

        # NOTE: chained list comprehension
        points.extend([matrix_toLocal @ p.location.copy()
                       for psys in obj_eval.particle_systems
                       for p in psys.particles])

    # geom own
    if 'VERT_OWN' in source:
        points_from_verts(obj)

    # geom children
    if 'VERT_CHILD' in source:
        for obj_child in obj.children:
            points_from_verts(obj_child)

    # geom particles
    if 'PARTICLE_OWN' in source:
        points_from_particles(obj)

    if 'PARTICLE_CHILD' in source:
        for obj_child in obj.children:
            points_from_particles(obj_child)

    # grease pencil
    def points_from_stroke(stroke):
        return [matrix_toLocal @ point.co.copy() for point in stroke.points]

    def points_from_splines(gp):
        if gp.layers.active:
            frame = gp.layers.active.active_frame
            return [points_from_stroke(stroke) for stroke in frame.strokes]
        else:
            return []

    if 'PENCIL' in source:
        # Used to be from object in 2.7x, now from scene.
        scene = context.scene
        gp = scene.grease_pencil
        if gp:
            points.extend([p for spline in points_from_splines(gp) for p in spline])

    DEV_log(f"Found {len(points)} points", {"SETUP"})
    return points

# -------------------------------------------------------------------

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

# -------------------------------------------------------------------

def cont_fromPoints(points: list[Vector], bb: list[Vector, 6], faces4D: list[Vector]) -> Container:
    # Container bounds expected as tuples
    bb_tuples = [ p.to_tuple() for p in bb ]

    # Build the container and cells
    cont = Container(points=points, limits=bb_tuples, walls=faces4D)

    DEV_log(f"Found {len(cont)} cells ({len(faces4D)} faces)", {"CALC"})
    return cont