import bpy
import bpy.types as types

from .properties import (
    MW_gen_cfg,
    MW_sim_cfg,
    MW_vis_cfg,
)


# -------------------------------------------------------------------

def getRoot_cfg(ob: types.Object):
    """ Retrieve the root object holding the config """
    if "NONE" in ob.mw_gen.type:
        return ob, None

    else:
        while "CHILD" in ob.mw_gen.type:
            # Maybe the user deleted the root only
            if not ob.parent:
                return ob, None
            ob = ob.parent

        return ob, ob.mw_gen


def copyProperties(src, dest):
    """ Copy all properties of the property group to the object """
    # The whole property is read-only but its values can be modified, avoid writing it one by one...
    for prop_name in dir(src):
        if not prop_name.startswith("__") and not callable(getattr(src, prop_name)):
            try:
                setattr(dest, prop_name, getattr(src, prop_name))
            except AttributeError:
                # Avoid read-only RNA types
                pass