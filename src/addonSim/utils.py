import bpy
import bpy.types as types
from mathutils import Vector, Matrix, Quaternion

from .utils_dev import DEV
from .stats import getStats, timeit


#-------------------------------------------------------------------
# IDEA:: split into utils scene, math, misc etc -> at least blender / non-blender


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
    """ Get the object bounding box MIN/MAX Vector pair in world space """
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

    # NOTE:: atm limited to mesh, otherwise check and use depsgraph
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

# XXX:: parent matrix not updated rec tho
# OPT:: move log flag to dev
def trans_update(obj: types.Object, log=False):
    """ Updates the world matrix of the object, better than updating the whole scene with context.view_layer.update()
        * But this does not take into account constraints, only parenting.
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

    # make a raw copy or leave a linked mesh
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

def delete_object(obj: types.Object, ignore_data = False, ignore_mat = False):
    data,type,mat = obj.data, obj.type, obj.active_material
    #DEV.log_msg(f"Deleting {obj.name}", {"DELETE", "OBJ"})
    bpy.data.objects.remove(obj)

    # NOTE:: meshes/data is leftover otherwise, delete after removing the object user
    if not ignore_data and data:
        delete_data(data, type)
    if not ignore_mat and mat:
        delete_mat(mat)

# OPT:: logamount as flag in dev not here
def delete_objectRec(obj: types.Object, ignore_data = False, logAmount=False):
    """ Delete the object and children recursively """
    delete_objectChildren(obj, ignore_data, rec=True, logAmount=logAmount)
    delete_object(obj, ignore_data)

def delete_objectChildren(ob_father: types.Object, ignore_data = False, rec=True, logAmount=False):
    """ Delete the children objects """

    # deleting a parent leads to a deleted children (not its mesh tho)
    toDelete = ob_father.children if not rec else ob_father.children_recursive
    if logAmount:
        DEV.log_msg(f"Deleting {len(toDelete)} objects", {"DELETE"})

    for child in reversed(toDelete):
        delete_object(child, ignore_data)

def delete_data(data, type = "MESH", do_unlink=False):
    """ NOTE:: seems like deleting the data deletes the object? """
    if not do_unlink and data.users: return
    #DEV.log_msg(f"Deleting {data.name}", {"DELETE", "DATA"})
    try:
        if type == "MESH":      collection=bpy.data.meshes
        elif type == "CURVE":   collection=bpy.data.curves
        else: raise TypeError(f"Unimplemented data type {type} from {data.name}")
        collection.remove(data, do_unlink=do_unlink)

    except Exception as e:
        DEV.log_msg(str(e), {"DELETE", "DATA", "ERROR"})

def delete_mat(mat, do_unlink=False):
    if not do_unlink and mat.users: return
    bpy.data.materials.remove(mat, do_unlink=do_unlink)

def delete_orphanData(collectionNames = None, logAmount = True):
    """ When an object is deleted its mesh/data may be left over """
    if collectionNames is None: collectionNames = ["meshes", "curves"]
    DEV.log_msg(f"Checking collections: {collectionNames}", {"DELETE"})

    # dynamically check it has the collection
    for colName in collectionNames:
        colName = colName.strip()
        if not hasattr(bpy.data, colName): continue
        collection = getattr(bpy.data, colName)

        toDelete = []
        for data in collection:
            if not data.users: toDelete.append(data)

        if logAmount: DEV.log_msg(f"Deleting {len(toDelete)}/{len(collection)} {colName}", {"DELETE"})
        for data in toDelete:
            collection.remove(data, do_unlink=False)

#-------------------------------------------------------------------

# OPT:: not robuts... All names are unique, even under children hierarchies. Blender adds .001 etc
def get_nameClean(name):
    try: return name if name[-4] != "." else name[:-4]
    except IndexError: return name

# IDEA:: maybe all children search based methods should return the explored objs
def get_object_fromList(objects: list[types.Object], name: str, exactMatch = True) -> types.Object|None:
    """ Find an object by name inside the list provided """
    if exactMatch:
        for obj in objects:
            if obj.name == name: return obj

    # cleaning the suffix instead of direclty comparing the names
    else:
        name = get_nameClean(name)
        for obj in objects:
            cleanName = get_nameClean(obj.name)
            if cleanName == name: return obj

    return None

def get_object_fromScene(scene: types.Scene, name: str, exactMatch = True) -> types.Object|None:
    """ Find an object in the scene by name (starts with to avoid limited exact names). Returns the first found. """
    return get_object_fromList(scene.objects, name, exactMatch)

def get_child(obj: types.Object, name: str, rec=False, exactMatch = False) -> types.Object|None:
    """ Find child by name (starts with to avoid limited exact names) """
    toSearch = obj.children if not rec else obj.children_recursive
    return get_object_fromList(toSearch, name, exactMatch)

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

def scale_objectBB(obj: types.Object, s:float|Vector, replace_s = True):
    """ Scale an object aroung its BB center """
    bb, bb_center, bb_radius = get_bb_data(obj, worldSpace=True)
    scale_object(**get_kwargs(), pivot = bb_center)

# WIP:: pivots space world/local etc break + hard to replace s too -> move center of curves to its center?
def scale_object(obj: types.Object, s:float|Vector, replace_s = True, pivot:Vector = None):
    """ Scale an object optionally around a pivot point """
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
    """ Generate a new child with the CHILD mw_id.type """
    obj_child = bpy.data.objects.new(name, mesh)
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
    return gen_child(**get_kwargs())

def gen_childReuse(
    obj: types.Object, name: str, context: types.Context,
    mesh: types.Mesh = None, keepTrans = True, noInv = False, hide: bool = False
    ):
    """ Generate a new child, reuse the previous one if found """
    obj_child = get_child(obj, name)
    if obj_child:
        #  NOTE:: subtitute to unlink and then delete prev data, otherwise deleting it deletes the object?
        if obj_child.data:
            prevMesh = obj_child.data
            obj_child.data = mesh
            delete_data(prevMesh, obj_child.type)

        #set_child(obj_child, obj, keepTrans, noInv)
        obj_child.hide_set(hide)
        return obj_child

    return gen_child(**get_kwargs())

#-------------------------------------------------------------------

def needsSanitize_object(obj):
    """ Check broken reference to bl object """
    if obj is None: return False
    try:
        name_obj = obj.name
        return False
    except ReferenceError:
        return True

def returnSanitized_object(obj):
    """ Change object to none in case of broken bl object """
    if needsSanitize_object(obj):
        return None
    else:
        return obj

#-------------------------------------------------------------------
# NOTE:: misc utils may be better somewhere else...

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

def rnd_string(length=16):
    """Generates a random string of specified length"""
    import string
    import random as rnd
    letters = string.ascii_letters
    return ''.join(rnd.choice(letters) for _ in range(length))

uuidxLast = -1
def get_uuidx():
    global uuidxLast
    uuidxLast +=1
    return uuidxLast

# OPT:: test perf? timeit(lambda: dict(**get_kwargs()))
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

def assure_vector3(val_v3):
    if not isinstance(val_v3, Vector):
        return Vector([val_v3]*3)
    # NOTE:: also check to_3d?
    return val_v3

def assure_list(val_list):
    if not isinstance(val_list, list):
        return [val_list]
    return val_list

def compare_dicts(dict1, dict2):
    if set(dict1.keys()) != set(dict2.keys()):
        return False
    for key in dict1:
        if dict1[key] != dict2[key]:
            return False
    return True

def listMap_dict(d):
    l = [None] * len(d)
    for k,val in d.items():
        l[k] = val
    return l

def vec3_to_string(v:Vector, fmt:str = ".2f"):
    fmt_vec = f"({{:{fmt}}},{{:{fmt}}},{{:{fmt}}})"
    return f"{fmt_vec}".format(*v)

def key_to_string(k:tuple[int,int], fmt:str = ">2"):
    fmt_vec = f"({{:{fmt}}},{{:{fmt}}})"
    return f"{fmt_vec}".format(*k)