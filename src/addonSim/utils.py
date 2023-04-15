import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)

from .ui import DEV_log

from mathutils import Vector, Matrix


# -------------------------------------------------------------------

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

def cfg_copyProps(src, dest):
    """ Copy all properties of the property group to the object """
    # The whole property is read-only but its values can be modified, avoid writing it one by one...
    for prop_name in dir(src):
        if not prop_name.startswith("__") and not callable(getattr(src, prop_name)):
            try:
                setattr(dest, prop_name, getattr(src, prop_name))
            except AttributeError:
                # Avoid read-only RNA types
                pass

# -------------------------------------------------------------------

def transform_verts(verts: list[Vector], matrix) -> list[Vector, 6]:
    """ INPLACE: Transform given vertices by the matrix """
    verts_world = [matrix @ v.co for v in verts]

def get_worldVerts(obj: types.Object) -> list[Vector, 6]:
    """ Get the object vertices in world space """
    mesh = obj.data
    matrix = obj.matrix_world

    verts_world = [matrix @ v.co for v in mesh.vertices]
    return verts_world

def get_worldBB_radius(obj: types.Object, margin_disp = 0.0) -> tuple[list[Vector, 6], float]:
    """ Get the object bounding box MIN/MAX Vector pair in world space """
    matrix = obj.matrix_world
    bb_world_full = [matrix @ Vector(v) for v in obj.bound_box]

    disp = Vector()
    disp.xyz = margin_disp
    bb_world = (bb_world_full[0]- disp, bb_world_full[6] + disp)
    bb_radius = ((bb_world[0] - bb_world[1]).length / 2.0)

    # TODO atm limited to mesh, otherwise check and use depsgraph
    #DEV_log("Found %d bound verts" % len(bb_world_full))
    return bb_world, bb_radius

def get_worldFaces_4D(obj: types.Object, n_disp = 0.0) -> list[Vector, Vector]:
    """ Get the object faces as 4D vectors in world space """
    mesh = obj.data
    matrix = obj.matrix_world
    matrix_normal = matrix.inverted_safe().transposed().to_3x3()

    # displace the center a bit by n_disp
    face_centers = [matrix @ (f.center + f.normal * n_disp) for f in mesh.polygons]
    face_normals = [matrix_normal @ f.normal for f in mesh.polygons]

    faces_4D = [
            Vector( [fn.x, fn.y, fn.z, fn.dot(fc)] )
        for (fc,fn) in zip(face_centers, face_normals)
    ]
    return faces_4D

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
    #print("^BEFORE update")

    if obj.parent is None:
        obj.matrix_world = obj.matrix_basis
    else:
        obj.matrix_world = obj.parent.matrix_world @ obj.matrix_parent_inverse @ obj.matrix_basis

    #trans_printMatrices(obj)
    #print("^AFTER update")

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

def delete_objectRec(obj: types.Object):
    """ Delete the object and children recursively """
    for child in obj.children:
        delete_objectRec(child)
    bpy.data.objects.remove(obj, do_unlink=True)

def delete_childrenRec(ob_father: types.Object):
    """ Delete the children objects recursively """
    for child in ob_father.children:
        delete_objectRec(child)

def get_child(obj: types.Object, name: str):
    """ Find child by name (starts with to avoid limited exact names) """
    # All names are unique, even under children hierarchies. Blender adds .001 etc
    nameSub = name+"."

    # TODO tried to add a property pointer to types.Object but the addon cannot have it? for now use name
    for child in obj.children:
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
    """ Child object with the same options as the viewport, also updates the child world and local matrix """
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

def gen_child(obj: types.Object, name: str, mesh: types.Mesh, hide: bool, context: types.Context):
    """ Generate a new child with the CHILD meta_type"""
    obj_child = bpy.data.objects.new(name, mesh)
    obj_child.mw_gen.meta_type = {"CHILD"}
    obj_child.parent = obj
    context.scene.collection.objects.link(obj_child)
    obj_child.hide_set(hide)
    return obj_child

def gen_childClean(obj: types.Object, name: str, mesh: types.Mesh, hide: bool, context: types.Context):
    """ Generate a new child, delete the previous one if found """
    obj_child = get_child(obj, name)
    if obj_child:
        delete_objectRec(obj_child)
    return gen_child(obj, name, mesh, hide, context)

# -------------------------------------------------------------------

def match_anySub(word: str, subs: list) -> bool:
    for sub in subs:
        if sub in word:
            return True
    return False

def rnd_seed(s: int = None) -> int:
    """ Persists across separate module imports, return the seed to store in the config """
    import mathutils.noise as bl_rnd
    import random as rnd

    if s is None or s < 0:
        from datetime import datetime
        tim = datetime.now()
        s = tim.hour*10000+tim.minute*100+tim.second

    rnd.seed(s)
    bl_rnd.seed_set(s)
    return s