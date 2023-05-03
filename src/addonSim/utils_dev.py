# Avoiding imports for circular dependencies
#-------------------------------------------------------------------

class DEV:
    DEBUG = True
    HANDLE_GLOBAL_EXCEPT = False
    CALLBACK_REGISTER_ALL = False

    LEGACY_CONT = False
    """ Checking some stats of legacy cont (could also do for the regular one) """

    # IDEA:: some access from UI to toggle dynamically?
    # IDEA:: better list of sets to use combinations
    logs = True
    logs_skipped = {
        'NONE', #except when empty, parsed as dict?
        'UPDATE',
        'INIT', "PARSED"
        #'OP_FLOW',
        #'CALLBACK',
    }
    ui_vals = True

    # IDEA:: profiling levels instead of just bool, or stats log uisng log_msg with tags
    logs_stats = True

    assert_voro_posW = True


#-------------------------------------------------------------------

    # OPT:: use list instead of set to preserve type order
    @staticmethod
    def log_msg(msg, msgType = {'DEV'}, ui = None):
        """ Log to console if DEV.logs and type not filtered by DEV.logs_skipped """
        if not DEV.logs: return
        if msgType & DEV.logs_skipped: return

        print(msgType, msg)
        if ui: ui.report(msgType, msg)
        #ui.report({'INFO'}, "Operation successful!")
        #ui.report({'ERROR'}, "Operation failed!")

        global log_msg_last
        log_msg_last = msg,msgType

    log_msg_last = "",{"NONE"}

    @staticmethod
    def draw_val(ui, msg, value):
        """ Draw value with label if DEV.ui_vals is set """
        if not DEV.ui_vals: return
        ui.label(text=f"{msg}: {value}", icon="BLENDER")