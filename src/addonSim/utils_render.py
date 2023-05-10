import bpy
import bpy.types as types
from mathutils import Vector, Matrix
from random import uniform

from . import utils

#-------------------------------------------------------------------

class COLORS:
    """ Common colors and generators """
    red   = Vector([1.0, 0.0, 0.0])
    green = Vector([0.0, 1.0, 0.0])
    blue  = Vector([0.0, 0.0, 1.0])
    list_rgb = [red, green, blue]

    yellow  = (red+green) * 0.5
    orange  = (red+yellow) * 0.5
    pink    = (red+blue) * 0.5
    aqua    = (green+blue) * 0.5
    list_fade = [red, orange, yellow, green, aqua, blue, pink]

    black   = Vector([0.0, 0.0, 0.0])
    white   = Vector([1.0, 1.0, 1.0])
    gray   = white * 0.5
    list_gray = [black, gray, white]

    default_name = "colorMat"
    default_precision = 1
    def rounded(c: Vector, precision=default_precision, alphaToo = False):
        cc = Vector()
        cc.x = round(c.x, precision)
        cc.y = round(c.y, precision)
        cc.z = round(c.z, precision)
        if len(c) > 3: cc.w = round(c.w, precision) if alphaToo else c.w
        return cc

    def assure_4d_alpha(c: Vector, a=1.0):
        if len(c) > 3: return c
        c = c.to_4d()
        c.w = a
        return c

    def get_random(minC=0.0, maxC=1.0, alpha=0.0) -> Vector:
        c = Vector( [uniform(minC,maxC), uniform(minC,maxC), uniform(minC,maxC)] )
        if alpha: c = COLORS.toColor4D(c, alpha)
        return c

    def get_ramp(start = 0.1, stop = 0.9, step = 0.2, alpha=0.0) -> list[Vector]:
        startV = Vector( [start]*3 )
        stepV = Vector( [step]*3 )

        colors: list[Vector] = []
        for x in range(int((stop - start) / step) + 1):
            for y in range(int((stop - start) / step) + 1):
                for z in range(int((stop - start) / step) + 1):
                    c = startV + Vector( [x,y,z] ) *stepV
                    if alpha: c = COLORS.toColor4D(c, alpha)
                    colors.append(c)
        return colors

def get_colorMat(color3=COLORS.red, alpha=1.0, matName: str=None):
    if not matName: matName = COLORS.default_name
    mat = bpy.data.materials.new(matName)
    mat.use_nodes = False

    color3 = COLORS.rounded(color3)
    mat.diffuse_color[0] = color3[0]
    mat.diffuse_color[1] = color3[1]
    mat.diffuse_color[2] = color3[2]
    mat.diffuse_color[3] = alpha
    return mat

def get_randomMat(minC=0.0, maxC=1.0, alpha=1.0, matName: str=None):
    # OPT:: could do a single mat that shows a random color per object ID using a ramp
    if not matName: matName = "randomMat"
    color = COLORS.randomColor(minC, maxC)
    mat = get_colorMat(color, alpha, matName)
    return mat

#-------------------------------------------------------------------

class ATTRS:
    """ Common mesh attributes """
    attrs_atype = [ 'FLOAT', 'FLOAT_COLOR', 'FLOAT2', 'FLOAT_VECTOR', 'BYTE_COLOR', 'BOOLEAN', 'INT', 'INT8', 'STRING' ]
    attrs_adomain = [ 'POINT', 'CORNER', 'EDGE', 'FACE', 'CURVE' ] # INSTANCE too
    attrsColor_atype = [ "FLOAT_COLOR", "BYTE_COLOR" ]
    attrsColor_adomain = [ "POINT", "CORNER" ]

    def get_src_inDomain(mesh: types.Mesh, adomain:str):
        """ Map the str to the mesh data """
        if adomain == "POINT": return mesh.vertices
        elif adomain == "EDGE": return mesh.edges
        elif adomain == "FACE": return mesh.polygons
        elif adomain == "CORNER": return mesh.loops
        return []

    def get_value_inType(atype:str, v):
        """ Get a value of the type aprox """
        if   atype == "FLOAT"       : val= v
        elif atype == "FLOAT_COLOR" : val= Vector((v,v,v, 1.0))
        elif atype == "FLOAT2"      : val= Vector((v,v))
        elif atype == "FLOAT_VECTOR": val= Vector((v,v,v))
        elif atype == "BYTE_COLOR"  : val= Vector((v,v,v, 1.0)) * 256
        elif atype == "BOOL"        : val= bool(v)
        elif atype == "INT"         : val= round(v)
        elif atype == "INT8"        : val= round(v * 256)
        elif atype == "STRING"      : val= str(v)
        else                        : raise TypeError(f"{atype} not in {ATTRS.attrs_atype}")
        return val

    def get_rnd_inType(atype:str, minC = 0.0, maxC = 1.0):
        """ Get a random value of the type aprox """
        if   atype == "FLOAT"       : rnd= uniform(minC, maxC)
        elif atype == "FLOAT_COLOR" : rnd= COLORS.get_random(minC, maxC, 1.0)
        elif atype == "FLOAT2"      : rnd= Vector((uniform(minC, maxC), uniform(minC, maxC)))
        elif atype == "FLOAT_VECTOR": rnd= COLORS.get_random(minC, maxC)
        elif atype == "BYTE_COLOR"  : rnd= COLORS.get_random(minC, maxC, 1.0) * 256
        elif atype == "BOOL"        : rnd= round(uniform(minC,maxC))
        elif atype == "INT"         : rnd= round(minC + uniform(0,1) * maxC)
        elif atype == "INT8"        : rnd= round(uniform(0,1) * 256)
        elif atype == "STRING"      : rnd= utils.rnd_string(maxC-minC)
        else                        : raise TypeError(f"{atype} not in {ATTRS.attrs_atype}")
        return rnd

    def get_periodic_inType(atype:str, minC = 0.0, maxC = 1.0, period_id:int = None, period = 2):
        """ Get periodic value in the type (building a ramp from 0-1 in period)"""
        step = int((period_id % period) / period) + 1
        stepVal = minC + step * maxC
        val = ATTRS.get_value_inType(atype, stepVal)
        return val

    rndRep_vals = { atype: list() for atype in attrs_atype }
    rndRep_count = { atype: 0 for atype in attrs_atype }
    def get_rnd_periodic_inType(atype:str, minC = 0.0, maxC = 1.0, period = 2):
        """ Get a random value of the type with certain periodicity (limit rnd values) """
        if len(ATTRS.rndRep_vals[atype]) < period:
            ATTRS.rndRep_vals[atype].append(ATTRS.get_rnd_inType(atype, minC, maxC))

        vid = ATTRS.rndRep_count[atype] % period
        rndRep = ATTRS.rndRep_vals[atype][vid]
        ATTRS.rndRep_count[atype] +=1
        return rndRep

    def get_deferred_inType(atype:str, minC = 0.0, maxC = 1.0, period_id:int = None, period = 2):
        """ Proxy function to pick the random method used in other functions"""
        return ATTRS.get_rnd_inType(atype, minC, maxC)
        #return ATTRS.get_periodic_inType(atype, minC, maxC, period_id, period)
        #return ATTRS.get_rnd_periodic_inType(atype, minC, maxC, period)

#-------------------------------------------------------------------

def get_colorMat(color3=COLORS.red, alpha=1.0, matName: str=None):
    if not matName: matName = COLORS.default_name
    mat = bpy.data.materials.new(matName)
    mat.use_nodes = False

    COLORS.roundColor(color3)
    mat.diffuse_color[0] = color3[0]
    mat.diffuse_color[1] = color3[1]
    mat.diffuse_color[2] = color3[2]
    mat.diffuse_color[3] = alpha
    return mat

def set_colorMat(obj: types.Object, color3=COLORS.red, alpha=1.0, matName: str=None):
    mat = get_colorMat(color3, alpha, matName)
    obj.active_material = mat
    return mat

def set_mat(obj: types.Object, mat: types.Material):
    obj.active_material = mat

#-------------------------------------------------------------------

def get_randomMat(minC=0.0, maxC=1.0, alpha=1.0, matName: str=None):
    """ Get a random colored mat """
    # OPT:: could do a single mat that shows a random color per object ID using a ramp
    if not matName: matName = "randomMat"
    color = COLORS.randomColor(minC, maxC)
    mat = get_colorMat(color, alpha, matName)
    return mat

def set_randomUV(mesh: types.Mesh, minC=0.0, maxC=1.0):
    """ Get a random UV layer """
    uv = mesh.uv_layers.new()
    for i, faceL in enumerate(mesh.loops):
        uv.data[i].uv = ATTRS.get_deferred_inType("FLOAT2", minC, maxC, i)
    return uv

def set_randomVC_legacy(mesh: types.Mesh, minC=0.0, maxC=1.0, alpha=1.0):
    """ Get a random vertex color legacy layer (must be per loop)"""
    vc = mesh.vertex_colors.new()
    for i, l in enumerate(mesh.loops):
        color = ATTRS.get_deferred_inType("FLOAT_COLOR", minC, maxC, i)
        color.w = alpha
        vc.data[i].color = color
    return vc

def set_randomVC(mesh: types.Mesh, minC=0.0, maxC=1.0, alpha=1.0, atype="FLOAT_COLOR", adomain="POINT"):
    """ Get a random vertex color using color attributes layer: per loop or vertex """
    assert(atype in ATTRS.attrsColor_atype)
    assert(adomain in ATTRS.attrsColor_adomain)
    colors = mesh.color_attributes.new(f"{atype}_{adomain}", atype, adomain)

    source = ATTRS.get_src_inDomain(mesh, adomain)
    for i, datum in enumerate(source):
        color = ATTRS.get_deferred_inType(atype, minC, maxC, i)
        color.w = alpha
        colors.data[i].color = color
    return colors

def set_randomAC(mesh: types.Mesh, minC=0.0, maxC=1.0, alpha=1.0, atype="FLOAT_COLOR", adomain="EDGE"):
    """ Get a random vertex color using custom attributes layer: per loop, face, edge, vertex, etc """
    assert(atype in ATTRS.attrsColor_atype)
    assert(adomain in ATTRS.attrs_adomain)
    acolors = mesh.attributes.new(f"{atype}_{adomain}", atype, adomain)

    source = ATTRS.get_src_inDomain(mesh, adomain)
    for i, datum in enumerate(source):
        color = ATTRS.get_deferred_inType(atype, minC, maxC, i)
        color.w = alpha
        acolors.data[i].color = color
    return acolors

def set_randomAttr(mesh: types.Mesh, minC=0.0, maxC=1.0, alpha=1.0, atype="FLOAT", adomain="EDGE"):
    """ Get a random attribute using custom attributes layer: per loop, face, edge, vertex, etc """
    assert(atype in ATTRS.attrs_atype)
    assert(adomain in ATTRS.attrs_adomain)
    attrs = mesh.attributes.new(f"{atype}_{adomain}", atype, adomain)

    source = ATTRS.get_src_inDomain(mesh, adomain)
    for i, datum in enumerate(source):
        val = ATTRS.get_deferred_inType(atype, minC, maxC, i)
        attrs.data[i].value = val
    return attrs

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

def get_curveData(points: list[Vector], name ="poly-curve", w=0.05, res=0):
    # Create new POLY curve
    curve_data = bpy.data.curves.new(name, 'CURVE')
    curve_data.dimensions = '3D'
    line = curve_data.splines.new('POLY')

    # Add the points to the spline
    for i,p in enumerate(points):
        if i!=0: line.points.add(1)
        line.points[i].co = p.to_4d()

    # Set the visuals
    curve_data.bevel_depth = w
    curve_data.bevel_resolution = res
    curve_data.fill_mode = "FULL" #'FULL', 'HALF', 'FRONT', 'BACK'
    return curve_data