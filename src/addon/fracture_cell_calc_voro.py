
# Using tess voro++ adaptor
from tess import Container, Cell

# import bpy
# import bmesh

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
    matrix = obj.matrix_world.copy()
    verts = [matrix @ v.co for v in mesh.vertices]

    from . import info_mesh
    info_mesh.desc_mesh_data(mesh)
    info_mesh.desc_mesh_inspect(mesh)

    # WIP early exit
    return []
