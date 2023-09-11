import bpy
import bpy.types as types
from mathutils import Vector, Matrix
from math import pi as PI, cos, sin, radians

from . import utils_trans


#-------------------------------------------------------------------

class SHAPES:
    octa_verts = [
        Vector((0, 0, 1)),
        Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0)), Vector((0, -1, 0)),
        Vector((0, 0, -1)),
    ]
    octa_faces = [
        [0,1,2], [0,2,3], [0,3,4], [0,4,1],
        [5,2,1], [5,3,2], [5,4,3], [5,1,4],
    ]
    @staticmethod
    def get_octahedron(meshName:str = "octa") ->types.Mesh:
        me = bpy.data.meshes.new(meshName)
        me.from_pydata(vertices=SHAPES.octa_verts, edges=[], faces=SHAPES.octa_faces)
        return me

    tetra_verts = octa_verts[:-1]
    tetra_faces = octa_faces[:4]+[[4,3,2,1]]
    @staticmethod
    def get_tetrahedron(meshName:str = "tetra") ->types.Mesh:
        me = bpy.data.meshes.new(meshName)
        me.from_pydata(vertices=SHAPES.tetra_verts, edges=[], faces=SHAPES.tetra_faces)
        return me

    cuboid_verts = [
        Vector((1, 0, 1)), Vector((0, 1, 1)), Vector((-1, 0, 1)), Vector((0, -1, 1)),
        Vector((1, 0, -1)), Vector((0, 1, -1)), Vector((-1, 0, -1)), Vector((0, -1, -1)),
    ]
    cuboid_faces = [
        [0,1,2,3], [7,6,5,4],
        [4,5,1,0], [5,6,2,1], [6,7,3,2], [7,4,0,3],
    ]
    @staticmethod
    def get_cuboid(meshName:str = "cuboid") ->types.Mesh:
        me = bpy.data.meshes.new(meshName)
        me.from_pydata(vertices=SHAPES.cuboid_verts, edges=[], faces=SHAPES.cuboid_faces)
        return me

#-------------------------------------------------------------------

def set_smoothShading(me: types.Mesh, active=True, faces_idx = None):
    """ set smooth shading for specified faces or for all when none provided """
    if faces_idx:
        for f in faces_idx:
            me.polygons[f].use_smooth = active
    else:
        for f in me.polygons:
            f.use_smooth = active

def getEmpty_curveData(name ="poly-curve", w=0.05, resFaces=0):
    """ creates an empty blender poly-curve """
    # Create new POLY curve
    curve_data = bpy.data.curves.new(name, 'CURVE')
    curve_data.dimensions = '3D'
    line = curve_data.splines.new('POLY')

    # Set the visuals
    curve_data.bevel_depth = w
    curve_data.bevel_resolution = resFaces
    curve_data.fill_mode = "FULL" #'FULL', 'HALF', 'FRONT', 'BACK'
    return curve_data

def get_curveData(points: list[Vector], name ="poly-curve", w=0.05, resFaces=0):
    """ creates a blender poly-curve following the points """
    curve_data = getEmpty_curveData(name, w, resFaces)
    line = curve_data.splines[0]

    # Add the points to the spline
    for i,p in enumerate(points):
        if i!=0: line.points.add(1)
        line.points[i].co = p.to_4d()

    return curve_data

def get_resFaces_fromCurveRes(curveRes):
    """ return the number sample points (or side faces) the curve profile will have
        # NOTE:: most mesh attrs use CORNERS, so multiply by 2 to get triangles in each quad
    """
    return 4 + curveRes*2

#-------------------------------------------------------------------

def get_ringVerts(v:Vector, radii:float, resFaces:float, step:float, vertsOut:list[Vector], axisU = Vector((1,0,0)), axisV=Vector((0,1,0))):
    for i in range(resFaces):
        sample = v + radii * (cos(i * step) * axisU + sin(i * step) * axisV)
        vertsOut.append(sample)

def get_ringVerts_interleaved(vList:list[Vector], radii:float, resFaces:float, step:float, vertsOut:list[Vector], axisU = Vector((1,0,0)), axisV=Vector((0,1,0))):
    for i in range(resFaces):
        for v in vList:
            sample = v + radii * (cos(i * step) * axisU + sin(i * step) * axisV)
            vertsOut.append(sample)

#attributesData:dict[str,dict] = None,
def get_tubeMesh_pairsQuad(src_verts_pairs:list[tuple[Vector]], src_scale:list[float] = None, name ="tube-mesh", radii=0.05, resFaces=4, smoothShade = True):
    """ direction aligned simplified version: only single pairs and quad faces"""
    assert (resFaces >= 2)
    res_step = PI * 2 / resFaces
    verts, faces = [], []

    # directly work on each face
    for vid, vPair in enumerate(src_verts_pairs):
        normal = vPair[1] - vPair[0]
        #if utils_trans.almostNull(normal): continue

        u,v = utils_trans.getPerpendicularBase_stable(normal)
        r = radii*src_scale[vid] if src_scale else radii
        get_ringVerts_interleaved(vPair, r, resFaces, res_step, verts, u,v)

        # generate faces quads -> ccw so normals towards outside
        vs_id_base = vid*resFaces*2
        for i in range(0, resFaces-1):
            vs_id = vs_id_base + i *2
            faces.append((vs_id, vs_id+2, vs_id+3, vs_id+1))

        # add connection from first to last too
        vs_id = vs_id_base + resFaces*2 -2
        faces.append((vs_id, vs_id_base, vs_id_base+1, vs_id+1))

    me = bpy.data.meshes.new(name)
    me.from_pydata(vertices=verts, edges=[], faces=faces)

    # apply smooth shading
    if smoothShade: set_smoothShading(me)
    return me

def get_tubeMesh_AAtriFan(src_verts:list[Vector], src_edges:list[tuple[int]], src_scale:list[float] = None, name ="tube-mesh", radii=0.05, resFaces=4, smoothShade = True):
    """ extrudes AA sampled circle points around the vertices using a triangle fan"""
    assert (resFaces >= 2)
    res_step = PI * 2 / resFaces
    verts, faces = [], []

    # generate the new vertices (axis aligned sampled circle)
    for v_id in range(len(src_verts)):
        v = src_verts[v_id]
        r = radii*src_scale[v_id] if src_scale else radii
        get_ringVerts(v, r, resFaces, res_step, verts)

    # generate faces triangle stripes joining verts from the edges -> ccw so normals towards outside
    for v1_id, v2_id in src_edges:
        for i in range(1, resFaces):
            vs_id = v2_id * resFaces + i
            vs_id_prev = v1_id * resFaces + i
            # print(f"vs_id: {vs_id} - vsp_id: {vsp_id}")
            faces.append((vs_id - 1, vs_id_prev - 1, vs_id))
            faces.append((vs_id_prev - 1, vs_id_prev, vs_id))

        # add connection from first to last too
        vs_id = v2_id * resFaces
        vs_id_prev = v1_id * resFaces
        faces.append((vs_id +resFaces- 1, vs_id_prev +resFaces - 1, vs_id))
        faces.append((vs_id_prev +resFaces- 1, vs_id_prev, vs_id))

    me = bpy.data.meshes.new(name)
    me.from_pydata(vertices=verts, edges=[], faces=faces)

    # apply smooth shading
    if smoothShade: set_smoothShading(me)
    return me