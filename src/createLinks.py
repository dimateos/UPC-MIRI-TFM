# from bpy import data as D
# from bpy import context as C
# from mathutils import *
# from math import *
print("\n-----------------------------------------------------------------------------------------")

import sys, os
print("* sys -v: ", sys.version_info)
# print("* sys path: ", sys.path)
print("* .exe: ", sys.executable)
print("* .cwd: ", os.getcwd())
print(f"* _name: {__name__}")
print(f"* _file: {__file__}")
# print(f"* _path: {__path__}")

import bpy
print(f"* blender -v: {bpy.app.version_string}")
print(f"* .blend path: {bpy.data.filepath}")

dir = os.path.dirname(__file__)
if not dir in sys.path: sys.path.append(dir)

import utils

if False:
    utils.envPrint()

    import bpy

    def createLinks():
        print("createLinks")

        # # Get the collection by name
        # collection_name = "MyCollection"
        # collection = bpy.data.collections[collection_name]

        # # Iterate through all the objects in the collection
        # for obj in collection.objects:
        #     # Perform some operation on the object
        #     obj.location = (0, 0, 0)  # Example: set object location to (0, 0, 0)


    # When executed from vscode extension __name__ gets overwritten
    # if __name__ == "__main__": runner(createLinks)
    print("\n---------------")
    createLinks()

