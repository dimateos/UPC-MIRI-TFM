from bpy import data as D
from bpy import context as C
from mathutils import *
from math import *
import bpy
import bpy.types as types
import bpy.props as props

def printEnv():
    import sys, os
    print("* sys -v: ", sys.version_info)
    # print("* sys path: ", sys.path)
    print("* .exe: ", sys.executable)
    print("* .cwd: ", os.getcwd())
    print(f"* _name: {__name__}")
    print(f"* _file: {__file__}")
    # print(f"* _path: {__path__}")

    print(f"* blender -v: {bpy.app.version_string}")
    print(f"* .blend path: {bpy.data.filepath}")

def fixLocalEnv():
    import sys, os
    dir = os.path.dirname(__file__)
    if not dir in sys.path: sys.path.append(dir)

def desc(me: types.Mesh, i=0):
    v = me.vertices[i] if me.vertices else None
    e = me.edges[i] if me.edges else None
    f = me.polygons[i] if me.polygons else None
    l = me.loops[i] if me.loops else None
    return v,e,f,l

fixLocalEnv()
import importlib
#-------------------------------------------------------------------

from addonSim.stats import getStats, testStats
#importlib.reload(getStats.__module__)
stats = getStats()

from addonSim import info_mesh
importlib.reload(info_mesh)

def main():
    ob = bpy.context.active_object
    me = ob.data
    if me: v,e,f,l = desc(me)
    #print(ob.name)
    info_mesh.desc_mesh(me)

    #testStats()
    stats.reset()

    bench_meshMaps(me)

#-------------------------------------------------------------------

from addonSim import utils
importlib.reload(utils)
from addonSim import utils_geo
importlib.reload(utils_geo)

def bench_meshMaps(me):
    stats.reset()

    # query mesh props
    utils_geo.queryLogAll_mesh(me)
    stats.logFull("queries")
    print()

    # mesh maps prev implementation
    stats.reset()
    for n in range(100):
        ret = utils_geo.map_VtoF_EtoF_VtoE_prev(me)
    stats.logFull("maps prev")
    del ret

    # mesh maps
    stats.reset()
    for n in range(100):
        ret = utils_geo.map_VtoF_EtoF_VtoE(me)
    stats.logFull("maps")
    del ret


#-------------------------------------------------------------------
# When executed from vscode extension __name__ gets overwritten
# if __name__ == "__main__": runner(main)
#printEnv()
if __name__ in ["__main__", "<run_path>"]:
    print("\n-----------------------------------------------------------------------------------------")
    main()
    print("\n-----------------------------------------------------------------------------------------")