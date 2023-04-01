bl_info = {
    "name": "_dimateos MW_sim",
    "author": "dimateos",
    "version": (0, 1, 0),
    "blender": (2, 90, 0),
    "location": "View3D > Sidebar > Dev",
    "description": "Mechanical Withering Simulation",
    "warning": "_WIP_",
    "wiki_url": "https://github.com/dimateos/UPC-MIRI-TFM",
    "tracker_url": "",
    "support": "TESTING",
    "category": "Development",
}


# -------------------------------------------------------------------

import bpy

from . import properties
from . import operators
from . import panels

submodules = (
    #properties,
    #operators,
    panels,
)


# -------------------------------------------------------------------
# Blender events

def register():
    for m in submodules:
        m.register()

def unregister():
    for m in submodules[::-1]:
        m.unregister()

loaded = True
