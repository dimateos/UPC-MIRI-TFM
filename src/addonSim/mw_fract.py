import bpy
import bpy.types as types
from . import handlers

from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
)

from .mw_cont import MW_Cont
from .mw_links import MW_Links

from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

class MW_Fract:
    """ Wrapper class around the core separate fracture related classes """

    def __init__(self):

        # TODO:: reference to root?

        self.cont  : MW_Cont = None
        self.links : MW_Links     = None
        self.sim = None

    def sanitize(self, root):
        cleaned = False

        if self.cont:
            cleaned |= self.cont.sanitize(root)
        if self.links:
            cleaned |= self.links.sanitize(root)

        return cleaned

#-------------------------------------------------------------------
# Blender events
_name = f"{__name__[14:]}" #\t(...{__file__[-32:]})"

def register():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "REG"})

    # callbaks for fract classes are called from here?

def unregister():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})

DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})