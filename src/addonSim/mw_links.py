import bpy.types as types
from mathutils import Vector, Matrix

from tess import Container, Cell

from . import utils
from . import utils_geo
from .utils_dev import DEV
from .stats import getStats


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


    def reset(self):
        """ Reset simulation parameters """
        self.life = 1.0


#-------------------------------------------------------------------

class LinkCollection():

    class CONST_ERROR_IDX:
        """ Use leftover indices between cont boundaries and custom walls for filler error idx """
        asymmetry = -7
        missing = -8
        e3 = -9

    def __init__(self, cont: Container, obj_shards: types.Object):
        stats = getStats()
        self.initialized = False

        # retrieve objs, meshes -> dicts per shard
        self.obj_shards = obj_shards
        self.shard_objs: list[types.Object]= [ shard for shard in obj_shards.children ]
        self.shard_meshes: list[types.Mesh]= [ shard.data for shard in self.shard_objs ]

        # NOTE:: store the dicts?
        meshes_dicts: list[dict] = [ utils_geo.get_meshDicts(me) for me in self.shard_meshes ]
        stats.logDt("calculated shards mesh dicts")


        # calculate missing cells and query neighs -> shard_objs match the missing ones
        self.cont = cont
        self.cont_foundId: list[int] = []
        self.cont_missingId: list[int] = []
        self.cont_neighs_found: list[list[int]] = []
        for i,cell in enumerate(cont):
            if cell is None:
                self.cont_missingId.append(i)
            else:
                self.cont_foundId.append(i)
                self.cont_neighs_found.append(cell.neighbors())

        stats.logDt(f"calculated voro cell neighs: {len(self.cont_foundId)} / {len(self.cont)} ({len(self.cont_missingId)} missing)")

        # build symmetric face map of the found cells
        self.cont_neighs_faces: list[list[int]] = []
        self.keys_asymmetry: list[Link.keyType] = []
        for i,neighs in zip(self.cont_foundId, self.cont_neighs_found):
            faces: list[int] = []
            for f,n in enumerate(neighs):
                # wall simply add its index
                if n < 0: faces.append(n)

                # otherwise check symmetry at the other end
                else:
                    try: faces.append(self.cont_neighs_found[n].index(i))
                    except ValueError:
                        # replace with error idx in the structures but preserve the rest
                        self.keys_asymmetry.append((i,n))
                        neighs[f] = self.CONST_ERROR_IDX.asymmetry
                        faces.append(self.CONST_ERROR_IDX.asymmetry)

            self.cont_neighs_faces.append(faces)

        stats.logDt(f"calculated cell neighs faces: {len(self.keys_asymmetry)} asymmetries"
                    f" {str(self.keys_asymmetry[:8])}..." if self.keys_asymmetry else "")


        # init cell dict with lists of its faces size (later index by face)
        self.keys_perCell: dict[int, list[Link.keyType]] = {
            id: list([Link.keyType()]* len(faces)) for id,faces in enumerate(self.cont_neighs_faces)
        }
        self.num_toCells = 0

        # init wall dict with just empty lists (some will remain empty)
        self.keys_perWall: dict[int, list[Link.keyType]] = {
            id: list() for id in cont.get_conainerId_limitWalls()+cont.walls_cont_idx
        }
        self.num_toWalls = 0

        # TODO:: unionfind joined components + manually delete links
        # IDEA:: dynamic lists of broken?
        self.link_map: dict[Link.keyType, Link] = dict()


        # FIRST loop to build the global dictionaries
        for idx_cell in self.cont_foundId:
            obj = self.shard_objs[idx_cell]
            me = self.shard_meshes[idx_cell]

            m_toWorld = utils.get_worldMatrix_unscaled(obj, update=True)
            mn_toWorld = utils.get_normalMatrix(m_toWorld)

            for idx_face, idx_neighCell in enumerate(self.cont_neighs_found[idx_cell]):

                # add asymmetries to keys per cell at least
                if idx_neighCell == self.CONST_ERROR_IDX.asymmetry:
                    key = (idx_neighCell, idx_cell)
                    self.keys_perCell[idx_cell][idx_face] = key
                    continue

                # get world props
                # XXX:: calculated here or per link with ability to recalc?
                face = me.polygons[idx_face]
                pos = m_toWorld @ face.center
                normal = mn_toWorld @ face.normal
                # XXX:: need to normalize normals after tranformation? in theory only rotates so no

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
        # XXX:: found empty key? () still with the particles inside cube inside ico


        # SECOND loop to aggregate the links neighbours, only need to iterate keys_perCell
        for idx_cell,keys_perFace in self.keys_perCell.items():
            for idx_face,key in enumerate(keys_perFace):
                # skip possible asymmetries
                if key[0] == self.CONST_ERROR_IDX.asymmetry:
                    continue

                # retrieve valid link
                l = self.link_map[key]
                #DEV.log_msg(f"l {l.key_cells} {l.key_cells}")

                # avoid recalculating link neighs (and duplicating them)
                if l.neighs:
                    continue

                # walls only add local faces from the same cell
                if l.toWall:
                    w_neighs = meshes_dicts[idx_cell]["FtoF"][idx_face]
                    w_neighs = [ keys_perFace[f] for f in w_neighs ]
                    l.neighs += w_neighs
                    continue

                # extract idx and geometry faces neighs
                c1, c2 = l.key_cells
                f1, f2 = l.key_faces
                m1_neighs = meshes_dicts[c1]["FtoF"]
                m2_neighs = meshes_dicts[c2]["FtoF"]
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