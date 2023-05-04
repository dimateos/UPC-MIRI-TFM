import bpy.types as types
from mathutils import Vector, Matrix

from .mw_links import Links, Link
from tess import Container, Cell

from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

class Simulation:

    def __init__(self, initial_links: Links):
        self.life = 1.0

