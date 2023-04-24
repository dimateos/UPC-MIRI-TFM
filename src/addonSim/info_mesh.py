# MIRI-A3DM
# Diego Mateos (UPC)
""" Sample functions to review mesh data\n
    OPT:: type annotations for autocompletion
"""

import bpy
import bpy.types as types


#-------------------------------------------------------------------
#- UTILS

def desc(me: types.Mesh, i=0):
    """ Quick access to data prop console:
    ob = bpy.context.active_object
    me = ob.data
    if me: v,e,f,l = desc(me)
    """
    v = me.vertices[i] if me.vertices else None
    e = me.edges[i] if me.edges else None
    f = me.polygons[i] if me.polygons else None
    l = me.loops[i] if me.loops else None
    return v,e,f,l

def desc_mesh(me: bpy.types.Mesh):
    """ Description of the mesh """
    print('Name of the mesh: %s' % me.name)
    print(' V= %d' % (len(me.vertices)))
    print(' E= %d' % (len(me.edges)))
    print(' F= %d' % (len(me.polygons)))

def desc_mesh_inspect(me: bpy.types.Mesh):
    """ WIP: Description of some props/api of the mesh """
    from . import info_inspect as ins

    import os
    print("\n? mesh attributes", me, os.getcwd())
    ins.print_attributes(me)

    poly = me.polygons[0]
    print("\n? poly attributes", poly)
    ins.print_attributes(poly)
    #ins.print_data(poly)

def desc_mesh_data(me: bpy.types.Mesh, limit=8, skipLoops=True):
    """ Description of the mesh data, with samples per collection type """
    desc_mesh(me)

    print('Vertex list:')
    for i in range(min(len(me.vertices), limit)):
        coord = me.vertices[i].co
        print(i, ":", coord[0], coord[1], coord[2])

    print("Edge list :")
    for i in range(min(len(me.edges), limit)):
        print(i, ":", me.edges[i].vertices[:])

    print('Face list:')
    for i in range(min(len(me.polygons), limit)):
        print(i, ":", me.polygons[i].vertices[:])

    for poly in me.polygons[:min(len(me.polygons), limit)]:
        print("Polygon index: %d, length: %d" % (poly.index, poly.loop_total))
        for loop_index in poly.loop_indices:
            # equivalent to
            #       for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
            print("    Vertex: %d" % me.loops[loop_index].vertex_index)

    # can also be obtained from poly.vertices[] directly:
    #       for v in poly.vertices[:]:
    #           print("    Vertex: %d" % v)

    if not skipLoops:
        print("Loops:")
        for i in me.loops:
            print(i.vertex_index)

    print("\nEnd of Data for mesh " + me.name + "\n\n")