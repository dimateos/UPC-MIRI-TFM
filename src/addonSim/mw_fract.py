import bpy
import bpy.types as types

from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
)

from .mw_cont import MW_Container
from .mw_links import MW_Links

from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

class MW_Fract:
    """ Wrapper class around the core separate fracture related classes """

    def __init__(self):

        # TODO:: reference to root?

        self.cont  : MW_Container = None
        self.links : MW_Links     = None
        self.sim = None