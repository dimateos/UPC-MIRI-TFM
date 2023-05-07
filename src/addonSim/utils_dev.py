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
    # OPT:: use list instead of set to preserve type order
    logs = True
    logs_type_skipped = {
        'NONE', #except when empty, parsed as dict?
        'UPDATE',
        'INIT', "PARSED"
        #'OP_FLOW',
        #'CALLBACK',
    }
    ui_vals = True

    logs_cutcol = 40
    logs_cutpath = 30
    logs_type_sep = ":: "

    # IDEA:: profiling levels instead of just bool, or stats log uisng log_msg with tags
    logs_stats = True
    logs_stats_sep = "   - "

    assert_voro_posW = True


#-------------------------------------------------------------------

    @staticmethod
    def log_justifyMsg(s):
        if len(s) > DEV.logs_cutcol:
            return s[:DEV.logs_cutcol-4]+"...}"
        else:
            return s.ljust(DEV.logs_cutcol)

    @staticmethod
    def log_msg(msg, msgType = {'DEV'}, ui = None):
        """ Log to console if DEV.logs and type not filtered by DEV.logs_type_skipped """
        if not DEV.logs: return
        if msgType & DEV.logs_type_skipped: return

        print(f"{DEV.log_justifyMsg(str(msgType))}{DEV.logs_type_sep}{msg}")

        # blender ui report?
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