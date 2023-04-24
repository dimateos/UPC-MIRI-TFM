import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

from .utils_dev import DEV
from .stats import getStats

from mathutils import Vector, Matrix


# OPT:: split some more files? or import less functions
# -------------------------------------------------------------------

# TODO:: should really try to acces the parent direclty
# XXX:: too much used around in poll functions, performance hit?
def cfg_getRoot(obj: types.Object) -> tuple[types.Object, MW_gen_cfg]:
    """ Retrieve the root object holding the config """
    if "NONE" in obj.mw_gen.meta_type:
        return obj, None

    else:
        while "CHILD" in obj.mw_gen.meta_type:
            # Maybe the user deleted the root only
            if not obj.parent:
                return obj, None
            obj = obj.parent

        return obj, obj.mw_gen


def cfg_setMetaTypeRec(obj: types.Object, type: dict):
    """ Set the property to the object and all its children (dictionary ies copied, not referenced) """
    obj.mw_gen.meta_type = type.copy()
    for child in obj.children:
        cfg_setMetaTypeRec(child, type)

# -------------------------------------------------------------------

def transform_points(points: list[Vector], matrix) -> list[Vector]:
    """ INPLACE: Transform given points by the trans matrix """
    # no list comprehension of the whole list, asigning to a reference var changes the reference not the referenced
    for i,p in enumerate(points):
        points[i] = matrix @ p

def get_verts(obj: types.Object, worldSpace=False) -> list[Vector, 6]:
    """ Get the object vertices in world space """
    mesh = obj.data

    if worldSpace:
        matrix = obj.matrix_world
        verts = [matrix @ v.co for v in mesh.vertices]
    else:
        verts = [v.co for v in mesh.vertices]
    return verts

def get_bb_radius(obj: types.Object, margin_disp = 0.0, worldSpace=False) -> tuple[list[Vector, 6], float]:
    """ Get the object bounding box MIN/MAX Vector pair in world space """
    disp = Vector()
    disp.xyz = margin_disp

    if worldSpace:
        matrix = obj.matrix_world
        bb_full = [matrix @ Vector(v) for v in obj.bound_box]
    else:
        bb_full = [Vector(v) for v in obj.bound_box]

    bb = (bb_full[0]- disp, bb_full[6] + disp)
    bb_radius = ((bb[0] - bb[1]).length / 2.0)

    # NOTE:: atm limited to mesh, otherwise check and use depsgraph
    getStats().log(f"calc bb: r {bb_radius:.3f} (margin {margin_disp:.4f})")
    return bb, bb_radius

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

    getStats().log(f"calc faces4D: {len(faces4D)} (n_disp {n_disp:.4f})")
    return faces4D

def get_worldMatrix_normalMatrix(obj: types.Object) -> tuple[types.Object, MW_gen_cfg]:
    """ Get the object world matrix and normal world matrix """
    matrix = obj.matrix_world.copy()

    # Normals will need a normal matrix to transform properly
    matrix_normal = matrix.inverted_safe().transposed().to_3x3()
    return matrix, matrix_normal

# -------------------------------------------------------------------

def trans_update(obj: types.Object):
    """ Updates the world matrix of the object, better than updating the whole scene with context.view_layer.update()
        * But this does not take into account constraints, only parenting.
    """
    #trans_printMatrices(obj)
    #print("^ BEFORE update")

    if obj.parent is None:
        obj.matrix_world = obj.matrix_basis
    else:
        obj.matrix_world = obj.parent.matrix_world @ obj.matrix_parent_inverse @ obj.matrix_basis

    #trans_printMatrices(obj)
    #print("^ AFTER update")

def trans_reset(obj: types.Object, locally = True, updateTrans = True):
    """ Reset all transformations of the object (does reset all matrices too) """
    #trans_printMatrices(obj)
    #print("^ BEFORE reset")

    if locally:
        obj.matrix_basis = Matrix.Identity(4)
    else:
        obj.matrix_world = Matrix.Identity(4)

    #trans_printMatrices(obj)
    #print("^ AFTER reset")

def trans_printMatrices(obj: types.Object, printName=True):
    """ Print all transform matrices, read the code for behavior description! """
    print()
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

# -------------------------------------------------------------------
# TODO:: performance hit with teapot due to REC or scene childen access?
# XXX:: all access to obj.children take O(n) where n is ALL objects of the scene...

def copy_objectRec(obj: types.Object, context: types.Context, link_mesh = False, namePreffix: str = None, nameSuffix: str = None) -> types.Object:
    """ Copy the object along its children """
    obj_copy: types.Object = obj.copy()
    if not link_mesh and obj.data:
        obj_copy.data = obj.data.copy()

    context.scene.collection.objects.link(obj_copy)

    if namePreffix is None: namePreffix = ""
    if nameSuffix is None: nameSuffix = ""
    obj_copy.name = f"{namePreffix}{obj.name}{nameSuffix}"

    for child in obj.children:
        child_copy = copy_objectRec(child, context, namePreffix, nameSuffix)
        child_copy.parent = obj_copy
    return obj_copy

def delete_objectRec(obj: types.Object, logAmount=False):
    """ Delete the object and children recursively """
    delete_childrenRec(obj, logAmount)
    bpy.data.objects.remove(obj)

def delete_childrenRec(ob_father: types.Object, logAmount=False):
    """ Delete the children objects recursively """
    childrenRec = ob_father.children_recursive

    if logAmount:
        DEV.log_msg(f"Deleting {len(childrenRec)} objects", {"DELETE"})
    for child in childrenRec:
        bpy.data.objects.remove(child)

def get_object_fromScene(scene: types.Scene, name: str) -> types.Object|None:
    """ Find an object in the scene by name (starts with to avoid limited exact names). Returns the first found. """
    # OPT:: improve as in get_child, also not recursive, could try to use the parent name direclty
    nameSub = name+"."
    for obj in scene.objects:
        if obj.name == name or obj.name.startswith(nameSub):
            return obj
    return None

def get_child(obj: types.Object, name: str) -> types.Object|None:
    """ Find child by name (starts with to avoid limited exact names) """
    # All names are unique, even under children hierarchies. Blender adds .001 etc
    nameSub = name+"."

    for child in obj.children:
        # OPT:: avoid double linear comparison
        if child.name == name or child.name.startswith(nameSub):
            return child
    return None

def hide_objectRec(obj: types.Object, hide=True):
    """ Hide the object and children recursively """
    for child in obj.children:
        hide_objectRec(child)

    obj.hide_set(hide)

# -------------------------------------------------------------------

def set_child(child: types.Object, parent: types.Object, keepTrans = True, noInv = False):
    """ Child object with the same options as the viewport, also updates the child world matrix """
    if keepTrans:
        if noInv:
            # Set the child basis matrix relative to the parent direclty
            child_matrix_local = parent.matrix_world.inverted() @ child.matrix_world
            child.parent = parent
            child.matrix_basis = child_matrix_local
        else:
            # Just set the matrix parent inverse
            child.parent = parent
            child.matrix_parent_inverse = parent.matrix_world.inverted()
    else:
        # Parenting directly so the world matrix will be applied as local
        child.parent = parent
        # Update world matrix manually instead of waiting for scene update, no need with keepTrans
        trans_update(child)

def gen_child(
    obj: types.Object, name: str, context: types.Context,
    mesh: types.Mesh = None, keepTrans = True, noInv = False, hide: bool = False
    ):
    """ Generate a new child with the CHILD meta_type """
    obj_child = bpy.data.objects.new(name, mesh)
    obj_child.mw_gen.meta_type = {"CHILD"}
    context.scene.collection.objects.link(obj_child)

    set_child(obj_child, obj, keepTrans, noInv)
    obj_child.hide_set(hide)
    return obj_child

def gen_childClean(
    obj: types.Object, name: str, context: types.Context,
    mesh: types.Mesh = None, keepTrans = True, noInv = False, hide: bool = False
    ):
    """ Generate a new child, delete the previous one if found """
    obj_child = get_child(obj, name)
    if obj_child:
        delete_objectRec(obj_child)
    return gen_child(obj, name, context, mesh, keepTrans, noInv, hide)

# -------------------------------------------------------------------

def get_timestamp() -> int:
    """ Get current timestamp as int """
    from datetime import datetime
    tim = datetime.now()
    return tim.hour*10000+tim.minute*100+tim.second

def rnd_seed(s: int = None) -> int:
    """ Persists across separate module imports, return the seed to store in the config """
    import mathutils.noise as bl_rnd
    import random as rnd

    if s is None or s < 0:
        s = get_timestamp()

    rnd.seed(s)
    bl_rnd.seed_set(s)
    return s