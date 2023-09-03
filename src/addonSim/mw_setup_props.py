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

def set_cells_scale(scale, proxy=False):
    obj = MW_global_selected.root
    DEV.log_msg(f"Scaling cell {obj.name if obj else '...'} -> {scale} {'(proxy)' if proxy else ''}", {'CALLBACK', 'VIS'})
    if not obj: return

    if proxy:
        obj.mw_vis.cell_scale = scale
        return

    cells_root = utils_scene.get_child(obj, getPrefs().names.cells)
    utils_trans.scale_objectChildren(cells_root, scale)

#def struct_linksScale_update(self, context):
#    obj = MW_global_selected.root
#    if not obj: return
#    links = utils_scene.get_child(obj, getPrefs().names.links)
#    if links: utils_trans.scale_objectChildren(links, self.struct_linksScale)
#    links_Air_Cell = utils_scene.get_child(obj, getPrefs().names.links_air)
#    if links_Air_Cell: utils_trans.scale_objectChildren(links_Air_Cell, self.struct_linksScale)