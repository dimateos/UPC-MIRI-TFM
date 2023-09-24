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

    #bench_meshMaps(me)
    bench_meshMaps_FtoF(me)

#-------------------------------------------------------------------

from addonSim import utils
importlib.reload(utils)
from addonSim import utils_geo
importlib.reload(utils_geo)

def bench_meshMaps(me):
    stats.reset()

    # query mesh props
    utils_geo.queryLogAll_mesh(me)
    stats.logFull("bench_meshMaps")
    print()
    nRep = 2
    n = 50
    delete = False

    ret1, ret2, ret3 = None, None, None
    for i in range(nRep):
        print()
        print(f"rep {i}")

        t = """ maps dict based """
        stats.reset()
        for n in range(n):
            ret1 = utils_geo.map_VtoF_EtoF_VtoE_dictBased(me)
        stats.logFull(t)
        if delete: del ret1

        t = """ maps general method """
        stats.reset()
        query = { "VtoF": True, "EtoF": True, "VtoE": True }
        for n in range(n):
            ret3 = utils_geo.get_meshDicts(me, queries_dict=query, queries_default=False)
        stats.logFull(t)
        if delete: del ret3

        t = """ maps pre-alloc list based """
        stats.reset()
        for n in range(n):
            ret2 = utils_geo.map_VtoF_EtoF_VtoE(me)
        stats.logFull(t)
        if delete: del ret2


    if not delete:
        t = """ assert equal results"""
        stats.reset()
        assert(ret2[0] == utils.listMap_dict(ret1[0]))
        assert(ret2[1] == utils.listMap_dict(ret1[1]))
        assert(ret2[2] == utils.listMap_dict(ret1[2]))
        assert(ret2[0] == ret3["VtoF"])
        assert(ret2[1] == ret3["EtoF"])
        assert(ret2[2] == ret3["VtoE"])
        stats.logFull(t)
    pass

def bench_meshMaps_FtoF(me):
    stats.reset()

    # query mesh props
    utils_geo.queryLogAll_mesh(me)
    stats.logFull("bench_meshMaps_FtoF")
    print()
    nRep = 2
    n = 50
    delete = False

    ret1, ret2 = None, None
    for i in range(nRep):
        print()
        print(f"rep {i}")

        t = """ maps general method """
        stats.reset()
        query = { "FtoF": True }
        for n in range(n):
            ret1 = utils_geo.get_meshDicts(me, queries_dict=query, queries_default=False)
        stats.logFull(t)
        if delete: del ret1

        t = """ maps specific method """
        stats.reset()
        for n in range(n):
            ret2 = utils_geo.map_FtoF(me)
        stats.logFull(t)
        if delete: del ret2

    if not delete:
        t = """ assert equal results"""
        stats.reset()
        assert(ret1["FtoF"] == ret2)
        stats.logFull(t)
    pass



#-------------------------------------------------------------------
# When executed from vscode extension __name__ gets overwritten
# if __name__ == "__main__": runner(main)
#printEnv()
if __name__ in ["__main__", "<run_path>"]:
    print("\n-----------------------------------------------------------------------------------------")
    main()
    print("\n-----------------------------------------------------------------------------------------")