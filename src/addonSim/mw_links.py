import bpy.types as types
from mathutils import Vector, Matrix

from tess import Container, Cell

from . import utils
from . import utils_geo
from .utils_dev import DEV
from .stats import getStats


class LINK_ERROR_IDX:
    """ Use leftover indices between cont boundaries and custom walls for filler error idx """

    missing = -7
    """ Missing a whole cell / object"""
    asymmetry = -8
    """ Missing connection at in the supposed neighbour """

    e3 = -9
    all = [ missing, asymmetry ]

#-------------------------------------------------------------------


# OPT:: could use a class or an array of props? pyhton already slow so ok class?
class Link():
    keyType = tuple[int, int]

    def __init__(self, col: "LinkCollection", key_cells: tuple[int, int], key_faces: tuple[int, int], pos_world:Vector, dir_world:Vector, toWall=False):
        self.reset()
        # XXX:: to out?
        self.toWall = toWall

        # properties in world space?
        self.pos = pos_world
        self.dir = dir_world


        # no directionality but tuple key instead of set
        self.collection: "LinkCollection" = col
        self.key_cells: Link.keyType = key_cells
        self.key_faces: Link.keyType = key_faces

        # neighs populated afterwards
        self.neighs: list[Link.keyType] = list()
        self.neighs_dead: list[Link.keyType] = list()

    #-------------------------------------------------------------------

    def degrade(self, deg):
        """ Degrade link preserving life [0,1] """
        self.life -= deg
        self.life = max(0, self.life)
        self.life = min(1, self.life)

    def reset(self, life=1.0):
        """ Reset simulation parameters """
        self.life = life

    #-------------------------------------------------------------------



#-------------------------------------------------------------------

class LinkCollection():

    def __init__(self, cont: Container, obj_shards: types.Object):
        stats = getStats()
        self.initialized = False
        """ Set to true only at the end of a complete LinkCollection initialization """


        # TODO:: unionfind joined components + manually delete links
        # IDEA:: dynamic lists of broken?
        self.link_map: dict[Link.keyType, Link] = dict()

        # init wall dict with just empty lists (some will remain empty)
        self.keys_perWall: dict[int, list[Link.keyType]] = {
            id: list() for id in cont.get_conainerId_limitWalls()+cont.walls_cont_idx
        }
        self.num_toWalls = 0

        # OPT:: raw int error substutiting lists or put in a list with just the errorring int?
        # cell dict lists will have the same size of neighs/faces so fill in the following loop while checking for missing ones
        self.keys_perCell: dict[int, list[Link.keyType] | int] = dict()
        """ NOTE:: missing cells are filled with a placeholder id to preserve original position idx """
        self.num_toCells = 0


        # calculate missing cells and query neighs
        self.cont = cont
        self.cont_foundId   : list[int]           = []
        self.cont_missingId : list[int]           = []
        self.cont_neighs    : list[list[int]|int] = [LINK_ERROR_IDX.missing]*len(cont)
        """ NOTE:: missing cells are filled with a placeholder id to preserve original position idx """

        for idx_cell,cell in enumerate(cont):
            if cell is None:
                self.cont_missingId.append(idx_cell)
                self.keys_perCell[idx_cell] = LINK_ERROR_IDX.missing
            else:
                self.cont_foundId.append(idx_cell)
                neighs = cell.neighbors()
                self.cont_neighs[idx_cell] = neighs
                # prefill with asymmetry keys too
                key = (LINK_ERROR_IDX.asymmetry, idx_cell)
                self.keys_perCell[idx_cell] = [key]*len(neighs)

        msg = f"calculated voro cell neighs: {len(self.cont_missingId)} / {len(cont)} missing"
        if self.cont_missingId: msg += f" {str(self.cont_missingId[:20])}"
        stats.logDt(msg) # uncut=True


        # build symmetric face map of the found cells
        self.keys_asymmetry    : list[Link.keyType]  = []
        self.cont_neighs_faces : list[list[int]|int] = [LINK_ERROR_IDX.missing]*len(cont)
        """ NOTE:: missing cells and neigh asymmetries are filled with a placeholder id too """

        for idx_cell,neighs in enumerate(self.cont_neighs):
            # skip missing cell
            if neighs == LinkCollection.CONST_ERROR_IDX.missing:
                continue

            faces: list[int] = [LINK_ERROR_IDX.asymmetry] * len(neighs)
            for idx_face,idx_neigh in enumerate(neighs):
                # wall connection always ok, so simply add its index
                if idx_neigh < 0: faces.append(idx_neigh)

                # general cases try retrieving other end respective face
                else:
                    neigh_idx_face = -1
                    neighsOther = self.cont_neighs[idx_neigh]

                    # possibly a whole missing cell at the other side
                    if neighsOther != LINK_ERROR_IDX.missing:
                        # symmetry checked with .index exception
                        try: neigh_idx_face = neighsOther.index(idx_cell)
                        except ValueError: pass

                    # correclty found face
                    if neigh_idx_face != -1:
                        faces[idx_face] = neigh_idx_face

                    # otherwise replace with error idx in the structures
                    else:
                        key = (idx_cell,idx_neigh)
                        self.keys_asymmetry.append(key)
                        neighs[idx_face] = LINK_ERROR_IDX.asymmetry

            self.cont_neighs_faces[idx_cell] = faces

        msg = f"calculated cell neighs faces: {len(self.keys_asymmetry)} asymmetries"
        if self.keys_asymmetry: msg += f" {str(self.keys_asymmetry[:10])}"
        stats.logDt(msg) # uncut=True


        # retrieve objs, meshes -> dicts per shard
        self.shards_parent = obj_shards
        self.shards_objs     : list[types.Object|int] = [LINK_ERROR_IDX.missing]* len(cont)
        self.shards_meshes   : list[types.Mesh|int]   = [LINK_ERROR_IDX.missing]* len(cont)
        self.shards_meshMaps : list[dict|int]         = [LINK_ERROR_IDX.missing]* len(cont)

        for idx_found,shard in enumerate(obj_shards.children):
            idx_cell = self.cont_foundId[idx_found]
            self.shards_objs[idx_cell] = shard
            mesh = shard.data
            self.shards_meshes[idx_cell] = mesh
            self.shards_meshMaps[idx_cell] = utils_geo.get_meshDicts(mesh)

        stats.logDt("calculated shards mesh dicts (interleaved missing cells)")

        # FIRST loop to build the global dictionaries
        for idx_cell in self.cont_foundId:

            # XXX:: data to calculate global pos here or leave for links to do?
            obj        = self.shards_objs[idx_cell]
            me         = self.shards_meshes[idx_cell]
            m_toWorld  = utils.get_worldMatrix_unscaled(obj, update=True)
            mn_toWorld = utils.get_normalMatrix(m_toWorld)

            # iterate all faces including asymmetry placeholders (missing cells already ignored with cont_foundId)
            for idx_face, idx_neighCell in enumerate(self.cont_neighs[idx_cell]):

                # skip asymmetric (already prefilled keys_perCell)
                if idx_neighCell == LINK_ERROR_IDX.asymmetry:
                    continue

                # get world props
                face: types.MeshPolygon = me.polygons[idx_face]
                pos = m_toWorld @ face.center
                normal = mn_toWorld @ face.normal
                # NOTE:: potentially rotated normals may have a length of 1.0 +- 1e-8 but not worth normalizing
                #DEV.log_msg(f"face.normal {face.normal} (l: {face.normal.length}) -> world {normal} (l: {normal.length})", cut=False)

                # link to a wall, wont be repeated
                if idx_neighCell < 0:
                    key = (idx_neighCell, idx_cell)
                    key_faces = (idx_neighCell, idx_face)
                    l = Link(self, key, key_faces, pos, normal, toWall=True)

                    # add to mappings per wall and cell
                    self.num_toWalls += 1
                    self.link_map[key] = l
                    self.keys_perWall[idx_neighCell].append(key)
                    self.keys_perCell[idx_cell][idx_face] = key
                    continue

                # check unique links between cells
                # XXX:: key does not include faces, convex cells so expected only one face conected between cells
                key,swap = LinkCollection.getKey_swap(idx_cell, idx_neighCell)
                key_rep = key in self.link_map
                if key_rep:
                    continue

                # build the link
                idx_neighFace = self.cont_neighs_faces[idx_cell][idx_face]
                key_faces = LinkCollection.getKey(idx_face, idx_neighFace, swap)
                l = Link(self, key, key_faces, pos, normal)

                # add to mappings for both per cells
                self.num_toCells += 1
                self.link_map[key] = l
                self.keys_perCell[idx_cell][idx_face] = key
                self.keys_perCell[idx_neighCell][idx_neighFace] = key

        stats.logDt(f"created link map")


        # SECOND loop to aggregate the links neighbours, only need to iterate keys_perCell
        for idx_cell in self.cont_foundId:
            keys_perFace = self.keys_perCell[idx_cell]
            for idx_face,key in enumerate(keys_perFace):
                # skip possible asymmetries
                if key[0] in LINK_ERROR_IDX.all:
                    continue

                # retrieve valid link
                l = self.link_map[key]
                #DEV.log_msg(f"l {l.key_cells} {l.key_cells}")

                # avoid recalculating link neighs (and duplicating them)
                if l.neighs:
                    continue

                # walls only add local faces from the same cell
                if l.toWall:
                    w_neighs = self.shards_meshMaps[idx_cell]["FtoF"][idx_face]
                    w_neighs = [ keys_perFace[f] for f in w_neighs ]
                    l.neighs += w_neighs
                    continue

                # extract idx and geometry faces neighs
                c1, c2 = l.key_cells
                f1, f2 = l.key_faces
                m1_neighs = self.shards_meshMaps[c1]["FtoF"]
                m2_neighs = self.shards_meshMaps[c2]["FtoF"]
                f1_neighs = m1_neighs[f1]
                f2_neighs = m2_neighs[f2]

                # the key is sorted, so query the keys per cell per each one
                c1_keys = self.keys_perCell[c1]
                c2_keys = self.keys_perCell[c2]
                c1_neighs = [ c1_keys[f] for f in f1_neighs ]
                c2_neighs = [ c2_keys[f] for f in f2_neighs ]
                l.neighs += c1_neighs + c2_neighs

        stats.logDt("aggregated link neighbours")
        logType = {"CALC", "LINKS"}
        if not self.link_map: logType |= {"ERROR"}
        DEV.log_msg(f"Found {self.num_toCells} links to cells + {self.num_toWalls} links to walls (total {len(self.link_map)})", logType)
        self.initialized = True

    #-------------------------------------------------------------------
    # IDEA:: not sure about what to give access to

    def getMesh(self, idx: list[int]|int) -> list[types.Mesh]|types.Mesh:
        """ return a mesh or list of meshes given idx  """
        try:
            return self.shard_meshes[idx]
        except TypeError:
            return [ self.shard_meshes[i] for i in idx ]

    def getFace(self, midx: list[int]|int, fidx: list[int]|int) -> list[types.MeshPolygon]|types.MeshPolygon:
        """ return a face or list of faces given idx  """
        try:
            return self.shard_meshes[midx].polygons[fidx]
        except TypeError:
            return [ self.shard_meshes[i].polygons[j] for i,j in zip(midx,fidx) ]

    #-------------------------------------------------------------------

    @staticmethod
    def getKey_swap(k1,k2) -> tuple[Link.keyType,bool]:
        swap = k1 > k2
        key = (k1, k2) if not swap else (k2, k1)
        return key,swap

    @staticmethod
    def getKey(k1,k2, swap) -> Link.keyType:
        key = (k1, k2) if not swap else (k2, k1)
        return key

#-------------------------------------------------------------------


# OPT:: store links between objects -> add json parser to store persistently? or retrieve from recalculated cont?
# OPT:: register some calback on object rename? free the map or remap
# XXX:: this storage is lost on module reload...
class LinkStorage:
    bl_links: dict[str, LinkCollection] = dict()
    bl_links_users: dict[str, types.Object] = dict()

    @staticmethod
    def addLinks(links, uniqueName, user):
        DEV.log_msg(f"Add: {uniqueName}...", {"STORAGE", "LINKS"})

        # add the links and the user to the storage
        if uniqueName in LinkStorage.bl_links:
            DEV.log_msg(f"Replacing found links", {"STORAGE", "LINKS", "ERROR"})
        LinkStorage.bl_links[uniqueName] = links
        LinkStorage.bl_links_users[uniqueName] = user

    @staticmethod
    def getLinks(uniqueName):
        DEV.log_msg(f"Get: {uniqueName}...", {"STORAGE", "LINKS"})
        try:
            return LinkStorage.bl_links[uniqueName]
        except KeyError:
            DEV.log_msg(f"Not found: probably reloaded the module?", {"STORAGE", "LINKS", "ERROR"})

    @staticmethod
    def freeLinks(uniqueName):
        DEV.log_msg(f"Del: {uniqueName}...", {"STORAGE", "LINKS"})
        try:
            # delete the links and only pop the user
            links = LinkStorage.bl_links.pop(uniqueName)
            del links
            user = LinkStorage.bl_links_users.pop(uniqueName)
        except KeyError:
            DEV.log_msg(f"Not found: probably reloaded the module?", {"STORAGE", "LINKS", "ERROR"})

    #-------------------------------------------------------------------

    @staticmethod
    def purgeLinks():
        toPurge = []

        # detect broken object references
        for name,obj in LinkStorage.bl_links_users.items():
            if utils.needsSanitize_object(obj):
                toPurge.append(name)

        DEV.log_msg(f"Purging {len(toPurge)}: {toPurge}", {"STORAGE", "LINKS"})
        for name in toPurge:
            LinkStorage.freeLinks(name)

    @staticmethod
    def purgeLinks_callback(_scene_=None, _undo_name_=None):
        LinkStorage.purgeLinks()