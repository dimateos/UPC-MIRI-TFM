import bpy
import bpy.types as types
import bpy.props as props

from .utils_dev import DEV
from .stats import getStats


#-------------------------------------------------------------------

class Common_OT_StartRefres(types.Operator):

    #meta_refresh: props.BoolProperty(
    #    name="Refresh", description="Refresh once on click",
    #    default=False,
    #)
    #meta_auto_refresh: props.BoolProperty(
    #    name="Auto-Refresh", description="Automatic refresh",
    #    default=True,
    #)

    def __init__(self) -> None:
        super().__init__()

    #def invoke(self, context, event):
    #    """ Runs only once on operator call """
    #    DEV.log_msg("invoke", {'OP_FLOW'})

    #    # refresh at least once
    #    self.cfg.meta_refresh = True
    #    # avoid last stored operation overide
    #    self.cfg.meta_type = {"NONE"}

    #    return self.execute(context)


    def start_op(self, msg = ""):
        getStats().reset()
        #getStats().testStats()
        print()
        getStats().logMsg(f"START: {self.bl_label} ({self.bl_idname})")
        DEV.log_msg(msg, {'SETUP'})

    def end_op(self, msg = "", skip=False):
        DEV.log_msg(f"END: {msg}", {'OP_FLOW'})
        getStats().logT("finished execution")
        print()
        return {"FINISHED"} if not skip else {'PASS_THROUGH'}

    def end_op_error(self, msg = "", skip=False):
        self.report({'ERROR'}, f"Operation failed: {msg}")
        self.end_op(msg, skip)

#-------------------------------------------------------------------
