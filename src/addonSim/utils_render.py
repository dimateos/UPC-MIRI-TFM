import bpy
import bpy.types as types

from mathutils import Vector, Matrix


# -------------------------------------------------------------------

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


# -------------------------------------------------------------------
