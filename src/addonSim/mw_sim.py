import bpy.types as types
from mathutils import Vector, Matrix

from .mw_links import LinkCollection, Link
from tess import Container, Cell

from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

class Simulation:

    def __init__(self, initial_links: LinkCollection):
        self.life = 1.0

