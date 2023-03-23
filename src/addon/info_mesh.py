# MIRI-A3DM
# Diego Mateos (UPC)
""" Sample functions to acces mesh data
    * TODO: type annotations for autocompletion
"""

### IMPORTS
import bpy


### UTILS
# Quick copypaste in blender to test stuff in its interactive shell
#   (full access to runtime types and methods, etc)
def desc(i=0):
    # ob,me,v,e,f,l = desc()
    ob = bpy.context.active_object
    me = ob.data
    return ob, me, me.vertices[i],me.edges[i],me.polygons[i],me.loops[i]

# Description of the mesh
def desc_mesh(me: bpy.types.Mesh):
    print('Name of the mesh: %s' % me.name)
    print(' V= %d' % (len(me.vertices)))
    print(' E= %d' % (len(me.edges)))
    print(' F= %d' % (len(me.polygons)))

# WIP test stuff
def desc_mesh_inspect(me: bpy.types.Mesh):
    from . import info_inspect as ins

    print("\n? mesh attributes", me)
    ins.print_attributes(me)

    poly = me.polygons[0]
    print("\n? poly attributes", poly)
    ins.print_attributes(poly)
    #ins.print_data(poly)

# Description of the mesh data, with samples per collection type
def desc_mesh_data(me: bpy.types.Mesh, limit=8, skipLoops=True):
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