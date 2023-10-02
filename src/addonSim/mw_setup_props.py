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
    #return None,None
    obj = MW_global_selected.root
    proxy = getattr(cfg, "nbl_prefsProxy")

    DEV.log_msg(f"{obj.name if obj else '...'} -> {prop_name} {'(proxy)' if proxy else ''}", {'CALLBACK', 'PROP', 'PROXY'})
    if not obj:
        return None,None

    obj_cfg = getattr(obj, cfg_name)
    if proxy:
        setattr(obj_cfg, prop_name, getattr(cfg, prop_name))
        return None,None

    return obj, getattr(obj_cfg, prop_name)

def getRoot_checkProxy_None(cfg, cfg_name:str, prop_name:str):
    """ Check common prefs proxy flag and return None """
    obj = MW_global_selected.root
    proxy = getattr(cfg, "nbl_prefsProxy")
    if not obj:
        return

    if proxy:
        obj_cfg = getattr(obj, cfg_name)
        setattr(obj_cfg, prop_name, getattr(cfg, prop_name))

#-------------------------------------------------------------------

def cell_scale_update(cfg):
    root, scale = getRoot_checkProxy(cfg, "mw_vis", "cell_scale")
    if root is None: return

    cells_root = utils_scene.get_child(root, getPrefs().names.cells)
    utils_trans.scale_objectChildren(cells_root, scale)

def cell_color_update(cfg, prop_name:str, cells_name:str):
    root, color = getRoot_checkProxy(cfg, "mw_vis", prop_name)
    if root is None: return

    cells_root = utils_scene.get_child(root, cells_name)
    cells_root.active_material.diffuse_color = color

def links_smoothShade_update(cfg):
    root, smooth = getRoot_checkProxy(cfg, "mw_vis", "links_smoothShade")
    if root is None: return

    links_ALL = utils_scene.get_children(root, getPrefs().names.links_ALL)
    for links in links_ALL:
        if links and links.data:
            utils_mesh.set_smoothShading(links.data, smooth)