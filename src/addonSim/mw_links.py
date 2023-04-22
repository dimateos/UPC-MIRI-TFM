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

    def __init__(self, idx_pair: tuple[int, int], center: Vector, direction: Vector):
        self.life = 1.0

        # no directionality
        self.idx_pair = idx_pair
        self.center = center
        self.direction = direction

        # WIP:: ref to object/mesh or collection to acess others?


# -------------------------------------------------------------------

class Links():

    def __init__(self, cont: Container, obj_shards: types.Object):
        # WIP:: copy instead of ref?
        self.cont = cont
        self.obj_shards = obj_shards
        meshes = [ shard.data for shard in obj_shards.children ]

        # WIP:: store more info: e.g. maps from each wall to cells, links from cell, etc
        self.in_air = []
        self.in_cells = []
        neigh_set = set()

        # XXX:: decouple scene from sim? but using cells mesh for mapping...


        for cell,me in zip(cont, meshes):
            # OPT:: annotate for intellisense, affects perf?
            assert(isinstance(cell, Cell))
            assert(isinstance(me, types.Mesh))

            # XXX:: dictionaries and that faces match
            me_maps = utils_geo.get_meshDicts(me, queries_default=True)

            # iterate the cell neighbours -> the mesh face idx matches by generation
            neighs = cell.neighbors()
            for idx_face, idx_neigh in enumerate(neighs):

                # TODO:: wall neigh links
                if idx_neigh < 0:
                    self.in_air.append( ( cell.id, idx_neigh ))
                    #name= f"s{cell.id}_w{-n_id}"
                    #obj_link = utils.gen_child(obj_group, name, context, None, keepTrans=False, hide=not cfg.struct_showLinks_walls)
                    continue

                # WIP:: check repetition
                key = tuple( sorted([cell.id, idx_neigh]) )
                key_rep = key in neigh_set
                if key_rep:
                    continue

                # build new link
                neigh_set.add(key)
                cell_neigh = cont[idx_neigh]
                face = me.polygons[idx_face]

                self.in_cells.append(key)


        logType = {"CALC"} if self.in_cells else {"CALC", "ERROR"}
        DEV.log_msg(f"Found {len(self.in_cells)} links in cells ({len(self.in_air)} in air walls)", logType)

