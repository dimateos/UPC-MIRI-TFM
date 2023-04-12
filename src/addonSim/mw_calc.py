from .properties import (
    MW_gen_cfg,
)

from mathutils import Vector
INF_FLOAT = float("inf")

# Using tess voro++ adaptor
from tess import Container, Cell

from . import utils
from .ui import DEV_log


# -------------------------------------------------------------------

def cont_fromPoints(
        points: list[Vector],
        bb_world: list[Vector, 6],
        cfg: MW_gen_cfg
) -> Container:

    # Calculate the 4D vectors representing the face planes
    face_normals = [mw_normal @ f.normal for f in mesh.polygons]
    # displace the center a bit by margin bounds
    face_centers = [mw @ (f.center + f.normal * cfg.margin_bounds) for f in mesh.polygons]
    walls = [
            Vector( list(n) + [fc.dot(n)] )
        for (fc,n) in zip(face_centers, face_normals)
    ]

    bb_tuples = [ p.to_tuple() for p in bb_world ]

    # Build the container and cells
    cont = Container(points=points, limits=bb_tuples, walls=walls)


    # OUTPUT: consists of a list of shards tuples (center point used, [convex hull vertices])
    # NOTE the vertices must use mathutils.Vectors and in LOCAL coordinates around the original position
    cells = [
        (
            Vector(cell.pos),
            [ Vector(v) for v in cell.vertices_local() ]
        )
        for cell in cont
    ]

    DEV_log("Found %d cells" % len(cont), {"CALC"})
    return cont

