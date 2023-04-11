import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
)

from . import utils


# -------------------------------------------------------------------

def gen_copyOriginal(cfg : MW_gen_cfg, ob: types.Object, context: types.Context):
    cfg.meta_type = {"ROOT"}
    cfg.struct_original = ob.name

    # Empty object to hold all of them
    ob_empty = bpy.data.objects.new(cfg.struct_original, None)
    context.scene.collection.objects.link(ob_empty)

    # Duplicate the original object
    ob_copy: types.Object = ob.copy()
    ob_copy.data = ob.data.copy()
    ob_copy.name = "Original"
    ob_copy.parent = ob_empty
    ob_copy.mw_gen.meta_type = {"CHILD"}
    context.scene.collection.objects.link(ob_copy)

    # Hide and select
    ob.hide_set(True)
    ob_copy.hide_set(True)
    ob_empty.select_set(True)
    context.view_layer.objects.active = ob_empty
    #bpy.ops.outliner.show_active(execution_context='INVOKE_DEFAULT') cannot expand hierarchy...

    return ob_empty, ob_copy

def gen_naming(cfg : MW_gen_cfg, ob: types.Object, context: types.Context):
    if ob.name.startswith(cfg.struct_original):
        ob.name = cfg.struct_original + "_" + cfg.struct_sufix
    else:
        ob.name += "_" + cfg.struct_sufix

def gen_shardsEmpty(cfg : MW_gen_cfg, ob: types.Object, context: types.Context):
    # Delete if exists along its shard children
    ob_emptyFrac = utils.get_child(ob, "Shards")
    if ob_emptyFrac:
        utils.delete_object(ob_emptyFrac)

    # Generate empty for the fractures
    ob_emptyFrac = bpy.data.objects.new("Shards", None)
    ob_emptyFrac.mw_gen.meta_type = {"CHILD"}
    ob_emptyFrac.parent = ob
    context.scene.collection.objects.link(ob_emptyFrac)


# -------------------------------------------------------------------
# ref: original cell fracture modifier

def get_points_from_object_fallback(depsgraph, scene, obj, source):
    points = get_points_from_object(depsgraph, scene, obj, source)

    if not points:
        print("No points found... using fallback (own vertices)")
        points = get_points_from_object(depsgraph, scene, obj, {'VERT_OWN'})
    if not points:
        print("No points found either...")
        return []
    return points

def get_points_from_object(depsgraph, scene, obj, source):

    _source_all = {
        'PARTICLE_OWN', 'PARTICLE_CHILD',
        'PENCIL',
        'VERT_OWN', 'VERT_CHILD',
    }
    # print(source - _source_all)
    # print(source)
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
        gp = scene.grease_pencil
        if gp:
            points.extend([p for spline in get_splines(gp) for p in spline])

    print("Found %d points" % len(points))
    return points