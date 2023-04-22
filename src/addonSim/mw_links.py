import bpy.types as types

from . import utils
from . import utils_geo
from .utils_dev import DEV

from mathutils import Vector, Matrix

# Using tess voro++ adaptor
from tess import Container, Cell


# -------------------------------------------------------------------

# OPT:: could use a class or an array of props? pyhton already slow so ok class?
class Link():

    def __init__(self, idx_pair: tuple[int, int], mesh: types.Mesh, idx_face: int):
        self.life = 1.0
        self.air = idx_pair[0] < 0 or idx_pair[1] < 0

        # no directionality
        self.idx_pair = idx_pair

        # WIP:: blender map...
        self.mesh = mesh
        self.idx_face = idx_face

        # neighs populated afterwards
        self.neighs = []

# -------------------------------------------------------------------

class Links():

    def __init__(self, cont: Container, obj_shards: types.Object):
        # WIP:: copy instead of ref?
        self.cont = cont
        self.obj_shards = obj_shards
        meshes = [ shard.data for shard in obj_shards.children ]

        # IDEA:: dynamic lists or global one?
        self.in_air = []
        self.in_cells = []
        link_keySet = set()

        for cell_me in zip(cont, meshes):
            cell: Cell = cell_me[0]
            me: types.Mesh = cell_me[1]

            # iterate the cell neighbours -> the mesh face idx matches by generation
            neighs = cell.neighbors()
            for idx_face, idx_neigh in enumerate(neighs):
                f = me.polygons[idx_face]

                # link to wall, wont be repeated
                if idx_neigh < 0:
                    key = (idx_neigh, cell.id)
                    l = Link(key, idx_face, f.center, f.normal)
                    self.in_air.append(l)
                    continue

                # check unique links between cells
                key = tuple( sorted([cell.id, idx_neigh]) )
                key_rep = key in link_keySet
                if key_rep:
                    continue

                # build new link
                link_keySet.add(key)
                l = Link(key, idx_face, f.center, f.normal)
                self.in_cells.append(l)

        # calculate neighs with blender mesh map


            # XXX:: decouple scene from sim? calculate the FtoF map inside voro isntead of blender mesh...
            me_maps = utils_geo.get_meshDicts(me, queries_default=True)
            FtoF = me_maps["FtoF"]


        logType = {"CALC"} if self.in_cells else {"CALC", "ERROR"}
        DEV.log_msg(f"Found {len(self.in_cells)} links in cells ({len(self.in_air)} in air walls)", logType)

