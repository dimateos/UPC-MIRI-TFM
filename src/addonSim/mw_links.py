import bpy.types as types

from . import utils
from . import utils_geo
from .utils_dev import DEV
from .stats import Stats

from mathutils import Vector, Matrix

# Using tess voro++ adaptor
from tess import Container, Cell


# -------------------------------------------------------------------

# OPT:: could use a class or an array of props? pyhton already slow so ok class?
class Link():

    def __init__(self, key_cells: tuple[int, int], key_faces: tuple[int, int]):
        self.life = 1.0
        self.wall = self.air = key_cells[0] < 0 or key_cells[1] < 0

        # no directionality
        self.key_cells = key_cells
        self.key_faces = key_faces

        # neighs populated afterwards
        self.neighs = []

# -------------------------------------------------------------------

class Links():

    def __init__(self, cont: Container, obj_shards: types.Object, stats: Stats):
        # WIP:: copy instead of ref?
        self.cont = cont
        self.obj_shards = obj_shards

        # XXX:: decouple scene from sim? calculate the FtoF map inside voro isntead of blender mesh...
        meshes = [ shard.data for shard in obj_shards.children ]
        meshes_dicts = [ utils_geo.get_meshDicts(me) for me in meshes ]
        stats.log("calculated shards mesh dicts")

        # XXX:: could be calculated in voro++, also avoid checking twice...
        # XXX:: using lists or maps to support non linear cell.id?
        cont_neighs = [ cell.neighbors() for cell in cont ]
        stats.log("calculated voro cell neighs")
        cont_neighs_faces = []
        for i,neighs in enumerate(cont_neighs):
            faces = [ n if n<0 else cont_neighs[n].index(i) for n in neighs ]
            cont_neighs_faces.append(faces)
        stats.log("calculated cell neighs faces")


        # TODO:: unionfind joined components
        # IDEA:: dynamic lists of separated?
        self.link_map: dict[tuple[int, int], Link] = dict()

        # IDEA:: keys to global map or direclty the links?
        # init cell dict with lists of its faces size (later index by face)
        self.keys_perCell: dict[int, list[Link]] = {cell.id: list([None]* len(cont_neighs[cell.id])) for cell in cont}
        # init wall dict with just empty lists (some will remain empty)
        self.keys_perWall: dict[int, list[Link]] = {id: list() for id in cont.get_conainerId_limitWalls()+cont.walls_cont_idx}


        # FIRST loop to build the global dictionaries
        for cell in cont:
            idx_cell = cell.id
            for idx_face, idx_neighCell in enumerate(cont_neighs[idx_cell]):

                # link to a wall, wont be repeated
                if idx_neighCell < 0:
                    key = (idx_neighCell, idx_cell)
                    key_faces = (idx_neighCell, idx_face)
                    l = Link(key, key_faces)
                    # add to mappings
                    self.link_map[key] = l
                    self.keys_perCell[idx_cell][idx_face] = key
                    self.keys_perWall[idx_neighCell].append(key)
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

                # add to global, per wall and to the cell
                self.link_map[key] = l
                self.keys_perCell[idx_cell][idx_face] = key
                self.keys_perCell[idx_neighCell][idx_neighFace] = key

        stats.log("created link set")

        #self.per_wall_empty: dict[int, list[Link]] = {id: [] for id in cont.walls_cont_idx}

        ## SECOND loop to aggregate the links neighbours
        #for link in self.in_air:
        #    c1, c2 = link.key_cells
        #    f1, f2 = link.key_faces
        #    neighs1 = meshes_dicts[c1]["FtoF"][f1]
        #    neighs2 = meshes_dicts[c2]["FtoF"][f2]
        #    links1 = [  ]
        #    #link.neighs

        logType = {"CALC"} if self.in_cells else {"CALC", "ERROR"}
        DEV.log_msg(f"Found {len(self.in_cells)} links in cells ({len(self.in_air)} in air walls)", logType)


    @staticmethod
    def getKey_swap(k1,k2):
        swap = k1 > k2
        key = (k1, k2) if not swap else (k2, k1)
        return key,swap

    @staticmethod
    def getKey(k1,k2, swap):
        key = (k1, k2) if not swap else (k2, k1)
        return key