
# Using tess voro++ adaptor
from tess import Container, Cell

import bpy
#import bmesh

def points_as_bmesh_cells(
        obj,
        points,
        points_scale=None,
        margin_bounds=0.05,
        margin_cell=0.0,
):
    """
    obj: WIP: atm recieve all obj and data, later reduce information shared?
    points: selected points to use for fractures, usually limited amount: own/child vertices, own/child particles...
    """
    mesh: bpy.types.Mesh = obj.data

    # Verts in world space
    matrix = obj.matrix_world.copy()
    verts = [matrix @ v.co for v in mesh.vertices]

    # TEST: check out some mesh properties and API
    if 0:
        from . import info_mesh
        info_mesh.desc_mesh_data(mesh)
        info_mesh.desc_mesh_inspect(mesh)

    from math import sqrt
    from mathutils import Vector
    #import mathutils
    INF_LARGE = 10000000000.0  # a big value!


    # Calculate the bounding box for the outer walls of the container
    xa = [v[0] for v in verts]
    ya = [v[1] for v in verts]
    za = [v[2] for v in verts]

    xmin, xmax = min(xa) - margin_bounds, max(xa) + margin_bounds
    ymin, ymax = min(ya) - margin_bounds, max(ya) + margin_bounds
    zmin, zmax = min(za) - margin_bounds, max(za) + margin_bounds
    bb = [ (xmin, ymin, zmin), (xmax, ymax, zmax) ]


    # Calculate the 4D vectors representing the face planes
    walls = []


    # Build the container and cells
    cont = Container(points=points, limits=bb, walls=walls)


    # OUTPUT: consists of a list of shards tuples (center point used, [convex hull vertices])
    # NOTE the vertices must use mathutils.Vectors and in LOCAL coordinates around the original position
    cells = [
        (
            Vector(cell.pos),
            [ Vector(v) for v in cell.vertices_local() ]
        )
        for cell in cont
    ]

    #print(cells)
    return cells

