import bpy
import bpy.types as types
from mathutils import Vector

from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
)

# Using tess voro++ adaptor
from tess import Container, Cell

from . import utils
from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

class MW_Container(Container):

    def __init__(self, points: list[Vector], bb: list[Vector, 6], faces4D: list[Vector], precision: int):
        #self.links = None

        # construct voro++ cont
        self.initialized = False
        self.build_cont(points, bb, faces4D, precision)

    def build_cont(self, points: list[Vector], bb: list[Vector, 6], faces4D: list[Vector], precision: int):
        """ Build a voro++ container using the points and the faces as walls """

        # Container bounds expected as tuples
        bb_tuples = [ p.to_tuple() for p in bb ]

        #Legacy cont some tests mid operator
        if DEV.LEGACY_CONT:
            super().__init__(points=points, limits=bb_tuples)
            DEV.log_msg(f"Found {len(self.cont)} cells (NO walls - {len(faces4D)} faces)", {"CALC", "CONT", "LEGACY"})
            self.initialized = True
            return

        # Set wall planes precision used
        if precision != Container.custom_walls_precision_default:
            Container.custom_walls_precision = precision
            DEV.log_msg(f"Set Container.custom_walls_precision: {precision}", {"CALC", "CONT"})
        else:
            Container.custom_walls_precision = Container.custom_walls_precision_default

        # XXX:: container creation might fail do to some voro++ config params... hard to tweak for all?
        # XXX:: also seems that if the mesh vertices/partilces are further appart if behaves better? clustered by tolerance?
        # XXX:: some tiny intersection between cells might happen due to tolerance -> check or not worth it, we shrink then would not be noticeable

        try:
            # Build the container and cells
            super().__init__(points=points, limits=bb_tuples, walls=faces4D)
            # TODO:: log verts outside/ cell not calculated?

            # Check non empty
            getStats().logDt("calculated cont")
            logType = {"CALC", "CONT"}
            if not len(self.cont): logType |= {"ERROR"}
            DEV.log_msg(f"Found {len(self.cont)} cells ({len(self.cont.walls)} walls from {len(faces4D)} faces)", logType)
            self.initialized = True

        except Exception as e:
            DEV.log_msg(f"exception cont >> {str(e)}", {"CALC", "CONT", "ERROR"})
            self.initialized = False