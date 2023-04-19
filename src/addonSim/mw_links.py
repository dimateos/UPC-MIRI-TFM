from . import utils
from .utils_dev import DEV

from mathutils import Vector, Matrix

# Using tess voro++ adaptor
from tess import Container, Cell
from typing import List


# -------------------------------------------------------------------

class Link():
    pass


# -------------------------------------------------------------------

# TODO: class that collects the links as in container?
class Links(list[Link]):

    def __init__(self, cont: Container):
        # TODO: reps?
        neigh_set = set()

        for cell in cont:
            cell_centroid_4d = Vector(cell.centroid()).to_4d()

            # iterate the cell neighbours
            neigh = cell.neighbors()
            for n_id in neigh:
                # wall link
                if n_id < 0:
                    #name= f"s{cell.id}_w{-n_id}"
                    #obj_link = utils.gen_child(obj_group, name, context, None, keepTrans=False, hide=not cfg.struct_showLinks_walls)
                    continue

                # neighbour link
                else:
                    # check repetition
                    key = tuple( sorted([cell.id, n_id]) )
                    key_rep = key in neigh_set
                    if not key_rep: neigh_set.add(key)

                    # custom ordered name
                    #name= f"s{cell.id}_n{n_id}"
                    # Create new curve per neighbour

                    # Add the centroid points using a poly line
                    #neigh_centroid_4d = Vector(cont[n_id].centroid()).to_4d()

        # store produced cells as a self.list
        cells: List[Cell] = self._container.get_cells()
        list.__init__(self, cells)

        # notify when no cells are produced
        if len(self) == 0:
            print(f"Empty container, no voronoi cell was generated! Maybe all points ended OUT/ON the walls?")

        #logType = {"CALC"} if cont else {"CALC", "ERROR"}
        #DEV.log_msg(f"Found {len(cont)} cells ({len(faces4D)} faces)", logType)
        #return cont
