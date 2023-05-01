import bpy
import bpy.types as types
from mathutils import Vector, Matrix

from .preferences import getPrefs, ADDON
from .properties import (
    MW_gen_cfg,
)

from .utils_dev import DEV
from .stats import getStats


# OPT:: split some more files? or import less functions
#-------------------------------------------------------------------

def cfg_hasRoot(obj: types.Object) -> bool:
    """ Quick check if the object is part of a fracture """
    return "NONE" not in obj.mw_gen.meta_type

# TODO:: should really try to acces the parent direclty
# XXX:: too much used around in poll functions, performance hit?
def cfg_getRoot(obj: types.Object) -> tuple[types.Object, MW_gen_cfg]:
    """ Retrieve the root object holding the config """
    if "NONE" in obj.mw_gen.meta_type:
        return obj, None

    # Maybe the user deleted the root only
    try:
        obj_chain = obj
        while "CHILD" in obj_chain.mw_gen.meta_type:
            obj_chain = obj.parent
        return obj_chain, obj_chain.mw_gen
    except:
        DEV.log_msg(f"cfg_getRoot chain broke ({obj.name})", {"ERROR", "CFG"})
        return obj, None


def cfg_setMetaTypeRec(obj: types.Object, type: dict):
    """ Set the property to the object and all its children (dictionary ies copied, not referenced) """
    obj.mw_gen.meta_type = type.copy()
    for child in obj.children:
        cfg_setMetaTypeRec(child, type)

#-------------------------------------------------------------------

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
    getStats().logDt(f"calc bb: r {bb_radius:.3f} (margin {margin_disp:.4f})")
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

    getStats().logDt(f"calc faces4D: {len(faces4D)} (n_disp {n_disp:.4f})")
    return faces4D

def get_worldMatrix_normalMatrix(obj: types.Object, update = False) -> tuple[types.Object, MW_gen_cfg]:
    """ Get the object world matrix and normal world matrix """
    if update: trans_update(obj)
    matrix = obj.matrix_world.copy()

    # Normals will need a normal matrix to transform properly
    matrix_normal = matrix.inverted_safe().transposed().to_3x3()
    return matrix, matrix_normal

#-------------------------------------------------------------------

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

#-------------------------------------------------------------------
# XXX:: all access to obj.children take O(n) where n is ALL objects of the scene...

def copy_object(obj: types.Object, context: types.Context, link_mesh = False, keep_mods = True, namePreffix = "", nameSuffix = "") -> types.Object:
    """ Copy the object but not its children """
    obj_copy: types.Object = obj.copy()
    context.scene.collection.objects.link(obj_copy)

    # make a raw copy of leave a linked mesh
    if not link_mesh and obj.data:
        obj_copy.data = obj.data.copy()
        obj_copy.data.name = f"{namePreffix}{obj.data.name}{nameSuffix}"

    # remove mods or not
    if not keep_mods:
        for mod in obj_copy.modifiers:
            obj_copy.modifiers.remove(mod)

    # avoid setting name unless specified, otherwise the copy gets the priority name without .001
    if namePreffix or nameSuffix:
        obj_copy.name = f"{namePreffix}{obj.name}{nameSuffix}"

    # keep original visibility
    obj_copy.hide_set(obj.hide_get())

    return obj_copy

def copy_objectRec(obj: types.Object, context: types.Context, link_mesh = False, keep_mods = True, namePreffix = "", nameSuffix = "") -> types.Object:
    """ Copy the object along its children """
    obj_copy = copy_object(**get_kwargs())

    # copy rec + set parenting and force them to keep the original world pos
    for child in obj.children:
        child_copy = copy_objectRec(child, **get_kwargs(1))
        child_copy.parent = obj_copy
        child_copy.matrix_world = child.matrix_world
    return obj_copy

#-------------------------------------------------------------------

def delete_object(obj: types.Object, ignore_mesh = False):
    # NOTE:: meshes are leftover otherwise
    if not ignore_mesh and obj.data:
        bpy.data.meshes.remove(obj.data)
    bpy.data.objects.remove(obj)

def delete_objectRec(obj: types.Object, ignore_mesh = False, logAmount=False):
    """ Delete the object and children recursively """
    delete_objectChildren(obj, ignore_mesh, rec=True, logAmount=logAmount)
    delete_object(obj, ignore_mesh)

def delete_objectChildren(ob_father: types.Object, ignore_mesh = False, rec=True, logAmount=False):
    """ Delete the children objects """
    toDelete = ob_father.children if not rec else ob_father.children_recursive
    if logAmount:
        DEV.log_msg(f"Deleting {len(toDelete)} objects", {"DELETE"})

    for child in toDelete:
        delete_object(child, ignore_mesh)

def delete_meshesOrphan(logAmount):
    """ When an object is deleted its mesh may be left over """
    toDelete = []
    for mesh in bpy.data.meshes:
        if not mesh.users: toDelete.append(mesh)

    DEV.log_msg(f"Deleting {len(toDelete)}/{len(bpy.data.meshes)} meshes", {"DELETE"})
    for mesh in toDelete:
        bpy.data.meshes.remove(mesh)

#-------------------------------------------------------------------

def get_object_fromScene(scene: types.Scene, name: str) -> types.Object|None:
    """ Find an object in the scene by name (starts with to avoid limited exact names). Returns the first found. """
    for obj in scene.objects:
        if obj.name.startswith(name): return obj
    return None

def get_child(obj: types.Object, name: str, rec=False) -> types.Object|None:
    """ Find child by name (starts with to avoid limited exact names) """
    toSearch = obj.children if not rec else obj.children_recursive

    for child in toSearch:
        # All names are unique, even under children hierarchies. Blender adds .001 etc
        if child.name.startswith(name): return child
    return None

#-------------------------------------------------------------------

def select_unhide(obj: types.Object, context: types.Context, select=True):
    obj.hide_set(False)

    if select:
        obj.select_set(True)
        context.view_layer.objects.active = obj
        #context.view_layer.objects.selected += [obj]   # appended by select_set
        #context.active_object = obj                    # read-only
    else:
        obj.select_set(False)

    #DEV.log_msg(f"{obj.name}: select {select}", {"SELECT"})

def select_unhideRec(obj: types.Object, context: types.Context, select=True, selectChildren=True):
    """ Hide the object and children recursively """
    for child in obj.children_recursive:
        select_unhide(child, context, selectChildren)
    select_unhide(obj, context, select)

def hide_objectRec(obj: types.Object, hide=True):
    """ Hide the object and children recursively """
    for child in obj.children_recursive:
        hide_objectRec(child, hide)
    obj.hide_set(hide)

#-------------------------------------------------------------------

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

#-------------------------------------------------------------------

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

def get_kwargs(startKey_index = 0):
    from inspect import currentframe, getargvalues
    frame = currentframe().f_back
    keys, _, _, values = getargvalues(frame)
    kwargs = {}
    for key in keys[startKey_index:]:
        if key != 'self':
            kwargs[key] = values[key]
    return kwargs

def get_filtered(listFull:list, filter:str):
    listFiltered = []

    filters = filter.split(",")
    for f in filters:
        f = f.strip()

        # range filter
        if "_" in f:
            i1,i2 = f.split("_")
            listFiltered += listFull[int(i1):int(i2)]
        # specific item
        else:
            try: listFiltered.append(listFull[int(f)])
            except IndexError: pass

    return listFiltered

