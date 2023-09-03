import bpy
import bpy.types as types
from mathutils import Vector, Matrix

from .preferences import getPrefs
from .properties_global import (
    MW_global_selected
)

from . import utils, utils_scene, utils_trans, utils_mat, utils_mesh
from .utils_dev import DEV


# includes callbacks from props: visual edit... avoid circular deps
#-------------------------------------------------------------------

def getRoot_checkProxy(cfg, cfg_name:str, prop_name:str):
    """ Check common prefs proxy flag and return the object when the update is required"""
    obj = MW_global_selected.root
    proxy = getattr(cfg, "nbl_prefsProxy")

    DEV.log_msg(f"Scaling cell {obj.name if obj else '...'} -> {prop_name} {'(proxy)' if proxy else ''}", {'CALLBACK', 'PROP', 'PROXY'})
    if not obj:
        return None,None

    obj_cfg = getattr(obj, cfg_name)
    if proxy:
        setattr(obj_cfg, prop_name, getattr(cfg, prop_name))
        return None,None

    return obj, getattr(obj_cfg, prop_name)

#-------------------------------------------------------------------

def cell_scale_update(cfg):
    root, scale = getRoot_checkProxy(cfg, "mw_vis", "cell_scale")
    if root is None: return

    cells_root = utils_scene.get_child(root, getPrefs().names.cells)
    utils_trans.scale_objectChildren(cells_root, scale)

def cell_matAlpha_update(cfg):
    root, alpha = getRoot_checkProxy(cfg, "mw_vis", "cell_matAlpha")
    if root is None: return

    cells_root = utils_scene.get_child(root, getPrefs().names.cells)
    mat = cells_root.active_material
    mat.diffuse_color.w = alpha

#def struct_linksScale_update(self, context):
#    obj = MW_global_selected.root
#    if not obj: return
#    links = utils_scene.get_child(obj, getPrefs().names.links)
#    if links: utils_trans.scale_objectChildren(links, self.struct_linksScale)
#    links_Air_Cell = utils_scene.get_child(obj, getPrefs().names.links_air)
#    if links_Air_Cell: utils_trans.scale_objectChildren(links_Air_Cell, self.struct_linksScale)