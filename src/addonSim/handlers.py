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

    def dispatch(self, params):
        for c in self: c(*params)

# dict of function because doing .clear is risky, other addons might try to remove callbacks too
_all_handlers = { # hacky way of ignoring all passed arguments while making the lambda referenced value show up
    hn : lambda s1=None,s2=None,s3=None, n=hn: DEV.log_msg(f"handler: {n}", {"CALLBACK", "TEST-HANDLERS", "DEV"})
    for hn in getProps_namesFiltered(bpy.app.handlers, "-n_")
}

def registerAllHandlers():
    """ Check whenever they are called etc"""
    global _all_handlers
    prev = DEV.logs_type_whitelist
    DEV.logs_type_whitelist = { "TEST-HANDLERS" } # get the log get in
    DEV.log_msg(f"Registering {len(_all_handlers)}", {"CALLBACK", "TEST-HANDLERS", "DEV"})

    for hn,fn in _all_handlers.items():
        fn(None)
        getattr(bpy.app.handlers, hn).append(fn)
    DEV.logs_type_whitelist = prev

def unregisterAllHandlers():
    global _all_handlers
    prev = DEV.logs_type_whitelist
    DEV.logs_type_whitelist = { "TEST-HANDLERS" } # get the log get in
    DEV.log_msg(f"Unregistering {len(_all_handlers)}", {"CALLBACK", "TEST-HANDLERS", "DEV"})

    for hn,fn in _all_handlers.items():
        try: getattr(bpy.app.handlers, hn).remove(fn)
        except ValueError: pass
    DEV.logs_type_whitelist = prev

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
        callback_selectionChange_actions.dispatch([scene, callback_selectionChange_current])

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
    DEV.log_msg(f"callback_UNDO: {last_op}", {"CALLBACK", "UNDO"})

    global callback_undo_actions
    callback_undo_actions.dispatch([scene, last_op])

callback_undo_actions = Actions()
""" Function actions to be called on callback undo: c(scene, last_op) """

@persistent
def callback_redo(scene=None):
    """ Redo called, similar problems like with undo """
    last_op = bpy.ops.ed.undo_history()
    DEV.log_msg(f"callback_REDO: {last_op}", {"CALLBACK", "REDO"})

    global callback_redo_actions
    callback_redo_actions.dispatch([scene, last_op])

callback_redo_actions = Actions()
""" Function actions to be called on callback redo: c(scene, last_op) """

#-------------------------------------------------------------------

@persistent
def callback_loadFile(scene=None):
    """ Post loaded a new file """
    name = bpy.data.filepath
    #import os
    #file_name = os.path.basename(blend_file_name)

    DEV.log_msg(f"callback_loadFile: {name}", {"CALLBACK", "LOAD"})

    global callback_loadFile_actions
    callback_loadFile_actions.dispatch([scene, name])

callback_loadFile_actions = Actions()
""" Function actions to be called on callback undo: c(scene, fileName) """


#-------------------------------------------------------------------
# Blender events
_name = f"{__name__[14:]}" #\t(...{__file__[-32:]})"

def register():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "REG"})
    if DEV.CALLBACK_REGISTER_ALL: registerAllHandlers()

    bpy.app.handlers.load_post.append(callback_loadFile)
    bpy.app.handlers.depsgraph_update_post.append(callback_updatePost)
    bpy.app.handlers.undo_post.append(callback_undo)
    bpy.app.handlers.redo_post.append(callback_redo)

def unregister():
    DEV.log_msg(f"{_name}", {"ADDON", "INIT", "UN-REG"})
    if DEV.CALLBACK_REGISTER_ALL: unregisterAllHandlers()

    bpy.app.handlers.load_post.remove(callback_loadFile)
    bpy.app.handlers.depsgraph_update_post.remove(callback_updatePost)
    bpy.app.handlers.undo_post.remove(callback_undo)
    bpy.app.handlers.redo_post.remove(callback_redo)


DEV.log_msg(f"{_name}", {"ADDON", "PARSED"})