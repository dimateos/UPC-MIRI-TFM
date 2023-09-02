import bpy
import bpy.types as types
from mathutils import Vector

from .preferences import getPrefs
from .properties import (
    MW_gen_cfg,
)

# Using tess voro++ adaptor
from tess import Container as VORO_Container

from . import utils_geo
from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

link_key_t = tuple[int, int]

class ERROR_IDX:
    """ Use leftover indices between cont boundaries and custom walls for filler error idx?
        IDEA:: could just multiply id by a lot to keep track of original instead?
    """
    _zerosForHighlight = 1000000

    MISSING = -7 *_zerosForHighlight
    """ Missing a whole cell / object"""
    ASYMMETRY = -8 *_zerosForHighlight
    """ Missing connection at in the supposed neighbour """

    e3 = -9 *_zerosForHighlight
    all = [ MISSING, ASYMMETRY ]

#-------------------------------------------------------------------

class MW_Container:

    def __init__(self, points: list[Vector], bb: list[Vector, 6], faces4D: list[Vector], precision: int):
        self.initialized = False
        """ Set to true after succesfully inserted all points in the voro cointainer """
        self.precalculated = False
        """ Set to true after succesfully precalculated all the data """

        # construct voro++ cont
        self.voro_cont = self.build_cont(points, bb, faces4D, precision)
        if self.voro_cont is not None:
            self.initialized = True

    def precalculate_data(self, obj_cells_root : types.Object, cells_list : list[types.Object]):
        """ Precalculate/query data such as valid neighbours and mapping faces """
        stats = getStats()

        # init wall dict with just empty lists (some will remain empty)
        self.keys_perWall: dict[int, list[link_key_t]] = {
            id: list() for id in self.voro_cont.get_conainerId_limitWalls()+self.voro_cont.walls_cont_idx
        }
        # cell dict lists will have the same size of neighs/faces so fill in the following loop while checking for missing ones
        self.keys_perCell: dict[int, list[link_key_t] | int] = dict()
        """ NOTE:: missing cells are filled with a placeholder id to preserve original position idx """

        # calculate missing cells and query neighs
        self.foundId   : list[int]           = []
        self.missingId : list[int]           = []
        self.neighs    : list[list[int]|int] = [ERROR_IDX.MISSING]*len(self.voro_cont)
        """ NOTE:: missing cells are filled with a placeholder id to preserve original position idx """

        for idx_cell, obj_cell in enumerate(self.voro_cont):
            if obj_cell is None:
                self.missingId.append(idx_cell)
                self.keys_perCell[idx_cell] = ERROR_IDX.MISSING
            else:
                self.foundId.append(idx_cell)
                neighs_cell = obj_cell.neighbors()
                self.neighs[idx_cell] = neighs_cell
                # prefill with asymmetry keys too
                key = (ERROR_IDX.ASYMMETRY, idx_cell)
                self.keys_perCell[idx_cell] = [key]*len(neighs_cell)

        msg = f"calculated voro cell neighs: {len(self.missingId)} / {len(self.voro_cont)} missing"
        if self.missingId: msg += f" {str(self.missingId[:20])}"
        stats.logDt(msg) # uncut=True

        # retrieve objs, meshes -> dicts per cell
        self.cells_parent = obj_cells_root
        self.cells_objs        : list[types.Object|int] = [ERROR_IDX.MISSING]* len(self.voro_cont)
        self.cells_meshes      : list[types.Mesh|int]   = [ERROR_IDX.MISSING]* len(self.voro_cont)
        self.cells_meshes_FtoF : list[dict|int]         = [ERROR_IDX.MISSING]* len(self.voro_cont)

        for idx_found, obj_cell in enumerate(cells_list):
            # asign idx cell managing missing ones
            idx_cell = self.foundId[idx_found]
            self.cells_objs[idx_cell] = obj_cell
            obj_cell.mw_id.cell_id = idx_cell

            # store mesh and faces map
            mesh = obj_cell.data
            self.cells_meshes[idx_cell] = mesh
            #self.cells_meshes_FtoF[idx_cell] = utils_geo.get_meshDicts(mesh)["FtoF"]
            self.cells_meshes_FtoF[idx_cell] = utils_geo.map_FtoF(mesh)

        stats.logDt("calculated cells mesh dicts (interleaved missing cells)")

        # build symmetric face map of the found cells
        self.keys_asymmetry : list[link_key_t]    = []
        self.keys_missing   : list[link_key_t]    = []
        self.neighs_faces   : list[list[int]|int] = [ERROR_IDX.MISSING]*len(self.voro_cont)
        """ NOTE:: missing cells and neigh asymmetries are filled with a placeholder id too """

        for idx_cell in self.foundId:
            neighs_cell = self.neighs[idx_cell]

            faces: list[int] = [ERROR_IDX.ASYMMETRY] * len(neighs_cell)
            for idx_face,idx_neigh in enumerate(neighs_cell):
                # wall connection always ok, so simply add its index
                if idx_neigh < 0: faces.append(idx_neigh)

                # general cases try retrieving the respective face at the neighbour end
                else:
                    neighs_other = self.neighs[idx_neigh]

                    # check missing whole cell -> alter neighs acording to found error
                    if neighs_other == ERROR_IDX.MISSING:
                        self.keys_missing.append((idx_cell,idx_neigh))
                        neighs_cell[idx_face] = ERROR_IDX.MISSING
                        # also reasign the exact error code in the keys_perCell structure too (started as asymmetry)
                        self.keys_perCell[idx_cell][idx_face] = (ERROR_IDX.MISSING, idx_cell)

                    # try to find valid face matching index
                    else:
                        try:
                            neigh_idx_face = neighs_other.index(idx_cell)
                            faces[idx_face] = neigh_idx_face

                        # symmetry checked with .index exception -> also alter neighs
                        except ValueError:
                            self.keys_asymmetry.append((idx_cell,idx_neigh))
                            neighs_cell[idx_face] = ERROR_IDX.ASYMMETRY

            self.neighs_faces[idx_cell] = faces

        stats.logDt(f"calculated cell neighs faces: {len(self.keys_missing)} broken due missing")
        msg =       f"      ...found {len(self.keys_asymmetry)} asymmetries"
        if self.keys_asymmetry: msg += f": {str(self.keys_asymmetry[:10])}"
        stats.logDt(msg) # uncut=True
        self.precalculated = True


    def build_cont(self, points: list[Vector], bb: list[Vector, 6], faces4D: list[Vector], precision: int):
        """ Build a voro++ container using the points and the faces as walls """

        # Container bounds expected as tuples
        bb_tuples = [ p.to_tuple() for p in bb ]

        #Legacy cont some tests mid operator
        if DEV.LEGACY_CONT:
            voro_cont = VORO_Container(points=points, limits=bb_tuples)
            DEV.log_msg(f"Found {len(voro_cont)} cells (NO walls - {len(faces4D)} faces)", {"CALC", "CONT", "LEGACY"})
            return voro_cont

        # Set wall planes precision used
        if precision != VORO_Container.custom_walls_precision_default:
            VORO_Container.custom_walls_precision = precision
            DEV.log_msg(f"Set Container.custom_walls_precision: {precision}", {"CALC", "CONT"})
        else:
            VORO_Container.custom_walls_precision = VORO_Container.custom_walls_precision_default

        # XXX:: container creation might fail do to some voro++ config params... hard to tweak for all? NOT DYNAMIC, requires recompilation
        # XXX:: some tiny intersection between cells might happen due to tolerance -> check or not worth it, we shrink then would not be noticeable
        try:
            # Build the container and cells
            voro_cont = VORO_Container(points=points, limits=bb_tuples, walls=faces4D)
            # OPT:: init in two phases: define walls and then insert points?

            # Check non empty
            getStats().logDt("built voro container")
            logType = {"CALC", "CONT"}
            if not len(voro_cont): logType |= {"ERROR"}
            DEV.log_msg(f"Found {len(voro_cont)} cells ({len(voro_cont.walls)} walls from {len(faces4D)} faces)", logType)
            return voro_cont

        except Exception as e:
            DEV.log_msg(f"exception cont >> {str(e)}", {"CALC", "CONT", "ERROR"})
            return None

    #-------------------------------------------------------------------

    def getMeshes(self, idx: list[int]|int) -> list[types.Mesh]|types.Mesh:
        """ return a mesh or list of meshes given idx  """
        try:
            return self.cells_meshes[idx]
        except TypeError:
            return [ self.cells_meshes[i] for i in idx ]

    def getFaces(self, midx: list[int]|int, fidx: list[int]|int) -> list[types.MeshPolygon]|types.MeshPolygon:
        """ return a face or list of faces given idx  """
        try:
            return self.cells_meshes[midx].polygons[fidx]
        except TypeError:
            return [ self.cells_meshes[i].polygons[j] for i,j in zip(midx,fidx) ]