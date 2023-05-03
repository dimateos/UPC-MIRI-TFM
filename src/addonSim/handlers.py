import bpy
from bpy.app.handlers import persistent

from .utils_dev import DEV

# OPT:: probably lists are unloaded on new files? @persistent is only for functions
#-------------------------------------------------------------------

class Actions(list):
    """ Extend a list with checks to avoid repetition """

    def appendCheck(self, c):
        if c not in self: self.append(c)
        else: DEV.log_msg(f"Append: {c} rep", {"CALLBACK", "ACTIONS", "ERROR"})

    def removeCheck(self, c):
        try: self.remove(c)
        except ValueError: DEV.log_msg(f"Remove: {c} not found", {"CALLBACK", "ACTIONS", "ERROR"})

#-------------------------------------------------------------------

@persistent
def callback_updatePost(scene):
    """ Called AFTER each scene update """
    DEV.log_msg(f"callback_updatePost: depsgraph_update_post", {"CALLBACK", "UPDATE"})

    # check change in selection
    global callback_selectionChange_current
    if bpy.context.selected_objects != callback_selectionChange_current:
        # support prev selections check?
        global callback_selectionChange_prev, callback_selectionChange_prev_valid
        callback_selectionChange_prev = callback_selectionChange_current
        if callback_selectionChange_current: callback_selectionChange_prev_valid = callback_selectionChange_current

        callback_selectionChange_current = bpy.context.selected_objects
        activeName = bpy.context.active_object.name if bpy.context.active_object else "None"
        selectedNames = [ s.name for s in callback_selectionChange_current ]
        DEV.log_msg(f"Selection change: (active: {activeName}) \t{selectedNames}", {"CALLBACK", "SELECTION"})

        global callback_selectionChange_actions
        for c in callback_selectionChange_actions: c(scene, callback_selectionChange_current)

callback_selectionChange_actions = Actions()
""" Function actions to be called on selection change: c(scene, last_op) """
callback_selectionChange_current = []
callback_selectionChange_prev = []
callback_selectionChange_prev_valid = []
#callback_updatePost_action = list()

#-------------------------------------------------------------------

@persistent
def callback_undo(scene):
    """ Undo called, including all the time in the edit last op panel """
    # Seems like there is no way to read info about the stack from python...
    last_op = bpy.ops.ed.undo_history()
    DEV.log_msg(f"{last_op}", {"CALLBACK", "UNDO"})

    global callback_undo_actions
    for c in callback_undo_actions: c(scene, last_op)

callback_undo_actions = Actions()
""" Function actions to be called on callback undo: c(scene, last_op) """


#-------------------------------------------------------------------
# Blender events

def register():
    bpy.app.handlers.depsgraph_update_post.append(callback_updatePost)
    bpy.app.handlers.undo_post.append(callback_undo)

def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(callback_updatePost)
    bpy.app.handlers.undo_post.remove(callback_undo)
