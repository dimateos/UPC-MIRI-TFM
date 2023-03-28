# SPDX-License-Identifier: GPL-2.0-or-later
# Script copyright (C) Blender Foundation 2012

# TODO: could add time limit, or at least some loggin of the progress
# NOTE: the "Show progress realtime" computes ALL cells and THEN slowly shows them before applying the boolean op


def points_as_bmesh_cells(
        verts,
        points,
        points_scale=None,
        margin_bounds=0.05,
        margin_cell=0.0,
):
    """
    verts: all vertices of the mesh (recieved in global space).
    points: selected points to use for fractures, usually limited amount: own/child vertices, own/child particles...
    """
    from math import sqrt
    import mathutils
    from mathutils import Vector
    INF_LARGE = 10000000000.0  # a big value!

    # OUTPUT: consists of a list of shards tuples (center point used, [convex hull vertices])
    cells = []

    # BUG: check distance limit implementation
    distance_max_listP = []


    # local iteration variables: the points will be sorted by distance each time!
    # NOTE: maybe could use some hierarchy accelerator suck as a k-d tree library
    points_sorted_current = [p for p in points]
    plane_indices = []
    vertices = []

    # points_scale affect the scale of the shards
    if points_scale is not None:
        points_scale = tuple(points_scale)
    if points_scale == (1.0, 1.0, 1.0):
        points_scale = None

    # BB of the mesh for the outer wall planes, could use convex hull for better precission
    # NOTE: afterwards a boolean operator is required to limit the wall planes to the actual geometry
    # BB is fastest but some shards may not end properly inside the boolean region causing them to be left unclipped!
    # NOTE: maybe there is better way to get BB using some blender function
    if 1:
        xa = [v[0] for v in verts]
        ya = [v[1] for v in verts]
        za = [v[2] for v in verts]

        xmin, xmax = min(xa) - margin_bounds, max(xa) + margin_bounds
        ymin, ymax = min(ya) - margin_bounds, max(ya) + margin_bounds
        zmin, zmax = min(za) - margin_bounds, max(za) + margin_bounds
        convexPlanes = [
            Vector((+1.0, 0.0, 0.0, -xmax)),
            Vector((-1.0, 0.0, 0.0, +xmin)),
            Vector((0.0, +1.0, 0.0, -ymax)),
            Vector((0.0, -1.0, 0.0, +ymin)),
            Vector((0.0, 0.0, +1.0, -zmax)),
            Vector((0.0, 0.0, -1.0, +zmin)),
        ]
        convexVertices = [
            Vector((xmin, ymin, zmin)), # all combinations to get 8 vertices (000 to 111)
            Vector((xmin, ymin, zmax)),
            Vector((xmin, ymax, zmin)),
            Vector((xmin, ymax, zmax)),
            Vector((xmax, ymin, ymin)),
            Vector((xmax, ymin, zmax)),
            Vector((xmax, ymax, ymin)),
            Vector((xmax, ymax, zmax)),
        ]
        convexVertices_test, plane_indices_test = mathutils.geometry.points_in_planes(convexPlanes)


    # iterate all points and try to yield a cell per each of them (it could be discarded)
    # NOTE: cells are built individually by adding planes between the closest points,
    #       then the algorithm stops when the influence is deemed not strong enough anymore
    for i, point_cell_current in enumerate(points):
        planes = [None] * len(convexPlanes)

        # add the projection length on to each axis to the bounding box planes
        # WIP: this moves the BB to be centered around the point? why do so if later the boolean operator clips it?
        for j in range(len(convexPlanes)):
            planes[j] = convexPlanes[j].copy()
            planes[j][3] += planes[j].xyz.dot(point_cell_current)

        # radius test over the outter wall
        # NOTE: should never happen if the points come from the original mesh
        # radius_max = max( [  ] )
        distance_max = INF_LARGE
        distance_max_listP.append([])

        # sort points by distance to the current point
        # WIP: take into account the radius test already here?
        points_sorted_current.sort(key=lambda p: (p - point_cell_current).length_squared)


        # add planes for each near point to limit the walls of the cell constructing a convex cell with the calculated planes
        for j in range(1, len(points)):
            normal = points_sorted_current[j] - point_cell_current
            nlength = normal.length

            # apply shard scaling
            if points_scale is not None:
                normal_alt = normal.copy()
                normal_alt.x *= points_scale[0]
                normal_alt.y *= points_scale[1]
                normal_alt.z *= points_scale[2]

                # rotate plane to new distance
                scalar = normal_alt.normalized().dot(normal.normalized())
                # assert(scalar >= 0.0) should always be positive, could abs incase
                nlength *= scalar
                normal = normal_alt

            # STOP: createria based on max distance: following points are supposed to have no effect on the cell hull
            if nlength > distance_max:
                break


            # put an additional plane in the middle of the closest points
            plane = normal.normalized()
            plane.resize_4d()
            plane[3] = (-nlength / 2.0) + margin_cell
            planes.append(plane)

            # try obtain vertices of the boundary of the convex defined by all planes
            # NOTE: probably always succeeds when the random fracture points come from the mesh vertices
            # WIP: breaking due to this is correct?
            vertices[:], plane_indices[:] = mathutils.geometry.points_in_planes(planes)
            if len(vertices) == 0:
                break

            # copy the currenlty planes for the following iterations
            # NOTE: here we should use some hash/id and relate planes and particles to later retrieve neighboring info
            if len(plane_indices) != len(planes):
                planes[:] = [planes[k] for k in plane_indices]


            # readjust the max distance
            # WIP: but seems like never does with the big value reset!
            distance_max = INF_LARGE
            for v in vertices:
                # cmp length_squared and delay converting to a real length
                distance = v.length_squared
                if distance_max < distance:
                    distance_max = distance

            distance_max = sqrt(distance_max) # make real length
            distance_max *= 2.0               # from mid point to vertex
            distance_max_listP[i].append(distance_max)


        # not even the closes point had vertices
        if len(vertices) == 0:
            continue

        # append the calculated cell to the output
        cells.append((point_cell_current, vertices[:]))
        del vertices[:]


    # WIP check if the radius test is actually purging particles
    mins = [min(l) for l in distance_max_listP]
    maxs = [max(l) for l in distance_max_listP]
    print("distance_max_list min max:", min(mins), max(maxs))
    return cells
