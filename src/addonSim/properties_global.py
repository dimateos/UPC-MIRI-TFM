import bpy
import bpy.types as types
import bpy.props as props

from . import handlers
from . import utils
from .utils_dev import DEV

from .properties_utils import Prop_inspector

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
        options={'ENUM_FLAG'},
        default={'NONE'},
    )

    storage_id: props.IntProperty(
        name="Storage id", description="Id to access the pairing global storage data",
        default=-1,
    )

    cell_id: props.IntProperty(
        name="Cell id", description="Id that matches the voronoi cell index",
        default=-1,
    )


#-------------------------------------------------------------------

class MW_id_utils:
    """ MW_id util functions stored outside the class to avoid all the memory footprint inside the objects"""

    @staticmethod
    def isRoot(obj: types.Object) -> bool:
        return "ROOT" in obj.mw_id.meta_type
    @staticmethod
    def isChild(obj: types.Object) -> bool:
        return "CHILD" in obj.mw_id.meta_type

    @staticmethod
    def hasRoot(obj: types.Object) -> bool:
        """ Quick check if the object is part of a fracture """
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
        roots = [ obj for obj in scene.objects if MW_id_utils.isRoot(obj) ]
        return roots

    @staticmethod
    def setMetaType(obj: types.Object, type: set[str], skipParent = False, childrenRec = True):
        """ Set the property to the object and all its children (dictionary ies copied, not referenced)
            # NOTE:: acessing obj children is O(len(bpy.data.objects)), so just call it on the root again
            # OPT:: avoid using this and just set the children?
        """
        if not skipParent:
            obj.mw_id.meta_type = type.copy()

        toSet = obj.children_recursive if childrenRec else obj.children
        #DEV.log_msg(f"Setting {type} to {len(toSet)} objects", {"CFG"})
        for child in toSet:
            child.mw_id.meta_type = type.copy()

    def resetMetaType(obj: types.Object):
        obj.mw_id.meta_type = {"NONE"}

    #-------------------------------------------------------------------

    storage_uuid = 0
    """ Simple counter as uuid"""

    @staticmethod
    def setStorageId(obj: types.Object):
        """ Set a new UUID for the storage, usually best to use getStorageId """
        obj.mw_id.storage_id = MW_id_utils.storage_uuid
        MW_id_utils.storage_uuid += 1

    @staticmethod
    def validStorageId(obj: types.Object):
        return obj.mw_id.storage_id != -1

    @staticmethod
    def getStorageId(obj: types.Object):
        """ Gets the storage id (assigns new uuid when needed) """
        if not MW_id_utils.validStorageId(obj):
            MW_id_utils.setStorageId(obj)
        return obj.mw_id.storage_id

    @staticmethod
    def getStorageId_assert(obj: types.Object):
        """ Gets the storage id (excepts when unset) """
        if not MW_id_utils.validStorageId(obj):
            raise ValueError(f"{obj.name}: Invalid storage id (-1)!")
        return obj.mw_id.storage_id

    @staticmethod
    def resetStorageId(obj: types.Object):
        obj.mw_id.storage_id = -1


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
        if MW_id_utils.validStorageId(obj):
            id = obj.mw_id.storage_id
            if id in cls.id_fracts:
                cls.freeFract_fromID(id)

    # callback triggers
    enable_autoPurge_default = False
    enable_autoPurge = enable_autoPurge_default

    @classmethod
    def purgeFracts(cls):
        """ Remove fracts of deleted scene objects (that could appear again with UNDO etc)"""
        toPurge = []

        # detect broken object references
        for id,obj in cls.id_fracts_obj.items():
            if utils.needsSanitize_object(obj):
                toPurge.append(id)

        DEV.log_msg(f"Purging {len(toPurge)}: {toPurge}", {"GLOBAL", "STORAGE"})
        for id in toPurge:
            cls.freeFract_fromID(id)

    @classmethod
    def purgeFracts_callback(cls, _scene_=None, _undo_name_=None):
        if cls.enable_autoPurge:
            cls.purgeFracts()


#-------------------------------------------------------------------

class MW_global_selected:
    """  Keep a reference to the selected root with a callback on selection change """
    # OPT:: store the data in the scene/file to avoid losing it on reload? Still issues with global storage anyway
    #class MW_global_selected(types.PropertyGroup): + register the class etc
    #my_object: bpy.props.PointerProperty(type=bpy.types.Object)

    # root fracture object
    root            : types.Object = None
    fract                          = None
    prevalid_root   : types.Object = None
    prevalid_fract                 = None
    """ prevalid are the previous ones and always valid (not at the start) """

    # common selection
    selection       : types.Object = None
    last            : types.Object = None
    prevalid_last   : types.Object = None

    @classmethod
    def setSelected(cls, selected):
        """ Update global selection status and query fract root
        # OPT:: multi-root selection? work with current active?
        """
        if selected:
            if cls.last:
                cls.prevalid_last = cls.last
            cls.selection = selected.copy() if isinstance(selected, list) else [selected]
            cls.last = cls.selection[-1]

            newRoot = MW_id_utils.getRoot(cls.last)
            if newRoot:
                if cls.root:
                    cls.prevalid_root  = cls.root
                    cls.prevalid_fract = cls.fract
                cls.root  = newRoot
                cls.fract = MW_global_storage.getFract(newRoot)
            else:
                cls.root = None
                cls.fract = None

        else:
            cls.resetSelected()

        cls.logSelected()

    @classmethod
    def recheckSelected(cls):
        cls.setSelected(cls.selection)

    @classmethod
    def logSelected(cls):
        DEV.log_msg(f"root: {cls.root.name if cls.root else '...'} | last: {cls.last.name if cls.last else '...'}"
                    f" | selection: {len(cls.selection) if cls.selection else '...'}", {"GLOBAL", "SELECTED"})

    @classmethod
    def resetSelected(cls):
        """ Reset all to None but keep sanitized references to prevalid """
        cls.selection = None
        cls.last      = None
        cls.prevalid_last = utils.returnSanitized_object(cls.prevalid_last)

        cls.root      = None
        cls.fract     = None
        cls.prevalid_root = utils.returnSanitized_object(cls.prevalid_root)
        if cls.prevalid_root is None:
            cls.prevalid_fract = None

    @classmethod
    def sanitizeSelected(cls):
        """ Potentially sanitize objects no longer on the scene """
        if utils.needsSanitize_object(cls.root):
            cls.resetSelected()

    # callback triggers
    @classmethod
    def setSelected_callback(cls, _scene_=None, _selected_=None):
        cls.setSelected(_selected_)

    @classmethod
    def sanitizeSelected_callback(cls, _scene_=None, _name_selected_=None):
        cls.sanitizeSelected()


#-------------------------------------------------------------------
# Blender events

classes = [
    Prop_inspector,
    MW_id,
]
_name = f"{__name__[14:]}" #\t(...{__file__[-32:]})"

def register():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "REG"})

    # sanitize in case of reload module
    MW_global_selected.sanitizeSelected()

    # callbaks
    handlers.callback_selectionChange_actions.append(MW_global_selected.setSelected_callback)
    handlers.callback_loadFile_actions.append(MW_global_selected.sanitizeSelected_callback)
    handlers.callback_undo_actions.append(MW_global_storage.purgeFracts_callback)
    handlers.callback_loadFile_actions.append(MW_global_storage.purgeFracts_callback)

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
    handlers.callback_loadFile_actions.remove(MW_global_selected.sanitizeSelected_callback)
    handlers.callback_undo_actions.removeCheck(MW_global_storage.purgeFracts_callback)
    handlers.callback_loadFile_actions.remove(MW_global_storage.purgeFracts_callback)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})