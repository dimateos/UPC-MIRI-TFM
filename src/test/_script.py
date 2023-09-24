import bpy
import bpy.types as types

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
    currentDir = os.path.dirname(__file__)
    if not currentDir in sys.path: sys.path.append(currentDir)
    moduleDir = os.path.abspath(currentDir + "/..")
    if not moduleDir in sys.path: sys.path.append(moduleDir)

def desc(me: types.Mesh, i=0):
    v = me.vertices[i] if me.vertices else None
    e = me.edges[i] if me.edges else None
    f = me.polygons[i] if me.polygons else None
    l = me.loops[i] if me.loops else None
    return v,e,f,l

fixLocalEnv()
import importlib
#-------------------------------------------------------------------

# default imports by blender
from bpy import data as D
from bpy import context as C
from mathutils import *
from math import *

from addonSim.stats import getStats, testStats
#importlib.reload(getStats.__module__)
stats = getStats()

from addonSim import info_mesh
importlib.reload(info_mesh)

from bench import *

def main():
    ob = bpy.context.active_object
    me = ob.data
    if me: v,e,f,l = desc(me)
    #print(ob.name)
    info_mesh.desc_mesh(me)

    #testStats()
    stats.reset()

    #bench_meshMaps(stats, me)
    #bench_meshMaps_FtoF(stats, me)

#-------------------------------------------------------------------
# When executed from vscode extension __name__ gets overwritten
#printEnv()
if __name__ in ["__main__", "<run_path>"]:
    print("\n-----------------------------------------------------------------------------------------")
    main()
    print("\n-----------------------------------------------------------------------------------------")