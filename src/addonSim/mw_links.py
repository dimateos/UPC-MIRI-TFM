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
        self.air = key_cells[0] < 0 or key_cells[1] < 0

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
        cont_neighs = [ cell.neighbors() for cell in cont ]
        stats.log("calculated voro cell neighs")
        cont_neighs_faces = []
        for i,neighs in enumerate(cont_neighs):
            faces = [ n if n<0 else cont_neighs[n].index(i) for n in neighs ]
            cont_neighs_faces.append(faces)
        stats.log("calculated cell neighs faces")


        # IDEA:: dynamic lists or global one?
        self.in_air: list[Link] = []
        self.in_cells: list[Link] = []
        link_keySet = set()

        for idx_cell,cell in enumerate(cont):
            for idx_face, idx_neighCell in enumerate(cont_neighs[i]):

                # link to wall, wont be repeated
                if idx_neighCell < 0:
                    key = (idx_neighCell, idx_cell)
                    key_faces = (idx_neighCell, idx_face)
                    l = Link(key, key_faces)
                    self.in_air.append(l)
                    continue

                # check unique links between cells
                swap = idx_cell > idx_neighCell
                key = (idx_cell, idx_neighCell) if not swap else (idx_neighCell, idx_cell)
                key_rep = key in link_keySet
                if key_rep:
                    continue

                # build the link
                link_keySet.add(key)
                idx_neighFace = cont_neighs_faces[i][idx_face]
                key_faces = (idx_face, idx_neighFace) if not swap else (idx_neighFace, idx_face)

                l = Link(key, key_faces)
                self.in_cells.append(l)

        # now calculate neighs with blender mesh map
        stats.log("created link set")

        for link in self.in_air:
            c1, c2 = link.key_cells
            f1, f2 = link.key_faces

        #    me_maps = utils_geo.get_meshDicts(me, queries_default=True)
        #    FtoF = me_maps["FtoF"]

        logType = {"CALC"} if self.in_cells else {"CALC", "ERROR"}
        DEV.log_msg(f"Found {len(self.in_cells)} links in cells ({len(self.in_air)} in air walls)", logType)

