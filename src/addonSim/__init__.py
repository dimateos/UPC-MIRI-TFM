bl_info = {
    "name": "_dimateos MW",
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

from . import handlers
from . import preferences
from . import properties
from . import operators
from . import panels

from .utils_dev import DEV
preferences.ADDON._bl_info = bl_info.copy()
preferences.ADDON._bl_name = __name__


#-------------------------------------------------------------------
# Blender events

submodules = [
    handlers,
    preferences,
    properties,
    operators,
    panels,
]
_name = f"{__name__}  (...{__file__[-DEV.logs_cutpath:]})"

def register():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "REG"})
    for m in submodules:
        m.register()
    DEV.log_msg(f"{_name}... complete", {"ADDON", "COMPLETE", "REG"})

def unregister():
    print("\n\n")
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})
    for m in reversed(submodules):
        m.unregister()
    DEV.log_msg(f"{_name}... complete", {"ADDON", "COMPLETE", "UN-REG"})


loaded = True
preferences.ADDON._bl_loaded = True
DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})
