import bpy.types as types

from . import utils
from .utils_dev import DEV

from mathutils import Vector, Matrix

# Using tess voro++ adaptor
from tess import Container, Cell


# -------------------------------------------------------------------

# TODO: could use a class or an array of props? pyhton already slow so ok class?
class Link():

    def __init__(self, idx_pair: tuple[int, int], center: Vector, direction: Vector):
        self.life = 1.0

        # TODO: no directionality, etc?
        self.life = idx_pair
        self.center = center
        self.direction = direction

        # TODO: ref to object/mesh or collection to acess others?

    # TODO: external generator reading props better to avoid innecesary bpy deps
    #def genMesh / object

# -------------------------------------------------------------------

# TODO: class that collects the links as in container? maybe not cause air vs cell links
class Links():

    def __init__(self, cont: Container, obj_shards: types.Object):
        # TODO: copies at least mesh or something?
        self.cont = cont
        self.obj_shards = obj_shards
        meshes = [ shard.data for shard in obj_shards.children ]

        # TODO: store more info: e.g. maps from each wall to cells, links from cell, etc
        self.from_walls = []
        self.from_cells = []

        # TODO: something with reps? store info?
        neigh_set = set()

        for cell,me in zip(cont, meshes):
            assert(isinstance(cell, Cell))
            assert(isinstance(me, types.Mesh))

            # iterate the cell neighbours -> the mesh face idx matches by generation
            neighs = cell.neighbors()
            for idx in neighs:

                # TODO: wall neigh
                if idx < 0:
                    self.from_walls.append(idx)
                    #name= f"s{cell.id}_w{-n_id}"
                    #obj_link = utils.gen_child(obj_group, name, context, None, keepTrans=False, hide=not cfg.struct_showLinks_walls)
                    continue

                # TODO: check repetition
                key = tuple( sorted([cell.id, idx]) )
                key_rep = key in neigh_set
                if key_rep:
                    continue

                # build new link
                neigh_set.add(key)
                face = me.polygons[idx]
                cell_neigh = cont[idx]

                self.from_cells.append(key)


        logType = {"CALC"} if self.from_cells else {"CALC", "ERROR"}
        DEV.log_msg(f"Found {len(self.from_cells)} links from cells ({len(self.from_walls)} from walls)", logType)
        return cont

