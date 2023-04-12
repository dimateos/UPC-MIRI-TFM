import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
)

from . import utils
from .ui import DEV_log

from mathutils import Vector
import mathutils.noise as bl_rnd
import random as rnd

NAME_ORIGINAL = "Original"
NAME_ORIGINAL_BB = "Original_bb"
NAME_SHARDS = "Shards"
NAME_SHARDS_POINTS = "Shards_source"


# -------------------------------------------------------------------

def gen_copyOriginal(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    cfg.meta_type = {"ROOT"}
    cfg.struct_nameOriginal = obj.name

    # Empty object to hold all of them
    obj_empty = bpy.data.objects.new(cfg.struct_nameOriginal, None)
    context.scene.collection.objects.link(obj_empty)

    # Duplicate the original object
    obj_copy: types.Object = obj.copy()
    obj_copy.data = obj.data.copy()
    obj_copy.name = NAME_ORIGINAL
    obj_copy.parent = obj_empty
    obj_copy.mw_gen.meta_type = {"CHILD"}
    context.scene.collection.objects.link(obj_copy)

    # Hide and select after link
    obj.hide_set(not cfg.struct_showOrignal)
    obj_copy.hide_set(True)
    obj_empty.select_set(True)
    context.view_layer.objects.active = obj_empty
    #bpy.ops.outliner.show_active(execution_context='INVOKE_DEFAULT') cannot expand hierarchy...

    return obj_empty, obj_copy

def gen_naming(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    if obj.name.startswith(cfg.struct_nameOriginal):
        obj.name = cfg.struct_nameOriginal + "_" + cfg.struct_nameSufix
    else:
        obj.name += "_" + cfg.struct_nameSufix

def gen_shardsEmpty(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    obj_emptyFrac = utils.gen_childClean(obj, NAME_SHARDS, None, not cfg.struct_showShards, context)
    return obj_emptyFrac

def gen_pointsObject(obj: types.Object, points: list[Vector], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(NAME_SHARDS_POINTS)
    mesh.from_pydata(points, [], [])
    #mesh.update()

    obj_points = utils.gen_childClean(obj, NAME_SHARDS_POINTS, mesh, not cfg.struct_showPoints, context)
    return obj_points

def gen_boundsObject(obj: types.Object, bb: list[Vector, 2], cfg: MW_gen_cfg, context: types.Context):
    # Create a new mesh data block and add only verts
    mesh = bpy.data.meshes.new(NAME_ORIGINAL_BB)
    mesh.from_pydata(bb, [], [])

    obj_bb = utils.gen_childClean(obj, NAME_ORIGINAL_BB, mesh, not cfg.struct_showBB, context)
    obj_bb.show_bounds = True
    return obj_bb

# -------------------------------------------------------------------
# ref: original cell fracture modifier

def get_points_from_object_fallback(obj: types.Object, cfg: MW_gen_cfg, context):
    points = get_points_from_object(obj, cfg, context)

    if not points:
        DEV_log("No points found... changing to fallback (own vertices)", {"SETUP"})
        cfg.source = {'VERT_OWN'}
        points = get_points_from_object(obj, cfg, context)
    if not points:
        DEV_log("No points found either...", {"SETUP"})
        return []
    return points

def get_points_from_object(obj: types.Object, cfg: MW_gen_cfg, context):
    source = cfg.source
    _source_all = {
        'PARTICLE_OWN', 'PARTICLE_CHILD',
        'PENCIL',
        'VERT_OWN', 'VERT_CHILD',
    }
    # DEV_log(source - _source_all)
    # DEV_log(source)
    assert(len(source | _source_all) == len(_source_all))
    assert(len(source))

    points = []

    def edge_center(mesh, edge):
        v1, v2 = edge.vertices
        return (mesh.vertices[v1].co + mesh.vertices[v2].co) / 2.0

    def poly_center(mesh, poly):
        from mathutils import Vector
        co = Vector()
        tot = 0
        for i in poly.loop_indices:
            co += mesh.vertices[mesh.loops[i].vertex_index].co
            tot += 1.0
        return co / tot

    def points_from_verts(obj):
        """Takes points from _any_ object with geometry"""
        if obj.type == 'MESH':
            points.extend(utils.get_worldVerts(obj))
        else:
            # TODO atm limited to mesh anyway
            depsgraph = context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depsgraph)
            try:
                mesh = obj_eval.to_mesh()
            except:
                mesh = None

            if mesh is not None:
                verts = mesh.vertices
                utils.transform_verts(verts, obj_eval.matrix_world)
                points.extend(verts)
                obj_eval.to_mesh_clear()

    def points_from_particles(obj):
        depsgraph = context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        # NOTE: chained list comprehension
        points.extend([p.location.copy()
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
    def get_points(stroke):
        return [point.co.copy() for point in stroke.points]

    def get_splines(gp):
        if gp.layers.active:
            frame = gp.layers.active.active_frame
            return [get_points(stroke) for stroke in frame.strokes]
        else:
            return []

    if 'PENCIL' in source:
        # Used to be from object in 2.7x, now from scene.
        scene = context.scene
        gp = scene.grease_pencil
        if gp:
            points.extend([p for spline in get_splines(gp) for p in spline])

    DEV_log("Found %d points" % len(points), {"SETUP"})
    return points


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