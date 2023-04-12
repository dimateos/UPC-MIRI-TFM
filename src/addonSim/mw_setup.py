import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
)

from . import utils


# -------------------------------------------------------------------

def gen_copyOriginal(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    cfg.meta_type = {"ROOT"}
    cfg.struct_original = obj.name

    # Empty object to hold all of them
    obj_empty = bpy.data.objects.new(cfg.struct_original, None)
    context.scene.collection.objects.link(obj_empty)

    # Duplicate the original object
    obj_copy: types.Object = obj.copy()
    obj_copy.data = obj.data.copy()
    obj_copy.name = "Original"
    obj_copy.parent = obj_empty
    obj_copy.mw_gen.meta_type = {"CHILD"}
    context.scene.collection.objects.link(obj_copy)

    # Hide and select
    obj.hide_set(True)
    obj_copy.hide_set(True)
    obj_empty.select_set(True)
    context.view_layer.objects.active = obj_empty
    #bpy.ops.outliner.show_active(execution_context='INVOKE_DEFAULT') cannot expand hierarchy...

    return obj_empty, obj_copy

def gen_naming(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    if obj.name.startswith(cfg.struct_original):
        obj.name = cfg.struct_original + "_" + cfg.struct_sufix
    else:
        obj.name += "_" + cfg.struct_sufix

def gen_shardsEmpty(obj: types.Object, cfg: MW_gen_cfg, context: types.Context):
    # Delete if exists along its shard children
    obj_emptyFrac = utils.get_child(obj, "Shards")
    if obj_emptyFrac:
        utils.delete_object(obj_emptyFrac)

    # Generate empty for the fractures
    obj_emptyFrac = bpy.data.objects.new("Shards", None)
    obj_emptyFrac.mw_gen.meta_type = {"CHILD"}
    obj_emptyFrac.parent = obj
    context.scene.collection.objects.link(obj_emptyFrac)


# -------------------------------------------------------------------
# ref: original cell fracture modifier

def get_points_from_object_fallback(obj: types.Object, cfg: MW_gen_cfg, depsgraph, scene):
    points = get_points_from_object(obj, cfg, depsgraph, scene)

    if not points:
        print("No points found... changing to fallback (own vertices)")
        cfg.source = {'VERT_OWN'}
        points = get_points_from_object(obj, cfg, depsgraph, scene)
    if not points:
        print("No points found either...")
        return []
    return points

def get_points_from_object(obj: types.Object, cfg: MW_gen_cfg, depsgraph, scene):
    cfg_source = cfg.cfg_source

    _source_all = {
        'PARTICLE_OWN', 'PARTICLE_CHILD',
        'PENCIL',
        'VERT_OWN', 'VERT_CHILD',
    }
    # print(cfg_source - _source_all)
    # print(cfg_source)
    assert(len(cfg_source | _source_all) == len(_source_all))
    assert(len(cfg_source))

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
            mesh = obj.data
            matrix = obj.matrix_world.copy()
            points.extend([matrix @ v.co for v in mesh.vertices])
        else:
            obj_eval = obj.evaluated_get(depsgraph)
            try:
                mesh = obj_eval.to_mesh()
            except:
                mesh = None

            if mesh is not None:
                matrix = obj.matrix_world.copy()
                points.extend([matrix @ v.co for v in mesh.vertices])
                obj_eval.to_mesh_clear()

    def points_from_particles(obj):
        obj_eval = obj.evaluated_get(depsgraph)
        # NOTE: chained list comprehension
        points.extend([p.location.copy()
                       for psys in obj_eval.particle_systems
                       for p in psys.particles])

    # geom own
    if 'VERT_OWN' in cfg_source:
        points_from_verts(obj)

    # geom children
    if 'VERT_CHILD' in cfg_source:
        for obj_child in obj.children:
            points_from_verts(obj_child)

    # geom particles
    if 'PARTICLE_OWN' in cfg_source:
        points_from_particles(obj)

    if 'PARTICLE_CHILD' in cfg_source:
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

    if 'PENCIL' in cfg_source:
        # Used to be from object in 2.7x, now from scene.
        gp = scene.grease_pencil
        if gp:
            points.extend([p for spline in get_splines(gp) for p in spline])

    print("Found %d points" % len(points))
    return points


def points_limitNum(points: list, cfg: MW_gen_cfg):
    source_limit = cfg.source_limit
    if source_limit <= 0 and source_limit < len(points):
        rnd.shuffle(points)
        points[source_limit:] = []
    return points

def points_4D_noDoubles(points: list, cfg: MW_gen_cfg, rnd):
    from mathutils import Vector
    points_set = {Vector.to_tuple(p, 4) for p in points}
    points = list(points_set.values())
    return points

def points_addNoise(points: list, cfg: MW_gen_cfg, rnd):
    from random import random
    # boundbox approx of overall scale
    from mathutils import Vector
    matrix = obj.matrix_world.copy()
    bb_world = [matrix @ Vector(v) for v in obj.bound_box]
    scalar = source_noise * ((bb_world[0] - bb_world[6]).length / 2.0)

    from mathutils.noise import random_unit_vector

    points[:] = [p + (random_unit_vector() * (scalar * random())) for p in points]