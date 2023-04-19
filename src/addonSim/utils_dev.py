# Avoiding imports for circular dependencies
# -------------------------------------------------------------------

# TODO: some access from UI to toggle dynamically?
class DEV:
    DEBUG = True

    logs = True
    logs_stats = True
    logs_skipped = [
        #{'OP_FLOW'}
    ]
    ui_vals = True

    assert_voro_posW = True

# -------------------------------------------------------------------

    @staticmethod
    def log_msg(msg, type = {'DEV'}, ui = None):
        """ Log to console if DEV.logs and type not filtered by DEV.logs_skipped """
        if not DEV.logs: return
        if type in DEV.logs_skipped: return

        print(type, msg)
        if ui: ui.report(type, msg)
        #ui.report({'INFO'}, "Operation successful!")
        #ui.report({'ERROR'}, "Operation failed!")

    @staticmethod
    def draw_val(ui, msg, value):
        """ Draw value with label if DEV.ui_vals is set """
        if not DEV.ui_vals: return
        ui.label(text=f"{msg}: {value}", icon="BLENDER")