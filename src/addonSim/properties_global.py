import bpy
import bpy.types as types
import bpy.props as props

from . import handlers
from .properties_utils import Prop_inspector, RND_config

from . import utils_scene
from .utils_dev import DEV


#-------------------------------------------------------------------

class MW_id(types.PropertyGroup):
    """ Property stored in the objects to identify the root and other ID"""

    meta_type: props.EnumProperty(
        name="Type", description="Meta type added to the object to control some logic",
        items=(
            ('NONE', "No fracture", "No fracture generated"),
            ('ROOT', "Root object", "Root object holding the fracture"),
            ('CHILD', "Child object", "Child object part of the fracture"),
        ),
        default={'NONE'},
        options={'ENUM_FLAG'},
    )

    storage_id: props.IntProperty(
        name="Storage id", description="Id to access the pairing global storage data",
        default=-1,
    )

    cell_id: props.IntProperty(
        name="Cell id", description="Id that matches the voronoi cell index",
        default=-1,
    )

    cell_state: props.IntProperty(
        name="Cell state", description="State that matches the cont cell state",
        default=-1,
    )

#-------------------------------------------------------------------

class MW_id_utils:
    """ MW_id util functions stored outside the class to avoid all the memory footprint inside the objects"""

    @staticmethod
    def isRoot(obj: types.Object) -> bool:
        """ Check if this is a root object, core the fracture (holds most of the config) """
        return "ROOT" in obj.mw_id.meta_type
    @staticmethod
    def setRoot(obj: types.Object):
        obj.mw_id.meta_type = {"ROOT"}
    @staticmethod
    def isMetaChild(obj: types.Object) -> bool:
        """ Check if this is a child object part of a fracture (but could be either a cell, link, or intermediate object) """
        return "CHILD" in obj.mw_id.meta_type
    @staticmethod
    def setMetaChild(obj: types.Object):
        obj.mw_id.meta_type = {"CHILD"}

    @staticmethod
    def hasRoot(obj: types.Object) -> bool:
        """ Check if the object is part of a fracture (default value objects have) """
        #DEV.log_msg(f"hasRoot check: {obj.name} -> {obj.mw_id.meta_type}", {"REC", "CFG"})
        return "NONE" not in obj.mw_id.meta_type

    @staticmethod
    def getRoot(obj: types.Object) -> types.Object | None:
        """ Retrieve the root object holding the config (MW_id forward declared)"""
        #DEV.log_msg(f"getRoot search: {obj.name} -> {obj.mw_id.meta_type}", {"REC", "CFG"})
        if "NONE" in obj.mw_id.meta_type:
            return None

        try:
            obj_chain = obj
            while "CHILD" in obj_chain.mw_id.meta_type:
                obj_chain = obj_chain.parent

            # NOTE:: check the root is actually root: could happen if an object is modified at some step by the obj
            if "ROOT" not in obj_chain.mw_id.meta_type: raise ValueError("Chain ended with no root")
            #DEV.log_msg(f"getRoot chain end: {obj_chain.name}", {"RET", "CFG"})
            return obj_chain

        # the parent was removed
        except AttributeError:
            DEV.log_msg(f"getRoot chain broke: {obj.name} -> no rec parent", {"ERROR", "CFG"})
            return None
        # the parent was not root
        except ValueError:
            DEV.log_msg(f"getRoot chain broke: {obj_chain.name} -> not root ({obj_chain.mw_id.meta_type})", {"ERROR", "CFG"})
            return None

    @staticmethod
    def getSceneRoots(scene: types.Scene) -> list[types.Object]:
        """ Retrieve the root objects in the scene, if any (empty list)
            # OPT:: in some cases could use the global storage instead of iterating the scene
        """
        roots = [ obj for obj in scene.objects if MW_id_utils.isRoot(obj) ]
        return roots

    @staticmethod
    def getSceneRoot_any(scene: types.Scene) -> list[types.Object]:
        """ Retrieve the first root object found in the scene, if any
            # OPT:: in some cases could use the global storage instead of iterating the scene
        """
        for obj in scene.objects:
            if MW_id_utils.isRoot(obj):
                return obj
        return None

    @staticmethod
    def setMetaType_rec(obj: types.Object, type: set[str], skipParent = False, childrenRec = True):
        """ Set the property to the object and all its children (dictionary ies copied, not referenced)
            # NOTE:: acessing obj children is O(len(bpy.data.objects)), so just call it on the root again
            # OPT:: could avoid using this and just set the children like for cell_id?
        """
        if not skipParent:
            obj.mw_id.meta_type = type.copy()

        toSet = obj.children_recursive if childrenRec else obj.children
        #DEV.log_msg(f"Setting {type} to {len(toSet)} objects", {"CFG"})
        for child in toSet:
            child.mw_id.meta_type = type.copy()

    @staticmethod
    def resetMetaType(obj: types.Object):
        obj.mw_id.meta_type = {"NONE"}

    #-------------------------------------------------------------------

    storage_uuid = 0
    """ Simple counter as uuid
        # OPT:: should be a read-only property
    """

    @staticmethod
    def genStorageId(obj: types.Object):
        """ Set a new UUID for the storage, usually best to use getStorageId. Does not check the current id beforehand. """
        obj.mw_id.storage_id = MW_id_utils.storage_uuid
        MW_id_utils.storage_uuid += 1

    @staticmethod
    def hasStorageId(obj: types.Object):
        """ Check if the storage_id has been initialized, both the root and cells have it """
        return obj.mw_id.storage_id != -1

    @staticmethod
    def sameStorageId(obj_a: types.Object, obj_b: types.Object):
        """ Check if both objects are part of the same fracture """
        return obj_a.mw_id.storage_id == obj_b.mw_id.storage_id

    @staticmethod
    def getStorageId(obj: types.Object):
        """ Gets the storage id (assigns new uuid when not set yet) """
        if not MW_id_utils.hasStorageId(obj):
            MW_id_utils.genStorageId(obj)
        return obj.mw_id.storage_id

    @staticmethod
    def getStorageId_assert(obj: types.Object):
        """ Gets the storage id (raises an exception if the id is not set yet) """
        if not MW_id_utils.hasStorageId(obj):
            raise ValueError(f"{obj.name}: Invalid storage id (-1)!")
        return obj.mw_id.storage_id

    @staticmethod
    def resetStorageId(obj: types.Object):
        """ Leave storage_id as not initilized """
        obj.mw_id.storage_id = -1

    #-------------------------------------------------------------------

    @staticmethod
    def hasCellId(obj: types.Object):
        """ Check if the cell_id has been initialized, meaning this is a cell object! """
        return obj.mw_id.cell_id != -1

    @staticmethod
    def resetCellId(obj: types.Object):
        """ Leave cell_id as not initilized """
        obj.mw_id.cell_id = -1


#-------------------------------------------------------------------

class MW_global_storage:
    """  Blender properties are quite limited, ok for editting in the UI but for just data use python classes.
        # NOTE:: atm this storage is lost on file or module reload... could store in a .json as part of the .blend
    """

    id_fracts       = dict() # id:int -> MW_fract
    id_fracts_obj   = dict() # id:int -> Object

    @classmethod
    def addFract(cls, fract, obj):
        id = MW_id_utils.getStorageId(obj)
        DEV.log_msg(f"Add: {obj.name} ({id})...", {"GLOBAL", "STORAGE"})

        # add the fract and the obj to the storage
        if id in cls.id_fracts:
            DEV.log_msg(f"Replacing found fract", {"GLOBAL", "STORAGE", "ERROR"})
        cls.id_fracts[id] = fract
        cls.id_fracts_obj[id] = obj
        return id

    @classmethod
    def getFract_fromID(cls, id):
        #DEV.log_msg(f"Get: {id}", {"GLOBAL", "STORAGE"})
        try:
            return cls.id_fracts[id]
        except KeyError:
            DEV.log_msg(f"Not found {id}: probably reloaded the module?", {"GLOBAL", "STORAGE", "ERROR"})

    @classmethod
    def getFract(cls, obj):
        id = MW_id_utils.getStorageId_assert(obj)
        return cls.getFract_fromID(id)

    @classmethod
    def hasFract(cls, obj):
        id = MW_id_utils.getStorageId_assert(obj)
        return id in cls.id_fracts

    @classmethod
    def freeFract_fromID(cls, id):
        DEV.log_msg(f"Free: {id}", {"GLOBAL", "STORAGE"})
        try:
            # delete the fract and only pop the obj
            fract = cls.id_fracts.pop(id)
            del fract.cont
            del fract.links
            del fract.sim
            del fract
            obj = cls.id_fracts_obj.pop(id)
        except KeyError:
            DEV.log_msg(f"Not found {id}: probably reloaded the module?", {"GLOBAL", "STORAGE", "ERROR"})

    @classmethod
    def freeFract(cls, obj):
        id = MW_id_utils.getStorageId_assert(obj)
        return cls.freeFract_fromID(id)

    @classmethod
    def freeFract(cls, obj):
        id = MW_id_utils.getStorageId_assert(obj)
        return cls.freeFract_fromID(id)

    @classmethod
    def freeFract_attempt(cls, obj):
        if MW_id_utils.hasStorageId(obj):
            id = obj.mw_id.storage_id
            if id in cls.id_fracts:
                cls.freeFract_fromID(id)

    #-------------------------------------------------------------------

    # callback triggers
    enable_autoPurge_default = False
    enable_autoPurge = enable_autoPurge_default

    @classmethod
    def getFracts_splitID_needsSanitize(cls):
        """ Detect broken references to scene objects """
        broken = []
        ok = []

        for id,obj in cls.id_fracts_obj.items():
            if utils_scene.needsSanitize(obj):
                broken.append(id)
            else:
                ok.append(id)
        return ok, broken

    @classmethod
    def purgeFracts(cls, broken = None):
        """ Remove fracts of deleted scene objects (that could appear again with UNDO etc)"""
        if broken is None:
            ok, broken = cls.getFracts_splitID_needsSanitize()

        DEV.log_msg(f"Purging {len(broken)}: {broken}", {"GLOBAL", "STORAGE", "SANITIZE"})
        for id in broken:
            cls.freeFract_fromID(id)

    @classmethod
    def recoverFracts(cls, broken = None):
        """ Try to recover objects that might have pop back into the scene """
        if broken is None:
            ok, broken = cls.getFracts_splitID_needsSanitize()
        DEV.log_msg(f"Check recover {len(broken)}: {broken}", {"GLOBAL", "STORAGE", "SANITIZE"})

        # skip query scene roots when there are no broken
        if not broken:
            return

        roots = MW_id_utils.getSceneRoots(bpy.context.scene)
        recovered = []
        for root in roots:
            id = root.mw_id.storage_id
            if id in broken:
                recovered.append(id)
                cls.id_fracts_obj[id] = root

        DEV.log_msg(f"Recovered {len(recovered)} / {len(roots)} roots: {recovered}", {"GLOBAL", "STORAGE", "SANITIZE"})
        return recovered

    @classmethod
    def sanitizeFracts(cls):
        ok, broken = cls.getFracts_splitID_needsSanitize()

        # free from memory unreferences conts (could pop back again tho)
        if cls.enable_autoPurge:
            cls.purgeFracts(broken)

        # some might reapear when undoing a delete
        else:
            recovered = cls.recoverFracts(broken)
            if recovered:
                ok += recovered

        # potentially recalculate some parts of the fract
        for id in ok:
            cls.id_fracts[id].sanitize(cls.id_fracts_obj[id])

    @classmethod
    def sanitizeFracts_callback(cls, _scene_=None, _undo_name_=None):
        cls.sanitizeFracts()

#-------------------------------------------------------------------

class MW_global_selected:
    """  Keep a reference to the selected root with a callback on selection change """
    # OPT:: store the data in the scene/file to avoid losing it on reload? Still issues with global storage anyway
    #class MW_global_selected(types.PropertyGroup): + register the class etc
    #my_object: bpy.props.PointerProperty(type=bpy.types.Object)

    # root fracture object
    root                : types.Object = None
    fract                              = None
    prevalid_root       : types.Object = None
    prevalid_fract                     = None
    """ prevalid are the previous ones and always valid (not at the start) """

    # common selection
    selection           : types.Object = None
    current             : types.Object = None
    prevalid_current    : types.Object = None

    @classmethod
    def setSelected(cls, new_selection):
        """ Update global selection status and query fract root
            # NOTE:: new_selection lists objects alphabetically not by order of selection
            # OPT:: multi-root selection? work with current active instead of last new active?
        """
        rootChange = False

        if new_selection:
            if cls.current:
                cls.prevalid_current = cls.current
            cls.selection = new_selection.copy() if isinstance(new_selection, list) else [new_selection]
            #cls.current = cls.selection[-1]

            # will differ later if the active_object is changed to one among already selected
            if bpy.context.active_object:
                cls.current = bpy.context.active_object
            else:
                cls.current = new_selection[0] # multi-selection might leave none as active

            newRoot = MW_id_utils.getRoot(cls.current)
            if newRoot:
                if cls.root:
                    cls.prevalid_root  = cls.root
                    cls.prevalid_fract = cls.fract
                else:
                    # going from none to something triggers the callback
                    rootChange = True

                cls.root  = newRoot
                cls.fract = MW_global_storage.getFract(newRoot)

                # new root selected callback
                if cls.root != cls.prevalid_root:
                    rootChange = True

            else:
                cls.root = None
                cls.fract = None

        else:
            cls.reset()

        cls.prevalid_sanitize()
        cls.logSelected()
        if rootChange:
            DEV.log_msg(f"Selection ROOT change: {cls.root.name}", {"CALLBACK", "SELECTION", "ROOT"})
            cls.callback_rootChange_actions.dispatch([cls.root])

    @classmethod
    def last_root(cls):
        if cls.root:
            return cls.root
        else:
            return cls.prevalid_root

    @classmethod
    def last_fract(cls):
        if cls.fract:
            return cls.fract
        else:
            return cls.prevalid_fract

    #-------------------------------------------------------------------

    @classmethod
    def recheckSelected(cls):
        cls.sanitize()
        cls.justReloaded = False
        cls.setSelected(bpy.context.selected_objects)

    @classmethod
    def logSelected(cls):
        DEV.log_msg(f"root: {cls.root.name if cls.root else '...'} | last: {cls.current.name if cls.current else '...'}"
                    f" | selection: {len(cls.selection) if cls.selection else '...'}", {"GLOBAL", "SELECTED"})

    @classmethod
    def reset(cls):
        """ Reset all to None but keep sanitized references to prevalid """
        if cls.current:
            cls.prevalid_current = cls.current
        if cls.root:
            cls.prevalid_root = cls.root
        if cls.fract:
            cls.prevalid_fract = cls.fract

        cls.selection = None
        cls.current   = None
        cls.root      = None
        cls.fract     = None
        cls.prevalid_sanitize()

    @classmethod
    def sanitize(cls):
        """ Potentially sanitize objects no longer on the scene """
        cleaned = False

        if utils_scene.needsSanitize(cls.current):
            cls.reset()
            cleaned |= True
        else:
            cleaned |= cls.prevalid_sanitize()

        return cleaned

    @classmethod
    def prevalid_sanitize(cls):
        cleaned = False

        cls.prevalid_current = utils_scene.returnSanitized(cls.prevalid_current)
        if cls.prevalid_current is None:
            cleaned |= True

        cls.prevalid_root = utils_scene.returnSanitized(cls.prevalid_root)
        if cls.prevalid_root is None:
            cls.prevalid_fract = None
            cleaned |= True

        # sometimes root alone fails?
        cls.root = utils_scene.returnSanitized(cls.root)
        if cls.root is None:
            cls.fract = None
            cleaned |= True

        return cleaned

    # callback triggers
    @classmethod
    def setSelected_callback(cls, _scene_=None, _selected_=None):
        cls.setSelected(_selected_)

    @classmethod
    def sanitizeSelected_callback(cls, _scene_=None, _name_selected_=None):
        cls.sanitize()
        cls.prevalid_sanitize()

    # callback serviced
    callback_rootChange_actions = handlers.Actions()


#-------------------------------------------------------------------
# Blender events

classes = [
    Prop_inspector,
    RND_config,
    MW_id,
]
_name = f"{__name__[14:]}" #\t(...{__file__[-32:]})"

def register():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "REG"})

    # sanitize in case of reload module
    MW_global_selected.sanitize()

    # cannot be done mid loading -> some classes not registered yet etc (fails no matter register order)
    #if DEV.SELECT_ROOT_LOAD:
    #    from .utils_scene import select_unhide
    #    from .properties_global import MW_id_utils
    #    root_any =  MW_id_utils.getSceneRoot_any()
    #    if root_any:
    #        utils_scene.select_unhide(root_any)
    # do it afterwards once from the panel
    MW_global_selected.justReloaded = DEV.SELECT_ROOT_LOAD

    # callbaks
    handlers.callback_selectionChange_actions.append(MW_global_selected.setSelected_callback)
    handlers.callback_undo_actions.append(MW_global_storage.sanitizeFracts_callback)
    handlers.callback_redo_actions.append(MW_global_storage.sanitizeFracts_callback)

    # OPT:: callback_loadFile not very well tested tho
    handlers.callback_loadFile_actions.append(MW_global_selected.sanitizeSelected_callback)
    handlers.callback_loadFile_actions.append(MW_global_storage.sanitizeFracts_callback)

    for cls in classes:
        bpy.utils.register_class(cls)

    # appear as part of default object props
    bpy.types.Object.mw_id = props.PointerProperty(
        type=MW_id,
        name="MW_id", description="MW fracture ids")

def unregister():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})

    # callbacks (might end up set or not, use check)
    handlers.callback_selectionChange_actions.remove(MW_global_selected.setSelected_callback)
    handlers.callback_undo_actions.removeCheck(MW_global_storage.sanitizeFracts_callback)
    handlers.callback_redo_actions.removeCheck(MW_global_storage.sanitizeFracts_callback)

    handlers.callback_loadFile_actions.remove(MW_global_selected.sanitizeSelected_callback)
    handlers.callback_loadFile_actions.remove(MW_global_storage.sanitizeFracts_callback)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})