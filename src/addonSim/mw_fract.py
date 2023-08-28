import bpy
import bpy.types as types

from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
)

from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

class MW_Fract:
    """ Wrapper class around the core separate fracture related classes """

    def __init__(self):

        self.cont = None
        self.links = None
        self.sim = None

        pass