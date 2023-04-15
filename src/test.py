from bpy import data as D
from bpy import context as C
from mathutils import *
from math import *
import bpy

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

    dir = os.path.dirname(__file__)
    if not dir in sys.path: sys.path.append(dir)

# -------------------------------------------------------------------


def main():
    def desc(i=0):
        # ob,me,v,e,f,l = desc()
        ob = bpy.context.active_object
        me = ob.data
        return ob, me, me.vertices[i],me.edges[i],me.polygons[i],me.loops[i]

    ob,me,v,e,f,l = desc()
    print(ob.name)




# -------------------------------------------------------------------

# When executed from vscode extension __name__ gets overwritten
# if __name__ == "__main__": runner(createLinks)
if __name__ in ["__main__", "<run_path>"]:
    print("\n-----------------------------------------------------------------------------------------")
    main()
    print("\n-----------------------------------------------------------------------------------------")