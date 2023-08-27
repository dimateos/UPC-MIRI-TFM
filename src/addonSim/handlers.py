import bpy
from bpy.app.handlers import persistent

from .properties_utils import getProps_namesFiltered

from .utils_dev import DEV

# IDEA:: probably save_post to store some json for some sim

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

def registerAllHandlers():
    """ Check whenever they are called etc"""
    handler_names = getProps_namesFiltered(bpy.app.handlers, "-n_")
    DEV.log_msg(f"Registering {len(handler_names)}: {handler_names}", {"CALLBACK", "TEST-HANDLERS", "DEV"})

    for hn in handler_names:
        f = lambda scene: DEV.log_msg(f"handler: {hn}", {"CALLBACK", "TEST-HANDLERS", "DEV"})
        getattr(bpy.app.handlers, hn).append(f)

def unregisterAllHandlers():
    handler_names = getProps_namesFiltered(bpy.app.handlers, "-n_")
    DEV.log_msg(f"Unregistering {len(handler_names)}: {handler_names}", {"CALLBACK", "TEST-HANDLERS", "DEV"})
    for hn in handler_names: getattr(bpy.app.handlers, hn).clear()


#-------------------------------------------------------------------

@persistent
def callback_updatePost(scene=None):
    """ Called AFTER each scene update """
    DEV.log_msg(f"callback_updatePost: depsgraph_update_post", {"CALLBACK", "UPDATE"})
    global callback_selectionChange_current, callback_selectionChange_prev, callback_selectionChange_prev_valid

    # check change in selection
    if bpy.context.selected_objects != callback_selectionChange_current:
        # support prev selections check?
        callback_selectionChange_prev = callback_selectionChange_current
        if callback_selectionChange_current:
            callback_selectionChange_prev_valid = callback_selectionChange_current

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
def callback_undo(scene=None):
    """ Undo called, including all the time in the edit last op panel """
    # Seems like there is no way to read info about the stack from python...
    last_op = bpy.ops.ed.undo_history()
    DEV.log_msg(f"callback_undo: {last_op}", {"CALLBACK", "UNDO"})

    global callback_undo_actions
    for c in callback_undo_actions: c(scene, last_op)

callback_undo_actions = Actions()
""" Function actions to be called on callback undo: c(scene, last_op) """

#-------------------------------------------------------------------

@persistent
def callback_loadFile(scene=None):
    """ Post loaded a new file """
    name = bpy.data.filepath
    #import os
    #file_name = os.path.basename(blend_file_name)

    DEV.log_msg(f"callback_loadFile: {name}", {"CALLBACK", "LOAD"})

    global callback_loadFile_actions
    for c in callback_loadFile_actions: c(scene, name)

callback_loadFile_actions = Actions()
""" Function actions to be called on callback undo: c(scene, fileName) """


#-------------------------------------------------------------------
# Blender events
_name = f"{__name__[14:]}" #\t(...{__file__[-32:]})"

def register():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "REG"})
    if DEV.CALLBACK_REGISTER_ALL: registerAllHandlers()

    bpy.app.handlers.depsgraph_update_post.append(callback_updatePost)
    bpy.app.handlers.undo_post.append(callback_undo)
    bpy.app.handlers.load_post.append(callback_loadFile)

def unregister():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})

    bpy.app.handlers.depsgraph_update_post.remove(callback_updatePost)
    bpy.app.handlers.undo_post.remove(callback_undo)
    bpy.app.handlers.load_post.remove(callback_loadFile)

    if DEV.CALLBACK_REGISTER_ALL: unregisterAllHandlers()
    DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})