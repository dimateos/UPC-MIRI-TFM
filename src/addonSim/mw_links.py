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

    def __init__(self, key_cells: tuple[int, int], key_faces: tuple[int, int], toWall=False):
        self.life = 1.0

        # no directionality
        self.key_cells: Link.keyType = key_cells
        self.key_faces: Link.keyType = key_faces

        # neighs populated afterwards
        # IDEA:: separate to cells / walls?
        self.toWall = toWall
        self.neighs: list[Link.keyType] = list()

#-------------------------------------------------------------------

class Links():

    def __init__(self, cont: Container, obj_shards: types.Object):
        stats = getStats()
        self.cont = cont
        self.obj_shards = obj_shards

        # XXX:: decouple scene from sim? calculate the FtoF map inside voro isntead of blender mesh...
        meshes = [ shard.data for shard in obj_shards.children ]
        meshes_dicts = [ utils_geo.get_meshDicts(me) for me in meshes ]
        stats.logDt("calculated shards mesh dicts")

        # XXX:: could be calculated in voro++, also avoid checking twice...
        # XXX:: using lists or maps to support non linear cell.id?
        cont_neighs = [ cell.neighbors() for cell in cont ]
        stats.logDt("calculated voro cell neighs")

        cont_neighs_faces = []
        for i,neighs in enumerate(cont_neighs):
            faces = [ n if n<0 else cont_neighs[n].index(i) for n in neighs ]
            cont_neighs_faces.append(faces)
        stats.logDt("calculated cell neighs faces")


        # TODO:: unionfind joined components
        # IDEA:: dynamic lists of separated?
        self.link_map: dict[Link.keyType, Link] = dict()
        self.num_toCells = 0
        self.num_toWalls = 0

        # IDEA:: keys to global map or direclty the links?
        # init cell dict with lists of its faces size (later index by face)
        self.keys_perCell: dict[int, list[Link.keyType]] = {cell.id: list([Link.keyType()]* len(cont_neighs[cell.id])) for cell in cont}
        # init wall dict with just empty lists (some will remain empty)
        self.keys_perWall: dict[int, list[Link.keyType]] = {id: list() for id in cont.get_conainerId_limitWalls()+cont.walls_cont_idx}


        # FIRST loop to build the global dictionaries
        for cell in cont:
            idx_cell = cell.id
            for idx_face, idx_neighCell in enumerate(cont_neighs[idx_cell]):

                # link to a wall, wont be repeated
                if idx_neighCell < 0:
                    key = (idx_neighCell, idx_cell)
                    key_faces = (idx_neighCell, idx_face)
                    l = Link(key, key_faces, toWall=True)

                    # add to mappings per wall and cell
                    self.num_toWalls += 1
                    self.link_map[key] = l
                    self.keys_perWall[idx_neighCell].append(key)
                    self.keys_perCell[idx_cell][idx_face] = key
                    continue

                # check unique links between cells
                # NOTE:: key does not include faces, expected only one face conected between cells
                key,swap = Links.getKey_swap(idx_cell, idx_neighCell)
                key_rep = key in self.link_map
                if key_rep:
                    continue

                # build the link
                idx_neighFace = cont_neighs_faces[idx_cell][idx_face]
                key_faces = Links.getKey(idx_face, idx_neighFace, swap)
                l = Link(key, key_faces)

                # add to mappings for both per cells
                self.num_toCells += 1
                self.link_map[key] = l
                self.keys_perCell[idx_cell][idx_face] = key
                self.keys_perCell[idx_neighCell][idx_neighFace] = key

        stats.logDt("created link map")
        return


        # SECOND loop to aggregate the links neighbours, only need to iterate keys_perCell
        for idx_cell,keys_perFace in self.keys_perCell.items():
            for idx_face,key in enumerate(keys_perFace):
                l = self.link_map[key]
                DEV.log_msg(f"l {l.key_cells} {l.key_cells}")

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
                f1_neighs = meshes_dicts[c1]["FtoF"][f1]
                f2_neighs = meshes_dicts[c2]["FtoF"][f2]

                # the key is sorted, so query the keys per cell per each one
                c1_neighs = [ self.keys_perCell[c1][f] for f in f1_neighs ]
                c2_neighs = [ self.keys_perCell[c2][f] for f in f2_neighs ]
                l.neighs += c1_neighs + c2_neighs

        stats.logDt("aggregated link neighbours")
        logType = {"CALC"} if self.link_map else {"CALC", "ERROR"}
        DEV.log_msg(f"Found {self.num_toCells} links to cells + {self.num_toWalls} links to walls (total {len(self.link_map)})", logType)


    @staticmethod
    def getKey_swap(k1,k2):
        swap = k1 > k2
        key = (k1, k2) if not swap else (k2, k1)
        return key,swap

    @staticmethod
    def getKey(k1,k2, swap):
        key = (k1, k2) if not swap else (k2, k1)
        return key