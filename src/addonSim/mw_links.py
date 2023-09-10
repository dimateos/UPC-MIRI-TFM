import bpy.types as types
from mathutils import Vector, Matrix
INF_FLOAT = float("inf")
import networkx as nx

from .mw_cont import MW_Cont, CELL_ERROR_ENUM, CELL_STATE_ENUM, neigh_key_t, neighFaces_key_t
from . import mw_resistance

from . import utils, utils_trans
from .utils_dev import DEV
from .stats import getStats

#-------------------------------------------------------------------

class LINK_STATE_ENUM:
    """ Current links state, preserves some sequentiality"""
    SOLID = 0
    WALL = 1
    AIR = 2

    all = [ SOLID, WALL, AIR ]
    all_str = [ "SOLID", "WALL", "AIR" ]

    @classmethod
    def to_str(cls, e:int):
        if e == cls.SOLID:  return "SOLID"
        if e == cls.WALL:   return "WALL"
        if e == cls.AIR:    return "AIR"
        return "none"
        #raise ValueError(f"CELL_STATE_ENUM: {e} is not in {cls.all}")
    @classmethod
    def from_str(cls, s:str):
        if s == "SOLID":    return cls.SOLID
        if s == "WALL":     return cls.WALL
        if s == "AIR":      return cls.AIR
        raise ValueError(f"CELL_STATE_ENUM: {s} is not in {cls.all_str}")

class Link():
    """ # OPT:: could use separate array of props? pyhton already slow so ok class?"""

    def __init__(self, key_cells: neigh_key_t, key_faces: neighFaces_key_t, pos_world:Vector, dir_world:Vector, face_area:float, state=LINK_STATE_ENUM.SOLID):
        # no directionality but tuple key instead of set
        self.key_cells : neigh_key_t      = key_cells
        self.key_faces : neighFaces_key_t = key_faces

        # sim props
        self.state_initial = state
        self.reset()

        # properties in world space
        self.pos = pos_world
        self.dir = dir_world
        # properties to later normalize
        self.area = face_area

        # TODO:: resistance
        #self.resistance = 0.5 + 0.5* mw_resistance.get2D(self.pos.x, self.pos.y)
        self.resistance = mw_resistance.get2D(self.pos.x, self.pos.y)

    def reset(self, life=1.0):
        """ Reset simulation parameters """
        self.state = self.state_initial
        self.life = life
        self.picks = self.picks_entry = 0

    def __str__(self):
        s = f"k{self.key_cells}: a({self.area:.3f}) life({self.life:.3f}) p{self.picks, self.picks_entry}) s({self.state,self.state_initial})"
        if self.airLink_initial:
            s += f" [AIR-WALL] dir{self.dir.to_tuple(2)}"
        elif self.airLink: s += f" [AIR]"
        return s

    def degrade(self, deg):
        """ Degrade link life, return true when broken """
        self.picks +=1
        self.life -= deg
        return self.life <= 0

    @property
    def life_clamped(self):
        """ Get link life clamped [0,1] """
        return min( max(self.life, 0), 1)

    def clamp(self):
        """ Clamp link life [0,1] """
        self.life = self.life_clamped

#-------------------------------------------------------------------

class MW_Links():

    def __init__(self, cont: MW_Cont):
        stats = getStats()
        self.initialized = False
        """ Set to true after succesfully computed the link map """

        self.cont = cont
        """ Shortcut to container """

        self.cells_graph = nx.Graph()
        """ Graph connecting the cells to find connected components, also adds walls with negative indices
            # NOTE:: edges for a given node are not returned sorted by face, for this query the faceKey inside the link
            # NOTE:: removing nodes from the graphs takes all their edges too, adding edges creates nodess
        """

        self.comps = []
        """ List of sets with connected components cells id """
        self.comps_subgraph = nx.Graph() # used to leave cells_graph untouched (edges get removed along nodes)
        self.comps_len = -1

        self.links_graph = nx.Graph()
        """ Graph connecting links! Links connect with other links from adjacent faces from both cells """
        self.external : list[Link] = list()
        """ Dynamic list of external links: AIR/WALL to CELL, mainly used as entry points in the simulation """
        self.internal : list[Link] = list()
        """ Dynamic list of internal links: CELL to CELL, mainly used for rendering of the links """

        # OPT:: maybe voro++ face normal/area is faster?
        self.min_pos = Vector([INF_FLOAT]*3)
        self.max_pos = Vector([-INF_FLOAT]*3)
        self.min_area = INF_FLOAT
        self.max_area = -INF_FLOAT
        self.avg_area = 0

        # key is always sorted numerically -> negative walls id go at the beginning
        def getKey_swap(k1,k2) -> tuple[neigh_key_t,bool]:
            swap = k1 > k2
            key = (k1, k2) if not swap else (k2, k1)
            return key,swap
        def getKey(k1,k2, swap) -> neigh_key_t:
            key = (k1, k2) if not swap else (k2, k1)
            return key


        # FIRST loop to build the global dictionaries
        for idx_cell in cont.foundId:
            # skip deleted afterwards
            if idx_cell in cont.deletedId:
                continue

            # Will store some constant precalculated global data in the links
            obj        = cont.cells_objs[idx_cell]
            me         = cont.cells_meshes[idx_cell]
            m_toWorld  = utils_trans.get_worldMatrix_unscaled(obj, update=True)
            mn_toWorld = utils_trans.get_normalMatrix(m_toWorld)

            # iterate all faces including asymmetry placeholders (missing cells already ignored with cont_foundId)
            for idx_face, idx_neighCell in enumerate(cont.neighs[idx_cell]):

                # skip asymmetric (already prefilled keys_perCell)
                if idx_neighCell in CELL_ERROR_ENUM.all:
                    continue
                if idx_neighCell in cont.deletedId:
                    continue

                # get world props
                face: types.MeshPolygon = me.polygons[idx_face]
                pos = m_toWorld @ face.center
                normal = mn_toWorld @ face.normal
                area = face.area
                # NOTE:: rotated normals may potentially have a length of 1.0 +- 1e-8 but not worth normalizing
                #DEV.log_msg(f"face.normal {face.normal} (l: {face.normal.length}) -> world {normal} (l: {normal.length})", cut=False)

                # check min/max
                if self.min_pos.x > pos.x: self.min_pos.x = pos.x
                elif self.max_pos.x < pos.x: self.max_pos.x = pos.x
                if self.min_pos.y > pos.y: self.min_pos.y = pos.y
                elif self.max_pos.y < pos.y: self.max_pos.y = pos.y
                if self.min_pos.z > pos.z: self.min_pos.z = pos.z
                elif self.max_pos.z < pos.z: self.max_pos.z = pos.z
                # area too
                self.avg_area += area
                if self.min_area > area: self.min_area = area
                elif self.max_area < area: self.max_area = area

                if idx_neighCell < 0:
                    # link to a wall, wont be repeated
                    key = (idx_neighCell, idx_cell)
                    key_faces = (idx_neighCell, idx_face)
                    l = Link(key, key_faces, pos, normal, area, LINK_STATE_ENUM.WALL)

                    # add to graphs and external
                    self.cells_graph.add_edge(*key, l=l)
                    self.links_graph.add_node(key, l=l)
                    self.external.append(l)
                    # also static cont maps
                    cont.keys_perWall[idx_neighCell].append(key)
                    cont.keys_perCell[idx_cell][idx_face] = key

                else:
                    # internal link, check unique between cells (networkx works without swapping the key tho)
                    key,swap = getKey_swap(idx_cell, idx_neighCell)
                    if self.links_graph.has_node(key):
                        continue

                    # build the link
                    idx_neighFace = cont.neighs_faces[idx_cell][idx_face]
                    key_faces = getKey(idx_face, idx_neighFace, swap)
                    l = Link(key, key_faces, pos, normal, area, LINK_STATE_ENUM.SOLID)

                    # add to graphs and internal
                    self.cells_graph.add_edge(*key, l=l)
                    self.links_graph.add_node(key, l=l)
                    self.internal.append(l)
                    # also static cont maps
                    cont.keys_perCell[idx_cell][idx_face] = key
                    cont.keys_perCell[idx_neighCell][idx_neighFace] = key


        # count the links and calcualte averages
        self.links_len = self.links_graph.number_of_nodes()
        if self.links_len:
            self.avg_area /= float(self.links_len)

        stats.logDt(f"created link map: {self.links_len}")
        DEV.log_msg(f"Pos limits: {utils.vec3_to_string(self.min_pos)}, {utils.vec3_to_string(self.max_pos)}"
                    f" | Area limits: ({self.min_area:.2f},{self.max_area:.2f}) avg:{self.avg_area:.2f}",
                    {"CALC", "LINKS", "LIMITS"}, cut=False)


        # SECOND loop to aggregate the links neighbours, only need to iterate cont_foundId
        for idx_cell in cont.foundId:
            # skip deleted afterwards
            if idx_cell in cont.deletedId:
                continue

            # the face id is not indexed by the order in edges_perCell, then use static cont map that includes missing ones
            keys_perFace = cont.keys_perCell[idx_cell]
            for idx_face,key in enumerate(keys_perFace):

                # skip possible asymmetries
                if key[0] in CELL_ERROR_ENUM.all:
                    continue

                # avoid recalculating link neighs (and duplicating them)
                if len(self.get_link_neighsId(key)):
                    continue

                # retrieve valid link
                l = self.get_link(key)
                #DEV.log_msg(f"l {l.key_cells} {l.key_cells}")

                # calculate area factor relative to avg area (avg wont be zero when there are links_graph.nodes)
                l.area = l.area / self.avg_area

                # no AIR links
                if l.state == LINK_STATE_ENUM.WALL:
                    # walls only add local faces from the same cell
                    wf_neighs = cont.cells_meshes_FtoF[idx_cell][idx_face]
                    w_neighs = [ keys_perFace[f] for f in wf_neighs ]
                    self.links_graph.add_edges_from(w_neighs)

                else:
                    # regular links add both neigh faces from same and the other cell
                    # extract idx and geometry faces neighs
                    c1, c2 = l.key_cells
                    f1, f2 = l.key_faces
                    m1_neighs = cont.cells_meshes_FtoF[c1]
                    m2_neighs = cont.cells_meshes_FtoF[c2]
                    f1_neighs = m1_neighs[f1]
                    f2_neighs = m2_neighs[f2]

                    # the key is sorted, so query the keys per cell per each one
                    c1_keys = cont.keys_perCell[c1]
                    c2_keys = cont.keys_perCell[c2]
                    c1_neighs = [ c1_keys[f] for f in f1_neighs ]
                    c2_neighs = [ c2_keys[f] for f in f2_neighs ]
                    self.links_graph.add_edges_from(c1_neighs + c2_neighs)

        stats.logDt("aggregated link neighbours")

        # initial components subgraph calculation
        self.comps_recalc()

        logType = {"CALC", "LINKS"}
        if not self.links_len:
            logType |= {"ERROR"}
        DEV.log_msg(f"Found {self.links_len} links: {len(self.external)} external | {len(self.internal)} internal", logType)
        self.initialized = True

    def sanitize(self, root):
        """ Remove deleted cells from the graph and recalculate comps
            # OPT:: due to potential UNDO/REDO making cells reapear all foundID are added again
        """
        cleaned = False
        if not self.cont.deletedId or self.cont.deletedId == self.cont.deletedId_prev:
            return cleaned

        ## detect changes -> not ok cause removing nodes removes past edges
        #curr = set(self.cont.deletedId)
        #prev = set(self.cont.deletedId_prev)
        #newDeleted = curr - prev
        #newAdded = prev - curr
        ## add / remove cells
        #self.cells_graph.add_nodes_from(newAdded)
        #self.cells_graph.remove_nodes_from(newDeleted)

        # recalculate the components
        self.comps_recalc()
        return cleaned

    def comps_recalc(self):
        """ Recalc cell connected componentes, return true when changed """
        prevLen = self.comps_len

        # create a subgraph with no air, no missing cells and no additional walls
        stateMap = self.cont.getCells_splitID_state()
        valid = stateMap[CELL_STATE_ENUM.SOLID] + CELL_STATE_ENUM.SOLID[CELL_STATE_ENUM.CORE]
        self.comps_subgraph = self.cells_graph.subgraph(valid)

        # calc components
        self.comps = list(nx.connected_components(self.comps_subgraph))
        self.comps_len = len(self.comps)

        newSplit = prevLen != self.comps_len
        getStats().logDt(f"calculated components: {self.comps_len} {'[new SPLIT]' if newSplit else ''}")
        return newSplit

    def comps_linkBreak(self, key):
        l = self.get_link(key)

    #-------------------------------------------------------------------

    def get_link(self, key:neigh_key_t) -> Link:
        return self.links_graph.nodes[key]["l"]

    def get_link_neighsId(self, key:neigh_key_t) -> list[neigh_key_t]:
        """ The links neighs ID unordered by face or anything """
        return list(self.links_graph.edges(key))

    def get_link_neighs(self, key:neigh_key_t) -> list[Link]:
        """ The links neighs unordered by face or anything """
        return [ self.get_link(k) for k in self.get_link_neighsId(key) ]

    def reset_links(self):
        for key in self.links_graph.nodes():
            l = self.get_link(key)
            l.reset()
