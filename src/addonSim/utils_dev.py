# Avoiding imports for circular dependencies
#-------------------------------------------------------------------

# OPT:: a lot of room to do it
# IDEA:: some access from UI to toggle dynamically?
class DEV:
    HANDLE_GLOBAL_EXCEPT  = False   # more robust extension global error but harder to debug
    CALLBACK_REGISTER_ALL = False   # inspect when all available callbacks are triggered

    DEBUG_MODEL           = True    # fake 2D so ignore some directional links (at sim)
    DEBUG_COMPS           = False    # break links at the middle of the model to test comps (at link gen)

    ASSERT_CELL_POS       = True    # assert some local and global pos match
    LEGACY_CONT           = False   # check some stats of legacy cont
    VISUAL_TESTS          = True    # testing some visual props

    # IDEA:: profiling levels instead of just bool, or stats log uisng log_msg with tags
    logs = True
    logs_stats = True
    ui_vals = True

    # IDEA:: better list of sets to use combinations
    # OPT:: use list instead of set to preserve type order
    logs_type_skipped = {
        'NONE', #except when empty, parsed as dict?
        'UPDATE',
        'INIT', "PARSED"
        #'OP_FLOW',
        #'CALLBACK',
    }

    # IDEA:: separators per type?
    logs_type_sep = " :: "
    logs_stats_sep = "    - "

    logs_cutcol = 40
    logs_cutmsg = 110
    logs_cutpath = 30

    #-------------------------------------------------------------------

    @staticmethod
    def get_cutMsg(s, cutPos=logs_cutmsg):
        if len(s) > cutPos: return s[:cutPos-3]+"..."
        else: return s

    @staticmethod
    def get_justifiedMsg(s, justPos=logs_cutcol):
        if len(s) > justPos:
            return s[:justPos-4]+"...}"
        else:
            return s.ljust(justPos)

    #-------------------------------------------------------------------

    @staticmethod
    def log_msg(msg, msgType = {'DEV'}, msgStart=None, sep=logs_type_sep, cut=True):
        """ Log to console if DEV.logs and type not filtered by DEV.logs_type_skipped """
        if not DEV.logs: return
        if msgType & DEV.logs_type_skipped: return

        # use type as msg start ot not
        if not msgStart:
            msgStart = str(msgType)

        # justify into columns
        left = DEV.get_justifiedMsg(msgStart)
        full = f"{left}{sep}{msg}" if msg else left

        # limit full size
        if cut: full = DEV.get_cutMsg(full, DEV.logs_cutmsg)
        print(full)

        # keep the last msg?
        global log_msg_last
        log_msg_last = msg,msgType
    log_msg_last = "",{"NONE"}

    # OPT:: not much use
    @staticmethod
    def draw_val(ui, msg, value):
        """ Draw value with label if DEV.ui_vals is set """
        if not DEV.ui_vals: return
        ui.label(text=f"{msg}: {value}", icon="BLENDER")