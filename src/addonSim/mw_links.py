import bpy
import bpy.types as types
from mathutils import Vector, Matrix
INF_FLOAT = float("inf")
import networkx as nx
import itertools

from .mw_cont import MW_Cont, CELL_ERROR_ENUM, CELL_STATE_ENUM, neigh_key_t, neighFaces_key_t
from . import mw_resistance

from . import utils, utils_trans
from .utils_trans import VECTORS
from .utils_dev import DEV
from .stats import getStats

#-------------------------------------------------------------------

class LINK_STATE_ENUM:
    """ Current links state, preserves some sequentiality """
    SOLID = 0
    WALL = 1
    AIR = 2

    all = { SOLID, WALL, AIR }

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
        raise ValueError(f"CELL_STATE_ENUM: {s} is not in {set(LINK_STATE_ENUM.to_str(s) for s in cls.all)}")

class Link():
    """ # OPT:: could use separate array of props? pyhton already slow so ok class?"""

    def __init__(self, key_cells: neigh_key_t, key_faces: neighFaces_key_t, pos_world:Vector, dir_world:Vector, dir_from:int, face_area:float, state=LINK_STATE_ENUM.SOLID):
        # no directionality but tuple key instead of set
        self.key_cells : neigh_key_t      = key_cells
        self.key_faces : neighFaces_key_t = key_faces

        # sim props
        self.state_initial = state
        self.reset()

        # properties in world space
        self.pos = pos_world
        self.dir = dir_world
        self.dir_from = dir_from
        # properties to later normalize
        self.area = face_area

        # TODO:: resistance
        #self.resistance = 0.5 + 0.5* mw_resistance.get2D(self.pos.x, self.pos.y)
        self.resistance = mw_resistance.get2D(self.pos.x, self.pos.y)

    def reset(self, life=1.0, picks=0, picks_entry=0):
        """ Reset simulation parameters """
        self.state = self.state_initial
        self.life = life
        self.picks = picks
        self.picks_entry = picks_entry

    def set_broken(self):
        self.state = LINK_STATE_ENUM.AIR
        # TODO:: count exit, picks_exit?
        #self.life = 0
        self.picks = 0

    def flip_dir(self):
        self.dir = -self.dir
        if self.dir_from == self.key_cells[0]:
            self.dir_from = self.key_cells[1]
        else:
            self.dir_from = self.key_cells[0]

    def __str__(self):
        #a({self.area:.2f}), p({self.picks},{self.picks_entry}),
        if self.state == LINK_STATE_ENUM.WALL:
            return f"W{self.key_cells[0]}: p({self.picks_entry}), dir{self.dir.to_tuple(2)}"
        elif self.state == LINK_STATE_ENUM.AIR:
            return f"kA{self.key_cells}: l({self.life:.3f}), dir{self.dir.to_tuple(2)}"
        else:
            return f"k{self.key_cells}: l({self.life:.3f}), dir{self.dir.to_tuple(2)}"

    def degrade(self, deg):
        """ Degrade link life, return true when broken """
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
            # NOTE:: edges for a given node are not returned sorted by face, use faceKey inside the link to get the actual face index
            # NOTE:: adding edges creates nodes, but added edges might swap the indices order! use getKey_swap to make sure
            # NOTE:: removing nodes from the graphs takes all their edges too (use subgraphs)
        """

        self.comps = []
        """ List of sets with connected components cells id """
        self.comps_subgraph = nx.Graph() # used to leave cells_graph untouched (edges get removed along nodes)
        self.comps_len = 1               # initial expected

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

                # get link dir props
                face: types.MeshPolygon = me.polygons[idx_face]
                normal = mn_toWorld @ face.normal
                # NOTE:: rotated normals may potentially have a length of 1.0 +- 1e-8 but not worth normalizing
                #DEV.log_msg(f"face.normal {face.normal} (l: {face.normal.length}) -> world {normal} (l: {normal.length})", cut=False)

                # skip aligned with z for debug model
                if MW_Links.skip_dir_debugModel(normal):
                    # could set IGNORED error idx but not worth it
                    continue

                # get world props, some normalized afterwards
                pos = m_toWorld @ face.center
                area = face.area

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
                    l = Link(key, key_faces, pos, normal, idx_cell, area, LINK_STATE_ENUM.WALL)

                    # add to graphs and external
                    self.cells_graph.add_edge(*key, l=l)
                    #self.links_graph.add_node(key, l=l)
                    self.external.append(l)
                    # also static cont maps
                    cont.keys_perWall[idx_neighCell].append(key)
                    cont.keys_perCell[idx_cell][idx_face] = key

                else:
                    # internal link, check unique between cells (networkx works without swapping the key tho)
                    key,swap = self.getKey_swap(idx_cell, idx_neighCell)
                    if self.cells_graph.has_edge(*key):
                    #if self.links_graph.has_node(key):
                        continue

                    # build the link
                    idx_neighFace = cont.neighs_faces[idx_cell][idx_face]
                    key_faces = self.getKey(idx_face, idx_neighFace, swap)
                    l = Link(key, key_faces, pos, normal, idx_cell, area, LINK_STATE_ENUM.SOLID)

                    # add to graphs and internal
                    self.cells_graph.add_edge(*key, l=l)
                    #self.links_graph.add_node(key, l=l)
                    self.internal.append(l)
                    # also static cont maps
                    cont.keys_perCell[idx_cell][idx_face] = key
                    cont.keys_perCell[idx_neighCell][idx_neighFace] = key


        # count the links and calcualte averages
        self.links_len = self.cells_graph.number_of_edges()
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

                # avoid recalculating link neighs, create a node in links_graph now
                if self.links_graph.has_node(key):
                    if "l" in self.links_graph.nodes[key]:
                        continue
                l : Link = self.cells_graph.edges[key]["l"]
                self.links_graph.add_node(key, l=l)

                # calculate area factor relative to avg area (avg wont be zero when there are links_graph.nodes)
                l.area = l.area / self.avg_area

                # no AIR links
                if l.state == LINK_STATE_ENUM.WALL:
                    # walls only add local faces from the same cell
                    wf_neighs = cont.cells_meshes_FtoF[idx_cell][idx_face]
                    w_neighs = [ keys_perFace[f] for f in wf_neighs ]
                    self.add_links_neigs(key, w_neighs)

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
                    self.add_links_neigs(key, c1_neighs + c2_neighs)

        stats.logDt("aggregated link neighbours")

        # initial components subgraph calculation
        self.comps_recalc()

        #assert(len(list(self.cells_graph.edges)) == len(list(self.links_graph.nodes)))
        #assert( { getKey_swap(k[0],k[1])[0] for k in self.cells_graph.edges } == set(self.links_graph.nodes))

        logType = {"CALC", "LINKS"}
        if not self.links_len:
            logType |= {"ERROR"}
        DEV.log_msg(f"Found {self.links_len} links: {len(self.external)} external | {len(self.internal)} internal", logType)
        self.initialized = True

    def add_links_neigs(self, key, newNeighs):
        #self.links_graph.add_edges_from(newNeighs)
        for nn in newNeighs:
            if nn[0] not in CELL_ERROR_ENUM.all:
                self.links_graph.add_edge(key, nn)

    #-------------------------------------------------------------------

    def sanitize(self, root):
        """ Remove deleted cells from the graph and recalculate comps
            # OPT:: due to potential UNDO/REDO making cells reapear all foundID are added again
        """
        # TODO:: undo/redo not fully working + exepcts with deleted cells?
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
        """ Recalc cell connected componentes, return true and recalc frontier when changed """
        prevLen = self.comps_len

        # create a subgraph excluding missing cells and links
        self.comps_recalc_subgraph()
        # OPT:: shared statemaps across methods, or keep uptodate
        # OPT:: too much link/id interchange and requery too..

        # calc components
        self.comps = list(nx.connected_components(self.comps_subgraph))
        self.comps_len = len(self.comps)

        newSplit = prevLen != self.comps_len
        getStats().logDt(f"calculated components: {self.comps_len} {'[new SPLIT]' if newSplit else ''}")
        if newSplit:
            self.comps_recalc_frontier()
        return newSplit

    def comps_recalc_subgraph(self):
        # create a subgraph with no air, no missing cells and no additional walls
        stateMap = self.cont.getCells_splitID_state()
        valid = stateMap[CELL_STATE_ENUM.SOLID] + stateMap[CELL_STATE_ENUM.CORE]
        # copy the read only subgraph, cannot copy and remove because there are extra edges from virtual wall cells
        self.comps_subgraph : nx.Graph = self.cells_graph.subgraph(valid).copy()

        # remove missing links too
        stateMap_links = self.get_link_splitID_state()
        removed_links = stateMap_links[LINK_STATE_ENUM.AIR] + stateMap_links[LINK_STATE_ENUM.WALL]
        self.comps_subgraph.remove_edges_from(removed_links)

    def comps_recalc_frontier(self):
        """ Check new internal and external links, also changes cells state to air """
        # potential detach of cells
        if self.comps_len > 1:
            self.comps_detach_frontier()

        # all solid are internal
        stateMap_linksRaw = self.get_link_split_state()
        self.internal = stateMap_linksRaw[LINK_STATE_ENUM.SOLID]

        # external pick only the ones with at least a solid at the other side
        self.external.clear()
        for l in stateMap_linksRaw[LINK_STATE_ENUM.WALL] + stateMap_linksRaw[LINK_STATE_ENUM.AIR]:
            c1,c2 = l.key_cells
            s2 = self.cont.cells_state[c2]
            if s2 == LINK_STATE_ENUM.SOLID:
                self.external.append(l)

            # walls have negative id, there is no cell associated
            if l.state != LINK_STATE_ENUM.WALL:
                s1 = self.cont.cells_state[c1]
                if s1 == LINK_STATE_ENUM.SOLID:
                    self.external.append(l)

    def comps_detach_frontier(self):
        stateMap = self.cont.getCells_splitID_state()

        # filter core comps
        comp_notCore = []
        for i, comp_cells in enumerate(self.comps):
            notCore = True
            # OPT:: could just iterate once and check states, no need for state map either
            for coreId in stateMap[CELL_STATE_ENUM.CORE]:
                if coreId in comp_cells:
                    notCore = False
                    break
            if notCore:
                comp_notCore.append(i)

        # all core, do nothing
        if not comp_notCore:
            return

        comps_canditates = [ self.comps[i] for i in comp_notCore ]
        new_air_cells = []

        # some core so remove the rest
        if len(comp_notCore) != len(self.comps):
            new_air_cells = list(itertools.chain.from_iterable(comps_canditates))
        # no core so remove all but largest one
        else:
            comps_canditates = sorted(comps_canditates, key=len)
            new_air_cells = list(itertools.chain.from_iterable(comps_canditates[:-1]))


        # set the state for all and update in the scene
        self.cont.setCells_state(new_air_cells, CELL_STATE_ENUM.AIR)
        from . import mw_setup
        mw_setup.update_cellsState(self.cont, self.cont.root)

        # break links between air cells
        for cell_id in new_air_cells:
            for key in self.get_cell_linksKeys(cell_id):
                self.check_link_air(key)

        # OPT:: update all visuals? should be reusing meshes?
        #mw_setup.gen_linksAll(bpy.context)

    #-------------------------------------------------------------------

    def check_link_break(self, key, apply=True):
        """ Check the broken link than may divide the comps, return true and recalc frontier when changed """
        l = self.get_link(key)
        l.set_broken()
        c1,c2 = l.key_cells
        self.comps_subgraph.remove_edges_from([l.key_cells])
        # TODO:: handle links to deleted cells (remove_edges_from silently ignore missing)

        if apply:
            breaking = not nx.has_path(self.cells_graph, c1, c2)
            if breaking:
                self.comps_recalc_frontier()
            return breaking
        return False

    def check_link_air(self, key):
        l = self.get_link(key)

        # break all that were solid
        if l.state != LINK_STATE_ENUM.SOLID:
            return
        self.check_link_break(key, False)

        # potentially flip normals
        if self.cont.cells_state[l.dir_from] != CELL_STATE_ENUM.SOLID:
            l.flip_dir()

    #-------------------------------------------------------------------

    def get_link(self, key:neigh_key_t) -> Link:
        return self.links_graph.nodes[key]["l"]
    def get_links(self, keys:list[neigh_key_t]) -> list [Link]:
        return [self.links_graph.nodes[k]["l"] for k in keys ]

    def get_link_neighsId(self, key:neigh_key_t) -> list[neigh_key_t]:
        """ The links neighs ID unordered by face or anything """
        return list(self.links_graph.neighbors(key))
    def get_link_neighs(self, key:neigh_key_t) -> list[Link]:
        """ The links neighs unordered by face or anything """
        return [ self.get_link(k) for k in self.get_link_neighsId(key) ]

    def get_cell_linksKeys(self, idx:int) -> list[Link]:
        """ The links ID from a given cell with properly sorted keys """
        return [ self.getKey_swap(k[0],k[1])[0] for k in self.cells_graph.edges(idx) ]

    def get_cell_links(self, idx:int) -> list[Link]:
        """ The links from a given cell """
        return self.get_links(self.get_cell_linksKeys(idx))

    def get_link_splitID_state(self):
        """ Split links ID by state
            # OPT:: store and only update?
        """
        stateMap = {
            state : [] for state in LINK_STATE_ENUM.all
        }

        for key in self.links_graph.nodes():
            l = self.get_link(key)
            stateMap[l.state].append(key)

        return stateMap

    def get_link_split_state(self):
        """ Split links by state
            # OPT:: store and only update? + same code almost
        """
        stateMap = {
            state : [] for state in LINK_STATE_ENUM.all
        }

        for key in self.links_graph.nodes():
            l = self.get_link(key)
            stateMap[l.state].append(l)

        return stateMap

    #-------------------------------------------------------------------

    # key is always sorted numerically -> negative walls id go at the beginning
    # tuples are inmutable so need to return a new one
    @staticmethod
    def getKey_swap(k1,k2) -> tuple[neigh_key_t,bool]:
        swap = k1 > k2
        key = (k1, k2) if not swap else (k2, k1)
        return key,swap
    @staticmethod
    def getKey(k1,k2, swap) -> neigh_key_t:
        key = (k1, k2) if not swap else (k2, k1)
        return key

    # debug model is basically 2D
    @staticmethod
    def skip_dir_debugModel(d:Vector):
        if DEV.DEBUG_MODEL:
            return utils_trans.aligned(d, VECTORS.backY, bothDir=True)
        return False
    @staticmethod
    def skip_link_debugModel(l:Link):
        if DEV.DEBUG_MODEL:
            return MW_Links.skip_dir_debugModel(l.dir)
        return False