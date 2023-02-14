from utils import *
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
runner(createLinks)