import bpy
import bpy.types as types
import bpy.props as props

from . import handlers
from . import utils
from .utils_dev import DEV

from .properties_utils import Prop_inspector

#-------------------------------------------------------------------

class MW_id(types.PropertyGroup):
    """ Property stored in the objects to identify the roots """

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

            # NOTE:: check the root is actually root: could happen if an object is modified at some step by the user
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


    # OPT:: avoid using this and just set the children?
    @staticmethod
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

class MW_global_selected:
    # OPT:: store the data in the scene/file to avoid losing it on reload? Still issues with global storage anyway
    #class MW_global_selected(types.PropertyGroup): + register the class etc
    #my_object: bpy.props.PointerProperty(type=bpy.types.Object)

    # root fracture object
    root = None

    # common selection
    selection = None
    last = None

    @classmethod
    def setSelected(cls, selected):
        # OPT:: multi-selection / root inside selected?
        cls.selection = selected

        if cls.selection:
            cls.last = cls.selection[-1]
            cls.root = MW_id_utils.getRoot(cls.last)
        else:
            cls.resetSelected()

    @classmethod
    def resetSelected(cls):
        cls.selection = None
        cls.last = None
        cls.root = None

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

    handlers.callback_selectionChange_actions.append(MW_global_selected.setSelected_callback)
    handlers.callback_loadFile_actions.append(MW_global_selected.sanitizeSelected_callback)

    for cls in classes:
        bpy.utils.register_class(cls)

    # appear as part of default object props
    bpy.types.Object.mw_id = props.PointerProperty(
        type=MW_id,
        name="MW_id", description="MW fracture id")

def unregister():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})

    handlers.callback_selectionChange_actions.remove(MW_global_selected.setSelected_callback)
    handlers.callback_loadFile_actions.remove(MW_global_selected.sanitizeSelected_callback)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})