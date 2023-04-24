import bpy
import bpy.types as types

from mathutils import Vector, Matrix


#-------------------------------------------------------------------

class COLORS:
    red   = Vector([1.0, 0.0, 0.0])
    green = Vector([0.0, 1.0, 0.0])
    blue  = Vector([0.0, 0.0, 1.0])

    pink    = (red+blue) * 0.5
    yellow  = (red+green) * 0.5
    orange  = (red+yellow) * 0.5

    white   = Vector([1.0, 1.0, 1.0])
    gray   = white * 0.5
    black   = Vector([0.0, 0.0, 0.0])

    default_name = "colorMat"


def get_colorMat(color3=COLORS.red, alpha=1.0, colorName: str=None):
    if not colorName: colorName = COLORS.default_name
    mat = bpy.data.materials.new(colorName)
    mat.use_nodes = False
    mat.diffuse_color[0] = color3[0]
    mat.diffuse_color[1] = color3[1]
    mat.diffuse_color[2] = color3[2]
    mat.diffuse_color[3] = alpha
    return mat

def set_mat(obj: types.Object, mat: types.Material):
    obj.active_material = mat

def set_colorMat(obj: types.Object, color3=COLORS.red, alpha=1.0, colorName: str=None):
    mat = get_colorMat(color3, alpha, colorName)
    obj.active_material = mat
    return mat


#-------------------------------------------------------------------

class SHAPES:
    octa_verts = [
        Vector((0, 0, 1)),
        Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0)), Vector((0, -1, 0)),
        Vector((0, 0, -1)),
    ]
    octa_faces = [
        [0,1,2], [0,2,3], [0,3,4], [0,4,1],
        [5,2,1], [5,3,2], [5,4,3], [5,1,4],
    ]
    @staticmethod
    def get_octahedron(meshName:str = "octa") ->types.Mesh:
        me = bpy.data.meshes.new(meshName)
        me.from_pydata(vertices=SHAPES.octa_verts, edges=[], faces=SHAPES.octa_faces)
        return me

    tetra_verts = octa_verts[:-1]
    tetra_faces = octa_faces[:4]+[[4,3,2,1]]
    @staticmethod
    def get_tetrahedron(meshName:str = "tetra") ->types.Mesh:
        me = bpy.data.meshes.new(meshName)
        me.from_pydata(vertices=SHAPES.tetra_verts, edges=[], faces=SHAPES.tetra_faces)
        return me

    cuboid_verts = [
        Vector((1, 0, 1)), Vector((0, 1, 1)), Vector((-1, 0, 1)), Vector((0, -1, 1)),
        Vector((1, 0, -1)), Vector((0, 1, -1)), Vector((-1, 0, -1)), Vector((0, -1, -1)),
    ]
    cuboid_faces = [
        [0,1,2,3], [7,6,5,4],
        [4,5,1,0], [5,6,2,1], [6,7,3,2], [7,4,0,3],
    ]
    @staticmethod
    def get_cuboid(meshName:str = "cuboid") ->types.Mesh:
        me = bpy.data.meshes.new(meshName)
        me.from_pydata(vertices=SHAPES.cuboid_verts, edges=[], faces=SHAPES.cuboid_faces)
        return me