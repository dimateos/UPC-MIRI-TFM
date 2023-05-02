import bpy
from bpy.app.handlers import persistent

from .utils_dev import DEV


#-------------------------------------------------------------------

@persistent
def callback_undo(scene):
    """ Undo called, including all the time in the edit last op panel """
    # Seems like there is no way to read info about the stack from python...
    last_op = bpy.ops.ed.undo_history()
    DEV.log_msg(f"{last_op}", {"CALLBACK", "UNDO"})

#-------------------------------------------------------------------
# Blender events

def register():
    bpy.app.handlers.undo_post.append(callback_undo)

def unregister():
    bpy.app.handlers.undo_post.remove(callback_undo)
