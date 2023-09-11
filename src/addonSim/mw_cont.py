import bpy
import bpy.types as types
from mathutils import Vector

from .preferences import getPrefs
from .properties_global import (
    MW_global_selected, MW_id_utils
)


# Using tess voro++ adaptor
from tess import Container as VORO_Container

from . import utils_geo, utils_scene
from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

neigh_key_t      = tuple[int, int]
neighFaces_key_t = tuple[int, int]

class CELL_ERROR_ENUM:
    """ Use leftover indices between cont boundaries and custom walls for filler error idx?
        # NOTE:: could be using any number, sequentiality not used
        # OPT:: sequential check of id in all, so in case of slow process just use a unique error etc
    """
    # could use original ID to preserve it? anyway need to be either very high or between 7-9 (walls id)
    _zerosForHighlight = 1000000

    MISSING = -1 *_zerosForHighlight
    """ Missing a whole cell / object """
    ASYMMETRY = -2 *_zerosForHighlight
    """ Missing connection at in the supposed neighbour """
    DELETED = -3 *_zerosForHighlight
    """ Deleted from the scene """
    #IGNORED = -4 *_zerosForHighlight
    #""" Model debug ignored """

    all = { MISSING, ASYMMETRY, DELETED }
    build_process = { MISSING, ASYMMETRY }

    @classmethod
    def str(cls, idx):
        if idx == cls.MISSING:   return "MISSING"
        if idx == cls.ASYMMETRY: return "ASYMMETRY"
        if idx == cls.DELETED:   return "DELETED"
        #if idx == cls.IGNORED:   return "IGNORED"
        return "unknown"

class CELL_STATE_ENUM:
    """ Current cell state, preserves some sequentiality"""
    SOLID = 0
    CORE = 1
    AIR = 2

    all = { SOLID, CORE, AIR }

    @classmethod
    def to_str(cls, e:int):
        if e == cls.SOLID:  return "SOLID"
        if e == cls.CORE:   return "CORE"
        if e == cls.AIR:    return "AIR"
        if e in CELL_ERROR_ENUM.all: return "ERROR_ENUM"
        return "none"
        #raise ValueError(f"CELL_STATE_ENUM: {e} is not in {cls.all}")
    @classmethod
    def from_str(cls, s:str):
        if s == "SOLID":    return cls.SOLID
        if s == "CORE":     return cls.CORE
        if s == "AIR":      return cls.AIR
        raise ValueError(f"CELL_STATE_ENUM: {s} is not in { set(CELL_STATE_ENUM.to_str(s) for s in cls.all) }")

#-------------------------------------------------------------------

class MW_Cont:

    def __init__(self, root :types.Object, points: list[Vector], bb: list[Vector, 6], faces4D: list[Vector], precision: int):
        self.initialized = False
        """ Set to true after succesfully inserted all points in the voro cointainer """
        self.precalculated = False
        """ Set to true after succesfully precalculated all the data """

        self.root = root
        """ Shortcut to fracture root object """

        # construct voro++ cont
        self.voro_cont = self.build_voro(points, bb, faces4D, precision)
        if self.voro_cont is not None:
            self.initialized = True

    def precalculations(self, cells_list : list[types.Object]):
        """ Precalculate/query data such as valid neighbours and mapping faces, also adds storage and cell id to cell objects """
        stats = getStats()

        # init wall dict with just empty lists (some will remain empty)
        self.wallsId : list[int] = self.voro_cont.get_conainerId_limitWalls()+self.voro_cont.walls_cont_idx
        self.keys_perWall: dict[int, list[neigh_key_t]] = {
            id: list() for id in self.wallsId
        }
        # cell dict lists will have the same size of neighs/faces so fill in the following loop while checking for missing ones
        self.keys_perCell: dict[int, list[neigh_key_t] | int] = dict()
        """ # NOTE:: missing cells are filled with a placeholder id to preserve original position idx """


        # calculate missing cells and query neighs (also with placeholders idx)
        self.foundId   : list[int]           = []
        self.missingId : list[int]           = []
        self.deletedId : list[int]           = [] # NOTE:: will be treated as AIR cells, but missing geometry!
        self.deletedId_prev = self.deletedId.copy()
        self.neighs    : list[list[int]|int] = [CELL_ERROR_ENUM.MISSING]*len(self.voro_cont)

        for idx_cell, obj_cell in enumerate(self.voro_cont):
            if obj_cell is None:
                self.missingId.append(idx_cell)
                self.keys_perCell[idx_cell] = CELL_ERROR_ENUM.MISSING
            else:
                self.foundId.append(idx_cell)
                neighs_cell = obj_cell.neighbors()
                self.neighs[idx_cell] = neighs_cell
                # prefill with asymmetry keys too
                key = (CELL_ERROR_ENUM.ASYMMETRY, idx_cell)
                self.keys_perCell[idx_cell] = [key]*len(neighs_cell)

        msg = f"calculated voro cell neighs: {len(self.missingId)} / {len(self.voro_cont)} missing"
        if self.missingId: msg += f" {str(self.missingId[:20])}"
        stats.logDt(msg) # uncut=True

        # retrieve objs, meshes -> dicts per cell
        self.cells_objs        : list[types.Object|int] = [CELL_ERROR_ENUM.MISSING]* len(self.voro_cont)
        self.cells_meshes      : list[types.Mesh|int]   = [CELL_ERROR_ENUM.MISSING]* len(self.voro_cont)
        self.cells_meshes_FtoF : list[dict|int]         = [CELL_ERROR_ENUM.MISSING]* len(self.voro_cont)
        self.cells_state       : list[types.Object|int] = [CELL_ERROR_ENUM.MISSING]* len(self.voro_cont)
        prefs = getPrefs()
        self.cells_root = utils_scene.get_child(self.root, prefs.names.cells)
        self.cells_root_core = utils_scene.get_child(self.root, prefs.names.cells_core)
        self.cells_root_air = utils_scene.get_child(self.root, prefs.names.cells_air)

        for idx_found, obj_cell in enumerate(cells_list):
            # asign idx cell managing missing ones
            idx_cell = self.foundId[idx_found]
            self.cells_objs[idx_cell] = obj_cell

            # asign data to the scene object too, including the storage id
            obj_cell.mw_id.cell_id = idx_cell
            obj_cell.mw_id.storage_id = self.root.mw_id.storage_id

            # initial state is SOLD
            self.cells_state[idx_cell] = CELL_STATE_ENUM.SOLID
            obj_cell.mw_id.cell_state = CELL_STATE_ENUM.SOLID

            # store mesh and faces map
            mesh = obj_cell.data
            self.cells_meshes[idx_cell] = mesh
            #self.cells_meshes_FtoF[idx_cell] = utils_geo.get_meshDicts(mesh)["FtoF"]
            self.cells_meshes_FtoF[idx_cell] = utils_geo.map_FtoF(mesh)

        stats.logDt("calculated cells mesh dicts (interleaved missing cells)")

        # build symmetric face map of the found cells
        self.neighs_keys_asymmetry : list[neigh_key_t]   = []
        self.neighs_keys_missing   : list[neigh_key_t]   = []
        self.neighs_faces          : list[list[int]|int] = [CELL_ERROR_ENUM.MISSING]*len(self.voro_cont)
        """ # NOTE:: missing cells and neigh asymmetries are filled with a placeholder id too """

        for idx_cell in self.foundId:
            neighs_cell = self.neighs[idx_cell]

            faces: list[int] = [CELL_ERROR_ENUM.ASYMMETRY] * len(neighs_cell)
            for idx_face,idx_neigh in enumerate(neighs_cell):
                # wall connection always ok, so simply add its index
                if idx_neigh < 0: faces.append(idx_neigh)

                # general cases try retrieving the respective face at the neighbour end
                else:
                    neighs_other = self.neighs[idx_neigh]

                    # check missing whole cell (self.neighs default value) -> alter neighs acording to found error
                    if neighs_other == CELL_ERROR_ENUM.MISSING:
                        self.neighs_keys_missing.append((idx_cell,idx_neigh))
                        neighs_cell[idx_face] = CELL_ERROR_ENUM.MISSING
                        # also reasign the exact error code in the keys_perCell structure too (started as asymmetry)
                        self.keys_perCell[idx_cell][idx_face] = (CELL_ERROR_ENUM.MISSING, idx_cell)

                    # try to find valid face matching index
                    else:
                        try:
                            neigh_idx_face = neighs_other.index(idx_cell)
                            faces[idx_face] = neigh_idx_face

                        # symmetry checked with .index exception -> also alter neighs
                        except ValueError:
                            self.neighs_keys_asymmetry.append((idx_cell,idx_neigh))
                            neighs_cell[idx_face] = CELL_ERROR_ENUM.ASYMMETRY

            # add the merged list of faces
            self.neighs_faces[idx_cell] = faces

        stats.logDt(f"calculated cell neighs faces: {len(self.neighs_keys_missing)} broken due missing")
        msg =       f"      ...found {len(self.neighs_keys_asymmetry)} asymmetries"
        if self.neighs_keys_asymmetry: msg += f": {str(self.neighs_keys_asymmetry[:10])}"
        stats.logDt(msg) # uncut=True
        self.precalculated = True

    def build_voro(self, points: list[Vector], bb: list[Vector, 6], faces4D: list[Vector], precision: int):
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

    def sanitize(self, root):
        """ Query all objects references from the scene again, sometimes just in case """
        cleaned = self.root != root
        self.root = root
        DEV.log_msg(f"Sanitizing cont", {"CONT", "SANITIZE"})

        # query cell roots and their children
        prefs = getPrefs()
        self.cells_root = utils_scene.get_child(self.root, prefs.names.cells)
        self.cells_root_core = utils_scene.get_child(self.root, prefs.names.cells_core)
        self.cells_root_air = utils_scene.get_child(self.root, prefs.names.cells_air)
        cells_list = self.cells_root.children + self.cells_root_core.children + self.cells_root_air.children

        # iterate the unsorted cells and read their internal id
        for obj_cell in cells_list:
            if not MW_id_utils.hasCellId(obj_cell):
                continue
            idx_cell = obj_cell.mw_id.cell_id

            self.cells_objs[idx_cell] = obj_cell
            self.cells_meshes[idx_cell] = obj_cell.data
            # also recover state from scene
            cleaned |= self.cells_state[idx_cell] == obj_cell.mw_id.cell_state
            self.cells_state[idx_cell] = obj_cell.mw_id.cell_state

        # check some deleted obj (meshes not checked)
        ok, broken, error = self.getCells_splitID_needsSanitize()
        self.setCells_missing(broken)
        cleaned |= self.deletedId != self.deletedId_prev
        return cleaned

    def getCells_splitID_needsSanitize(self):
        """ Detect broken references to scene objects """
        ok, broken, error = [],[],[]
        broken_prev = []

        for id in self.foundId:
            cell = self.cells_objs[id]

            # skip build error
            if cell in CELL_ERROR_ENUM.build_process:
                error.append(id)
                continue

            # already broken
            if cell == CELL_ERROR_ENUM.DELETED:
                broken_prev.append(id)
            # deleted broken references
            elif utils_scene.needsSanitize(cell):
                broken.append(id)
            else:
                ok.append(id)

        return ok, broken+broken_prev, error

    def getCells_splitID_state(self):
        """ Detect broken references to scene objects
            # OPT:: store and only update?
        """
        stateMap = {
            state : [] for state in CELL_STATE_ENUM.all
        }

        for id in self.foundId:
            state = self.cells_state[id]
            stateMap[state].append(id)

        return stateMap

    def setCells_missing(self, broken:list[int]):
        """ Mark as DELETED to be treated as AIR but without access to geometry, dont touch other arrays """
        self.deletedId_prev = self.deletedId
        self.deletedId = broken

        for id in broken:
            self.cells_objs[id] = CELL_ERROR_ENUM.DELETED
            self.cells_meshes[id] = CELL_ERROR_ENUM.DELETED
            self.cells_state[id] = CELL_STATE_ENUM.AIR

    #-------------------------------------------------------------------

    def getCells(self, idx: list[int]|int) -> list[types.Object]|types.Object:
        """ return an object or list of objects given idx  """
        try:
            return self.cells_objs[idx]
        except TypeError:
            return [ self.cells_objs[i] for i in idx]

    def getMeshes(self, midx: list[int]|int) -> list[types.Mesh]|types.Mesh:
        """ return a mesh or list of meshes given idx  """
        try:
            return self.cells_meshes[midx]
        except TypeError:
            return [ self.cells_meshes[i] for i in midx ]

    def getFaces(self, midx: list[int]|int, fidx: list[int]|int) -> list[types.MeshPolygon]|types.MeshPolygon:
        """ return a face or list of faces given idx  """
        try:
            return self.cells_meshes[midx].polygons[fidx]
        except TypeError:
            return [ self.cells_meshes[i].polygons[j] for i,j in zip(midx,fidx) ]

    def getCells_Faces(self, idx: list[int]|int, fidx: list[int]|int) -> list[tuple[types.Object,types.MeshPolygon]]|tuple[types.Object,types.MeshPolygon]:
        """ return a pair or list of pairs  """
        try:
            return (self.cells_objs[idx], self.cells_meshes[idx].polygons[fidx])
        except TypeError:
            return [ (self.cells_objs[i], self.cells_meshes[i].polygons[j]) for i,j in zip(idx,fidx) ]