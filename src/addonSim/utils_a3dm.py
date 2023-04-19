# MIRI-A3DM
# Diego Mateos (UPC)
""" Different blender mesh queries """


### IMPORTS
import mathutils
from unionfind import UnionFind

### UTILS
def r(a):
    return int(a*1000+0.5)/1000.0

def centroid(vertices_id, vertices):
    """ Calculate average of 3D vectors given list of indices and container """
    c = mathutils.Vector((0.0, 0.0, 0.0))
    for v in vertices_id: c += vertices[v]
    c /= len(vertices_id)
    return c

## Mappings
def map_EtoF(me):
    """ Returns the dictionary from Edge to Faces"""
    # build the dictionary from edge "key" to edge id
    edgeKey_edge = dict()
    for i,e in enumerate(me.edges):
        edgeKey_edge[str(e.key)] = i

    # build edge to face relation using a list of sets (to remove repetitions)
    edge_faces = [set() for v in me.edges]
    for face in me.polygons:
        for e_key in face.edge_keys:
            # use pair as the string key to retieve index
            e_index = edgeKey_edge[str(e_key)]
            # store based on index instead of key
            edge_faces[e_index].add(face.index)

    return edge_faces

def map_VtoF_EtoF_VtoE(me):
    """ Returns multiple mappings of the mesh (that complement blenders) """
    # build vertex to face relation using a list of sets (to remove repetitions)
    vertex_faces = [set() for v in me.vertices]

    # build the dictionary from edge "key" to edge id
    edgeKey_edge = dict()
    for i,e in enumerate(me.edges): edgeKey_edge[str(e.key)] = i
    # build edge to face relation using a list of sets (to remove repetitions)
    edge_faces = [set() for v in me.edges]

    for face in me.polygons:
        for v in face.vertices:
            vertex_faces[v].add(face.index)

        for e_key in face.edge_keys:
            # use pair as the string key to retieve index
            e_index = edgeKey_edge[str(e_key)]
            # store based on index instead of key
            edge_faces[e_index].add(face.index)

    # build the dictionary from vertex to edge too
    vertex_edges = [set() for v in me.vertices]
    for e in me.edges:
        for v in e.vertices:
            vertex_edges[v].add(e.index)

    return vertex_faces, edge_faces, vertex_edges

### EXERCISES
# some improvements afterwards

## EXERCISE 1
def centroid_mesh(me, log=True):
    c = mathutils.Vector((0.0, 0.0, 0.0))
    for v in me.vertices:
        c += v.co
    c /= len(me.vertices)
    if log: print(f" centroid= {c}")
    return c

## EXERCISE 3
def valences_mesh(me, log=True):
    # Number of edges conected to the vertices
    valences = [ 0 for v in me.vertices ]

    # iterate non edges (non repeated pairs)
    for e in me.edges:
        # print(f" --edge= {e.vertices[:]}")
        valences[e.vertices[0]] += 1
        valences[e.vertices[1]] += 1

    val_min = min(valences)
    val_max = max(valences)
    val_sum = sum(valences) # acumulate avg

    if log:
        print(f" val_min= {val_min}")
        print(f" val_max= {val_max}")
        print(f" val_avg= {r(val_sum / len(valences))}")
    return val_min, val_max, val_sum / len(valences)

## EXERCISE 4
def manifold_types_mesh(me, log=True):
    # build edge to face relation using a dict of sets
    edge_faces = map_EtoF(me)

    # clasify the vertices based on amount of faces
    num_boundary = 0
    num_manifold = 0
    num_nomanifold = 0
    for faces in edge_faces:
        if len(faces) == 1: num_boundary+=1
        elif len(faces) == 2: num_manifold+=1
        else: num_nomanifold+=1

    if log:
        print(f" num_boundary= {num_boundary}")
        print(f" num_manifold= {num_manifold}")
        print(f" num_nomanifold= {num_nomanifold}")
    return num_boundary, num_manifold, num_nomanifold

## EXERCISE 6
def shells_mesh(me, log=True):
    # build union-find object and join using all edges
    vertex_union = UnionFind(len(me.vertices))
    for e in me.edges:
        # print(f" ---edge= {e.vertices[:]}")
        vertex_union.union(e.vertices[0], e.vertices[1])

    # retrieve the shells as the connected components
    if log: print(f" num_shells= {vertex_union.num_components}")
    return vertex_union.num_components

def get_vertex_shells(me):
    # build union-find object and join all edges
    uf = UnionFind(len(me.vertices))
    for e in me.edges:
        # print(f" ---edge= {e.vertices[:]}")
        uf.union(e.vertices[0], e.vertices[1])

    return uf.retrieve_compoents()

def get_face_shells_manifold(vertex_shells, VtoF, EtoF, VtoE):
    """ Returns a list of lists containing the faces (index) for each separate shell """
    # use the dicts to get the face_shells (list of lists of faces per shell)
    # at the same time check that all the edges related are 2-manifold
    face_shells = list()
    for i,vertices in enumerate(vertex_shells):
        faces = set()
        manifold = True

        # iterate all vertices of each shell
        for v in vertices:
            # get the mapped faces and edges
            v_faces = VtoF[v]
            v_edges = VtoE[v]

            # use edges to check any non-manifold -> whole shell dropped
            for e in v_edges:
                e_faces = EtoF[e]
                # all edges must have 2 faces (1 would be boundary and more non-2-manifold)
                if len(e_faces) != 2:
                    print(f" skipped shell ({i}): non-2-manifold edge")
                    print(f"    edge [{e}]: faces {e_faces}")
                    manifold = False
                    break           # skip resto of edges
            if not manifold: break  # skip the rest of shell vertices too

            # update method of a set to add all the elements in the list
            faces.update(v_faces)
        if manifold: face_shells.append(faces)

    return face_shells

## EXERCISE 7
def genus_mesh(me, log=True):
    # based on Euler-Poincare equataion [F + V = E + R + 2(S-H)]
    # [H] is the number of holes, the genus of the object
    # Derived: [H = (-F - V + E + R)/2 + S]
    # In blender, faces do not include interior loops, so [R=0]
    # So we just have to calculate the number of shells [S]

    f = len(me.polygons)
    v = len(me.vertices)
    e = len(me.edges)

    # build union-find object and join using all edges
    vertex_union = UnionFind(len(me.vertices))
    for edge in me.edges:
        # print(f" ---edge= {e.vertices[:]}")
        vertex_union.union(edge.vertices[0], edge.vertices[1])

    # retrieve the shells as the connected components
    num_shells = vertex_union.num_components
    genus = (-f - v + e)/2 + num_shells

    if log:
        print(f" ...S= { num_shells }")
        print(f" genus= { int(genus) }")
    return int(genus)

## EXERCISE 8
def calc_area_mesh(me, log=True):
    # sum the area of all the polygons + compare with BLENDER
    sum_area = 0
    sum_area_BLENDER = 0

    for face in me.polygons:
        sum_area_BLENDER += face.area
        # print(f" **face(BLENDER)= {r(face.area)}")

        # calculate area of 3D polygon (trapezoid method w/ projections)
        Sx,Sy,Sz = 0,0,0
        for i in range(len(face.vertices)):
            v1 = me.vertices[face.vertices[i]]
            v2 = me.vertices[face.vertices[i+1 if i+1!=len(face.vertices) else 0]]
            # area must be divided by 2, but can be done outside the sum
            Sx += (v1.co[1]-v2.co[1]) * (v1.co[2]+v2.co[2])
            Sy += (v1.co[2]-v2.co[2]) * (v1.co[0]+v2.co[0])
            Sz += (v1.co[0]-v2.co[0]) * (v1.co[1]+v2.co[1])

        # area is the lenght of the vector S=(Sx,Sy,Sz)
        face_area = mathutils.Vector((Sx/2.0,Sy/2.0,Sz/2.0)).length
        sum_area += face_area
        # print(f" **face= {r(face_area)}")

    if log:
        print(f" area(BLENDER)= { r(sum_area_BLENDER) }")
        print(f" area= { r(sum_area) }")
    return sum_area

def polygon_area(me, face_index, log=True):
    """ Return the calculated area of a 3D blender polygon (trapezoid method w/ projections)  """
    face = me.polygons[face_index]

    # calculate area of 3D polygon (trapezoid method w/ projections)
    Sx, Sy, Sz = 0, 0, 0
    for i in range(len(face.vertices)):
        v1 = me.vertices[face.vertices[i]]
        v2 = me.vertices[face.vertices[i + 1 if i + 1 != len(face.vertices) else 0]]
        # area must be divided by 2, but can be done outside the sum
        Sx += (v1.co[1] - v2.co[1]) * (v1.co[2] + v2.co[2])
        Sy += (v1.co[2] - v2.co[2]) * (v1.co[0] + v2.co[0])
        Sz += (v1.co[0] - v2.co[0]) * (v1.co[1] + v2.co[1])

    # area is the lenght of the vector S=(Sx,Sy,Sz)
    face_area = mathutils.Vector((Sx / 2.0, Sy / 2.0, Sz / 2.0)).length
    if log:
        print(f" **face= {r(face_area)}")
        print(f" **face(BLENDER)= {r(face.area)}")
    return face_area

### EXERCISE 9 / 10
def calc_volume_centerMass(me, calc_centerMass=False, log=True):
    # retrieve shells of the mesh
    vertex_shells = get_vertex_shells(me)
    print(f" number of shells= { len(vertex_shells) }")

    # retrieve the relation dictionaries
    VtoF, EtoF, VtoE = map_VtoF_EtoF_VtoE(me)

    # ignore non-2-manifold shells
    face_shells_manifold = get_face_shells_manifold(vertex_shells, VtoF, EtoF, VtoE)

    # compute volume and center of mass per manifold shell
    sum_vol = 0
    sum_G = mathutils.Vector((0.0, 0.0, 0.0))
    for i,shell in enumerate(face_shells_manifold):
        for f_index in shell:
            face = me.polygons[f_index]

            # Compute the volume using surface integrals (divergence theorem)
            # [vol = (Surface integral) surface_point_y · surface_n_y * surface_area]
            # Average volume projected to all axis to improve results
            # [vol = 1/3 * (Surface integral) surface_point · surface_n * surface_area]

            face_area = polygon_area(me, f_index, log=False)
            face_vertex = me.vertices[face.vertices[0]].co

            # calculate normal as cross product of vertices instead of using blenders
            # face_normal = face.normal
            v1 = me.vertices[face.vertices[1]].co - face_vertex
            v2 = me.vertices[face.vertices[2]].co - face_vertex
            face_normal = v1.cross(v2).normalized()

            # 1/3 division applied outside the integral (all shells actually)
            sum_vol += face_vertex.dot(face_normal) * face_area

            if not calc_centerMass: continue
            # Compute the center of mass with surface integrals too
            # must be divided by [2*vol], so will do it at the end
            sum_G.x += face_vertex.x**2 * face_normal.x * face_area
            sum_G.y += face_vertex.y**2 * face_normal.y * face_area
            sum_G.z += face_vertex.z**2 * face_normal.z * face_area

        print(f" ...sum_vol= {r(sum_vol / 3.0)} (shell [{i}] partial)")

    # At the end volume might be negative if the face normals were reversed
    # ex: hollow icosa were the outer shell is deleted, now counts as an outer shell
    sum_vol = abs(sum_vol / 3.0)

    # check no volume (no 2-manifold without boundaries)
    if sum_vol > 0.0001: sum_G = sum_G / (2 * sum_vol)
    elif log: print(" *object has no volume (no interior defined)...")

    if log:
        print(f" sum_vol= {r(sum_vol)}")
        if calc_centerMass: print(f" center_mass= {sum_G}")

    return sum_vol, sum_G if calc_centerMass else sum_vol

    return sum_vol, sum_G