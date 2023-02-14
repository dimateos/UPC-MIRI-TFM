def runner(f):
    envPrint()
    print("---------------\n")
    f()
    print("\n---------------")

def envPrint():
    import sys, os
    print("sys: ", sys.version_info)
    print("path: ", sys.executable)
    print("cwd: ", os.getcwd())
    print(f"name: {__name__}")

    import bpy
    print(f"blender: {bpy.app.version_string}")