import bpy.types as types
from mathutils import Vector, Matrix, Quaternion

from . import utils


# transform utils: math and 3D algebra + some scene interaction
#-------------------------------------------------------------------

getPerpendicular_stable_minMagSq = 1e-3*1e-3
""" small magnitudes will be unstable when normalizing """

def getPerpendicular_stable(n:Vector, normalize=True):
    """ find the most stable perpendicular vector """

    global getPerpendicular_stable_minMagSq
    if getPerpendicular_stable_minMagSq:
        assert(n.length_squared > getPerpendicular_stable_minMagSq)

    # pick the axis vector that yields the lowest dot product (least aligned one)
    Ax, Ay, Az = abs(n.x), abs(n.y), abs(n.z)

    # do cross product with that axis (directly compose the resulting vector)
    if Ax < Ay:
        if Ax < Az:
            perp = Vector((0, -n.z, n.y))
        else:
            perp = Vector((-n.y, n.x, 0))
    else:
        if Ay < Az:
            perp = Vector((n.z, 0, -n.x))
        else:
            perp = Vector((-n.y, n.x, 0))

    if normalize: perp.normalize()
    return perp

def getPerpendicularBase_stable(n:Vector, normalize=True):
    """ find the most stable basis """
    perp = getPerpendicular_stable(n, normalize)
    perp2 = n.cross(perp)

    if normalize: perp2.normalize()
    return perp, perp2

#-------------------------------------------------------------------

def transform_points(points: list[Vector] |  list[list], matrix) -> list[Vector]:
    """ INPLACE: Transform given points by the trans matrix """
    # no list comprehension of the whole list, asigning to a reference var changes the reference not the referenced
    for i,p in enumerate(points):
        points[i] = matrix @ Vector(p)

def get_verts(obj: types.Object, worldSpace=False) -> list[Vector, 6]:
    """ Get the object vertices in world space """
    mesh = obj.data

    if worldSpace:
        matrix = obj.matrix_world
        verts = [matrix @ v.co for v in mesh.vertices]
    else:
        verts = [v.co for v in mesh.vertices]
    return verts

def get_bb_data(obj: types.Object, margin_disp = 0.0, worldSpace=False) -> tuple[list[Vector], float, float]:
    """ Get the object bounding box MIN/MAX Vector pair in world space
        # NOTE:: atm limited to mesh, otherwise check and use depsgraph
    """
    disp = Vector([margin_disp]*3)

    if worldSpace:
        matrix = obj.matrix_world
        bb_full = [matrix @ Vector(v) for v in obj.bound_box]
    else:
        bb_full = [Vector(v) for v in obj.bound_box]

    bb = (bb_full[0]- disp, bb_full[6] + disp)
    bb_center = (bb[0] + bb[1]) / 2.0
    bb_radius = (bb_center - bb[0]).length
    #bb_diag = (bb[0] - bb[1])
    #bb_radius = (bb_diag.length / 2.0)

    return bb, bb_center, bb_radius

def get_faces_4D(obj: types.Object, n_disp = 0.0, worldSpace=False) -> list[Vector, Vector]:
    """ Get the object faces as 4D vectors in world space """
    mesh = obj.data

    if worldSpace:
        matrix = obj.matrix_world
        matrix_normal = matrix.inverted_safe().transposed().to_3x3()
        # displace the center a bit by n_disp
        face_centers = [matrix @ (f.center + f.normal * n_disp) for f in mesh.polygons]
        face_normals = [matrix_normal @ f.normal for f in mesh.polygons]

    else:
        face_centers = [(f.center + f.normal * n_disp) for f in mesh.polygons]
        face_normals = [f.normal for f in mesh.polygons]

    faces4D = [
            Vector( [fn.x, fn.y, fn.z, fn.dot(fc)] )
        for (fc,fn) in zip(face_centers, face_normals)
    ]
    return faces4D

#-------------------------------------------------------------------

def get_composedMatrix(loc:Vector, rot:Quaternion, scale:Vector) -> Matrix:
    T = Matrix.Translation(loc)
    R = rot.to_matrix().to_4x4()
    S = Matrix.Diagonal(scale.to_4d())
    #I = Matrix()

    #assert(obj.matrix_basis == T @ R @ S)
    return T @ R @ S

def get_normalMatrix(matrix_world: Matrix) -> Matrix:
    # Normals will need a normal matrix to transform properly
    return matrix_world.inverted_safe().transposed().to_3x3()

def get_worldMatrix_normalMatrix(obj: types.Object, update = False) -> tuple[Matrix, Matrix]:
    """ Get the object world matrix and normal world matrix """
    if update: trans_update(obj)
    matrix:Matrix = obj.matrix_world.copy()

    return matrix, get_normalMatrix(matrix)

def get_worldMatrix_unscaled(obj: types.Object, update = False) -> Matrix:
    """ Get the object world matrix without scale """
    if update: trans_update(obj)
    loc, rot, scale = obj.matrix_world.decompose()
    return get_composedMatrix(loc, rot, Vector([1.0]*3))

#-------------------------------------------------------------------

def trans_update(obj: types.Object, log=False):
    """ Updates the world matrix of the object, better than updating the whole scene with context.view_layer.update()
        * But this does not take into account constraints, only parenting.
        # XXX:: parent matrix not updated rec tho
    """
    if log:
        trans_printMatrices(obj)
        print("^ BEFORE update")

    if obj.parent is None:
        obj.matrix_world = obj.matrix_basis
    else:
        obj.matrix_world = obj.parent.matrix_world @ obj.matrix_parent_inverse @ obj.matrix_basis

    if log:
        trans_printMatrices(obj)
        print("^ AFTER update")

def trans_reset(obj: types.Object, locally = True, log=False):
    """ Reset all transformations of the object (does reset all matrices too) """
    if log:
        trans_printMatrices(obj)
        print("^ BEFORE reset")

    if locally:
        obj.matrix_basis = Matrix.Identity(4)
    else:
        obj.matrix_world = Matrix.Identity(4)

    if log:
        trans_printMatrices(obj)
        print("^ AFTER reset")

def trans_printMatrices(obj: types.Object, printName=True):
    """ Print all transform matrices, read the code for behavior description! """
    if printName:
        print(f"> (matrices) {obj.name}")
        print(f"> (parent)   {obj.parent}")

    # calculated on scene update and takes into account parenting (see trans_update) plus other constraints etc
    print(obj.matrix_world, "matrix_world\n")
    # calculate on scene update and also when parenting, but relative to the matrix world at that time
    print(obj.matrix_local, "matrix_local\n")

    # calculated at the time of parenting, is the inverted world matrix of the parent
    print(obj.matrix_parent_inverse, "matrix_parent_inverse\n")

    # calculated on pos/rot/scale update and also when world/local is modified
    print(obj.matrix_basis, "matrix_basis\n")
    print()

#-------------------------------------------------------------------

def scale_objectBB(obj: types.Object, s:float|Vector, replace_s = True):
    """ Scale an object aroung its BB center """
    bb, bb_center, bb_radius = get_bb_data(obj, worldSpace=True)
    scale_object(**utils.get_kwargs(), pivot = bb_center)

def scale_object(obj: types.Object, s:float|Vector, replace_s = True, pivot:Vector = None):
    """ Scale an object optionally around a pivot point
        # WIP:: pivots space world/local etc break + hard to replace s too -> move center of curves to its center?
    """
    sv = assure_vector3(s)
    if not replace_s: sv *= obj.scale

    if not pivot:
        obj.scale = sv

    # pivot requires a change of basis
    else:
        M = (
            Matrix.Translation(pivot) @
            Matrix.Diagonal(sv).to_4x4() @
            #Matrix.Rotation(angle, 4, axis) @
            Matrix.Translation(-pivot)
            )

        #trans_printMatrices(obj)
        obj.matrix_world = M @ get_worldMatrix_unscaled(obj)
        #trans_update(obj,log=True)

def scale_objectChildren(obj_father: types.Object, s:float|Vector, replace_s=True, pivotBB=False, ignore_empty=True, rec=True):
    """ Scale an object children optionally ignoring empty """
    toScale = obj_father.children if not rec else obj_father.children_recursive
    sv = assure_vector3(s)

    for child in toScale:
        if ignore_empty and child.type == "EMPTY": continue

        #trans_update(child)
        if pivotBB: scale_objectBB(child, sv, replace_s)
        #if pivotBB: scale_object(child, sv, replace_s, pivot=Vector([1,0,0]))
        else: scale_object(child, sv, replace_s)

#-------------------------------------------------------------------

def assure_vector3(val_v3):
    """ NOTE:: converts single values to 3D, skips vectors (not checked if 3D tho) """
    if not isinstance(val_v3, Vector):
        return Vector([val_v3]*3)
    return val_v3