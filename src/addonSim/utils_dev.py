# Avoiding imports for circular dependencies
#-------------------------------------------------------------------

class DEV:
    HANDLE_GLOBAL_EXCEPT  = False   # more robust extension global error but harder to debug
    CALLBACK_REGISTER_ALL = False   # inspect when all available callbacks are triggered
    SELECT_ROOT_LOAD      = True    # try to select any root after reloading

    DEBUG_MODEL           = True    # fake 2D so ignore some directional links (at sim)
    DEBUG_UI              = True    # some additional debug UI
    DEBUG_LINKS_NEIGHS    = True    # add additional mesh connecting links to neighbours
    DEBUG_LINKS_GEODATA   = True    # add additional links info to geometry data to visualize in table
    DEBUG_LINKS_ID_RAW    = True    # keep IDs raw for better data but no 2D visualization
    DEBUG_LINKS_PICKS     = True    # include info about number of picks

    SKIP_SANITIZE         = False   # skip attempt to keep up with the UNDO/REDO etc system
    SKIP_RESISTANCE       = False   # skip weighting links prob with resistance
    SKIP_PATH_CHECK       = False   # skip checking if a path still exists before recalc all graphs

    FORCE_NEW_MATS        = False   # force regeneration of gradient images to avoid debugging confussion
    FORCE_FIELD_IMAGE     = False   # workaround blender bug with image just being black after redo without touching it -> reexecutes the op

    LEGACY_CONT_ASSERT    = False   # assert some local and global pos match
    LEGACY_CONT_GEN       = False   # check some stats of legacy cont

    # tiny util to setup flags in reload time and then execute only once
    RELOAD_FLAGS : dict[str,bool] = dict()
    @classmethod
    def RELOAD_FLAGS_check(cls,s):
        if cls.RELOAD_FLAGS[s]:
            cls.RELOAD_FLAGS[s] = False
            return True
        return False

    #-------------------------------------------------------------------

    # OPT:: generated string messages are being constructed anyway: slow? -> if type: log()
    logs             = True
    logs_stats_dt    = True
    logs_stats_total = True
    ui_vals          = True

    # OPT:: list as type to preserve order? anyway this logging class is just a WIP
    logs_type_skipped = {
        #"# NOTE:: parsed as set when empty?",
        "UPDATE",           # callback and scene graph update
        "CALLBACK",
        "INIT",             # addon reloading
        "PARSED",
        #"GLOBAL",           # global storage/selection
    }
    @classmethod
    def get_logs_type_skipped(cls):
        return ", ".join(cls.logs_type_skipped)
    @classmethod
    def set_logs_type_skipped(cls, filter:str):
        filter = filter.replace(" ","").upper()
        cls.logs_type_skipped = set(filter.split(","))

    # preference over skipped
    logs_type_whitelist = {
        "STATS",
        "OP_FLOW",
        #"SELECTION",
        #"PROXY",
    }
    @classmethod
    def get_logs_type_whitelist(cls):
        return ", ".join(cls.logs_type_whitelist)
    @classmethod
    def set_logs_type_whitelist(cls, filter:str):
        filter = filter.replace(" ","").upper()
        cls.logs_type_whitelist = set(filter.split(","))

    # general format for the message
    logs_type_sep  = " :: "
    logs_stats_sep = "    - "
    logs_cutcol  = 40
    logs_cutmsg  = 110
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
        if not msgType & DEV.logs_type_whitelist:
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

    @staticmethod
    def log_msg_sep(sep=logs_cutmsg):
        print("-"*sep)

    @staticmethod
    def draw_val(ui, msg, value):
        """ Draw value with label if DEV.ui_vals is set. Rarely used, also mixed blender ui code... """
        if not DEV.ui_vals: return
        ui.label(text=f"{msg}: {value}", icon="BLENDER")