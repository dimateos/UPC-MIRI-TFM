import bpy
import bpy.types as types
import bpy.props as props

from .preferences import getPrefs

from . import handlers
from . import utils
from .utils_dev import DEV


#-------------------------------------------------------------------

class MW_id(types.PropertyGroup):
    """ The only property stored in the objects to identify the roots """

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

#-------------------------------------------------------------------
# Functions outside the class to avoid all the memory footprint inside the objects

def isRoot(obj: types.Object) -> bool:
    return "ROOT" in obj.mw_id.meta_type
def isChild(obj: types.Object) -> bool:
    return "CHILD" in obj.mw_id.meta_type

def hasRoot(obj: types.Object) -> bool:
    """ Quick check if the object is part of a fracture """
    #DEV.log_msg(f"hasRoot check: {obj.name} -> {obj.mw_id.meta_type}", {"REC", "CFG"})
    return "NONE" not in obj.mw_id.meta_type

def getRoot(obj: types.Object) -> tuple[types.Object, "MW_id"]:
    """ Retrieve the root object holding the config (MW_id forward declared)"""
    #DEV.log_msg(f"getRoot search: {obj.name} -> {obj.mw_id.meta_type}", {"REC", "CFG"})
    if "NONE" in obj.mw_id.meta_type:
        return obj, None

    try:
        obj_chain = obj
        while "CHILD" in obj_chain.mw_id.meta_type:
            obj_chain = obj_chain.parent

        # NOTE:: check the root is actually root: could happen if an object is copy pasted
        if "ROOT" not in obj_chain.mw_id.meta_type: raise ValueError("Chain ended with no root")
        #DEV.log_msg(f"getRoot chain end: {obj_chain.name}", {"RET", "CFG"})
        return obj_chain, obj_chain.mw_id

    # the parent was removed
    except AttributeError:
        DEV.log_msg(f"getRoot chain broke: {obj.name} -> no rec parent", {"ERROR", "CFG"})
        return obj, None
    # the parent was not root
    except ValueError:
        DEV.log_msg(f"getRoot chain broke: {obj_chain.name} -> not root ({obj_chain.mw_id.meta_type})", {"ERROR", "CFG"})
        return obj, None

def getSceneRoots(scene: types.Scene) -> list[types.Object]:
    roots = [ obj for obj in scene.objects if MW_id.isRoot(obj) ]
    return roots

# OPT:: avoid using this and just set the children?
def setMetaType(obj: types.Object, type: set[str], skipParent = False, childrenRec = True):
    """ Set the property to the object and all its children (dictionary ies copied, not referenced)
        # NOTE:: acessing obj children is O(len(bpy.data.objects)), so just call it on the root again
    """
    if not skipParent:
        obj.mw_id.meta_type = type.copy()

    toSet = obj.children_recursive if childrenRec else obj.children
    #DEV.log_msg(f"Setting {type} to {len(toSet)} objects", {"CFG"})
    for child in toSet:
        child.mw_id.meta_type = type.copy()

#-------------------------------------------------------------------
# callbacks for selection / undo to keep track of selected root fracture

class MW_root(types.PropertyGroup):
    # TODO:: store the data in the scene to avoid losing it?
    #my_object: bpy.props.PointerProperty(type=bpy.types.Object)

    # XXX:: unset on reload, could have a flag and let the panel update it -> cannot be done from addon register
    nbl_selected_cfg = None
    nbl_selected_obj = None

    @classmethod
    def hasSelected(cls) -> bool:
        return cls.nbl_selected_obj and cls.nbl_selected_cfg

    @classmethod
    def getSelected(cls) -> tuple[types.Object, "MW_id"]:
        return cls.nbl_selected_obj, cls.nbl_selected_cfg
    @classmethod
    def getSelected_obj(cls) -> types.Object:
        return cls.nbl_selected_obj
    @classmethod
    def getSelected_cfg(cls) -> "MW_id":
        return cls.nbl_selected_cfg


    @classmethod
    def setSelected(cls, selected):
        # OPT:: multi-selection / root?
        if selected: cls.nbl_selected_obj, cls.nbl_selected_cfg = cls.getRoot(selected[-1])
        else: cls.nbl_selected_obj, cls.nbl_selected_cfg = None,None

    # trigger new root on selection
    @classmethod
    def setSelected_callback(cls, _scene_=None, _selected_=None):
        cls.setSelected(_selected_)

    @classmethod
    def resetSelected(cls):
        cls.nbl_selected_obj, cls.nbl_selected_cfg = None, None


    @classmethod
    def sanitizeSelected(cls):
        if utils.needsSanitize_object(cls.nbl_selected_obj):
            cls.resetSelected()

    @classmethod
    def sanitizeSelected_callback(cls, _scene_=None, _name_selected_=None):
        cls.sanitizeSelected()


#-------------------------------------------------------------------
# Blender events

classes = [
    MW_id,
]
_name = f"{__name__[14:]}" #\t(...{__file__[-32:]})"

def register():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "REG"})

    handlers.callback_selectionChange_actions.append(MW_root.setSelected_callback)
    handlers.callback_loadFile_actions.append(MW_root.sanitizeSelected_callback)

    for cls in classes:
        bpy.utils.register_class(cls)

    # appear as part of default object props
    bpy.types.Object.mw_id = props.PointerProperty(
        type=MW_id,
        name="MW_id", description="MW fracture id")


def unregister():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})

    handlers.callback_selectionChange_actions.remove(MW_root.setSelected_callback)
    handlers.callback_loadFile_actions.remove(MW_root.sanitizeSelected_callback)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})